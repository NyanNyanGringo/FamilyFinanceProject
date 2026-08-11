import copy
import hashlib
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.expense_reclassification_apply import (
    ApplyError,
    ApplyExecutionError,
    BoundMapping,
    LiveCategories,
    LiveSnapshot,
    READONLY_SCOPE,
    READWRITE_SCOPE,
    WriteOutcome,
    aborted_report,
    build_batch_update_body,
    confirmation_token,
    dry_run_report,
    execute_apply_workflow,
    match_approved_changes,
    oauth_scope_for_mode,
    prepare_apply_plan,
    validate_approved_categories,
    validate_batch_update_response,
    validate_mapping_binding,
    validate_mapping_structure,
    validate_mode_requirements,
    validate_settings_and_data_categories,
    verify_applied_operations,
)
from scripts.expense_reclassification_preview import (
    Decision,
    Operation,
    assign_stable_ids,
    operation_record,
    operation_row_hash,
)


SPREADSHEET_ID = "test-spreadsheet"
EXPENSE_SHEET_ID = 77
MAPPING_SHA256 = "a" * 64
AFTER = "Покупки в дом"


def cell(value=None):
    result = {}
    if value is not None:
        key = "numberValue" if isinstance(value, (int, float)) else "stringValue"
        result["userEnteredValue"] = {key: value}
        result["effectiveValue"] = {key: value}
        result["formattedValue"] = str(value)
    return result


def expense_operation(
    before="Покупки в Дом",
    comment="Ведро",
    *,
    row=7,
    telegram_id=None,
    amount=10,
):
    values = (
        45000,
        "month-formula",
        before,
        "Card",
        amount,
        "EUR",
        "Committed",
        amount,
        "EUR",
        comment,
        None,
        telegram_id,
    )
    cells = tuple(cell(value) for value in values)
    return Operation(row, cells, operation_row_hash(cells))


def identified(*operations):
    return assign_stable_ids(operations)


def changed_record(operation, number, after=AFTER):
    decision = Decision(after, "approved", "Высокая", "test-approved")
    return operation_record(operation, decision, number)


def live_categories(*, regular=(AFTER,), events=("Event",)):
    return LiveCategories(tuple(regular), tuple(events), tuple(regular) + tuple(events))


def mapping_document(records, categories=None):
    categories = categories or live_categories()
    changed = sum(record["changed"] is True for record in records)
    unchanged = len(records) - changed
    spreadsheet_hash = hashlib.sha256(SPREADSHEET_ID.encode("utf-8")).hexdigest()
    return {
        "schema_version": "expense-reclassification-preview/v1",
        "snapshot": {
            "spreadsheet_id_sha256": spreadsheet_hash,
            "sheet_ids": {"↙️Расходы": EXPENSE_SHEET_ID},
        },
        "category_snapshot": {
            "regular_categories": list(categories.regular),
            "event_categories": list(categories.events),
            "allowed_categories": list(categories.allowed),
            "settings_regular_categories": list(categories.regular),
            "settings_event_categories": list(categories.events),
            "settings_categories": list(categories.allowed),
        },
        "audit": {
            "total_operations": len(records),
            "changed_count": changed,
            "unchanged_count": unchanged,
            "service_row_count": 1,
            "invariants": {"test": True},
            "artifact_validation": {"test": True},
        },
        "operations": list(records),
    }


def prepared_single_target(*, approved_row=7, current_row=20):
    approved = identified(expense_operation(row=approved_row, telegram_id=123))[0]
    mapping = mapping_document((changed_record(approved, 1),))
    current = identified(expense_operation(row=current_row, telegram_id=123))[0]
    live = LiveSnapshot((current,), live_categories(), EXPENSE_SHEET_ID, 1)
    plan = prepare_apply_plan(BoundMapping(mapping, MAPPING_SHA256), SPREADSHEET_ID, live)
    return mapping, plan


class ExpenseReclassificationApplyTests(unittest.TestCase):
    def test_mapping_binding_requires_exact_hash_or_token(self):
        validate_mapping_binding(MAPPING_SHA256, MAPPING_SHA256, None)
        validate_mapping_binding(MAPPING_SHA256, None, confirmation_token(MAPPING_SHA256))

        with self.assertRaises(ApplyError):
            validate_mapping_binding(MAPPING_SHA256, None, None)
        with self.assertRaises(ApplyError):
            validate_mapping_binding(MAPPING_SHA256, "b" * 64, None)
        with self.assertRaises(ApplyError):
            validate_mapping_binding(MAPPING_SHA256, None, confirmation_token("b" * 64))

    def test_row_shift_resolves_by_stable_id_and_raw_not_snapshot_row(self):
        _, plan = prepared_single_target(approved_row=7, current_row=20)

        self.assertEqual(len(plan.changes), 1)
        self.assertEqual(plan.changes[0].sheet_row, 20)
        request_range = plan.batch_update_body["requests"][0]["updateCells"]["range"]
        self.assertEqual((request_range["startRowIndex"], request_range["endRowIndex"]), (19, 20))

    def test_duplicate_current_telegram_id_aborts(self):
        approved = identified(expense_operation(telegram_id=123))[0]
        mapping = mapping_document((changed_record(approved, 1),))
        current = identified(
            expense_operation(row=20, telegram_id=123),
            expense_operation(comment="Other", row=21, telegram_id=123),
        )

        with self.assertRaises(ApplyError):
            match_approved_changes(mapping, current)

    def test_fingerprint_collision_with_same_decision_matches_exact_group(self):
        approved = identified(
            expense_operation(row=7),
            expense_operation(row=8),
        )
        records = tuple(changed_record(operation, number) for number, operation in enumerate(approved, 1))
        mapping = mapping_document(records)
        validate_mapping_structure(mapping)
        current = identified(
            expense_operation(row=30),
            expense_operation(row=31),
        )

        changes = match_approved_changes(mapping, current)

        self.assertEqual([change.sheet_row for change in changes], [30, 31])
        self.assertEqual(len({change.stable_id for change in changes}), 1)

    def test_fingerprint_collision_with_different_decisions_aborts(self):
        approved = identified(
            expense_operation(row=7),
            expense_operation(row=8),
        )
        records = (
            changed_record(approved[0], 1),
            changed_record(approved[1], 2, after="Другое"),
        )

        with self.assertRaises(ApplyError):
            validate_mapping_structure(mapping_document(records))

    def test_unrelated_new_current_operation_is_ignored_and_not_targeted(self):
        approved = identified(expense_operation(telegram_id=123))[0]
        mapping = mapping_document((changed_record(approved, 1),))
        current = identified(
            expense_operation(row=20, telegram_id=999, comment="New operation"),
            expense_operation(row=21, telegram_id=123),
        )
        live = LiveSnapshot(current, live_categories(), EXPENSE_SHEET_ID, 1)

        plan = prepare_apply_plan(BoundMapping(mapping, MAPPING_SHA256), SPREADSHEET_ID, live)

        self.assertEqual(plan.ignored_current_operation_count, 1)
        self.assertEqual([change.sheet_row for change in plan.changes], [21])
        request_range = plan.batch_update_body["requests"][0]["updateCells"]["range"]
        self.assertEqual(request_range["startRowIndex"], 20)

    def test_full_raw_drift_aborts_even_when_unique_telegram_still_matches(self):
        approved = identified(expense_operation(telegram_id=123))[0]
        mapping = mapping_document((changed_record(approved, 1),))
        drifted = identified(expense_operation(row=20, telegram_id=123, comment="Changed"))[0]

        with self.assertRaises(ApplyError):
            match_approved_changes(mapping, (drifted,))

    def test_drift_aborts_before_batch_body_is_constructed(self):
        approved = identified(expense_operation(telegram_id=123))[0]
        mapping = mapping_document((changed_record(approved, 1),))
        drifted = identified(expense_operation(row=20, telegram_id=123, comment="Changed"))[0]
        live = LiveSnapshot((drifted,), live_categories(), EXPENSE_SHEET_ID, 1)

        with patch(
            "scripts.expense_reclassification_apply.build_batch_update_body"
        ) as body_builder:
            with self.assertRaises(ApplyError):
                prepare_apply_plan(
                    BoundMapping(mapping, MAPPING_SHA256),
                    SPREADSHEET_ID,
                    live,
                )
            body_builder.assert_not_called()

    def test_unique_telegram_accepts_effective_and_display_drift_when_raw_is_exact(self):
        approved = identified(expense_operation(telegram_id=123))[0]
        mapping = mapping_document((changed_record(approved, 1),))
        current = identified(expense_operation(row=20, telegram_id=123))[0]

        drifted_cells = copy.deepcopy(current.cells)
        drifted_cells[7]["effectiveValue"] = {"numberValue": 999}
        drifted_cells[7]["formattedValue"] = "999.00"
        drifted = identified(
            Operation(20, drifted_cells, operation_row_hash(drifted_cells)),
        )[0]

        changes = match_approved_changes(mapping, (drifted,))

        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].sheet_row, 20)

    def test_raw_formula_or_value_drift_is_rejected_for_unique_telegram(self):
        approved = identified(expense_operation(telegram_id=123))[0]
        mapping = mapping_document((changed_record(approved, 1),))
        current = identified(expense_operation(row=20, telegram_id=123))[0]
        cases = ((1, {"stringValue": "changed-formula"}), (4, {"numberValue": 11}))
        for column_index, changed_raw in cases:
            with self.subTest(column_index=column_index):
                drifted_cells = copy.deepcopy(current.cells)
                drifted_cells[column_index]["userEnteredValue"] = changed_raw
                drifted = identified(
                    Operation(20, drifted_cells, operation_row_hash(drifted_cells)),
                )[0]
                with self.assertRaises(ApplyError):
                    match_approved_changes(mapping, (drifted,))

    def test_fingerprint_locator_uses_exact_raw_despite_effective_eur_drift(self):
        approved = identified(expense_operation())[0]
        mapping = mapping_document((changed_record(approved, 1),))
        current_cells = copy.deepcopy(expense_operation(row=20).cells)
        current_cells[7]["effectiveValue"] = {"numberValue": 999}
        current_cells[7]["formattedValue"] = "999.00"
        current = identified(
            Operation(20, current_cells, operation_row_hash(current_cells)),
        )[0]

        self.assertNotEqual(approved.stable_id, current.stable_id)
        changes = match_approved_changes(mapping, (current,))

        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].stable_id, approved.stable_id)
        self.assertEqual(changes[0].sheet_row, 20)

    def test_settings_and_data_category_drift_aborts(self):
        settings = {
            "regular": (AFTER,),
            "events": ("Event",),
            "allowed": (AFTER, "Event"),
        }
        data = {
            "regular": (AFTER, "Extra"),
            "events": ("Event",),
            "allowed": (AFTER, "Extra", "Event"),
        }

        with self.assertRaises(ApplyError):
            validate_settings_and_data_categories(settings, data)

    def test_current_categories_must_equal_approved_snapshot(self):
        approved = identified(expense_operation(telegram_id=123))[0]
        mapping = mapping_document((changed_record(approved, 1),))

        with self.assertRaises(ApplyError):
            validate_approved_categories(
                mapping,
                live_categories(regular=(AFTER, "Extra")),
            )

    def test_batch_body_has_only_one_cell_user_entered_value_updates(self):
        _, plan = prepared_single_target(current_row=20)
        body = build_batch_update_body(plan.expense_sheet_id, plan.changes)

        self.assertEqual(len(body["requests"]), 1)
        self.assertFalse(body["includeSpreadsheetInResponse"])
        update = body["requests"][0]["updateCells"]
        self.assertEqual(update["fields"], "userEnteredValue")
        self.assertEqual(
            update["range"],
            {
                "sheetId": EXPENSE_SHEET_ID,
                "startRowIndex": 19,
                "endRowIndex": 20,
                "startColumnIndex": 2,
                "endColumnIndex": 3,
            },
        )
        self.assertEqual(
            update["rows"],
            [{"values": [{"userEnteredValue": {"stringValue": AFTER}}]}],
        )

    def test_postwrite_verification_checks_category_and_all_other_raw_fields(self):
        _, plan = prepared_single_target(current_row=20)
        postwrite = identified(
            expense_operation(before=AFTER, row=20, telegram_id=123),
        )

        verify_applied_operations(plan, postwrite)

        drifted = identified(
            expense_operation(before=AFTER, row=20, telegram_id=123, amount=11),
        )
        with self.assertRaises(ApplyError):
            verify_applied_operations(plan, drifted)

    def test_postwrite_verification_checks_every_untargeted_prewrite_row(self):
        approved = identified(expense_operation(telegram_id=123))[0]
        mapping = mapping_document((changed_record(approved, 1),))
        prewrite = identified(
            expense_operation(row=20, telegram_id=123),
            expense_operation(row=21, telegram_id=999, comment="New but untargeted"),
        )
        plan = prepare_apply_plan(
            BoundMapping(mapping, MAPPING_SHA256),
            SPREADSHEET_ID,
            LiveSnapshot(prewrite, live_categories(), EXPENSE_SHEET_ID, 1),
        )
        valid_postwrite = identified(
            expense_operation(before=AFTER, row=20, telegram_id=123),
            expense_operation(row=21, telegram_id=999, comment="New but untargeted"),
        )

        verify_applied_operations(plan, valid_postwrite)

        drifted_postwrite = identified(
            expense_operation(before=AFTER, row=20, telegram_id=123),
            expense_operation(row=21, telegram_id=999, comment="Changed outside target"),
        )
        with self.assertRaises(ApplyError):
            verify_applied_operations(plan, drifted_postwrite)

    def test_batch_update_response_is_bound_to_sheet_and_request_count(self):
        validate_batch_update_response(
            {"spreadsheetId": SPREADSHEET_ID, "replies": [{}, {}]},
            SPREADSHEET_ID,
            2,
        )
        with self.assertRaises(ApplyError):
            validate_batch_update_response(
                {"spreadsheetId": "other", "replies": [{}, {}]},
                SPREADSHEET_ID,
                2,
            )
        with self.assertRaises(ApplyError):
            validate_batch_update_response(
                {"spreadsheetId": SPREADSHEET_ID, "replies": [{}]},
                SPREADSHEET_ID,
                2,
            )

    def test_dry_run_report_cannot_claim_a_write(self):
        _, plan = prepared_single_target(current_row=20)

        report = dry_run_report(plan)

        self.assertEqual(report["status"], "validated_dry_run")
        self.assertEqual(report["target_count"], 1)
        self.assertEqual(report["request_count"], 1)
        self.assertFalse(report["write_executed"])

    def test_only_explicit_apply_mode_uses_full_scope(self):
        self.assertEqual(oauth_scope_for_mode(False), READONLY_SCOPE)
        self.assertEqual(oauth_scope_for_mode(True), READWRITE_SCOPE)

    def test_pre_dispatch_failure_reports_write_false(self):
        error = ApplyExecutionError(
            "pre-dispatch validation failed",
            WriteOutcome.NOT_DISPATCHED,
            False,
        )

        report = aborted_report(error)

        self.assertIs(report["write_executed"], False)
        self.assertFalse(report["writers_paused_acknowledged"])

    def test_transport_failure_after_dispatch_reports_unknown(self):
        mapping, plan = prepared_single_target(current_row=20)
        with (
            patch(
                "scripts.expense_reclassification_apply.create_batch_update_request",
                return_value=object(),
            ),
            patch(
                "scripts.expense_reclassification_apply.dispatch_batch_update",
                side_effect=TimeoutError("timeout"),
            ),
        ):
            with self.assertRaises(ApplyExecutionError) as raised:
                execute_apply_workflow(
                    object(),
                    SPREADSHEET_ID,
                    plan,
                    mapping,
                    Path("unused.json"),
                    "started",
                )

        self.assertEqual(raised.exception.write_outcome, WriteOutcome.UNKNOWN)
        self.assertEqual(aborted_report(raised.exception)["write_executed"], "unknown")
        self.assertTrue(raised.exception.writers_paused_acknowledged)

    def test_request_construction_failure_remains_pre_dispatch_false(self):
        mapping, plan = prepared_single_target(current_row=20)
        with patch(
            "scripts.expense_reclassification_apply.create_batch_update_request",
            side_effect=ApplyError("request construction failed"),
        ):
            with self.assertRaises(ApplyExecutionError) as raised:
                execute_apply_workflow(
                    object(),
                    SPREADSHEET_ID,
                    plan,
                    mapping,
                    Path("unused.json"),
                    "started",
                )

        self.assertEqual(raised.exception.write_outcome, WriteOutcome.NOT_DISPATCHED)
        self.assertIs(aborted_report(raised.exception)["write_executed"], False)

    def test_postwrite_verification_failure_reports_write_true(self):
        mapping, plan = prepared_single_target(current_row=20)
        with (
            patch(
                "scripts.expense_reclassification_apply.create_batch_update_request",
                return_value=object(),
            ),
            patch(
                "scripts.expense_reclassification_apply.dispatch_batch_update",
                return_value={"spreadsheetId": SPREADSHEET_ID, "replies": [{}]},
            ),
            patch(
                "scripts.expense_reclassification_apply.fetch_live_response",
                return_value={},
            ),
            patch(
                "scripts.expense_reclassification_apply.verify_applied_snapshot",
                side_effect=ApplyError("verification drift"),
            ),
        ):
            with self.assertRaises(ApplyExecutionError) as raised:
                execute_apply_workflow(
                    object(),
                    SPREADSHEET_ID,
                    plan,
                    mapping,
                    Path("unused.json"),
                    "started",
                )

        self.assertEqual(raised.exception.write_outcome, WriteOutcome.CONFIRMED)
        self.assertIs(aborted_report(raised.exception)["write_executed"], True)

    def test_confirmed_response_success_reports_write_true_and_pause_ack(self):
        mapping, plan = prepared_single_target(current_row=20)
        verified = {"status": "applied_and_verified", "write_executed": True}
        with (
            patch(
                "scripts.expense_reclassification_apply.create_batch_update_request",
                return_value=object(),
            ),
            patch(
                "scripts.expense_reclassification_apply.dispatch_batch_update",
                return_value={"spreadsheetId": SPREADSHEET_ID, "replies": [{}]},
            ),
            patch(
                "scripts.expense_reclassification_apply.fetch_live_response",
                return_value={},
            ),
            patch(
                "scripts.expense_reclassification_apply.verify_applied_snapshot",
                return_value=verified,
            ),
            patch(
                "scripts.expense_reclassification_apply.write_apply_report",
                return_value=Path("report.json"),
            ),
        ):
            report = execute_apply_workflow(
                object(),
                SPREADSHEET_ID,
                plan,
                mapping,
                Path("unused.json"),
                "started",
            )

        self.assertIs(report["write_executed"], True)
        self.assertTrue(report["writers_paused_acknowledged"])

    def test_apply_rejects_mapping_sha_without_confirmation_token(self):
        with self.assertRaises(ApplyError):
            validate_mode_requirements(True, MAPPING_SHA256, None, True)

    def test_apply_requires_confirmation_token_and_writers_pause(self):
        token = confirmation_token(MAPPING_SHA256)
        with self.assertRaises(ApplyError):
            validate_mode_requirements(True, None, token, False)

        validate_mode_requirements(True, None, token, True)
        validate_mode_requirements(False, MAPPING_SHA256, None, False)


if __name__ == "__main__":
    unittest.main()
