from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence
from zoneinfo import ZoneInfo

READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
HTTP_TIMEOUT_SECONDS = 60
TIMEZONE = "Europe/Belgrade"
EXPENSES_SHEET = "↙️Расходы"
SETTINGS_SHEET = "⚙️Настройки"
DATA_SHEET = "*data"
EXPENSES_RANGE = f"'{EXPENSES_SHEET}'!A6:L"
SETTINGS_RANGE = f"'{SETTINGS_SHEET}'!A120:H220"
DATA_RANGE = f"'{DATA_SHEET}'!AD6:AK199"
SNAPSHOT_RANGES = (EXPENSES_RANGE, SETTINGS_RANGE, DATA_RANGE)
SPREADSHEET_FIELDS = "properties(title,locale,timeZone),sheets(properties(sheetId,title),data(startRow,startColumn,rowData(values(userEnteredValue,effectiveValue,formattedValue,dataValidation))))"
SERVICE_COMMENT = "Это строка шаблона. Не удалять."
SOURCE_COLUMNS = (0, 2, 3, 4, 6, 9, 10, 11)
COLUMN_NAMES = (
    "date",
    "month",
    "category",
    "account",
    "amount",
    "currency",
    "status",
    "amount_eur",
    "main_currency",
    "comment",
    "debtor",
    "telegram_message_id",
)
EXPECTED_OPERATION_COUNT = 3112
EXPECTED_REMOVED_CATEGORY_COUNT = 17
EXPECTED_REMOVED_ROW_COUNT = 1349
EXPECTED_EXISTING_EVENT_COUNT = 190
EXPECTED_NEW_EVENT_COUNT = 10
EXPECTED_FINAL_EVENT_COUNT = 200
HIGH = "Высокая"
MEDIUM = "Средняя"
REVIEW = "REVIEW"
PARKING_TOLL_CATEGORY = "Парковка и платная дорога"
SIMPLE_CATEGORY_MAP = {
    "Связь": "Мобильная связь и интернет",
    "Бассейн Логатор": "Развлечения",
    "Образование": "Образование и изучение языков",
    "Коммуналка Дом": "Коммуналка",
}
PERSONAL_CATEGORIES = frozenset(("Госпожа", "Господин"))
HOME_CATEGORIES = frozenset(("Покупки в Дом", "Покупки в дом"))
BEAUTY_SOURCES = PERSONAL_CATEGORIES | HOME_CATEGORIES | frozenset(("Здоровье", "Тренажерный зал", "Другое"))
SUBSCRIPTION_SERVICES = (
    ("chatgpt", r"chat\s*gpt|чат.*gpt|счет\s*gpt|чардж|джипит|чаджи"),
    ("claude", r"claude|cloude|anthropic|антропик|клауд|клоуд"),
    ("ticktick", r"tick.?tick|tic.?tic|тик.?\s*тик"),
    ("xiaomi", r"xiaomi|ксиом|ксиов|ксяом|сиом"),
    ("vdsina", r"vdsin|wd[-\s]?cina|вд\s*сина?"),
    ("magnific", r"magnifi|магниф"),
    ("higgsfield", r"higgs"),
    ("midjourney", r"midjourney"),
    ("telegram", r"telegram|телеграм"),
    ("yandex", r"яндекс плюс|яплюс|яндекс\.?музык|ямузык|яндекс[.\s-]*диск|я\s*диск|ядиск"),
    ("apple-cloud", r"apple|icloud|айклауд|i\s*cloud"),
    ("qobuz", r"qobuz"),
    ("journal", r"журнал"),
    ("kling", r"kling|клинг|клинок|клинк"),
    ("freepik", r"freepik"),
    ("adobe", r"adobe|photoshop|фотошоп"),
    ("sberprime", r"сбер\s*прайм|сберпрайм"),
    ("elevenlabs", r"elevenlabs"),
    ("sberbusiness", r"сбер\s*бизнес"),
    ("bank-card", r"плата за карту|оплата карты|оплата банка"),
)
SUBSCRIPTION_CONTEXT_ALIASES = (
    ("xiaomi", r"камер\w* к сеон\w*"),
    ("telegram", r"телега\s+премиум"),
    ("yandex", r"подписк\w*.*яндекс|яндекс.*подписк"),
    ("higgsfield", r"хиг+с\w*"),
)
USER_APPROVED_STABLE_OVERRIDES = {
    "fingerprint:v1:25142114002e7d228bff45774e513a3f3f1592764c36cdc250fd5785b9834614": (
        "Ремонт машины",
        "Пользователь явно подтвердил, что аккумулятор относится к ремонту машины",
    ),
    "telegram:4806": (
        "Покупки для Лунтинка",
        "Пользователь явно подтвердил категорию смешанной покупки для Лунтинка",
    ),
    "telegram:4782": (
        "Обслуживание машины",
        "Пользователь явно подтвердил категорию материалов для машины и дома",
    ),
    "fingerprint:v1:9b7ac34ef4e1aa940218bb6ab7b0341e6f822e58aa245480348303b40fc41e4e": (
        "Другое",
        "Пользователь явно подтвердил категорию операции с планшетом",
    ),
    "fingerprint:v1:1e294eda0f6a912a370b9f1c03b70c886f1f06b45dad1c50aa207eadd6237f54": (
        "Другое",
        "Пользователь явно подтвердил категорию операции с планшетом",
    ),
    "fingerprint:v1:9d01cbb44ff5cc6aef1d433ddf96041f08be3363ee6cefd644b46ca2577c46c7": (
        "Покупки для Лунтинка",
        "Пользователь явно подтвердил небольшую покупку для Лунтинка",
    ),
    "fingerprint:v1:0c579424c821a45b4099b8b24d8c22c6b9a92d13c65f86abb102aac196dd8177": (
        "Покупки для Лунтинка",
        "Пользователь явно подтвердил небольшую покупку для Лунтинка",
    ),
    "fingerprint:v1:221cc4f94acef8e6ef7282661db5ea27fc80edf98f9740dbb2d831ab0c83656e": (
        "Покупки для Лунтинка",
        "Пользователь явно подтвердил небольшую покупку для Лунтинка",
    ),
    "fingerprint:v1:a8abc3f5ad1f05d1c595ab514f17f1e525fed587f4f2e965d759ae19a7e0b0a8": (
        "Покупки для Лунтинка",
        "Пользователь явно подтвердил небольшую покупку для Лунтинка",
    ),
    "fingerprint:v1:cd8a72932574f5700ee05c426079d7198b72e333859cac98b6c2e6e196b7a2d6": (
        "Покупки для Лунтинка",
        "Пользователь явно подтвердил небольшую покупку для Лунтинка",
    ),
    "fingerprint:v1:a17b00f24244d5abb7ec35826621c35dd1570f98b458d6139a64a9af1aea9955": (
        "Покупки для Лунтинка",
        "Пользователь явно подтвердил небольшую покупку для Лунтинка",
    ),
    "fingerprint:v1:ca031acdc9c14175c8c793641730cc47b2a76479e5b03a916a6836352e9dfe67": (
        "Покупки для Лунтинка",
        "Пользователь явно подтвердил небольшую покупку для Лунтинка",
    ),
    "fingerprint:v1:8c857e664862fa631e291ce52e1d65a8c9102889fd0203fe7b42e2f23a5a3448": (
        "Покупки для Лунтинка",
        "Пользователь явно подтвердил небольшую покупку для Лунтинка",
    ),
    "fingerprint:v1:be4d83bd5e24fbdcf4386410446691c9282579276a561e632e752a8ca6af3144": (
        "Покупки для Лунтинка",
        "Пользователь явно подтвердил небольшую покупку для Лунтинка",
    ),
    "fingerprint:v1:122bf8fdbe795a1e51f1ac80b00fb443b52fc39033a1a5e649046cb660306412": (
        "Покупки для Лунтинка",
        "Пользователь явно подтвердил небольшую покупку для Лунтинка",
    ),
    "telegram:3895": (
        "Обслуживание машины",
        "Пользователь явно подтвердил категорию документов для управления машиной",
    ),
}


class PreviewError(RuntimeError):
    pass


@dataclass(frozen=True)
class GridBlock:
    title: str
    sheet_id: int
    start_row: int
    start_column: int
    rows: tuple[tuple[dict[str, Any], ...], ...]


@dataclass(frozen=True)
class Operation:
    sheet_row: int
    cells: tuple[dict[str, Any], ...]
    row_hash: str
    telegram_message_id: str | None = None
    stable_id: str | None = None
    match_count: int = 0


@dataclass(frozen=True)
class Decision:
    after: str
    reason: str
    confidence: str
    rule: str


@dataclass(frozen=True)
class RuleContext:
    operations: tuple[Operation, ...]
    allowed_categories: frozenset[str]
    event_categories: frozenset[str]
    subscription_counts: Counter[str]
    same_day_comments: dict[tuple[Any, str], tuple[str, ...]]


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def extended_value(cell: dict[str, Any], field: str) -> Any:
    value = cell.get(field, {})
    for key in ("stringValue", "numberValue", "boolValue", "formulaValue", "errorValue"):
        if key in value:
            return value[key]
    return None


def display_value(cell: dict[str, Any]) -> str:
    return str(cell.get("formattedValue", ""))


def effective_value(cell: dict[str, Any]) -> Any:
    return extended_value(cell, "effectiveValue")


def user_entered_value(cell: dict[str, Any]) -> Any:
    return extended_value(cell, "userEnteredValue")


def normalized_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def normalized_telegram_id(cell: dict[str, Any]) -> str | None:
    value = effective_value(cell)
    if value in (None, ""):
        value = display_value(cell)
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = normalized_text(value)
    return text or None


def padded_cells(row: Sequence[dict[str, Any]], width: int) -> tuple[dict[str, Any], ...]:
    cells = list(row[:width])
    return tuple(cells + [{} for _ in range(width - len(cells))])


def sheet_block(response: dict[str, Any], title: str, width: int) -> GridBlock:
    matches = [sheet for sheet in response.get("sheets", []) if sheet.get("properties", {}).get("title") == title]
    if len(matches) != 1:
        raise PreviewError(f"Expected exactly one sheet named {title!r}, got {len(matches)}")
    sheet = matches[0]
    blocks = sheet.get("data", [])
    if len(blocks) != 1:
        raise PreviewError(f"Expected exactly one grid block for {title!r}, got {len(blocks)}")
    data = blocks[0]
    rows = tuple(padded_cells(row.get("values", []), width) for row in data.get("rowData", []))
    properties = sheet["properties"]
    return GridBlock(title, properties["sheetId"], data.get("startRow", 0), data.get("startColumn", 0), rows)


def has_source_content(cells: Sequence[dict[str, Any]]) -> bool:
    return any(effective_value(cells[index]) not in (None, "") or display_value(cells[index]) for index in SOURCE_COLUMNS)


def operation_row_hash(cells: Sequence[dict[str, Any]]) -> str:
    return sha256_json([cell_snapshot(cell) for cell in cells])


def cell_snapshot(cell: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_entered": cell.get("userEnteredValue"),
        "effective": cell.get("effectiveValue"),
        "formatted": cell.get("formattedValue", ""),
        "data_validation": cell.get("dataValidation"),
    }


def parse_operations(block: GridBlock) -> tuple[Operation, ...]:
    operations = []
    for offset, cells in enumerate(block.rows[1:], start=1):
        if has_source_content(cells):
            operations.append(Operation(block.start_row + offset + 1, cells, operation_row_hash(cells)))
    return tuple(operations)


def operation_text(operation: Operation, index: int) -> str:
    value = effective_value(operation.cells[index])
    return normalized_text(value if value not in (None, "") else display_value(operation.cells[index]))


def is_service_operation(operation: Operation) -> bool:
    return (
        operation_text(operation, 9) == SERVICE_COMMENT
        and not operation_text(operation, 2)
        and not operation_text(operation, 3)
        and numeric_value(operation.cells[4]) == 0
        and operation_text(operation, 6) == "Committed"
    )


def numeric_value(cell: dict[str, Any]) -> float | None:
    value = effective_value(cell)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    try:
        return float(str(value).replace(" ", "").replace(",", "."))
    except (TypeError, ValueError):
        return None


def fingerprint_payload(operation: Operation) -> list[Any]:
    indexes = (0, 3, 4, 5, 2, 7, 6, 9, 10)
    return [effective_value(operation.cells[index]) for index in indexes]


def fingerprint_id(operation: Operation) -> str:
    return f"fingerprint:v1:{sha256_json(fingerprint_payload(operation))}"


def assign_stable_ids(operations: Sequence[Operation]) -> tuple[Operation, ...]:
    telegram_counts = Counter(normalized_telegram_id(item.cells[11]) for item in operations)
    provisional = [telegram_id_or_fingerprint(item, telegram_counts) for item in operations]
    stable_counts = Counter(provisional)
    return tuple(with_identity(item, stable_id, stable_counts[stable_id]) for item, stable_id in zip(operations, provisional))


def telegram_id_or_fingerprint(operation: Operation, counts: Counter[str | None]) -> str:
    telegram_id = normalized_telegram_id(operation.cells[11])
    if telegram_id and counts[telegram_id] == 1:
        return f"telegram:{telegram_id}"
    return fingerprint_id(operation)


def with_identity(operation: Operation, stable_id: str, match_count: int) -> Operation:
    telegram_id = normalized_telegram_id(operation.cells[11])
    return Operation(operation.sheet_row, operation.cells, operation.row_hash, telegram_id, stable_id, match_count)


def unique_nonempty(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def column_values(block: GridBlock, relative_column: int) -> tuple[str, ...]:
    return unique_nonempty(display_value(row[relative_column]).strip() for row in block.rows[1:])


def category_data(data_block: GridBlock) -> dict[str, Any]:
    regular = column_values(data_block, 0)
    events = column_values(data_block, 4)
    allowed_with_duplicates = tuple(display_value(row[7]).strip() for row in data_block.rows[1:] if display_value(row[7]).strip())
    return {
        "regular": regular,
        "events": events,
        "allowed": unique_nonempty(allowed_with_duplicates),
        "allowed_with_duplicates": allowed_with_duplicates,
        "duplicate_allowed": sorted(name for name, count in Counter(allowed_with_duplicates).items() if count > 1),
    }


def settings_expense_category_lists(block: GridBlock) -> dict[str, Any]:
    column_a = tuple(display_value(row[0]).strip() for row in block.rows)
    header_indexes = tuple(index for index, value in enumerate(column_a) if value.casefold() == "категории расходов")
    if len(header_indexes) != 2:
        raise PreviewError(f"Expected exactly two Settings expense-category headers, found {len(header_indexes)}")
    regular = contiguous_values_after_header(column_a, header_indexes[0])
    events = contiguous_values_after_header(column_a, header_indexes[1])
    if not regular or not events:
        raise PreviewError("Settings expense-category lists must both be non-empty")
    if len(regular) != len(set(regular)) or len(events) != len(set(events)):
        raise PreviewError("Settings expense-category lists contain duplicates")
    return {
        "regular": regular,
        "events": events,
        "allowed": regular + events,
        "header_sheet_rows": tuple(block.start_row + index + 1 for index in header_indexes),
        "lists_hash": sha256_json({"regular": regular, "events": events}),
    }


def contiguous_values_after_header(values: Sequence[str], header_index: int) -> tuple[str, ...]:
    collected = []
    for value in values[header_index + 1 :]:
        if not value:
            break
        collected.append(value)
    return tuple(collected)


def snapshot_hash(operations: Sequence[Operation]) -> str:
    return sha256_json([operation.row_hash for operation in operations])


def validation_rules(operations: Sequence[Operation]) -> list[dict[str, Any]]:
    rules = [operation.cells[2].get("dataValidation") for operation in operations]
    unique = {canonical_json(rule): rule for rule in rules if rule}
    return list(unique.values())


def normalized_comment(operation: Operation) -> str:
    return normalized_text(display_value(operation.cells[9])).casefold().replace("ё", "е")


def has_pattern(text: str, pattern: str) -> bool:
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def has_any_pattern(text: str, patterns: Sequence[str]) -> bool:
    return any(has_pattern(text, pattern) for pattern in patterns)


def make_decision(after: str, reason: str, confidence: str, rule: str) -> Decision:
    return Decision(after, reason, confidence, rule)


def unchanged_decision(before: str, reason: str = "Категория уже соответствует правилам") -> Decision:
    return make_decision(before, reason, HIGH, "unchanged")


def subscription_service(text: str, subscription_context: bool = False) -> str:
    for name, pattern in SUBSCRIPTION_SERVICES:
        if has_pattern(text, pattern):
            return name
    if subscription_context:
        for name, pattern in SUBSCRIPTION_CONTEXT_ALIASES:
            if has_pattern(text, pattern):
                return name
    words = re.findall(r"[a-zа-я0-9]+", text)
    return "other:" + "-".join(words[:4])


def is_subscription_candidate(before: str, text: str, service: str) -> bool:
    return before == "Подписки" or has_pattern(
        text,
        r"подписк|пописка|premium|премиум|журнал|на месяц|ежемес|telegram$|телеграм$|телега\s+премиум|яплюс|яндекс плюс|яндекс\.?музык|ямузык|яндекс[.\s-]*диск|я\s*диск|ядиск|higgs|хиг+с\w*|qobuz",
    )


def build_rule_context(operations: Sequence[Operation], categories: dict[str, Any]) -> RuleContext:
    services = []
    event_categories = frozenset(categories["events"])
    for item in operations:
        before = operation_text(item, 2)
        if before in event_categories:
            continue
        text = normalized_comment(item)
        subscription_context = is_subscription_candidate(before, text, "")
        service = subscription_service(text, subscription_context)
        if text and subscription_context:
            services.append(service)
    counts = Counter(services)
    same_day = build_same_day_comments(operations)
    return RuleContext(tuple(operations), frozenset(categories["allowed"]), frozenset(categories["events"]), counts, same_day)


def build_same_day_comments(operations: Sequence[Operation]) -> dict[tuple[Any, str], tuple[str, ...]]:
    grouped: dict[tuple[Any, str], list[str]] = {}
    for operation in operations:
        key = (effective_value(operation.cells[0]), operation_text(operation, 2))
        comment = normalized_comment(operation)
        if comment:
            grouped.setdefault(key, []).append(comment)
    return {key: tuple(dict.fromkeys(values)) for key, values in grouped.items()}


def approved_exception(operation: Operation) -> Decision | None:
    stable_override = user_approved_stable_override(operation)
    if stable_override:
        return stable_override
    before = operation_text(operation, 2)
    comment = normalized_comment(operation)
    telegram_id = operation.telegram_message_id
    if before == "Покупка Nissan Note 2013":
        return make_decision("Покупка Nissan Note E12 2013 2025", "Утвержденное переименование шести Nissan-операций", HIGH, "approved-nissan-event")
    if telegram_id == "6486" and before == "Госпожа" and has_pattern(comment, r"билет.*москв"):
        return make_decision("Россия Лиза 2026", "Утвержденный билет в Москву, ID 6486; дубль ID отсечен по комментарию", HIGH, "approved-moscow-event")
    if telegram_id == "5407" and before == "Господин" and "сюрприз" in comment:
        return make_decision("Предложение руки и сердца", "Утвержденный домик-сюрприз, ID 5407", HIGH, "approved-proposal-event")
    if is_approved_kiting(operation, before, comment):
        return make_decision("Египет 2024", "Утвержденный кайтинг 29.09.2024 на 225 EUR", HIGH, "approved-kiting-event")
    return approved_non_event_exception(operation, before)


def user_approved_stable_override(operation: Operation) -> Decision | None:
    override = USER_APPROVED_STABLE_OVERRIDES.get(str(operation.stable_id))
    if not override:
        return None
    after, reason = override
    return make_decision(after, reason, HIGH, "user-approved-stable-override")


def is_approved_kiting(operation: Operation, before: str, comment: str) -> bool:
    return (
        before in PERSONAL_CATEGORIES
        and effective_value(operation.cells[0]) == 45564
        and numeric_value(operation.cells[4]) == 225
        and operation_text(operation, 5) == "EUR"
        and "кайтинг" in comment
    )


def approved_non_event_exception(operation: Operation, before: str) -> Decision | None:
    telegram_id = operation.telegram_message_id
    if is_approved_glasses(operation, before):
        return make_decision("Одежда", "Утвержденные очки от 21.09.2024 на 26 240 RSD", HIGH, "approved-glasses")
    if telegram_id == "6524" and before == "Транспорт":
        return make_decision("Развлечения", "Утвержденные электровелосипеды, ID 6524", HIGH, "approved-electric-bikes")
    if telegram_id == "6827" and before == "Госпожа":
        return make_decision("Одежда", "H&M перед Москвой не является событием, ID 6827", HIGH, "approved-hm-clothing")
    if telegram_id == "4914" and before == "Покупки в Дом":
        return make_decision("Покупки в дом", "Растения из Нови-Сада не являются событием, ID 4914", HIGH, "approved-plants")
    if telegram_id == "6521" and before == "Развлечения":
        return unchanged_decision(before, "Электровелосипеды уже в верной категории, ID 6521")
    return None


def is_approved_glasses(operation: Operation, before: str) -> bool:
    return (
        before == "Госпожа"
        and effective_value(operation.cells[0]) == 45556
        and numeric_value(operation.cells[4]) == 26240
        and operation_text(operation, 5) == "RSD"
        and "очки" in normalized_comment(operation)
    )


def semantic_override(operation: Operation, context: RuleContext | None = None) -> Decision | None:
    before = operation_text(operation, 2)
    text = normalized_comment(operation)
    decision = specific_content_override(before, text, context)
    if decision:
        return decision
    if has_pattern(text, r"(^|\W)(парковк|паркинг)") and before != PARKING_TOLL_CATEGORY:
        return make_decision(PARKING_TOLL_CATEGORY, "В комментарии явно указана парковка или паркинг", HIGH, "semantic-parking")
    if "массаж" in text and before != "Развлечения":
        return make_decision("Развлечения", "Массаж по утвержденному правилу", HIGH, "semantic-massage")
    decision = lodging_override(before, text)
    if decision:
        return decision
    decision = psychology_override(before, text)
    if decision:
        return decision
    decision = residency_override(before, text)
    if decision:
        return decision
    decision = personal_subject_override(before, text, context)
    if decision:
        return decision
    decision = personal_care_or_health(before, text)
    if decision:
        return decision
    return valid_category_override(before, text)


def specific_content_override(before: str, text: str, context: RuleContext | None = None) -> Decision | None:
    if before == "Связь" and text == "коммунальные услуги":
        return make_decision("Коммуналка", "Явный комментарий о коммунальных услугах имеет приоритет над старой категорией", HIGH, "connection-utilities-exception")
    if before == "Здоровье" and has_pattern(text, r"крем\w* для здоровья|шампун\w* против перхот"):
        return unchanged_decision(before, "Комментарий явно описывает лечебное или медицинское назначение")
    if before in PERSONAL_CATEGORIES:
        return specific_personal_override(text)
    if before == "Покупки в Дом":
        return specific_old_home_purchase_override(text)
    if before == "Другое":
        return other_subject_override(text, context)
    return None


def specific_personal_override(text: str) -> Decision | None:
    if has_pattern(text, r"игров\w*.*батут.*день рождения"):
        return make_decision("Развлечения", "Явно оплачена игровая комната с батутами; день рождения не превращает расход в подарок или событие", HIGH, "personal-birthday-trampoline")
    if has_pattern(text, r"депозит.*(?:дн\w* рождения.*батут|батут.*дн\w* рождения)"):
        return make_decision("Развлечения", "Депозит надежно связан с серией игровой комнаты и батутов на день рождения", MEDIUM, "personal-birthday-trampoline-deposit")
    if has_pattern(text, r"книжк\w* психолог"):
        return make_decision("Хобби", "Это книга, а не сессия с психологом", HIGH, "personal-psychology-book")
    if has_pattern(text, r"расческ"):
        return make_decision("Уход за собой", "Расческа является предметом личного ухода; упоминание подаренных денег не меняет назначение", HIGH, "personal-hairbrush")
    if has_pattern(text, r"аптек") and has_pattern(text, r"отбеливател|средств\w* для лиц"):
        return make_decision("Уход за собой", "Конкретные товары для зубов и лица имеют приоритет над названием магазина", HIGH, "personal-pharmacy-care-items")
    if has_pattern(text, r"стельк\w*.*ортопед|ортопед.*стельк"):
        return make_decision("Здоровье", "Ортопедические стельки имеют медицинское назначение", HIGH, "personal-orthopedic-insoles")
    if has_pattern(text, r"стельк\w*.*для родител"):
        return make_decision("Одежда", "Стельки отнесены к одежде, но второй предмет не описан", REVIEW, "personal-mixed-insoles")
    return None


def specific_old_home_purchase_override(text: str) -> Decision | None:
    if has_pattern(text, r"цветн\w* карандаш"):
        return make_decision("Хобби", "Цветные карандаши являются материалом для творчества, а не цветами", MEDIUM, "home-colored-pencils")
    if has_pattern(text, r"листочк\w*.*цветн"):
        return make_decision("Покупки в дом", "Цветные листочки являются обычной канцелярской покупкой, а не цветами", HIGH, "home-colored-paper")
    if has_pattern(text, r"оливков\w* дерев|цветочк\w*.*олив|олив.*цветочк"):
        return make_decision("Покупки в дом", "Растения для дома не являются исходящим подарком", HIGH, "home-plants")
    if has_pattern(text, r"купил\w* лиз\w* прокладк|^прокладки(?:\W|$)|гигиен\w* прокладк") and not has_pattern(text, r"кабел"):
        return make_decision("Уход за собой", "Явно указаны гигиенические прокладки для Лизы", HIGH, "home-sanitary-pads")
    if has_pattern(text, r"прокладк\w* кабел|кабел\w*.*прокладк"):
        return make_decision("Покупки в дом", "Прокладка кабелей не является средством личного ухода; назначение работ нужно подтвердить", REVIEW, "home-cable-routing")
    if has_pattern(text, r"гель.*добровель.*лиз\w* для дома"):
        return make_decision("Покупки в дом", "Описание содержит неясные и, возможно, смешанные товары; предложена бытовая категория", REVIEW, "home-ambiguous-gel")
    if has_pattern(text, r"шампун\w*.*(?:какую-то|какую то).*фиговин"):
        return make_decision("Уход за собой", "Шампунь относится к личному уходу, второй товар не описан", REVIEW, "home-mixed-shampoo")
    if has_pattern(text, r"масло для тела.*антисеп|антисеп.*масло для тела"):
        return make_decision("Уход за собой", "Смешаны средство для тела и антисептик; предложен преобладающий личный уход", REVIEW, "home-mixed-body-care")
    if has_pattern(text, r"ватн\w* палоч.*помад|помад.*ватн\w* палоч"):
        return make_decision("Уход за собой", "Помада относится к личному уходу, а второй товар описан неясно", REVIEW, "home-mixed-pomade")
    if has_pattern(text, r"краск\w* для ус"):
        return make_decision("Уход за собой", "Краска для усов является товаром личного ухода", HIGH, "home-moustache-dye")
    if has_pattern(text, r"^кондей для лиз"):
        return make_decision("Уход за собой", "Вероятнее всего указан кондиционер для личного ухода, но сокращение неоднозначно", REVIEW, "home-ambiguous-conditioner")
    if has_pattern(text, r"половин\w*.*лекарств.*покупки в дом"):
        return make_decision("Здоровье", "Смешана лекарственная и бытовая части; предложено Здоровье по явной пометке в комментарии", REVIEW, "home-mixed-medicine")
    if has_pattern(text, r"^аптека$|аппарат.*давлен|таблетки для дома"):
        return make_decision("Здоровье", "Явно указаны аптека, лекарство или медицинский прибор", HIGH, "home-health")
    if has_pattern(text, r"батончик.*крем|косметик.*мыло.*дом|крем.*для дом|крем.*что-то для дом|шампунь.*покупки в дом|крем.*покупки в дом"):
        return make_decision("Уход за собой", "Смешаны личный уход и бытовая покупка; предложен преобладающий личный уход", REVIEW, "home-mixed-self-care")
    if has_pattern(text, r"бутылк|постельное белье|коробочк\w* под трус|полка под обув|полотенц\w*.*h&m|контейнер.*кондиционер для одеж"):
        return make_decision("Покупки в дом", "Конкретный бытовой предмет имеет приоритет над словом о магазине или хранении одежды", HIGH, "home-item-priority")
    mixed = r"свеч\w*.*миск.*собак|горш\w*.*светил|носк\w*.*(растен|горш)|ст[еи]льк\w*.*(?:шарик|мяч).*теннис|нож\w*.*какаш|йоршик.*штатив.*очк|вешалк.*носоч|д[еэ]йзик.*зубн.*товар|кубик.*йог.*губк.*носк|полотенц.*шапк.*резин"
    if has_pattern(text, mixed):
        return make_decision("Покупки в дом", "Смешанная покупка из нескольких предметных категорий; предложена преобладающая бытовая категория", REVIEW, "home-mixed-cart")
    return narrow_home_subject_override(text)


def narrow_home_subject_override(text: str) -> Decision | None:
    if has_pattern(text, r"носк\w*|носоч\w*|колгот\w*|тапоч\w*|тапк\w*|ателье"):
        return make_decision("Одежда", "Явно указаны одежда, обувь или ателье", HIGH, "home-clothing")
    sanitary_pad = r"^прокладк\w*$|гигиен\w* прокладк|прокладк\w* (?:женск|гигиен|ежедневн|для месяч|always)"
    if has_pattern(text, rf"sunscreen|тоник|масло для тела|{sanitary_pad}|средств\w* для волос|гел\w* для (волос|душа)|бегуд|мыть\w* письк|локситан.*масл|средств\w* для гигиен"):
        return make_decision("Уход за собой", "Явно указан товар личного ухода", HIGH, "home-self-care")
    if has_pattern(text, r"бегов\w* дорожк"):
        return make_decision("Крупные покупки и обучение", "Отдельно названная крупная цель; плановость нужно подтвердить", REVIEW, "home-large-goal")
    if has_pattern(text, r"лодк\w*|акварел|книг\w*|книжк\w*"):
        return make_decision("Хобби", "Творчество, книги или предмет для хобби", MEDIUM, "home-hobby")
    return None


def other_subject_override(text: str, context: RuleContext | None = None) -> Decision | None:
    rules = (
        (r"(^|\W)(yettel|мтс|билайн)(\W|$)", "Мобильная связь и интернет", "Явно указан оператор мобильной связи", HIGH, "other-mobile"),
        (r"розочк|роз\w* лиз|подарк\w* родител", "Подарки", "Явно указаны цветы или подарок", HIGH, "other-gift"),
        (r"карточка стрелка|метро мск", "Общественный транспорт", "Карта общественного транспорта или метро", HIGH, "other-public-transport"),
        (r"салют|фейерверк", "Развлечения", "Салют или фейерверк является развлечением", HIGH, "other-entertainment"),
        (r"zara|страдивариус|кроссовк", "Одежда", "Явно указаны одежда, обувь или магазин одежды", HIGH, "other-clothing"),
        (r"подписки vfx|оплата за банкинг|оплата карт", "Ежемесячные подписки", "Повторяющаяся подписка или банковское обслуживание", MEDIUM, "other-recurring-subscription"),
        (r"покупки.*макси", "Продукты", "Покупки в продуктовом магазине; должник не меняет предмет расхода", HIGH, "other-products"),
    )
    for pattern, after, reason, confidence, rule in rules:
        if has_pattern(text, pattern):
            return make_decision(after, reason, confidence, rule)
    if has_pattern(text, r"unreal engine"):
        return make_decision("Разовые подписки", "Цифровой сервис или приложение без надежной повторяющейся серии; назначение не описано", REVIEW, "other-unreal-engine")
    if has_pattern(text, r"^украшения[.!?]?$"):
        return make_decision("Покупки в дом", "Неясно, идет ли речь о декоре или украшениях; предложена бытовая категория", REVIEW, "other-ambiguous-decor")
    if has_pattern(text, r"планшет"):
        return make_decision("Крупные покупки и обучение", "Отдельно названный планшет; плановость нужно подтвердить", REVIEW, "other-large-tablet")
    if has_pattern(text, r"вайлдберрис|вайлдберис|вайлдбериз"):
        return make_decision("Покупки в дом", "Товар из маркетплейса не указан; предложена обычная покупка", REVIEW, "other-marketplace")
    if has_pattern(text, r"apple|icloud|айклауд"):
        service = subscription_service(text, subscription_context=True)
        count = context.subscription_counts[service] if context else 0
        if count > 1:
            return make_decision("Ежемесячные подписки", f"Apple/iCloud повторяется в истории ({count} операций)", MEDIUM, "other-apple-recurring")
        return make_decision("Разовые подписки", "Для Apple/iCloud не найдено надежного повторения", MEDIUM, "other-apple-single")
    return None


def lodging_override(before: str, text: str) -> Decision | None:
    pattern = r"(^|\W)(отел(?:ь|я|е|и|ю)|hotel|апартамент|гостевой дом|домик(?:а|е|и|у|ом|ов)?|ночев|проживан|квартир(?:а|ы|у|е|ой|ою))(\W|$)"
    sources = PERSONAL_CATEGORIES | frozenset(("Развлечения", "Другое"))
    if before in sources and has_pattern(text, pattern):
        return make_decision("Жилье вне дома и отели", "Обычное несобытийное жилье вне дома", HIGH, "semantic-lodging")
    return None


def psychology_override(before: str, text: str) -> Decision | None:
    if not has_pattern(text, r"психолог|психотерап"):
        return None
    if has_pattern(text, r"водительск.*прав"):
        return make_decision("ВНЖ ПМЖ", "Психолог для административной процедуры с водительскими правами", HIGH, "psychology-driving-documents")
    if has_pattern(text, r"вшэ|вебинар|курс|обучен"):
        return make_decision("Образование и изучение языков", "Психология указана как тема обучения, а не сессия", HIGH, "psychology-education")
    if before in PERSONAL_CATEGORIES | frozenset(("Здоровье", "Другое")) and before != "Психолог":
        return make_decision("Психолог", "Явно указана сессия с психологом", HIGH, "semantic-psychologist")
    return None


def residency_override(before: str, text: str) -> Decision | None:
    sources = PERSONAL_CATEGORIES | frozenset(("ИП", "Другое", "Печать документов"))
    pattern = r"(^|\W)(внж|пмж|биометр|боравак|боровак|личн.*документ|водительск\w* прав|замен\w* сербск\w* прав|смен\w* прав)"
    if before in sources and has_pattern(text, pattern):
        return make_decision("ВНЖ ПМЖ", "Личные административные документы или ВНЖ", HIGH, "semantic-residency")
    return None


def personal_subject_override(before: str, text: str, context: RuleContext | None = None) -> Decision | None:
    if before not in PERSONAL_CATEGORIES | HOME_CATEGORIES:
        return None
    flower = r"(^|\W)(роз(?:а|ы|у|е|ой|ами|очк\w*)|цвет(?:ок|ы|ов|ка|ки|ков|очк\w*))(\W|$)"
    if has_pattern(text, r"подар\w*|на день рождения|на др\b") or has_pattern(text, flower):
        return make_decision("Подарки", "Явно указан подарок или цветы для другого человека", HIGH, "semantic-gift")
    if has_pattern(text, r"гинеколог|мед\.? осмотр|ортопед\w* стельк"):
        return make_decision("Здоровье", "Явно указаны медосмотр, врач или ортопедическое изделие", HIGH, "semantic-personal-health")
    if has_pattern(text, r"(^|\W)кофе(\W|$)"):
        return make_decision("Продукты", "Кофе для употребления", HIGH, "semantic-personal-food")
    if has_pattern(text, r"кредит\w*|на год") and has_pattern(text, r"подписк|клинок|клинк|telegram|сбер прайм"):
        return make_decision("Разовые подписки", "Покупка кредитов или годовая оплата считается разовой", HIGH, "semantic-personal-one-off-subscription")
    if has_pattern(text, r"боулинг.*(еда|напитк)"):
        return make_decision("Развлечения", "Смешаны боулинг, еда и напитки; предложено преобладающее развлечение", REVIEW, "semantic-mixed-bowling")
    if "pool and beer" in text:
        return make_decision("Одежда", "Pool and beer распознано как искаженное Pull&Bear по контексту покупки и возврата", HIGH, "semantic-pull-and-bear")
    checks = (
        (r"(^|\W)(h&m|hm\b|zara|зар\w*|lime|mango|манго|oysho|ойшо|reserved|резерв\w*|bershka|берш\w*|massimo|массим\w*|pull&bear|trend island|woman.?s? secret|нью.?\s*йоркер|интерспорт|sportvision|спортвижн|тираново|эчин-дэм|одеж\w*|вещ\w*|костюм\w*|джинс\w*|куртк\w*|футболк\w*|рубашк\w*|толстов\w*|кофт\w*|трус\w*|бель\w*|кроссов\w*|кепк\w*|очк\w*|бут\w*|обув\w*|туфл\w*|штан\w*|шорт\w*|топик\w*|сумк\w*|легенс\w*|поло\b|стельк\w*|шнурок|аксессуар\w*|подштанник\w*|почтальник\w*)", "Одежда", "Явно указана одежда, обувь, аксесуар или магазин одежды", "semantic-clothing"),
        (r"(^|\W)(йог\w*|пилат\w*|pilates|тренажер\w*|фитнес\w*|курс\w* тренировок|абонемент.*зал)", "Тренажерный зал", "Плановый спорт или абонемент", "semantic-gym"),
        (r"(^|\W)(англий\w*|сербск\w*|японск\w*|с японского|репетитор\w* по речи|занят\w* по речи|сервис\w* речи|супервизор)", "Образование и изучение языков", "Явно указано занятие языком или речью", "semantic-language"),
        (r"(^|\W)(мтс|билайн|yettel|мобильн\w* связ|номер\w* телефон)", "Мобильная связь и интернет", "Мобильная связь или оплата номера", "semantic-personal-mobile"),
        (r"(^|\W)(спа\b|тир\b|боулинг|боблинг|бассейн)", "Развлечения", "СПА, тир, боулинг или бассейн являются развлечением", "semantic-entertainment"),
        (r"mac whisper|patreon.*nano banana|патрен\w*.*nano banana", "Разовые подписки", "Разовая покупка сервиса или цифрового продукта", "semantic-one-off-subscription"),
    )
    for pattern, after, reason, rule in checks:
        if has_pattern(text, pattern):
            return make_decision(after, reason, HIGH, rule)
    subscription = personal_subscription_override(text, context)
    if subscription:
        return subscription
    return personal_care_or_health(before, text)


def personal_subscription_override(text: str, context: RuleContext | None) -> Decision | None:
    signal = r"подписк|пописка|premium|журнал|яндекс плюс|яплюс|яндекс\.?музык|ямузык|яндекс[.\s-]*диск|я\s*диск|ядиск|apple|icloud|айклауд|higgsfield|qobuz|telegram$"
    if not has_pattern(text, signal):
        return None
    service = subscription_service(text, subscription_context=True)
    count = context.subscription_counts[service] if context else 0
    if count > 1 or has_pattern(text, r"на месяц|ежемес"):
        return make_decision("Ежемесячные подписки", f"Сервис повторяется в истории ({count} операций) или указан месяц", MEDIUM, "semantic-recurring-subscription")
    return make_decision("Разовые подписки", "Надежного повторения сервиса в истории нет; предложена разовая покупка", MEDIUM, "semantic-single-subscription")


def personal_care_or_health(before: str, text: str) -> Decision | None:
    beauty = r"(^|\W)(ногт|ногот|маникюр|педикюр|эпиляц|бров|ресниц|реснич|космет|сыворот|лосьон|масло для волос|мицел|брызгалк|стрижк|кератин|крем|маск.*лиц|уход.*кож|шампун|дезодорант|дезик)"
    if before in BEAUTY_SOURCES and has_pattern(text, beauty):
        return make_decision("Уход за собой", "Косметика, красота или личный уход", HIGH, "semantic-self-care")
    medical = r"(^|\W)(врач|аптек|лекарст|анализ|витамин|больниц|лечен|зуб|ортодонт)"
    if before in PERSONAL_CATEGORIES and has_pattern(text, medical):
        return make_decision("Здоровье", "Явно указаны медицина или лечение", HIGH, "semantic-health")
    return None


def valid_category_override(before: str, text: str) -> Decision | None:
    if before in ("Коммуналка", "Коммуналка Дом") and has_pattern(text, r"(^|\W)(yettel|a1|мтс|билайн|мобильн(?:ая|ого)|сотов(?:ая|ой)|номер телефона)\b"):
        return make_decision("Мобильная связь и интернет", "Мобильная связь была в коммуналке", HIGH, "semantic-mobile")
    if before == "Спорт" and "бассейн" in text:
        return make_decision("Развлечения", "Бассейн по утвержденному правилу", HIGH, "semantic-pool")
    if before == "Тренажерный зал" and has_pattern(text, r"батончик|протеин|вода|напиток"):
        return make_decision("Продукты", "Еда или напиток для употребления, а не оплата спорта", HIGH, "semantic-gym-food")
    if before == "Развлечения" and has_pattern(text, r"подписка на dj приложение"):
        return make_decision("Разовые подписки", "Разовая покупка DJ-приложения без повторяющейся серии", MEDIUM, "entertainment-dj-app")
    if before == "Развлечения" and has_pattern(text, r"подписка.*армфайт"):
        return make_decision("Разовые подписки", "Вероятнее всего это цифровая подписка, но возможна спортивная или развлекательная трактовка", REVIEW, "entertainment-armfight")
    if before == "Развлечения" and has_pattern(text, r"^килограмм лимонов|^продукты на пикник"):
        return make_decision("Продукты", "Конкретно указаны продукты питания; развлекательный контекст не меняет предмет расхода", HIGH, "entertainment-explicit-products")
    if before == "Развлечения" and has_pattern(text, r"покупка игры в steam"):
        return make_decision("Хобби", "Покупка игры в Steam согласована с предметной категорией других игр", MEDIUM, "entertainment-steam-game")
    return None


def classify_animal(operation: Operation, context: RuleContext) -> Decision:
    original_text = normalized_comment(operation)
    text = original_text
    if not original_text:
        text = " ".join(context.same_day_comments.get((effective_value(operation.cells[0]), "Животные"), ()))
    groups = animal_groups(text)
    if not groups:
        return make_decision("Корм для Лунтинка", "Нет достаточного описания; корм предложен как самый вероятный по истории", REVIEW, "animal-ambiguous")
    after = animal_preferred_group(groups)
    if len(groups) > 1:
        return make_decision(after, "Смешанная покупка для Лунтика; предложен преобладающий смысл", REVIEW, "animal-mixed")
    if not original_text:
        return make_decision(after, "Пустой комментарий; тип расхода определен по связанной операции того же дня", MEDIUM, "animal-same-day-context")
    return make_decision(after, "Тип расхода на Лунтика явно указан в комментарии", HIGH, "animal-subject")


def animal_groups(text: str) -> set[str]:
    groups = set()
    patterns = {
        "Корм для Лунтинка": r"корм|лаком|вкусня|бычий корень",
        "Покупки для Лунтинка": r"игруш|поводок|поводк|перенос|клетк|адресник|шейник|костюм|форм\w*|воротник|подушк|ножниц|пилочк|картон|покупк|подар",
        "Ветеринар для Лунтинка": r"ветерин|лекар|таблет|анализ|вакцин|привив|лечен|консульт|стерел|стерил|апоквел|опоквел|баровект|бравект|nextg(?:ard|uard)|некстг(?:ард|аурд)|fortiflora|фортифлора|милпразон|глист|капли|препарат",
        "Груминг для Лунтика": r"грум|когт|помы|помыв|почистил.*уш|спа для собак|шампун",
    }
    for name, pattern in patterns.items():
        if has_pattern(text, pattern):
            groups.add(name)
    return groups


def animal_preferred_group(groups: set[str]) -> str:
    order = ("Корм для Лунтинка", "Ветеринар для Лунтинка", "Груминг для Лунтика", "Покупки для Лунтинка")
    return next(name for name in order if name in groups)


def classify_car(operation: Operation) -> Decision:
    text = normalized_comment(operation)
    if has_pattern(text, r"платная дорога|платной дороги|^оплата дороги$"):
        return make_decision(PARKING_TOLL_CATEGORY, "Платная дорога входит в утвержденную объединенную категорию", HIGH, "car-toll-road")
    if has_pattern(text, r"вероятн\w*.*топлив.*обслуж|топлив.*или.*обслуж"):
        return make_decision("Обслуживание машины", "Комментарий сам указывает два возможных назначения: топливо или обслуживание", REVIEW, "car-mixed-fuel-service")
    if has_pattern(text, r"(бума[гж]|документ|разреш|доверен).*(лиз|заграниц|за границ)|(лиз|заграниц|за границ).*(бума[гж]|документ|разреш|доверен)"):
        return make_decision("ВНЖ ПМЖ", "Личные административные документы для управления машиной; точное место учета нужно подтвердить", REVIEW, "car-driving-documents")
    rules = (
        (r"страхов", "Страховка машины", "Страховка машины"),
        (r"(^|\W)(бензин|топлив|заправ)", "Бензин", "Топливо или заправка"),
        (r"слом|почин|прокол|электрик|печк|ремонт машины", "Ремонт машины", "Неожиданная поломка или ремонт"),
        (r"(^|\W)то(\W|$)|технич|(^|\W)шин\w*|мойк|масл|фильтр|колод|ремен|стекл|полир|лампоч|дворник|давлени|сход-развал|переобув|болт|клей|спрей|отражатель|тормозн\w* жидк|клипс|жидкост\w*.*(?:мыть|омыв).*стек|омыва", "Обслуживание машины", "Плановые работы, шины или расходники"),
        (r"ремонт", "Ремонт машины", "Неожиданный ремонт без признаков планового обслуживания"),
    )
    for pattern, after, reason in rules:
        if has_pattern(text, pattern):
            return make_decision(after, reason, HIGH, "car-subject")
    return make_decision("Обслуживание машины", "Из комментария нельзя надежно отличить плановую работу от неожиданной", REVIEW, "car-ambiguous")


def classify_transport(operation: Operation) -> Decision:
    text = normalized_comment(operation)
    if has_pattern(text, r"электровелосипед"):
        return make_decision("Развлечения", "Электровелосипеды по утвержденному правилу", HIGH, "transport-electric-bike")
    if has_pattern(text, r"заправ|бензин|топлив"):
        return make_decision("Бензин", "Заправка или топливо", HIGH, "transport-fuel")
    if has_pattern(text, r"платная дорога|платной дороги"):
        return make_decision(PARKING_TOLL_CATEGORY, "Платная дорога входит в утвержденную объединенную категорию", HIGH, "transport-toll-road")
    if "вонюч" in text:
        return make_decision("Обслуживание машины", "Небольшой расходник для машины", HIGH, "transport-car-consumable")
    confidence = REVIEW if not text or text == "туалет" else HIGH
    return make_decision("Общественный транспорт", "Такси, автобус, поезд или обычный транспорт; при неясности нужна проверка", confidence, "transport-public")


def classify_home(operation: Operation) -> Decision:
    text = normalized_comment(operation)
    if has_pattern(text, r"макбук|macbook|focal bathys|tissot|колонка маршал|xiaomi c500|камера xiaomi"):
        return make_decision("Крупные покупки и обучение", "Отдельная явно названная дорогая цель; плановость нужно подтвердить", REVIEW, "home-large-candidate")
    confidence = REVIEW if home_comment_is_ambiguous(text) or has_pattern(text, r"и в офис|для дома и офис") else HIGH
    reason = "Небольшая обычная покупка; пустой или смешанный комментарий помечен для проверки"
    return make_decision("Покупки в дом", reason, confidence, "home-small-purchase")


def home_comment_is_ambiguous(text: str) -> bool:
    if not text or text in ("?", "???"):
        return True
    status_only = r"^(?:upd.*(?:долг возвращен)?|семья должна.*(?:долг возвращен)?)$"
    shop_only = r"^(?:тему|пепко|pepco|лилли|lilli|ikea|икея|сенсей|щенчей|китайск\w*|китайский товар,? покупки в дом|покупки в дм|сделали заказ на тему,? покупки в дом|купили что-то (?:в кенгуре|для дома)|что-то|доставка|мастер|средства для стверчи|:0 мячик в китайском|done:3 китайский|done:3 резиночки и прочее|резиночки и прочее|паста|икеяdone: ножки для лизы, лампа)[.!?]?(?: upd.*)?$"
    return has_pattern(text, status_only) or has_pattern(text, shop_only)


def classify_office(operation: Operation) -> Decision:
    text = normalized_comment(operation)
    if has_pattern(text, r"кофе|продукт"):
        return make_decision("Продукты", "Продукты или кофе для употребления", HIGH, "office-food")
    if has_pattern(text, r"дом\w*.*офис|офис.*дом\w*"):
        return make_decision("Покупки в дом", "Смешанная покупка для дома и офиса; предложены обычные покупки", REVIEW, "office-mixed")
    if text == "домой":
        return make_decision("Покупки в дом", "Комментарий явно указывает на покупку домой", HIGH, "office-home-item")
    if text == "офис":
        return make_decision("Аренда офиса + коммуналка", "Краткий комментарий совпадает с серией аренды и содержания офиса", REVIEW, "office-premises-series")
    if has_pattern(text, r"оплата офиса|коммунал|офис и коммун|белые стены") or not text:
        confidence = REVIEW if not text else HIGH
        return make_decision("Аренда офиса + коммуналка", "Аренда, коммуналка или обслуживание офиса", confidence, "office-premises")
    return make_decision("Покупки в дом", "Небольшой предмет или оборудование для офиса", HIGH, "office-small-purchase")


def classify_ip(operation: Operation) -> Decision:
    text = normalized_comment(operation)
    account = operation_text(operation, 3).casefold().replace("ё", "е")
    if has_pattern(text, r"внж|пмж|биометр|боравак|боровак"):
        return make_decision("ВНЖ ПМЖ", "Личные документы или ВНЖ", HIGH, "ip-residency")
    if has_pattern(text, r"сбер|росс|декларац|первое полугодие|\b6%|\b1%") or "сбер" in account:
        confidence = MEDIUM if not text else HIGH
        return make_decision("ИП в России", "СберБизнес, российские налоги или декларация", confidence, "ip-russia")
    serbia = r"серб|пауш|паусал|(^|\W)апр(\W|$)|эконалог|эколог|бухгалт|извод|лист не по кредност"
    if has_pattern(text, serbia) or operation_text(operation, 5) == "RSD":
        confidence = MEDIUM if not text else HIGH
        return make_decision("ИП в Сербии", "Сербские налоги, паушал, APR или надежно повторяющаяся RSD-серия", confidence, "ip-serbia")
    return make_decision("ИП в России", "Недостаточно данных о юрисдикции; предложена Россия по исходной серии", REVIEW, "ip-ambiguous")


def classify_printing(operation: Operation, context: RuleContext) -> Decision:
    del context
    text = normalized_comment(operation)
    if has_pattern(text, r"внж|пмж|биометр|боравак|боровак|личн\w* документ"):
        return make_decision("ВНЖ ПМЖ", "Явно указана печать личных административных документов", HIGH, "printing-residency")
    if has_pattern(text, r"сбер|росс|декларац|российск\w* ип"):
        return make_decision("ИП в России", "Явно указана печать документов российского ИП", HIGH, "printing-russia")
    if has_pattern(text, r"серб|пауш|паусал|(^|\W)апр(\W|$)|эконалог|бухгалт"):
        return make_decision("ИП в Сербии", "Явно указана печать документов сербского ИП", HIGH, "printing-serbia")
    if has_pattern(text, r"офис|рабоч\w* документ"):
        return make_decision("Аренда офиса + коммуналка", "Явно указана офисная печать", HIGH, "printing-office")
    return make_decision("Другое", "Пользователь явно утвердил: печать без указанного назначения относится в Другое", HIGH, "printing-unspecified-approved")


def same_day_operations(operations: Sequence[Operation], date_value: Any, target: Operation) -> tuple[Operation, ...]:
    return tuple(item for item in operations if item is not target and effective_value(item.cells[0]) == date_value)


def classify_subscription(operation: Operation, context: RuleContext) -> Decision:
    text = normalized_comment(operation)
    service = subscription_service(text, subscription_context=True)
    count = context.subscription_counts[service]
    if has_pattern(text, r"курс.*эмоционал|вебинар|обучен"):
        return make_decision("Образование и изучение языков", "Это обучение, а не подписка", HIGH, "subscription-education")
    if service == "sberbusiness" or has_pattern(text, r"сбер\s*бизнес"):
        return make_decision("ИП в России", "СберБизнес является расходом российского ИП", HIGH, "subscription-business-russia")
    if has_pattern(text, r"подписк|пакет|счет") and has_pattern(text, r"(^|\W)ип(\W|$)"):
        return make_decision("ИП в России", "Бизнес-сервис ИП; юрисдикцию нужно подтвердить", REVIEW, "subscription-business-ambiguous")
    if service == "higgsfield" and count > 1 and has_pattern(text, r"подписк"):
        return make_decision("Ежемесячные подписки", f"Higgsfield повторяется в истории ({count} операций)", MEDIUM, "subscription-recurring")
    one_off = r"кредит|токен|tokens|\bapi\b|extra usage|нано-банан|пробн|случайн|на год|покупка vpn|покупка пакета adobe|(?:chat\s*gpt|openai|gpt).*(?:platform|платформ)|(?:platform|платформ).*(?:chat\s*gpt|openai|gpt)"
    if has_pattern(text, one_off):
        return make_decision("Разовые подписки", "Разовая лицензия, кредиты, API-расход или годовая покупка", HIGH, "subscription-one-off")
    if count > 1 or has_pattern(text, r"на месяц|ежемес"):
        return make_decision("Ежемесячные подписки", f"Сервис повторяется в истории ({count} операций) или указан месяц", MEDIUM, "subscription-recurring")
    return make_decision("Разовые подписки", "В истории нет надежного повторения; предложена разовая подписка", MEDIUM, "subscription-single")


def classify_personal(operation: Operation, context: RuleContext) -> Decision:
    text = normalized_comment(operation)
    if has_pattern(text, r"подар|на день рождения|на др\b"):
        return make_decision("Подарки", "Явно указан подарок", HIGH, "personal-gift")
    if has_pattern(text, r"макбук|macbook|focal bathys|tissot|streetmba|автошкол|оплат\w* учеб|телефон oppo|bose qc|наушник|instax|fujifilm"):
        return make_decision("Крупные покупки и обучение", "Отдельно названная дорогая цель или существенное обучение; плановость нужно подтвердить", REVIEW, "personal-large")
    if has_pattern(text, r"игр|боулинг|батут|концерт|фотосесс|тату|холст|краск|пазл|книг|книж|боккен"):
        return make_decision("Хобби", "Игра, творчество или личное хобби", MEDIUM, "personal-hobby")
    subscription = personal_subscription_override(text, context)
    if subscription:
        return subscription
    if has_pattern(text, r"^оплата дома$"):
        return make_decision("Аренда квартиры", "Краткий комментарий похож на оплату жилья, но тип нужно подтвердить", REVIEW, "personal-home-payment")
    if has_pattern(text, r"золот\w* прибор|коробочк|мышка компьютерн|ежедневник|обложк"):
        return make_decision("Покупки в дом", "Явно указан небольшой бытовой или канцелярский предмет", HIGH, "personal-clear-home-item")
    if not text or text in ("???", "?"):
        return make_decision("Покупки в дом", "Нет достаточного описания; предложена наиболее нейтральная обычная покупка", REVIEW, "personal-ambiguous")
    return make_decision("Покупки в дом", "Описание не попало под надежное предметное правило; предложены обычные покупки", REVIEW, "personal-unmatched")


def classify_removed(operation: Operation, context: RuleContext) -> Decision:
    before = operation_text(operation, 2)
    if before in SIMPLE_CATEGORY_MAP:
        return make_decision(SIMPLE_CATEGORY_MAP[before], "Однозначное утвержденное преобразование", HIGH, "simple-map")
    if before == "Животные":
        return classify_animal(operation, context)
    if before == "Машина":
        return classify_car(operation)
    if before == "Транспорт":
        return classify_transport(operation)
    if before == "Дом":
        return classify_old_home(operation)
    if before == "Покупки в Дом":
        return classify_home(operation)
    if before in ("Офис", "Обустройство офиса"):
        return classify_office(operation)
    if before == "ИП":
        return classify_ip(operation)
    if before == "Печать документов":
        return classify_printing(operation, context)
    if before == "Подписки":
        return classify_subscription(operation, context)
    if before in PERSONAL_CATEGORIES:
        return classify_personal(operation, context)
    raise PreviewError(f"No rule for removed category {before!r}")


def classify_old_home(operation: Operation) -> Decision:
    text = normalized_comment(operation)
    if has_pattern(text, r"полировк\w* фар") and has_pattern(text, r"стен\w* дом"):
        return make_decision("Покупки в дом", "Смешаны материалы для машины и дома; предложена преобладающая бытовая категория", REVIEW, "old-home-mixed-car-home")
    if has_pattern(text, r"уголь|материал|покупк"):
        return make_decision("Покупки в дом", "Материалы или обычные покупки для дома", MEDIUM, "old-home-purchase")
    confidence = REVIEW if not text or "давн" in text else HIGH
    return make_decision("Аренда квартиры", "Оплата квартиры; пустые и неясные строки предложены по повторяющейся серии", confidence, "old-home-rent")


def classify_operation(operation: Operation, context: RuleContext) -> Decision:
    before = operation_text(operation, 2)
    if before in context.event_categories:
        return unchanged_decision(before, "Существующая событийная категория сохранена без изменений")
    decision = approved_exception(operation)
    if decision:
        return decision
    decision = semantic_override(operation, context)
    if decision:
        return decision
    if before not in context.allowed_categories:
        return classify_removed(operation, context)
    return unchanged_decision(before)


def classify_all(operations: Sequence[Operation], categories: dict[str, Any]) -> tuple[RuleContext, tuple[Decision, ...]]:
    context = build_rule_context(operations, categories)
    decisions = tuple(classify_operation(operation, context) for operation in operations)
    return context, decisions


def diagnostics(response: dict[str, Any]) -> dict[str, Any]:
    expense_block = sheet_block(response, EXPENSES_SHEET, 12)
    settings_block = sheet_block(response, SETTINGS_SHEET, 8)
    data_block = sheet_block(response, DATA_SHEET, 8)
    source_rows = parse_operations(expense_block)
    service_rows = tuple(item for item in source_rows if is_service_operation(item))
    operations = assign_stable_ids(tuple(item for item in source_rows if not is_service_operation(item)))
    categories = category_data(data_block)
    settings = settings_expense_category_lists(settings_block)
    before_counts = Counter(operation_text(item, 2) for item in operations)
    allowed = set(categories["allowed"])
    removed = {name: count for name, count in before_counts.items() if name not in allowed}
    return {
        "operation_count": len(operations),
        "service_row_count": len(service_rows),
        "source_rows_hash": snapshot_hash(source_rows),
        "category_counts": dict(sorted(before_counts.items())),
        "removed_category_counts": dict(sorted(removed.items())),
        "removed_row_count": sum(removed.values()),
        "regular_categories": categories["regular"],
        "event_categories": categories["events"],
        "allowed_categories": categories["allowed"],
        "duplicate_allowed_categories": categories["duplicate_allowed"],
        "settings_regular_categories": settings["regular"],
        "settings_event_categories": settings["events"],
        "settings_category_header_rows": settings["header_sheet_rows"],
        "settings_category_lists_hash": settings["lists_hash"],
        "validation_rules": validation_rules(operations),
        "duplicate_stable_id_count": sum(1 for count in Counter(item.stable_id for item in operations).values() if count > 1),
    }


def block_hash(block: GridBlock) -> str:
    return sha256_json([[cell_snapshot(cell) for cell in row] for row in block.rows])


def category_snapshot_hash(settings_block: GridBlock, data_block: GridBlock) -> str:
    return sha256_json({"settings": block_hash(settings_block), "data": block_hash(data_block)})


def raw_row(operation: Operation) -> dict[str, Any]:
    return {name: operation.cells[index].get("userEnteredValue") for index, name in enumerate(COLUMN_NAMES)}


def effective_row(operation: Operation) -> dict[str, Any]:
    return {name: operation.cells[index].get("effectiveValue") for index, name in enumerate(COLUMN_NAMES)}


def display_row(operation: Operation) -> dict[str, str]:
    return {name: display_value(operation.cells[index]) for index, name in enumerate(COLUMN_NAMES)}


def changed_indexes(operations: Sequence[Operation], decisions: Sequence[Decision], allowed: Sequence[str]) -> list[int]:
    category_order = {category: index for index, category in enumerate(allowed)}
    indexes = [index for index, (item, decision) in enumerate(zip(operations, decisions)) if operation_text(item, 2) != decision.after]
    return sorted(indexes, key=lambda index: report_sort_key(operations[index], decisions[index], category_order))


def report_sort_key(operation: Operation, decision: Decision, order: dict[str, int]) -> tuple[Any, ...]:
    date_value = numeric_value(operation.cells[0]) or 0
    return (order.get(decision.after, len(order)), -date_value, operation.sheet_row)


def report_numbers(operations: Sequence[Operation], decisions: Sequence[Decision], allowed: Sequence[str]) -> dict[int, int]:
    return {index: number for number, index in enumerate(changed_indexes(operations, decisions, allowed), start=1)}


def locator_record(operation: Operation) -> dict[str, Any]:
    kind = "telegram" if operation.stable_id and operation.stable_id.startswith("telegram:") else "fingerprint"
    return {
        "kind": kind,
        "stable_id": operation.stable_id,
        "telegram_message_id": operation.telegram_message_id,
        "fingerprint": fingerprint_id(operation),
        "expected_match_count": operation.match_count,
        "snapshot_row_reference": operation.sheet_row,
        "snapshot_a1_reference": f"'{EXPENSES_SHEET}'!C{operation.sheet_row}",
        "row_reference_is_not_identity": True,
    }


def operation_record(operation: Operation, decision: Decision, number: int | None) -> dict[str, Any]:
    before = operation_text(operation, 2)
    return {
        "n": number,
        "changed": before != decision.after,
        "before": before,
        "after": decision.after,
        "reason": decision.reason,
        "confidence": decision.confidence,
        "rule": decision.rule,
        "row_hash": operation.row_hash,
        "locator": locator_record(operation),
        "raw": raw_row(operation),
        "effective": effective_row(operation),
        "display": display_row(operation),
    }


def eur_value(operation: Operation) -> Decimal | None:
    if operation_text(operation, 8) != "EUR":
        return None
    value = numeric_value(operation.cells[7])
    return Decimal(str(value)) if value is not None else None


def category_summary(operations: Sequence[Operation], decisions: Sequence[Decision]) -> list[dict[str, Any]]:
    grouped: dict[str, list[int]] = {}
    for index, (operation, decision) in enumerate(zip(operations, decisions)):
        if operation_text(operation, 2) != decision.after:
            grouped.setdefault(decision.after, []).append(index)
    return [summary_record(after, indexes, operations) for after, indexes in grouped.items()]


def summary_record(after: str, indexes: Sequence[int], operations: Sequence[Operation]) -> dict[str, Any]:
    values = [eur_value(operations[index]) for index in indexes]
    total = sum((value for value in values if value is not None), Decimal("0"))
    return {"after": after, "count": len(indexes), "amount_eur": str(total.quantize(Decimal("0.01"))), "excluded_from_eur_sum": sum(value is None for value in values)}


def pair_counts(operations: Sequence[Operation], decisions: Sequence[Decision]) -> list[dict[str, Any]]:
    counts = Counter((operation_text(item, 2), decision.after) for item, decision in zip(operations, decisions) if operation_text(item, 2) != decision.after)
    return [{"before": before, "after": after, "count": count} for (before, after), count in sorted(counts.items())]


def identity_audit(operations: Sequence[Operation], decisions: Sequence[Decision]) -> dict[str, Any]:
    telegram_counts = Counter(item.telegram_message_id for item in operations if item.telegram_message_id)
    stable_groups: dict[str, list[int]] = {}
    for index, operation in enumerate(operations):
        stable_groups.setdefault(str(operation.stable_id), []).append(index)
    collisions = collision_records(stable_groups, operations, decisions)
    return {
        "telegram_duplicate_value_count": sum(count > 1 for count in telegram_counts.values()),
        "telegram_duplicate_row_count": sum(count for count in telegram_counts.values() if count > 1),
        "telegram_max_multiplicity": max(telegram_counts.values(), default=0),
        "locator_collision_group_count": len(collisions),
        "locator_collision_row_count": sum(item["expected_match_count"] for item in collisions),
        "locator_max_multiplicity": max((item["expected_match_count"] for item in collisions), default=1),
        "locator_collision_groups": collisions,
    }


def collision_records(groups: dict[str, list[int]], operations: Sequence[Operation], decisions: Sequence[Decision]) -> list[dict[str, Any]]:
    records = []
    for stable_id, indexes in groups.items():
        if len(indexes) > 1:
            records.append({
                "stable_id": stable_id,
                "expected_match_count": len(indexes),
                "same_decision": len({decisions[index] for index in indexes}) == 1,
                "snapshot_row_references": [operations[index].sheet_row for index in indexes],
            })
    return records


def validate_invariants(operations: Sequence[Operation], decisions: Sequence[Decision], categories: dict[str, Any], service_count: int) -> dict[str, Any]:
    allowed = set(categories["allowed"])
    events = set(categories["events"])
    before_counts = Counter(operation_text(item, 2) for item in operations)
    removed = {name: count for name, count in before_counts.items() if name not in allowed}
    changed = sum(operation_text(item, 2) != decision.after for item, decision in zip(operations, decisions))
    existing_events = sum(operation_text(item, 2) in events for item in operations)
    new_events = sum(operation_text(item, 2) not in events and decision.after in events for item, decision in zip(operations, decisions))
    identity = identity_audit(operations, decisions)
    checks = invariant_checks(operations, decisions, categories, service_count, removed, changed, existing_events, new_events, identity)
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise PreviewError("Invariant failure: " + ", ".join(failed))
    return {
        "total_operations": len(operations),
        "changed_count": changed,
        "unchanged_count": len(operations) - changed,
        "review_count": sum(decision.confidence == REVIEW and operation_text(item, 2) != decision.after for item, decision in zip(operations, decisions)),
        "service_row_count": service_count,
        "removed_categories": dict(sorted(removed.items())),
        "removed_category_count": len(removed),
        "removed_row_count": sum(removed.values()),
        "existing_event_count": existing_events,
        "new_event_count": new_events,
        "final_event_count": existing_events + new_events,
        "identity": identity,
        "regression_id_cardinalities": regression_id_cardinalities(operations, decisions),
        "user_approved_override_cardinalities": user_approved_override_cardinalities(operations, decisions),
        "dropdown_source_checked": True,
        "dropdown_source_range": "'*data'!AK7:AK199",
        "invariants": checks,
    }


def invariant_checks(operations: Sequence[Operation], decisions: Sequence[Decision], categories: dict[str, Any], service_count: int, removed: dict[str, int], changed: int, existing_events: int, new_events: int, identity: dict[str, Any]) -> dict[str, bool]:
    allowed = set(categories["allowed"])
    events = set(categories["events"])
    collision_groups = identity["locator_collision_groups"]
    return {
        "operation_count_3112": len(operations) == EXPECTED_OPERATION_COUNT,
        "one_service_row": service_count == 1,
        "changed_plus_unchanged": changed + (len(operations) - changed) == EXPECTED_OPERATION_COUNT,
        "removed_category_count_17": len(removed) == EXPECTED_REMOVED_CATEGORY_COUNT,
        "removed_row_count_1349": sum(removed.values()) == EXPECTED_REMOVED_ROW_COUNT,
        "all_after_categories_allowed": all(decision.after in allowed for decision in decisions),
        "settings_regular_categories_equal_data_regular": tuple(categories.get("settings_regular", ())) == tuple(categories["regular"]),
        "settings_event_categories_equal_data_events": tuple(categories.get("settings_events", ())) == tuple(categories["events"]),
        "settings_categories_equal_allowed": tuple(categories.get("settings_allowed", ())) == tuple(categories["allowed"]),
        "settings_expense_header_count_2": len(categories.get("settings_header_rows", ())) == 2,
        "all_removed_rows_changed": all(operation_text(item, 2) in allowed or operation_text(item, 2) != decision.after for item, decision in zip(operations, decisions)),
        "existing_events_190": existing_events == EXPECTED_EXISTING_EVENT_COUNT,
        "new_events_10": new_events == EXPECTED_NEW_EVENT_COUNT,
        "final_events_200": existing_events + new_events == EXPECTED_FINAL_EVENT_COUNT,
        "existing_events_preserved": all(operation_text(item, 2) not in events or decision.after == operation_text(item, 2) for item, decision in zip(operations, decisions)),
        "approved_event_distribution": approved_event_distribution(operations, decisions, events),
        "regression_ids": regression_ids_pass(operations, decisions),
        "user_approved_overrides": user_approved_overrides_pass(operations, decisions),
        "locator_match_counts": all(item.match_count == sum(other.stable_id == item.stable_id for other in operations) for item in operations),
        "colliding_locators_have_same_decision": all(group["same_decision"] for group in collision_groups),
    }


def approved_event_distribution(operations: Sequence[Operation], decisions: Sequence[Decision], events: set[str]) -> bool:
    moves = Counter(decision.after for item, decision in zip(operations, decisions) if operation_text(item, 2) not in events and decision.after in events)
    expected = Counter({"Покупка Nissan Note E12 2013 2025": 6, "Египет 2024": 2, "Россия Лиза 2026": 1, "Предложение руки и сердца": 1})
    return moves == expected


def regression_ids_pass(operations: Sequence[Operation], decisions: Sequence[Decision]) -> bool:
    return all(
        item["total_count"] == 1 and item["matching_decision_count"] == 1
        for item in regression_id_cardinalities(operations, decisions).values()
    )


def regression_id_cardinalities(operations: Sequence[Operation], decisions: Sequence[Decision]) -> dict[str, dict[str, int]]:
    expected = {
        "6827": lambda item, decision: decision.after == "Одежда",
        "4914": lambda item, decision: decision.after == "Покупки в дом",
        "6524": lambda item, decision: decision.after == "Развлечения",
        "6521": lambda item, decision: operation_text(item, 2) == decision.after == "Развлечения",
    }
    pairs = tuple(zip(operations, decisions))
    return {
        telegram_id: {
            "total_count": sum(item.telegram_message_id == telegram_id for item, _ in pairs),
            "matching_decision_count": sum(
                item.telegram_message_id == telegram_id and predicate(item, decision)
                for item, decision in pairs
            ),
        }
        for telegram_id, predicate in expected.items()
    }


def user_approved_overrides_pass(
    operations: Sequence[Operation],
    decisions: Sequence[Decision],
    overrides: dict[str, tuple[str, str]] | None = None,
) -> bool:
    return all(
        counts["total_count"] == 1 and counts["matching_decision_count"] == 1
        for counts in user_approved_override_cardinalities(operations, decisions, overrides).values()
    )


def user_approved_override_cardinalities(
    operations: Sequence[Operation],
    decisions: Sequence[Decision],
    overrides: dict[str, tuple[str, str]] | None = None,
) -> dict[str, dict[str, int]]:
    expected = USER_APPROVED_STABLE_OVERRIDES if overrides is None else overrides
    pairs = tuple(zip(operations, decisions))
    return {
        stable_id: {
            "total_count": sum(item.stable_id == stable_id for item, _ in pairs),
            "matching_decision_count": sum(
                item.stable_id == stable_id
                and decision.after == after
                and decision.rule == "user-approved-stable-override"
                for item, decision in pairs
            ),
        }
        for stable_id, (after, _) in expected.items()
    }


def build_mapping(response: dict[str, Any], spreadsheet_id: str, spreadsheet_env: str, started_at: str, finished_at: str) -> tuple[dict[str, Any], str]:
    expense_block = sheet_block(response, EXPENSES_SHEET, 12)
    settings_block = sheet_block(response, SETTINGS_SHEET, 8)
    data_block = sheet_block(response, DATA_SHEET, 8)
    source_rows = parse_operations(expense_block)
    service_rows = tuple(item for item in source_rows if is_service_operation(item))
    operations = assign_stable_ids(tuple(item for item in source_rows if not is_service_operation(item)))
    categories = category_data(data_block)
    settings = settings_expense_category_lists(settings_block)
    categories.update(
        settings_regular=settings["regular"],
        settings_events=settings["events"],
        settings_allowed=settings["allowed"],
        settings_header_rows=settings["header_sheet_rows"],
        settings_lists_hash=settings["lists_hash"],
    )
    _, decisions = classify_all(operations, categories)
    audit = validate_invariants(operations, decisions, categories, len(service_rows))
    numbers = report_numbers(operations, decisions, categories["allowed"])
    records = [operation_record(item, decision, numbers.get(index)) for index, (item, decision) in enumerate(zip(operations, decisions))]
    mapping = mapping_document(response, spreadsheet_id, spreadsheet_env, started_at, finished_at, source_rows, settings_block, data_block, categories, audit, records, operations, decisions)
    markdown = render_markdown(mapping)
    mapping["audit"]["artifact_validation"] = validate_artifacts(mapping, markdown)
    return mapping, markdown


def mapping_document(response: dict[str, Any], spreadsheet_id: str, spreadsheet_env: str, started_at: str, finished_at: str, source_rows: Sequence[Operation], settings_block: GridBlock, data_block: GridBlock, categories: dict[str, Any], audit: dict[str, Any], records: list[dict[str, Any]], operations: Sequence[Operation], decisions: Sequence[Decision]) -> dict[str, Any]:
    sheet_ids = {sheet.get("properties", {}).get("title", ""): sheet.get("properties", {}).get("sheetId") for sheet in response.get("sheets", [])}
    return {
        "schema_version": "expense-reclassification-preview/v1",
        "snapshot": {
            "started_at": started_at,
            "finished_at": finished_at,
            "timezone": TIMEZONE,
            "spreadsheet_env": spreadsheet_env,
            "spreadsheet_id_sha256": hashlib.sha256(spreadsheet_id.encode("utf-8")).hexdigest(),
            "sheet_ids": sheet_ids,
            "ranges": list(SNAPSHOT_RANGES),
            "api_method": "spreadsheets.get",
            "oauth_scope": READONLY_SCOPE,
            "source_rows_hash": snapshot_hash(source_rows),
            "operation_rows_hash": snapshot_hash([item for item in source_rows if not is_service_operation(item)]),
            "category_snapshot_hash": category_snapshot_hash(settings_block, data_block),
        },
        "category_snapshot": {
            "settings_regular_categories": categories["settings_regular"],
            "settings_event_categories": categories["settings_events"],
            "settings_categories": categories["settings_allowed"],
            "settings_category_header_rows": categories["settings_header_rows"],
            "settings_category_lists_hash": categories["settings_lists_hash"],
            "data_category_lists_hash": sha256_json({"regular": categories["regular"], "events": categories["events"]}),
            "regular_categories": categories["regular"],
            "event_categories": categories["events"],
            "allowed_categories": categories["allowed"],
            "allowed_categories_with_duplicates": categories["allowed_with_duplicates"],
            "duplicate_allowed_categories": categories["duplicate_allowed"],
            "expense_category_validation_rules": validation_rules([item for item in source_rows if not is_service_operation(item)]),
            "expense_category_validation_available": bool(validation_rules([item for item in source_rows if not is_service_operation(item)])),
            "dropdown_source_checked": True,
            "dropdown_source_range": "'*data'!AK7:AK199",
        },
        "audit": audit,
        "category_summary": category_summary(operations, decisions),
        "pair_counts": pair_counts(operations, decisions),
        "operations": records,
    }


def markdown_escape(value: Any) -> str:
    return str(value or "").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>").replace("|", "\\|")


def format_operation_amount(record: dict[str, Any]) -> str:
    amount = record["display"]["amount"]
    currency = record["display"]["currency"]
    return markdown_escape(f"{amount} {currency}".strip())


def format_eur_amount(record: dict[str, Any]) -> str:
    effective = record["effective"]["amount_eur"] or {}
    if record["display"]["main_currency"] != "EUR" or "numberValue" not in effective:
        return "n/a"
    return markdown_escape(record["display"]["amount_eur"])


def compact_attention_row(record: dict[str, Any]) -> str:
    values = (record["n"], record["display"]["date"], record["display"]["comment"], record["before"], record["after"], record["reason"])
    return "| " + " | ".join(markdown_escape(value) for value in values) + " |"


def full_markdown_row(record: dict[str, Any]) -> str:
    values = (record["n"], record["display"]["date"], format_operation_amount(record), format_eur_amount(record), record["display"]["comment"], record["before"], record["after"], record["reason"], record["confidence"])
    return "| " + " | ".join(markdown_escape(value) for value in values) + " |"


def render_markdown(mapping: dict[str, Any]) -> str:
    audit = mapping["audit"]
    changed = sorted((item for item in mapping["operations"] if item["changed"]), key=lambda item: item["n"])
    reviews = [item for item in changed if item["confidence"] == REVIEW]
    lines = markdown_header(mapping, audit)
    lines.extend(markdown_summary(mapping["category_summary"]))
    lines.extend(markdown_attention(reviews))
    lines.extend(markdown_full_list(changed, mapping["category_snapshot"]["allowed_categories"]))
    return "\n".join(lines).rstrip() + "\n"


def markdown_header(mapping: dict[str, Any], audit: dict[str, Any]) -> list[str]:
    return [
        "# Предпросмотр перераспределения расходов",
        "",
        f"- Время снимка: {mapping['snapshot']['finished_at']}",
        f"- Всего операций: {audit['total_operations']}",
        f"- Изменяемых: {audit['changed_count']}",
        f"- Неизменяемых: {audit['unchanged_count']}",
        f"- REVIEW: {audit['review_count']}",
        "",
        (
            "Категории расходов на листе ↙️Расходы не изменялись. "
            "Отдельно по разрешению пользователя в ⚙️Настройки уже переименована "
            "категория: Парковка машины -> Парковка и платная дорога. "
            "Этот файл нужно утвердить до записи категорий расходов."
        ),
        "",
    ]


def markdown_summary(summary: Sequence[dict[str, Any]]) -> list[str]:
    lines = ["## Сводка по категориям После", "", "| Категория | Операций | Сумма в EUR | Исключено из EUR |", "| --- | ---: | ---: | ---: |"]
    lines.extend(f"| {markdown_escape(item['after'])} | {item['count']} | {item['amount_eur']} | {item['excluded_from_eur_sum']} |" for item in summary)
    lines.append("")
    return lines


def markdown_attention(reviews: Sequence[dict[str, Any]]) -> list[str]:
    lines = ["## Требует внимания", "", "| N | Дата | Комментарий | До | После | Основание |", "| ---: | --- | --- | --- | --- | --- |"]
    lines.extend(compact_attention_row(record) for record in reviews)
    lines.append("")
    return lines


def markdown_full_list(changed: Sequence[dict[str, Any]], allowed: Sequence[str]) -> list[str]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in changed:
        grouped.setdefault(record["after"], []).append(record)
    lines = ["## Полный список", ""]
    for category in allowed:
        if category in grouped:
            lines.extend(markdown_category(category, grouped[category]))
    return lines


def markdown_category(category: str, records: Sequence[dict[str, Any]]) -> list[str]:
    lines = [f"### {markdown_escape(category)}", "", "| N | Дата | Сумма | EUR | Комментарий | До | После | Основание | Уверенность |", "| ---: | --- | ---: | ---: | --- | --- | --- | --- | --- |"]
    lines.extend(full_markdown_row(record) for record in records)
    lines.append("")
    return lines


def validate_artifacts(mapping: dict[str, Any], markdown: str) -> dict[str, bool]:
    operations = mapping["operations"]
    changed = sorted((item for item in operations if item["changed"]), key=lambda item: item["n"])
    unchanged = [item for item in operations if not item["changed"]]
    changed_ns = [item["n"] for item in changed]
    review_ns = [item["n"] for item in changed if item["confidence"] == REVIEW]
    markdown_rows = parse_markdown_report(markdown)
    expected_full_groups = [(item["after"], item["n"]) for item in changed]
    checks = {
        "operation_count_matches_audit": len(operations) == mapping["audit"]["total_operations"],
        "changed_count_matches_audit": len(changed) == mapping["audit"]["changed_count"],
        "unchanged_count_matches_audit": len(unchanged) == mapping["audit"]["unchanged_count"],
        "changed_n_contiguous": changed_ns == list(range(1, len(changed) + 1)),
        "unchanged_n_null": all(item["n"] is None for item in unchanged),
        "markdown_full_rows_match_changed": markdown_rows["full_ns"] == changed_ns,
        "markdown_attention_matches_reviews": markdown_rows["attention_ns"] == review_ns,
        "markdown_groups_match_records": markdown_rows["full_groups"] == expected_full_groups,
        "mapping_groups_and_dates_sorted": records_follow_report_sort(changed, mapping["category_snapshot"]["allowed_categories"]),
        "category_summary_matches_operations": summary_matches_records(mapping["category_summary"], changed),
        "pair_counts_match_operations": pair_counts_match_records(mapping["pair_counts"], changed),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise PreviewError("Artifact validation failure: " + ", ".join(failed))
    return checks


def parse_markdown_report(markdown: str) -> dict[str, Any]:
    if "## Требует внимания" not in markdown or "## Полный список" not in markdown:
        raise PreviewError("Markdown report is missing required sections")
    attention, full = markdown.split("## Требует внимания", 1)[1].split("## Полный список", 1)
    attention_ns = markdown_row_numbers(attention)
    full_ns = []
    full_groups = []
    current_category = None
    for line in full.splitlines():
        if line.startswith("### "):
            current_category = line[4:].replace("\\|", "|")
            continue
        match = re.match(r"^\| (\d+) \|", line)
        if match:
            if current_category is None:
                raise PreviewError("Markdown full-list row appears before its category heading")
            number = int(match.group(1))
            full_ns.append(number)
            full_groups.append((current_category, number))
    return {"attention_ns": attention_ns, "full_ns": full_ns, "full_groups": full_groups}


def markdown_row_numbers(section: str) -> list[int]:
    return [int(match.group(1)) for line in section.splitlines() if (match := re.match(r"^\| (\d+) \|", line))]


def records_follow_report_sort(records: Sequence[dict[str, Any]], allowed: Sequence[str]) -> bool:
    category_order = {category: index for index, category in enumerate(allowed)}
    expected = sorted(
        records,
        key=lambda item: (
            category_order.get(item["after"], len(category_order)),
            -record_date_number(item),
            item["locator"]["snapshot_row_reference"],
        ),
    )
    return [item["n"] for item in expected] == [item["n"] for item in records]


def record_date_number(record: dict[str, Any]) -> float:
    value = record["effective"].get("date") or {}
    number = value.get("numberValue") if isinstance(value, dict) else None
    return float(number) if isinstance(number, (int, float)) else 0.0


def summary_matches_records(summary: Sequence[dict[str, Any]], records: Sequence[dict[str, Any]]) -> bool:
    expected: dict[str, dict[str, Any]] = {}
    for record in records:
        item = expected.setdefault(record["after"], {"count": 0, "amount_eur": Decimal("0"), "excluded_from_eur_sum": 0})
        item["count"] += 1
        effective = record["effective"].get("amount_eur") or {}
        value = effective.get("numberValue") if isinstance(effective, dict) else None
        if record["display"].get("main_currency") == "EUR" and isinstance(value, (int, float)):
            item["amount_eur"] += Decimal(str(value))
        else:
            item["excluded_from_eur_sum"] += 1
    normalized_expected = {
        after: {
            "count": item["count"],
            "amount_eur": str(item["amount_eur"].quantize(Decimal("0.01"))),
            "excluded_from_eur_sum": item["excluded_from_eur_sum"],
        }
        for after, item in expected.items()
    }
    normalized_actual = {
        item["after"]: {
            "count": item["count"],
            "amount_eur": item["amount_eur"],
            "excluded_from_eur_sum": item["excluded_from_eur_sum"],
        }
        for item in summary
    }
    return len(normalized_actual) == len(summary) and normalized_actual == normalized_expected


def pair_counts_match_records(pair_summary: Sequence[dict[str, Any]], records: Sequence[dict[str, Any]]) -> bool:
    expected = Counter((item["before"], item["after"]) for item in records)
    actual = Counter({(item["before"], item["after"]): item["count"] for item in pair_summary})
    return len(actual) == len(pair_summary) and actual == expected


def verify_category_snapshot(response: dict[str, Any], expected_hash: str) -> str:
    settings_block = sheet_block(response, SETTINGS_SHEET, 8)
    data_block = sheet_block(response, DATA_SHEET, 8)
    current_hash = category_snapshot_hash(settings_block, data_block)
    if current_hash != expected_hash:
        raise PreviewError("Categories changed after the expense snapshot; preview was not written")
    return current_hash


def write_artifacts(output_dir: Path, mapping: dict[str, Any], markdown: str) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / "expense_reclassification_review.md"
    mapping_path = output_dir / "expense_reclassification_mapping.json"
    markdown_temp = markdown_path.with_suffix(markdown_path.suffix + ".tmp")
    mapping_temp = mapping_path.with_suffix(mapping_path.suffix + ".tmp")
    markdown_temp.write_text(markdown, encoding="utf-8")
    mapping_temp.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(markdown_temp, markdown_path)
    os.replace(mapping_temp, mapping_path)
    return markdown_path, mapping_path


def load_spreadsheet_id(env_name: str) -> str:
    spreadsheet_id = os.getenv(env_name, "").strip()
    if not spreadsheet_id:
        raise PreviewError(f"Missing required environment variable: {env_name}")
    return spreadsheet_id


def build_readonly_service(credentials_path: Path):
    import httplib2
    from google_auth_httplib2 import AuthorizedHttp
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    credentials = Credentials.from_service_account_file(str(credentials_path), scopes=[READONLY_SCOPE])
    authorized_http = AuthorizedHttp(credentials, http=httplib2.Http(timeout=HTTP_TIMEOUT_SECONDS))
    return build("sheets", "v4", http=authorized_http, cache_discovery=False)


def fetch_snapshot(service: Any, spreadsheet_id: str, ranges: Sequence[str]) -> dict[str, Any]:
    request = service.spreadsheets().get(spreadsheetId=spreadsheet_id, ranges=list(ranges), includeGridData=True, fields=SPREADSHEET_FIELDS)
    return request.execute(num_retries=1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a read-only expense reclassification preview")
    parser.add_argument("--spreadsheet-env", default="GOOGLE_SPREADSHEET_ID")
    parser.add_argument("--credentials", type=Path, default=Path(".google_service_account_credentials.json"))
    parser.add_argument("--diagnose", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path("."))
    return parser.parse_args()


def main() -> int:
    from dotenv import load_dotenv

    args = parse_args()
    load_dotenv()
    started_at = datetime.now(ZoneInfo(TIMEZONE)).isoformat()
    spreadsheet_id = load_spreadsheet_id(args.spreadsheet_env)
    service = build_readonly_service(args.credentials.resolve())
    response = fetch_snapshot(service, spreadsheet_id, SNAPSHOT_RANGES)
    finished_at = datetime.now(ZoneInfo(TIMEZONE)).isoformat()
    if args.diagnose:
        result = diagnostics(response)
        result.update(snapshot_started_at=started_at, snapshot_finished_at=finished_at)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    mapping, markdown = build_mapping(response, spreadsheet_id, args.spreadsheet_env, started_at, finished_at)
    verification = fetch_snapshot(service, spreadsheet_id, (SETTINGS_RANGE, DATA_RANGE))
    verify_category_snapshot(verification, mapping["snapshot"]["category_snapshot_hash"])
    mapping["snapshot"]["category_verified_at"] = datetime.now(ZoneInfo(TIMEZONE)).isoformat()
    mapping["snapshot"]["read_call_count"] = 2
    markdown = render_markdown(mapping)
    mapping["audit"]["artifact_validation"] = validate_artifacts(mapping, markdown)
    markdown_path, mapping_path = write_artifacts(args.output_dir.resolve(), mapping, markdown)
    print(json.dumps({"status": "preview_written", "markdown": str(markdown_path), "mapping": str(mapping_path), "audit": mapping["audit"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
