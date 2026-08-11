from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Sequence
from zoneinfo import ZoneInfo

try:
    from scripts.expense_reclassification_preview import (
        COLUMN_NAMES,
        DATA_SHEET,
        EXPENSES_SHEET,
        HTTP_TIMEOUT_SECONDS,
        READONLY_SCOPE,
        SETTINGS_SHEET,
        SNAPSHOT_RANGES,
        SPREADSHEET_FIELDS,
        TIMEZONE,
        Operation,
        assign_stable_ids,
        canonical_json,
        category_data,
        is_service_operation,
        operation_text,
        parse_operations,
        raw_row,
        settings_expense_category_lists,
        sheet_block,
    )
except ModuleNotFoundError:
    from expense_reclassification_preview import (  # type: ignore[no-redef]
        COLUMN_NAMES,
        DATA_SHEET,
        EXPENSES_SHEET,
        HTTP_TIMEOUT_SECONDS,
        READONLY_SCOPE,
        SETTINGS_SHEET,
        SNAPSHOT_RANGES,
        SPREADSHEET_FIELDS,
        TIMEZONE,
        Operation,
        assign_stable_ids,
        canonical_json,
        category_data,
        is_service_operation,
        operation_text,
        parse_operations,
        raw_row,
        settings_expense_category_lists,
        sheet_block,
    )

READWRITE_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
MAPPING_SCHEMA = "expense-reclassification-preview/v1"
CONFIRMATION_PREFIX = "APPLY_EXPENSE_RECLASSIFICATION_SHA256:"
CATEGORY_COLUMN_INDEX = 2
EXPECTED_RAW_COLUMNS = frozenset(COLUMN_NAMES)


class ApplyError(RuntimeError):
    pass


class WriteOutcome(Enum):
    NOT_DISPATCHED = False
    UNKNOWN = "unknown"
    CONFIRMED = True


class ApplyExecutionError(ApplyError):
    def __init__(
        self,
        message: str,
        write_outcome: WriteOutcome,
        writers_paused_acknowledged: bool,
    ) -> None:
        super().__init__(message)
        self.write_outcome = write_outcome
        self.writers_paused_acknowledged = writers_paused_acknowledged


@dataclass(frozen=True)
class BoundMapping:
    document: dict[str, Any]
    sha256: str


@dataclass(frozen=True)
class LiveCategories:
    regular: tuple[str, ...]
    events: tuple[str, ...]
    allowed: tuple[str, ...]


@dataclass(frozen=True)
class LiveSnapshot:
    operations: tuple[Operation, ...]
    categories: LiveCategories
    expense_sheet_id: int
    service_row_count: int


@dataclass(frozen=True)
class PlannedChange:
    report_number: int
    stable_id: str
    before: str
    after: str
    sheet_row: int
    expected_prewrite_raw: dict[str, Any]


@dataclass(frozen=True)
class PrewriteOperation:
    sheet_row: int
    raw: dict[str, Any]


@dataclass(frozen=True)
class ApplyPlan:
    mapping_sha256: str
    spreadsheet_id_sha256: str
    expense_sheet_id: int
    current_operation_count: int
    ignored_current_operation_count: int
    categories: LiveCategories
    prewrite_operations: tuple[PrewriteOperation, ...]
    changes: tuple[PlannedChange, ...]
    batch_update_body: dict[str, Any]


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def spreadsheet_id_sha256(spreadsheet_id: str) -> str:
    return hashlib.sha256(spreadsheet_id.encode("utf-8")).hexdigest()


def confirmation_token(mapping_sha256: str) -> str:
    return f"{CONFIRMATION_PREFIX}{mapping_sha256}"


def validate_mapping_binding(
    actual_sha256: str,
    expected_sha256: str | None,
    supplied_confirmation_token: str | None,
) -> None:
    if not expected_sha256 and not supplied_confirmation_token:
        raise ApplyError("Mapping binding is required: provide its SHA-256 or confirmation token")
    if expected_sha256 and expected_sha256.casefold() != actual_sha256:
        raise ApplyError("Mapping SHA-256 does not match the approved value")
    if supplied_confirmation_token and supplied_confirmation_token != confirmation_token(actual_sha256):
        raise ApplyError("Confirmation token does not bind the exact mapping file")


def load_bound_mapping(
    mapping_path: Path,
    expected_sha256: str | None,
    supplied_confirmation_token: str | None,
) -> BoundMapping:
    content = mapping_path.read_bytes()
    digest = sha256_bytes(content)
    validate_mapping_binding(digest, expected_sha256, supplied_confirmation_token)
    try:
        document = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ApplyError(f"Mapping is not valid UTF-8 JSON: {error}") from error
    if not isinstance(document, dict):
        raise ApplyError("Mapping root must be a JSON object")
    validate_mapping_structure(document)
    return BoundMapping(document, digest)


def validate_mapping_structure(mapping: dict[str, Any]) -> None:
    if mapping.get("schema_version") != MAPPING_SCHEMA:
        raise ApplyError(f"Unsupported mapping schema: {mapping.get('schema_version')!r}")
    operations = mapping.get("operations")
    audit = mapping.get("audit")
    snapshot = mapping.get("snapshot")
    if not isinstance(operations, list) or not isinstance(audit, dict) or not isinstance(snapshot, dict):
        raise ApplyError("Mapping must contain operations, audit, and snapshot objects")
    changed = [record for record in operations if record.get("changed") is True]
    unchanged = [record for record in operations if record.get("changed") is False]
    expected_counts = (
        ("total_operations", len(operations)),
        ("changed_count", len(changed)),
        ("unchanged_count", len(unchanged)),
    )
    for name, actual in expected_counts:
        if audit.get(name) != actual:
            raise ApplyError(f"Mapping audit {name} does not match its operations")
    report_numbers = [record.get("n") for record in changed]
    if any(not isinstance(number, int) or isinstance(number, bool) for number in report_numbers):
        raise ApplyError("Every changed mapping operation must have an integer report number")
    if sorted(report_numbers) != list(range(1, len(changed) + 1)):
        raise ApplyError("Changed-operation report numbers must be contiguous and unique")
    if any(record.get("n") is not None for record in unchanged):
        raise ApplyError("Unchanged mapping operations must have n=null")
    require_successful_preview_audits(audit)
    for record in changed:
        validate_changed_record(record)
    validate_changed_locator_groups(operations, changed)


def require_successful_preview_audits(audit: dict[str, Any]) -> None:
    for name in ("invariants", "artifact_validation"):
        checks = audit.get(name)
        if not isinstance(checks, dict) or not checks or not all(checks.values()):
            raise ApplyError(f"Approved mapping does not have a fully successful {name} audit")


def validate_changed_record(record: dict[str, Any]) -> None:
    before = record.get("before")
    after = record.get("after")
    raw = record.get("raw")
    locator = record.get("locator")
    if not isinstance(before, str) or not before or not isinstance(after, str) or not after or before == after:
        raise ApplyError("Every changed operation must have distinct non-empty before and after categories")
    if not isinstance(raw, dict) or frozenset(raw) != EXPECTED_RAW_COLUMNS:
        raise ApplyError(f"Changed operation N{record.get('n')} must contain raw A:L exactly")
    for row_kind in ("effective", "display"):
        row = record.get(row_kind)
        if not isinstance(row, dict) or frozenset(row) != EXPECTED_RAW_COLUMNS:
            raise ApplyError(
                f"Changed operation N{record.get('n')} must contain {row_kind} A:L exactly"
            )
    if canonical_json(raw.get("category")) != canonical_json({"stringValue": before}):
        raise ApplyError(f"Changed operation N{record.get('n')} raw category does not equal before")
    if not isinstance(locator, dict):
        raise ApplyError(f"Changed operation N{record.get('n')} has no locator")
    stable_id = locator.get("stable_id")
    expected_count = locator.get("expected_match_count")
    kind = locator.get("kind")
    if not isinstance(stable_id, str) or not stable_id:
        raise ApplyError(f"Changed operation N{record.get('n')} has no stable ID")
    if not isinstance(expected_count, int) or isinstance(expected_count, bool) or expected_count < 1:
        raise ApplyError(f"Changed operation N{record.get('n')} has invalid locator multiplicity")
    if kind == "telegram" and not stable_id.startswith("telegram:"):
        raise ApplyError(f"Changed operation N{record.get('n')} has inconsistent Telegram locator")
    if kind == "fingerprint" and stable_id != locator.get("fingerprint"):
        raise ApplyError(f"Changed operation N{record.get('n')} has inconsistent fingerprint locator")
    if kind not in ("telegram", "fingerprint"):
        raise ApplyError(f"Changed operation N{record.get('n')} has unsupported locator kind")


def validate_changed_locator_groups(
    all_records: Sequence[dict[str, Any]],
    changed_records: Sequence[dict[str, Any]],
) -> None:
    all_counts = Counter(record.get("locator", {}).get("stable_id") for record in all_records)
    for stable_id, records in group_records_by_stable_id(changed_records).items():
        expected_counts = {record["locator"]["expected_match_count"] for record in records}
        decisions = {
            (
                record["before"],
                record["after"],
                record.get("reason"),
                record.get("confidence"),
                record.get("rule"),
            )
            for record in records
        }
        if len(expected_counts) != 1 or expected_counts.pop() != len(records):
            raise ApplyError(f"Approved locator group {stable_id} has inconsistent multiplicity")
        if all_counts[stable_id] != len(records):
            raise ApplyError(f"Approved locator group {stable_id} also contains an untargeted operation")
        if len(decisions) != 1:
            raise ApplyError(f"Approved locator collision {stable_id} has different decisions")


def group_records_by_stable_id(
    records: Iterable[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[record["locator"]["stable_id"]].append(record)
    return dict(groups)


def parse_live_snapshot(response: dict[str, Any]) -> LiveSnapshot:
    expense_block = sheet_block(response, EXPENSES_SHEET, len(COLUMN_NAMES))
    settings_block = sheet_block(response, SETTINGS_SHEET, 8)
    data_block = sheet_block(response, DATA_SHEET, 8)
    source_operations = parse_operations(expense_block)
    service_rows = tuple(operation for operation in source_operations if is_service_operation(operation))
    operations = assign_stable_ids(
        tuple(operation for operation in source_operations if not is_service_operation(operation))
    )
    settings = settings_expense_category_lists(settings_block)
    data = category_data(data_block)
    categories = validate_settings_and_data_categories(settings, data)
    return LiveSnapshot(operations, categories, expense_block.sheet_id, len(service_rows))


def validate_settings_and_data_categories(
    settings: dict[str, Any],
    data: dict[str, Any],
) -> LiveCategories:
    regular = tuple(settings["regular"])
    events = tuple(settings["events"])
    allowed = tuple(settings["allowed"])
    if regular != tuple(data["regular"]):
        raise ApplyError("Settings regular expense categories drifted from *data")
    if events != tuple(data["events"]):
        raise ApplyError("Settings event expense categories drifted from *data")
    if allowed != tuple(data["allowed"]):
        raise ApplyError("Settings combined expense categories drifted from *data dropdown source")
    return LiveCategories(regular, events, allowed)


def validate_approved_categories(mapping: dict[str, Any], live: LiveCategories) -> None:
    approved = mapping.get("category_snapshot")
    if not isinstance(approved, dict):
        raise ApplyError("Mapping has no approved category snapshot")
    comparisons = (
        ("regular", approved.get("regular_categories"), live.regular),
        ("events", approved.get("event_categories"), live.events),
        ("allowed", approved.get("allowed_categories"), live.allowed),
        ("settings regular", approved.get("settings_regular_categories"), live.regular),
        ("settings events", approved.get("settings_event_categories"), live.events),
        ("settings allowed", approved.get("settings_categories"), live.allowed),
    )
    for label, approved_values, live_values in comparisons:
        if tuple(approved_values or ()) != live_values:
            raise ApplyError(f"Current {label} categories drifted from the approved mapping")
    allowed = set(live.allowed)
    missing_after = sorted(
        {record["after"] for record in mapping["operations"] if record.get("changed") is True} - allowed
    )
    if missing_after:
        raise ApplyError(f"Approved after categories are absent from the current dropdown: {missing_after}")


def validate_spreadsheet_identity(
    mapping: dict[str, Any],
    spreadsheet_id: str,
    live_expense_sheet_id: int,
) -> str:
    actual_hash = spreadsheet_id_sha256(spreadsheet_id)
    expected_hash = mapping.get("snapshot", {}).get("spreadsheet_id_sha256")
    if actual_hash != expected_hash:
        raise ApplyError("Current spreadsheet ID does not match the approved mapping")
    approved_sheet_id = mapping.get("snapshot", {}).get("sheet_ids", {}).get(EXPENSES_SHEET)
    if live_expense_sheet_id != approved_sheet_id:
        raise ApplyError("Current expense sheet ID does not match the approved mapping")
    return actual_hash


def current_operations_by_raw(
    operations: Sequence[Operation],
) -> dict[str, list[Operation]]:
    groups: dict[str, list[Operation]] = defaultdict(list)
    for operation in operations:
        groups[canonical_json(raw_row(operation))].append(operation)
    return dict(groups)


def match_approved_changes(
    mapping: dict[str, Any],
    current_operations: Sequence[Operation],
) -> tuple[PlannedChange, ...]:
    changed_records = [record for record in mapping["operations"] if record.get("changed") is True]
    approved_groups = group_records_by_stable_id(changed_records)
    current_by_raw = current_operations_by_raw(current_operations)
    changes: list[PlannedChange] = []
    used_rows: set[int] = set()
    for stable_id, records in approved_groups.items():
        kinds = {record["locator"]["kind"] for record in records}
        if kinds == {"telegram"}:
            matched = match_telegram_locator_group(stable_id, records, current_operations)
        elif kinds == {"fingerprint"}:
            matched = match_fingerprint_locator_group(stable_id, records, current_by_raw)
        else:
            raise ApplyError(f"Approved locator group {stable_id} mixes locator kinds")
        if any(change.sheet_row in used_rows for change in matched):
            raise ApplyError(f"Approved locator group {stable_id} overlaps another target group")
        used_rows.update(change.sheet_row for change in matched)
        changes.extend(matched)
    if len(changes) != len(changed_records):
        raise ApplyError("Not every approved changed operation was matched exactly once")
    rows = [change.sheet_row for change in changes]
    if len(rows) != len(set(rows)):
        raise ApplyError("Multiple approved changes resolved to the same current sheet row")
    return tuple(sorted(changes, key=lambda change: change.sheet_row))


def match_telegram_locator_group(
    stable_id: str,
    approved_records: Sequence[dict[str, Any]],
    current_operations: Sequence[Operation],
) -> list[PlannedChange]:
    expected_count = approved_records[0]["locator"]["expected_match_count"]
    telegram_id = approved_records[0]["locator"].get("telegram_message_id")
    matches = [
        operation
        for operation in current_operations
        if operation.telegram_message_id == telegram_id
    ]
    if expected_count != 1 or len(approved_records) != 1 or len(matches) != 1:
        raise ApplyError(
            f"Telegram locator {stable_id} must remain unique; got {len(matches)} current matches"
        )
    record = approved_records[0]
    operation = matches[0]
    validate_current_target(record, operation)
    return [planned_change(stable_id, record, operation)]


def match_fingerprint_locator_group(
    stable_id: str,
    approved_records: Sequence[dict[str, Any]],
    current_by_raw: dict[str, list[Operation]],
) -> list[PlannedChange]:
    expected_count = approved_records[0]["locator"]["expected_match_count"]
    if len(approved_records) != expected_count:
        raise ApplyError(f"Fingerprint locator {stable_id} has inconsistent approved multiplicity")
    approved_by_raw: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in approved_records:
        approved_by_raw[canonical_json(record["raw"])].append(record)
    changes = []
    for raw_key, records in approved_by_raw.items():
        current_matches = current_by_raw.get(raw_key, [])
        if len(current_matches) != len(records):
            raise ApplyError(
                f"Fingerprint locator {stable_id} raw A:L expected {len(records)} matches, "
                f"got {len(current_matches)}"
            )
        for record, operation in zip(
            sorted(records, key=lambda item: item["n"]),
            sorted(current_matches, key=lambda item: item.sheet_row),
        ):
            validate_current_target(record, operation)
            changes.append(planned_change(stable_id, record, operation))
    return changes


def planned_change(
    stable_id: str,
    record: dict[str, Any],
    operation: Operation,
) -> PlannedChange:
    return PlannedChange(
        report_number=record["n"],
        stable_id=stable_id,
        before=record["before"],
        after=record["after"],
        sheet_row=operation.sheet_row,
        expected_prewrite_raw=record["raw"],
    )


def validate_current_target(record: dict[str, Any], operation: Operation) -> None:
    if canonical_json(raw_row(operation)) != canonical_json(record["raw"]):
        raise ApplyError(f"Raw A:L drift detected for approved operation N{record['n']}")


def build_batch_update_body(
    expense_sheet_id: int,
    changes: Sequence[PlannedChange],
) -> dict[str, Any]:
    requests = [single_category_update(expense_sheet_id, change) for change in changes]
    return {"requests": requests, "includeSpreadsheetInResponse": False}


def single_category_update(expense_sheet_id: int, change: PlannedChange) -> dict[str, Any]:
    start_row_index = change.sheet_row - 1
    return {
        "updateCells": {
            "range": {
                "sheetId": expense_sheet_id,
                "startRowIndex": start_row_index,
                "endRowIndex": start_row_index + 1,
                "startColumnIndex": CATEGORY_COLUMN_INDEX,
                "endColumnIndex": CATEGORY_COLUMN_INDEX + 1,
            },
            "rows": [
                {
                    "values": [
                        {"userEnteredValue": {"stringValue": change.after}},
                    ]
                }
            ],
            "fields": "userEnteredValue",
        }
    }


def validate_batch_update_body(plan: ApplyPlan) -> None:
    requests = plan.batch_update_body.get("requests")
    if not isinstance(requests, list) or len(requests) != len(plan.changes):
        raise ApplyError("Batch body request count does not match the validated changes")
    if plan.batch_update_body != build_batch_update_body(plan.expense_sheet_id, plan.changes):
        raise ApplyError("Batch body contains fields outside the validated category updates")


def prepare_apply_plan(
    bound_mapping: BoundMapping,
    spreadsheet_id: str,
    live: LiveSnapshot,
) -> ApplyPlan:
    approved_service_count = bound_mapping.document["audit"].get("service_row_count")
    if approved_service_count != live.service_row_count:
        raise ApplyError("Service-row count drifted from the approved mapping")
    identity_hash = validate_spreadsheet_identity(
        bound_mapping.document,
        spreadsheet_id,
        live.expense_sheet_id,
    )
    validate_approved_categories(bound_mapping.document, live.categories)
    changes = match_approved_changes(bound_mapping.document, live.operations)
    expected_count = bound_mapping.document["audit"]["changed_count"]
    if len(changes) != expected_count:
        raise ApplyError(f"Validated target count {len(changes)} does not equal approved count {expected_count}")
    body = build_batch_update_body(live.expense_sheet_id, changes)
    plan = ApplyPlan(
        mapping_sha256=bound_mapping.sha256,
        spreadsheet_id_sha256=identity_hash,
        expense_sheet_id=live.expense_sheet_id,
        current_operation_count=len(live.operations),
        ignored_current_operation_count=len(live.operations) - len(changes),
        categories=live.categories,
        prewrite_operations=tuple(
            PrewriteOperation(operation.sheet_row, raw_row(operation))
            for operation in sorted(live.operations, key=lambda item: item.sheet_row)
        ),
        changes=changes,
        batch_update_body=body,
    )
    validate_batch_update_body(plan)
    return plan


def changed_pair_counts(changes: Sequence[PlannedChange]) -> list[dict[str, Any]]:
    counts = Counter((change.before, change.after) for change in changes)
    return [
        {"before": before, "after": after, "count": count}
        for (before, after), count in sorted(counts.items())
    ]


def dry_run_report(plan: ApplyPlan) -> dict[str, Any]:
    rows = [change.sheet_row for change in plan.changes]
    return {
        "status": "validated_dry_run",
        "mapping_sha256": plan.mapping_sha256,
        "spreadsheet_id_sha256": plan.spreadsheet_id_sha256,
        "expense_sheet_id": plan.expense_sheet_id,
        "current_operation_count": plan.current_operation_count,
        "target_count": len(plan.changes),
        "request_count": len(plan.batch_update_body["requests"]),
        "ignored_current_operation_count": plan.ignored_current_operation_count,
        "target_row_min": min(rows, default=None),
        "target_row_max": max(rows, default=None),
        "updated_column_index": CATEGORY_COLUMN_INDEX,
        "update_fields": "userEnteredValue",
        "pair_counts": changed_pair_counts(plan.changes),
        "writers_paused_acknowledged": False,
        "write_executed": False,
    }


def verify_applied_operations(
    plan: ApplyPlan,
    postwrite_operations: Sequence[Operation],
) -> None:
    by_row = {operation.sheet_row: operation for operation in postwrite_operations}
    if len(by_row) != len(postwrite_operations):
        raise ApplyError("Post-write snapshot contains duplicate sheet-row references")
    prewrite_by_row = {operation.sheet_row: operation for operation in plan.prewrite_operations}
    if set(by_row) != set(prewrite_by_row):
        raise ApplyError("Operation rows changed between pre-write and post-write snapshots")
    changes_by_row = {change.sheet_row: change for change in plan.changes}
    for sheet_row, prewrite in prewrite_by_row.items():
        operation = by_row[sheet_row]
        change = changes_by_row.get(sheet_row)
        if change is None:
            if canonical_json(raw_row(operation)) != canonical_json(prewrite.raw):
                raise ApplyError(f"Untargeted operation changed at sheet row {sheet_row}")
            continue
        verify_applied_change(change, operation)


def verify_applied_change(change: PlannedChange, operation: Operation) -> None:
    if operation.sheet_row != change.sheet_row:
        raise ApplyError(f"Post-write target row disappeared for N{change.report_number}")
    actual_raw = raw_row(operation)
    validate_postwrite_non_category_raw(change, actual_raw)
    expected_category = {"stringValue": change.after}
    if canonical_json(actual_raw["category"]) != canonical_json(expected_category):
        raise ApplyError(f"Post-write category verification failed for N{change.report_number}")
    if operation_text(operation, CATEGORY_COLUMN_INDEX) != change.after:
        raise ApplyError(f"Post-write effective category verification failed for N{change.report_number}")


def validate_postwrite_non_category_raw(
    change: PlannedChange,
    actual_raw: dict[str, Any],
) -> None:
    for column in COLUMN_NAMES:
        if column == "category":
            continue
        if canonical_json(actual_raw[column]) != canonical_json(change.expected_prewrite_raw[column]):
            raise ApplyError(
                f"Post-write drift outside category column for N{change.report_number}, field {column}"
            )


def verify_applied_snapshot(
    plan: ApplyPlan,
    mapping: dict[str, Any],
    spreadsheet_id: str,
    response: dict[str, Any],
) -> dict[str, Any]:
    live = parse_live_snapshot(response)
    validate_spreadsheet_identity(mapping, spreadsheet_id, live.expense_sheet_id)
    validate_approved_categories(mapping, live.categories)
    if live.categories != plan.categories:
        raise ApplyError("Expense categories changed between pre-write and post-write snapshots")
    verify_applied_operations(plan, live.operations)
    return {
        "status": "applied_and_verified",
        "write_executed": True,
        "mapping_sha256": plan.mapping_sha256,
        "verified_count": len(plan.changes),
        "prewrite_operation_count": len(plan.prewrite_operations),
        "all_prewrite_raw_rows_verified": True,
        "pair_counts": changed_pair_counts(plan.changes),
        "non_category_columns_verified": [
            column for column in COLUMN_NAMES if column != "category"
        ],
    }


def oauth_scope_for_mode(apply: bool) -> str:
    return READWRITE_SCOPE if apply else READONLY_SCOPE


def build_sheets_service(credentials_path: Path, scope: str) -> Any:
    import httplib2
    from google_auth_httplib2 import AuthorizedHttp
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    credentials = Credentials.from_service_account_file(str(credentials_path), scopes=[scope])
    authorized_http = AuthorizedHttp(credentials, http=httplib2.Http(timeout=HTTP_TIMEOUT_SECONDS))
    return build("sheets", "v4", http=authorized_http, cache_discovery=False)


def fetch_live_response(service: Any, spreadsheet_id: str) -> dict[str, Any]:
    request = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        ranges=list(SNAPSHOT_RANGES),
        includeGridData=True,
        fields=SPREADSHEET_FIELDS,
    )
    return request.execute(num_retries=1)


def create_batch_update_request(
    service: Any,
    spreadsheet_id: str,
    body: dict[str, Any],
) -> Any:
    return service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body)


def dispatch_batch_update(request: Any) -> dict[str, Any]:
    return request.execute(num_retries=0)


def validate_batch_update_response(
    response: dict[str, Any],
    spreadsheet_id: str,
    expected_request_count: int,
) -> None:
    if response.get("spreadsheetId") != spreadsheet_id:
        raise ApplyError("batchUpdate response has an unexpected spreadsheet ID")
    replies = response.get("replies")
    if not isinstance(replies, list) or len(replies) != expected_request_count:
        raise ApplyError("batchUpdate response count does not match the submitted requests")


def execute_apply_workflow(
    service: Any,
    spreadsheet_id: str,
    plan: ApplyPlan,
    mapping: dict[str, Any],
    report_path: Path,
    started_at: str,
) -> dict[str, Any]:
    try:
        request = create_batch_update_request(service, spreadsheet_id, plan.batch_update_body)
    except Exception as error:
        raise ApplyExecutionError(
            f"batchUpdate request was not dispatched: {error}",
            WriteOutcome.NOT_DISPATCHED,
            True,
        ) from error
    try:
        batch_response = dispatch_batch_update(request)
        validate_batch_update_response(batch_response, spreadsheet_id, len(plan.changes))
    except Exception as error:
        raise ApplyExecutionError(
            f"batchUpdate dispatch outcome is not confirmed: {error}",
            WriteOutcome.UNKNOWN,
            True,
        ) from error
    try:
        verification_response = fetch_live_response(service, spreadsheet_id)
        report = verify_applied_snapshot(plan, mapping, spreadsheet_id, verification_response)
        report.update(
            started_at=started_at,
            finished_at=datetime.now(ZoneInfo(TIMEZONE)).isoformat(),
            batch_request_count=len(plan.changes),
            batch_response_count=len(batch_response["replies"]),
            writers_paused_acknowledged=True,
            write_executed=True,
        )
        written_report_path = write_apply_report(report_path, report)
        report["report_path"] = str(written_report_path)
        return report
    except Exception as error:
        raise ApplyExecutionError(
            f"Write was confirmed but post-write verification failed: {error}",
            WriteOutcome.CONFIRMED,
            True,
        ) from error


def write_apply_report(path: Path, report: dict[str, Any]) -> Path:
    destination = path.resolve()
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, destination)
    return destination


def load_spreadsheet_id(env_name: str) -> str:
    import os

    value = os.getenv(env_name, "").strip()
    if not value:
        raise ApplyError(f"Missing required environment variable: {env_name}")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Safely validate or apply an approved expense reclassification mapping"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    binding = parser.add_mutually_exclusive_group(required=True)
    binding.add_argument("--mapping-sha256")
    binding.add_argument("--confirmation-token")
    parser.add_argument(
        "--writers-paused",
        action="store_true",
        help="Acknowledge that external expense writers are paused; required with --apply",
    )
    parser.add_argument(
        "--mapping",
        type=Path,
        default=Path("expense_reclassification_mapping.json"),
    )
    parser.add_argument("--spreadsheet-env", default="GOOGLE_SPREADSHEET_ID")
    parser.add_argument(
        "--credentials",
        type=Path,
        default=Path(".google_service_account_credentials.json"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("expense_reclassification_apply_report.json"),
    )
    return parser.parse_args()


def validate_mode_requirements(
    apply: bool,
    mapping_sha256: str | None,
    supplied_confirmation_token: str | None,
    writers_paused: bool,
) -> None:
    if not mapping_sha256 and not supplied_confirmation_token:
        raise ApplyError("A mapping SHA-256 or exact confirmation token is required")
    if not apply:
        return
    if mapping_sha256 or not supplied_confirmation_token:
        raise ApplyError("--apply requires the exact --confirmation-token; SHA-256 alone is rejected")
    if not writers_paused:
        raise ApplyError("--apply requires explicit --writers-paused acknowledgement")


def main() -> int:
    from dotenv import load_dotenv

    args = parse_args()
    try:
        validate_mode_requirements(
            args.apply,
            args.mapping_sha256,
            args.confirmation_token,
            args.writers_paused,
        )
        load_dotenv()
        started_at = datetime.now(ZoneInfo(TIMEZONE)).isoformat()
        bound_mapping = load_bound_mapping(
            args.mapping.resolve(),
            args.mapping_sha256,
            args.confirmation_token,
        )
        spreadsheet_id = load_spreadsheet_id(args.spreadsheet_env)
        service = build_sheets_service(
            args.credentials.resolve(),
            oauth_scope_for_mode(args.apply),
        )
        live = parse_live_snapshot(fetch_live_response(service, spreadsheet_id))
        plan = prepare_apply_plan(bound_mapping, spreadsheet_id, live)
        if args.dry_run:
            print(json.dumps(dry_run_report(plan), ensure_ascii=False, indent=2))
            return 0
        report = execute_apply_workflow(
            service,
            spreadsheet_id,
            plan,
            bound_mapping.document,
            args.report,
            started_at,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except ApplyExecutionError:
        raise
    except ApplyError as error:
        raise ApplyExecutionError(
            str(error),
            WriteOutcome.NOT_DISPATCHED,
            bool(args.writers_paused),
        ) from error


def aborted_report(error: ApplyExecutionError) -> dict[str, Any]:
    return {
        "status": "aborted",
        "reason": str(error),
        "writers_paused_acknowledged": error.writers_paused_acknowledged,
        "write_executed": error.write_outcome.value,
    }


def cli_main() -> int:
    try:
        return main()
    except ApplyExecutionError as error:
        print(json.dumps(aborted_report(error), ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(cli_main())
