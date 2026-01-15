import logging
import os
import random
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Sequence, Tuple

from lib.utilities.google_utilities import (_SERVICE,  # type: ignore
                                            SPREADSHEET_ID, Category, ListName,
                                            OperationTypes, RequestData,
                                            Status, TransferType,
                                            ensure_min_rows,
                                            get_insert_row_above_request,
                                            get_update_cells_request,
                                            get_values,
                                            get_values_to_update_for_request,
                                            reset_dev_input_sheets,
                                            update_values)

LOGGER = logging.getLogger(__name__)


SHEETS_DATE_EPOCH = datetime(1899, 12, 30)
CURRENCY_RATES_RUB = {
    "RUB": 1.0,
    "EUR": 100.0,
    "USD": 90.0,
    "CNY": 13.0,
    "KZT": 0.35,
    "TRY": 3.0,
}
CURRENCY_KEYWORDS = {
    "EUR": ["eur", "евро"],
    "USD": ["usd", "доллар", "dollar"],
    "CNY": ["cny", "cnh", "юань"],
    "KZT": ["kzt", "тенге"],
    "TRY": ["try", "лира", "лиры"],
    "RUB": ["rub", "руб", "р", "₽"],
}


def _parse_date_string(value: str) -> Optional[date]:
    """
    Пытается распарсить строковую дату из ячейки Sheets.
    Поддерживает ISO, форматы с месяцами по-английски и простые dd.mm.yyyy.
    """
    patterns = [
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%B %d, %Y",  # January 14, 2026
        "%d %B %Y",  # 14 January 2026
    ]
    for pat in patterns:
        try:
            return datetime.strptime(value, pat).date()
        except Exception:
            continue
    return None


def sheet_serial_to_date(value) -> date:
    """
    Преобразует значение ячейки (serial или строка) в date.
    """
    if isinstance(value, (int, float)):
        return (SHEETS_DATE_EPOCH + timedelta(days=int(value))).date()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except Exception:
            parsed = _parse_date_string(value)
            if parsed:
                return parsed
    return date.today()


def date_to_serial(value: date) -> int:
    """
    Преобразует date в Sheets serial number.
    """
    return (datetime(value.year, value.month, value.day) - SHEETS_DATE_EPOCH).days


def read_start_date_from_settings() -> date:
    """
    Читает дату начала таблицы из ⚙️Настройки!C12.
    """
    values = get_values("⚙️Настройки!C12")
    if not values or not values[0]:
        LOGGER.warning("No start date in ⚙️Настройки!C12, fallback to today.")
        return date.today()
    return sheet_serial_to_date(values[0][0])


@dataclass
class DevSettingsTemplate:
    currencies: List[Tuple[str, str]] = field(default_factory=list)
    users: List[str] = field(default_factory=list)
    envelopes: List[str] = field(default_factory=list)
    banks: List[str] = field(default_factory=list)
    accounts: List[Tuple[str, bool, str, str, str, str]] = field(default_factory=list)
    expense_categories: List[
        Tuple[str, Optional[float], Optional[str], Optional[bool]]
    ] = field(default_factory=list)
    income_categories: List[str] = field(default_factory=list)


DEFAULT_SETTINGS_TEMPLATE = DevSettingsTemplate(
    currencies=[
        ("RUB", "рубли"),
        ("EUR", "евро"),
        ("USD", "доллары"),
        ("CNY", "юани"),
        ("KZT", "тенге"),
        ("TRY", "лиры"),
    ],
    users=["БИВИС", "БАТТХЕД"],
    envelopes=["ПОДУШКА", "НАКОПЛЕНИЯ", "ЗДОРОВЬЕ", "ИНВЕСТИЦИИ"],
    banks=["СБЕР", "ТИНЬКОФФ", "ЯНДЕКС", "ОЗОН"],
    accounts=[
        ("RUB", True, "СЕМЬЯ", "карта", "СБЕР", ""),
        ("RUB", True, "БИВИС", "карта", "ТИНЬКОФФ", ""),
        ("RUB", False, "БАТТХЕД", "карта", "ТИНЬКОФФ", ""),
        ("RUB", True, "СЕМЬЯ", "наличные", "", ""),
        ("EUR", True, "СЕМЬЯ", "счет", "ЯНДЕКС", ""),
        ("USD", True, "СЕМЬЯ", "счет", "ОЗОН", ""),
        ("CNY", False, "СЕМЬЯ", "вклад", "", ""),
        ("KZT", False, "СЕМЬЯ", "наличные", "", ""),
    ],
    expense_categories=[
        ("Продукты", 0, None, True),
        ("Еда вне дома", 0, None, True),
        ("Животные", 0, None, False),
        ("Квартплата", 0, None, False),
        ("Коммунальные услуги", 0, None, False),
        ("Покупки в Дом", 0, None, False),
    ],
    income_categories=["Зарплата", "Фриланс"],
)


def _pad_values(rows: List[List], width: int, max_rows: int) -> List[List]:
    padded = []
    for row in rows[:max_rows]:
        padded.append((row + [""] * width)[:width])
    return padded


def seed_dev_settings(
    template: DevSettingsTemplate = DEFAULT_SETTINGS_TEMPLATE, overwrite: bool = False
):
    """
    Заполняет лист ⚙️Настройки подготовленными значениями.
    Если overwrite=False, пропускает запись (ожидаем ручное подтверждение).
    """
    if not overwrite:
        LOGGER.info("seed_dev_settings skipped (overwrite=False)")
        return

    update_values(
        "⚙️Настройки!A18:B29",
        _pad_values([[c, n] for c, n in template.currencies], 2, 12),
    )
    update_values(
        "⚙️Настройки!A33:A42", _pad_values([[u] for u in template.users], 1, 10)
    )
    update_values(
        "⚙️Настройки!A46:A55", _pad_values([[e] for e in template.envelopes], 1, 10)
    )
    update_values(
        "⚙️Настройки!A59:A68", _pad_values([[b] for b in template.banks], 1, 10)
    )

    # Accounts: write only C-H (A is formula, B is link we do not fill)
    account_rows = []
    for currency, include_in_balance, owner, acc_type, bank, name in template.accounts:
        account_rows.append(
            [
                currency,  # C Валюта
                "TRUE" if include_in_balance else "FALSE",  # D Учитывать в балансе
                owner,  # E Владелец
                acc_type,  # F Тип
                bank,  # G Имя банка
                name or "",  # H Имя (опционально)
            ]
        )
    update_values("⚙️Настройки!C72:H133", _pad_values(account_rows, 6, 62))

    expense_rows = []
    for name, expected, _, use_status in template.expense_categories:
        expense_rows.append(
            [
                name,
                expected if expected is not None else "",
                "",  # Валюта не заполняем
                "TRUE" if use_status else "FALSE",
            ]
        )
    update_values("⚙️Настройки!A137:D158", _pad_values(expense_rows, 4, 22))

    income_rows = [[name] for name in template.income_categories]
    update_values("⚙️Настройки!A170:A179", _pad_values(income_rows, 1, 10))

    # Сбросить кэш категорий/счетов
    Category.force_update()
    LOGGER.info("Dev settings seeded and Category cache refreshed.")


@dataclass
class SimulationConfig:
    active_prob_weekday: float = 0.75
    active_prob_weekend: float = 0.55
    daily_ops_min: int = 4
    daily_ops_max: int = 7
    monthly_salary_min: int = 70_000
    monthly_salary_max: int = 140_000
    salary_jitter: float = 0.08
    transfer_prob: float = 0.08
    adjustment_prob: float = 0.02
    starting_adjustment_min: int = 5_000
    starting_adjustment_max: int = 15_000
    tx_min_fraction: float = 0.002
    tx_max_fraction: float = 0.02
    adjustment_every_days: int = 60


@dataclass
class DataOverrides:
    accounts: Optional[List[str]] = None
    expense_categories: Optional[List[str]] = None
    income_categories: Optional[List[str]] = None


@dataclass
class SimulationResult:
    run_id: str
    seed: int
    transactions: List[RequestData]
    ledger_summary: Dict[str, float]
    warnings: List[str] = field(default_factory=list)


@dataclass
class ApplyReport:
    run_id: str
    inserted: int
    reset_done: bool
    batches_sent: int


def _choose_salary_category(income_categories: Sequence[str]) -> Optional[str]:
    if not income_categories:
        return None
    keywords = ("зарплат", "оклад", "salary", "payroll")
    for cat in income_categories:
        lower = cat.lower()
        if any(key in lower for key in keywords):
            return cat
    return income_categories[0]


def _pick_accounts(
    accounts: Sequence[str],
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Возвращает (spend, savings, cash) при наличии хотя бы одного счета.
    """
    if not accounts:
        return None, None, None
    if len(accounts) == 1:
        return accounts[0], accounts[0], accounts[0]
    if len(accounts) == 2:
        return accounts[0], accounts[1], accounts[0]
    return accounts[0], accounts[1], accounts[2]


def _infer_currency(account_name: str) -> str:
    lower = account_name.lower()
    for code, keys in CURRENCY_KEYWORDS.items():
        if any(k in lower for k in keys):
            return code
    return "RUB"


def _to_account_amount(base_rub_amount: float, account_name: str) -> float:
    currency = _infer_currency(account_name)
    rate = CURRENCY_RATES_RUB.get(currency, 1.0)
    return round(base_rub_amount / rate, 2)


def _ensure_positive_balance(
    ledger: Dict[str, float], account: str, needed_base_rub: float, for_date: date
) -> Tuple[Optional[RequestData], float]:
    current = ledger.get(account, 0.0)
    if current >= needed_base_rub:
        return None, 0.0
    top_up = max(needed_base_rub - current, 0)
    today_serial = date_to_serial(for_date)
    return (
        RequestData(
            list_name=ListName.transfers,
            date=today_serial,
            transfer_type=TransferType.adjustment,
            account=account,
            replenishment_account=account,
            amount=0,
            replenishment_amount=_to_account_amount(top_up, account),
            status=Status.committed,
            comment="DEV_SEED:auto_adjust",
        ),
        top_up,
    )


def simulate_dev_history(
    seed: int,
    start_date: date,
    end_date: date,
    config: SimulationConfig = SimulationConfig(),
    overrides: DataOverrides = DataOverrides(),
) -> SimulationResult:
    random.seed(seed)
    run_id = f"DEV_SEED:{uuid.uuid4()}"

    accounts = [acc for acc in (overrides.accounts or Category.get_accounts()) if acc]
    expense_categories = [c for c in (overrides.expense_categories or Category.get_expenses()) if c]
    income_categories = [c for c in (overrides.income_categories or Category.get_incomes()) if c]

    salary_category = _choose_salary_category(income_categories)
    freelance_category = None
    if income_categories:
        for cat in income_categories:
            if "фриланс" in cat.lower() or "freelance" in cat.lower():
                freelance_category = cat
                break
    spend_account, savings_account, cash_account = _pick_accounts(accounts)
    account_pool = [a for a in (accounts or [spend_account, savings_account, cash_account]) if a]

    ledger: Dict[str, float] = {acc: 0.0 for acc in accounts}
    transactions: List[RequestData] = []
    warnings: List[str] = []
    # для контроля количества adjustments в день
    adjustments_today: Dict[date, set] = {}
    expenses_count = 0
    transfers_count = 0

    # стартовые корректировки для всех счетов
    for acc in account_pool:
        base_adj = random.randint(5_000, 15_000)
        ledger[acc] += base_adj
        transactions.append(
            RequestData(
                list_name=ListName.transfers,
                date=date_to_serial(start_date),
                transfer_type=TransferType.adjustment,
                account=acc,
                replenishment_account=acc,
                amount=0,
                replenishment_amount=_to_account_amount(base_adj, acc),
                status=Status.committed,
                comment=f"{run_id} start_adjust",
            )
        )

    day = start_date
    last_adjustment_day = start_date
    monthly_salary_plan: Dict[Tuple[int, int], Tuple[date, float]] = {}

    while day <= end_date:
        ym = (day.year, day.month)
        if ym not in monthly_salary_plan:
            salary_value = random.randint(
                config.monthly_salary_min, config.monthly_salary_max
            )
            salary_value = salary_value * (
                1 + random.uniform(-config.salary_jitter, config.salary_jitter)
            )
            pay_day = min(random.randint(5, 10), 28)
            monthly_salary_plan[ym] = (date(day.year, day.month, pay_day), salary_value)

        pay_date, salary_value = monthly_salary_plan[ym]
        is_weekend = day.weekday() >= 5
        active = random.random() < (
            config.active_prob_weekend if is_weekend else config.active_prob_weekday
        )

        def _add_tx(tx: RequestData):
            transactions.append(tx)

        # зарплата + фриланс мелкими частями
        salary_target = spend_account or (account_pool[0] if account_pool else None)
        if salary_category and day == pay_date and salary_target:
            base_amount = round(salary_value, 2)
            ledger[salary_target] += base_amount
            _add_tx(
                RequestData(
                    list_name=ListName.incomes,
                    date=date_to_serial(day),
                    incomes_category=salary_category,
                    account=salary_target,
                    amount=_to_account_amount(base_amount, salary_target),
                    status=Status.committed,
                    comment=f"{run_id} salary",
                )
            )
            # доп. фриланс в этом месяце 1-2 раза
            freelance_times = random.randint(1, 2)
            for _ in range(freelance_times):
                if freelance_category:
                    freelance_date = day + timedelta(days=random.randint(2, 10))
                    if freelance_date > end_date:
                        freelance_date = end_date
                    base_freelance_amount = round(random.uniform(8000, 40000), 2)
                    target_acc = random.choice(account_pool)
                    ledger[target_acc] = ledger.get(target_acc, 0) + base_freelance_amount
                    _add_tx(
                        RequestData(
                            list_name=ListName.incomes,
                            date=date_to_serial(freelance_date),
                            incomes_category=freelance_category,
                            account=target_acc,
                            amount=_to_account_amount(base_freelance_amount, target_acc),
                            status=Status.committed,
                            comment=f"{run_id} freelance",
                        )
                    )

        if active:
            ops_count = random.randint(config.daily_ops_min, config.daily_ops_max)
            expense_added = False
            for _ in range(ops_count):
                kind_roll = random.random()
                # reduce transfers frequency, prefer expenses
                if kind_roll < config.transfer_prob and len(account_pool) >= 2:
                    write_off = random.choice(account_pool)
                    replenishment = random.choice(
                        [acc for acc in account_pool if acc != write_off]
                        or account_pool
                    )
                    max_amount = max(config.tx_min_fraction * salary_value, 500)
                    base_amount = round(
                        random.uniform(
                            max_amount, salary_value * config.tx_max_fraction
                        ),
                        2,
                    )
                    base_amount = min(base_amount, 40_000)
                    need_adj, top_up = _ensure_positive_balance(ledger, write_off, base_amount, day)
                    if need_adj:
                        ledger[write_off] += top_up
                        _add_tx(need_adj)
                    ledger[write_off] -= base_amount
                    ledger[replenishment] = ledger.get(replenishment, 0.0) + base_amount
                    _add_tx(
                        RequestData(
                            list_name=ListName.transfers,
                            date=date_to_serial(day),
                            transfer_type=TransferType.transfer,
                            account=write_off,
                            replenishment_account=replenishment,
                            amount=_to_account_amount(base_amount, write_off),
                            replenishment_amount=_to_account_amount(base_amount, replenishment),
                            status=Status.committed,
                            comment=f"{run_id} transfer",
                        )
                    )
                    continue

                if (
                    kind_roll < config.transfer_prob + config.adjustment_prob
                    and account_pool
                ):
                    done_for_day = adjustments_today.setdefault(day, set())
                    target_adj_acc = random.choice(account_pool)
                    if target_adj_acc not in done_for_day:
                        adj_amount = round(random.uniform(-1500, 4000), 2)
                        if ledger[target_adj_acc] + adj_amount < 0:
                            adj_amount = -ledger[target_adj_acc]
                        if adj_amount == 0:
                            continue
                        ledger[target_adj_acc] += adj_amount
                        _add_tx(
                            RequestData(
                                list_name=ListName.transfers,
                                date=date_to_serial(day),
                                transfer_type=TransferType.adjustment,
                                account=target_adj_acc,
                                replenishment_account=target_adj_acc,
                                amount=0,
                                replenishment_amount=adj_amount,
                                status=Status.committed,
                                comment=f"{run_id} adhoc_adjust",
                            )
                        )
                        done_for_day.add(target_adj_acc)
                        last_adjustment_day = day
                        continue

                if expense_categories:
                    category = random.choice(expense_categories)
                    target_account = random.choice(account_pool)
                    max_amount = max(config.tx_min_fraction * salary_value, 200)
                    base_amount = round(
                        random.uniform(
                            max_amount, salary_value * config.tx_max_fraction
                        ),
                        2,
                    )
                    base_amount = min(base_amount, 15_000)
                    need_adj, top_up = _ensure_positive_balance(ledger, target_account, base_amount, day)
                    if need_adj:
                        ledger[target_account] += top_up
                        _add_tx(need_adj)
                    ledger[target_account] -= base_amount
                    _add_tx(
                        RequestData(
                            list_name=ListName.expenses,
                            date=date_to_serial(day),
                            expenses_category=category,
                            account=target_account,
                            amount=_to_account_amount(base_amount, target_account),
                            status=Status.committed,
                            comment=f"{run_id} expense",
                        )
                    )
                    expense_added = True
                    expense_added = True
                    expenses_count += 1
            if not expense_added and expense_categories and account_pool:
                category = random.choice(expense_categories)
                target_account = random.choice(account_pool)
                base_amount = 500.0
                need_adj, top_up = _ensure_positive_balance(ledger, target_account, base_amount, day)
                if need_adj:
                    ledger[target_account] += top_up
                    _add_tx(need_adj)
                ledger[target_account] -= base_amount
                _add_tx(
                    RequestData(
                        list_name=ListName.expenses,
                        date=date_to_serial(day),
                        expenses_category=category,
                        account=target_account,
                        amount=_to_account_amount(base_amount, target_account),
                        status=Status.committed,
                        comment=f"{run_id} expense",
                    )
                )
                expenses_count += 1

        # редкий adjustment если давно не было
        if (
            day - last_adjustment_day
        ).days >= config.adjustment_every_days and spend_account:
            adj_amount = round(random.uniform(-3000, 7000), 2)
            if ledger.get(spend_account, 0.0) + adj_amount < 0:
                adj_amount = -ledger.get(spend_account, 0.0)
            if adj_amount != 0:
                ledger[spend_account] += adj_amount
                _add_tx(
                    RequestData(
                        list_name=ListName.transfers,
                        date=date_to_serial(day),
                        transfer_type=TransferType.adjustment,
                        account=spend_account,
                        replenishment_account=spend_account,
                        amount=0,
                        replenishment_amount=_to_account_amount(adj_amount, spend_account),
                        status=Status.committed,
                        comment=f"{run_id} periodic_adjust",
                    )
                )
                last_adjustment_day = day

        day += timedelta(days=1)

    if expenses_count == 0 and expense_categories and account_pool:
        category = expense_categories[0]
        target_account = account_pool[0]
        base_amount = 500.0
        ledger[target_account] -= base_amount
        transactions.append(
            RequestData(
                list_name=ListName.expenses,
                date=date_to_serial(start_date),
                expenses_category=category,
                account=target_account,
                amount=_to_account_amount(base_amount, target_account),
                status=Status.committed,
                comment=f"{run_id} expense",
            )
        )
    if transfers_count == 0 and account_pool:
        acc = account_pool[0]
        transactions.append(
            RequestData(
                list_name=ListName.transfers,
                date=date_to_serial(start_date),
                transfer_type=TransferType.adjustment,
                account=acc,
                replenishment_account=acc,
                amount=0,
                replenishment_amount=_to_account_amount(1000.0, acc),
                status=Status.committed,
                comment=f"{run_id} ensure_transfer",
            )
        )

    return SimulationResult(
        run_id=run_id,
        seed=seed,
        transactions=transactions,
        ledger_summary=ledger,
        warnings=warnings,
    )


def apply_dev_history(
    sim: SimulationResult, reset: bool = True, batch_size: int = 200
) -> ApplyReport:
    """
    Применяет результаты симуляции в DEV-таблицу.
    """
    if reset:
        reset_dev_input_sheets()

    # гарантируем, что у всех вводных листов есть минимум строк для вставки над 7-й
    for lst in (ListName.expenses, ListName.incomes, ListName.transfers):
        ensure_min_rows(lst, 7)

    LOGGER.info(
        f"Applying run {sim.run_id} | total rows={len(sim.transactions)} "
        f"(expenses={sum(1 for t in sim.transactions if t.list_name==ListName.expenses)}, "
        f"incomes={sum(1 for t in sim.transactions if t.list_name==ListName.incomes)}, "
        f"transfers={sum(1 for t in sim.transactions if t.list_name==ListName.transfers)})"
    )

    requests = []
    for tx in sim.transactions:
        requests.append(
            get_insert_row_above_request(list_name=tx.list_name, insert_above_row=7)
        )
        requests.append(
            get_update_cells_request(
                list_name=tx.list_name,
                values_to_update=get_values_to_update_for_request(tx),
            )
        )

    batches_sent = 0
    total_batches = (len(requests) + batch_size * 2 - 1) // (batch_size * 2)
    for i in range(0, len(requests), batch_size * 2):
        chunk = requests[i : i + batch_size * 2]
        _SERVICE.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID, body={"requests": chunk}
        ).execute()
        batches_sent += 1
        if batches_sent % 5 == 0 or batches_sent == total_batches:
            LOGGER.info(
                f"Applied batch {batches_sent}/{total_batches} ({len(chunk)//2} rows)"
            )

    return ApplyReport(
        run_id=sim.run_id,
        inserted=len(sim.transactions),
        reset_done=reset,
        batches_sent=batches_sent,
    )


def run_dev_seed(
    seed: Optional[int] = None,
    overwrite_settings: bool = False,
    reset: bool = True,
    batch_size: Optional[int] = None,
) -> ApplyReport:
    """
    Удобный вход: читает дату начала, при желании заливает настройки, симулирует и применяет.
    """
    seed_value = seed if seed is not None else random.randint(1_000_000, 9_999_999)
    start_date = read_start_date_from_settings()
    end_date = date.today()

    seed_dev_settings(overwrite=overwrite_settings)

    sim = simulate_dev_history(
        seed=seed_value,
        start_date=start_date,
        end_date=end_date,
    )

    return apply_dev_history(sim, reset=reset, batch_size=batch_size or 200)
