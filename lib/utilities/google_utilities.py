import errno
import os
import socket
import ssl
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Optional, Union

from dotenv import load_dotenv
import google_auth_httplib2
import httplib2
from pydantic import BaseModel, Field

from google.auth.exceptions import TransportError
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from lib.utilities.date_utilities import get_google_sheets_current_date
from config import GOOGLE_SCOPES
from lib.utilities.os_utilities import _get_root_path


# LOGGING


from lib.utilities.log_utilities import get_logger
LOGGER = get_logger(__name__)


load_dotenv()


def _is_dev_mode() -> bool:
    return os.getenv("DEV", "").strip().lower() in {"1", "true", "yes", "on"}


def _get_spreadsheet_id() -> str:
    spreadsheet_env_var = "GOOGLE_SPREADSHEET_ID_DEV" if _is_dev_mode() else "GOOGLE_SPREADSHEET_ID"
    spreadsheet_id = os.getenv(spreadsheet_env_var)
    if not spreadsheet_id:
        raise ValueError(f"Missing required environment variable: {spreadsheet_env_var}")
    return spreadsheet_id


SPREADSHEET_ID = _get_spreadsheet_id()

GOOGLE_READ_ATTEMPTS = 3
GOOGLE_READ_RETRY_DELAYS = (0.5, 1.0)
GOOGLE_READ_TIMEOUT_SECONDS = 5
GOOGLE_WRITE_TIMEOUT_SECONDS = 30
FINANCE_CONFIG_TTL_SECONDS = 5 * 60
TRANSIENT_NETWORK_ERRNOS = {
    errno.ECONNABORTED,
    errno.ECONNREFUSED,
    errno.ECONNRESET,
    errno.EHOSTUNREACH,
    errno.ENETDOWN,
    errno.ENETRESET,
    errno.ENETUNREACH,
    errno.EPIPE,
    errno.ETIMEDOUT,
}


class GoogleWriteOutcomeUnknownError(RuntimeError):
    pass


def _authenticate_with_google():
    """
    Аутентифицирует пользователя с помощью Google Service Account и возвращает объект учётных данных.

    Returns:
        Credentials: Объект учётных данных Google.
    """
    service_account_path = os.path.join(_get_root_path(), ".google_service_account_credentials.json")
    
    if not os.path.exists(service_account_path):
        raise FileNotFoundError(f"Service Account key file not found at: {service_account_path}")
    
    creds = Credentials.from_service_account_file(service_account_path, scopes=GOOGLE_SCOPES)
    
    return creds


_CREDENTIALS = None
_CREDENTIALS_LOCK = threading.Lock()
_GOOGLE_REQUEST_LOCK = threading.Lock()


def _get_credentials():
    global _CREDENTIALS

    with _CREDENTIALS_LOCK:
        if _CREDENTIALS is None:
            _CREDENTIALS = _authenticate_with_google()
        return _CREDENTIALS


def _build_service(timeout_seconds: int):
    credentials = _get_credentials()
    transport = httplib2.Http(timeout=timeout_seconds)
    authorized_transport = google_auth_httplib2.AuthorizedHttp(
        credentials,
        http=transport,
    )
    return build(
        "sheets",
        "v4",
        http=authorized_transport,
        cache_discovery=False,
    )


def _close_service(service) -> None:
    close = getattr(service, "close", None)
    if callable(close):
        try:
            close()
        except Exception:
            LOGGER.exception("Failed to close Google Sheets transport")


def _is_transient_google_error(error: Exception) -> bool:
    if isinstance(error, HttpError):
        status = getattr(error.resp, "status", None)
        return status in {408, 429} or (status is not None and 500 <= status < 600)

    if isinstance(error, OSError) and error.errno in TRANSIENT_NETWORK_ERRNOS:
        return True

    return isinstance(
        error,
        (
            ConnectionError,
            TransportError,
            TimeoutError,
            httplib2.ProxiesUnavailableError,
            httplib2.ServerNotFoundError,
            socket.gaierror,
            socket.timeout,
            ssl.SSLError,
        ),
    )


def _execute_read(request_factory: Callable, attempts: int = GOOGLE_READ_ATTEMPTS):
    for attempt in range(attempts):
        service = None
        try:
            with _GOOGLE_REQUEST_LOCK:
                service = _build_service(GOOGLE_READ_TIMEOUT_SECONDS)
                request = request_factory(service)
                return request.execute(num_retries=0)
        except Exception as error:
            last_attempt = attempt == attempts - 1
            if last_attempt or not _is_transient_google_error(error):
                raise

            delay_index = min(attempt, len(GOOGLE_READ_RETRY_DELAYS) - 1)
            delay = GOOGLE_READ_RETRY_DELAYS[delay_index]
            LOGGER.warning(
                "Transient Google Sheets read failure. Retry %s/%s in %.1fs: %s",
                attempt + 2,
                attempts,
                delay,
                error,
            )
            time.sleep(delay)
        finally:
            if service is not None:
                _close_service(service)

    raise RuntimeError("Google Sheets read retry loop ended unexpectedly")


def _execute_write(request_factory: Callable):
    service = None
    try:
        with _GOOGLE_REQUEST_LOCK:
            service = _build_service(GOOGLE_WRITE_TIMEOUT_SECONDS)
            request = request_factory(service)
            try:
                return request.execute(num_retries=0)
            except Exception as error:
                if _is_transient_google_error(error):
                    raise GoogleWriteOutcomeUnknownError(
                        "Google Sheets write outcome is unknown"
                    ) from error
                raise
    finally:
        if service is not None:
            _close_service(service)


_SHEET_IDS_LOCK = threading.Lock()
_SHEETS_IDS = None


def _get_sheet_ids(force_refresh: bool = False) -> dict:
    """
    Получает идентификаторы всех листов в Google Spreadsheet.

    Returns:
        dict: Словарь с названиями листов и их идентификаторами.
    """
    global _SHEETS_IDS

    with _SHEET_IDS_LOCK:
        if _SHEETS_IDS is not None and not force_refresh:
            return _SHEETS_IDS.copy()

        response = _execute_read(
            lambda service: service.spreadsheets().get(
                spreadsheetId=SPREADSHEET_ID,
                fields="sheets(properties(sheetId,title))",
            )
        )
        sheet_ids = {
            sheet.get("properties", {}).get("title"): sheet.get("properties", {}).get("sheetId")
            for sheet in response.get("sheets", [])
            if sheet.get("properties", {}).get("title") is not None
        }
        _SHEETS_IDS = sheet_ids

    LOGGER.info("Loaded %s Google Sheet IDs", len(sheet_ids))
    return sheet_ids.copy()


def _get_sheet_row_count(list_name) -> int:
    """
    Возвращает количество строк листа по его названию.
    """
    response = _execute_read(
        lambda service: service.spreadsheets().get(
            spreadsheetId=SPREADSHEET_ID,
            fields="sheets(properties(sheetId,title,gridProperties(rowCount,columnCount)))",
        )
    )
    for sheet in response.get("sheets", []):
        props = sheet.get("properties", {})
        if props.get("title") == str(list_name):
            return props.get("gridProperties", {}).get("rowCount", 0)
    return 0


def ensure_min_rows(list_name, min_rows: int = 7) -> None:
    """
    Гарантирует, что лист имеет не меньше min_rows строк (нужно для вставки над строкой 7).
    """
    row_count = _get_sheet_row_count(list_name)
    if row_count >= min_rows:
        return
    sheet_ids = _get_sheet_ids()
    append_request = {
        "appendDimension": {
            "sheetId": sheet_ids.get(str(list_name)),
            "dimension": "ROWS",
            "length": min_rows - row_count,
        }
    }
    _execute_write(
        lambda service: service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"requests": [append_request]},
        )
    )
    LOGGER.info(f"Extended sheet {list_name} rows from {row_count} to {min_rows}")


class _GoogleBaseEnumClass(Enum):
    """
    Базовый класс для перечислений Google с дополнительными методами.
    """
    def __str__(self):
        return self.value

    @classmethod
    def values(cls):
        return [item.value for item in cls]

    @classmethod
    def get_item(cls, value: str):
        for item in cls:
            if item.value == value:
                return item
        raise ValueError(f"{value} is not a valid value for {cls.__name__}")


@dataclass(frozen=True)
class FinanceConfigSnapshot:
    expenses: tuple[str, ...]
    incomes: tuple[str, ...]
    accounts: tuple[str, ...]
    loaded_at: datetime


@dataclass(frozen=True)
class FinanceConfigResult:
    snapshot: FinanceConfigSnapshot
    used_stale: bool = False
    refresh_error: Optional[str] = None


class FinanceConfigUnavailableError(RuntimeError):
    pass


def _single_column_values(value_range: dict) -> tuple[str, ...]:
    values = []
    for row in value_range.get("values", []):
        if not isinstance(row, list):
            raise ValueError("Finance configuration row must be a list")
        if not row or row[0] in {None, ""}:
            continue
        if not isinstance(row[0], str):
            raise ValueError("Finance configuration value must be a string")
        values.append(row[0])
    return tuple(values)


def _normalize_a1_range(range_name: str) -> str:
    sheet_name, cells = range_name.split("!", maxsplit=1)
    normalized_sheet_name = sheet_name.strip("'")
    return f"{normalized_sheet_name}!{cells.upper()}"


def _load_finance_config_snapshot() -> FinanceConfigSnapshot:
    ranges = [
        str(ConfigRange.expenses),
        str(ConfigRange.incomes),
        str(ConfigRange.accounts),
    ]
    response = _execute_read(
        lambda service: service.spreadsheets().values().batchGet(
            spreadsheetId=SPREADSHEET_ID,
            ranges=ranges,
        )
    )
    if not isinstance(response, dict):
        raise ValueError("Google Sheets returned an invalid finance configuration payload")
    value_ranges = response.get("valueRanges", [])
    if not isinstance(value_ranges, list):
        raise ValueError("Google Sheets valueRanges must be a list")
    if len(value_ranges) != len(ranges):
        raise ValueError(
            f"Expected {len(ranges)} finance config ranges, got {len(value_ranges)}"
        )

    for expected_range, value_range in zip(ranges, value_ranges):
        if not isinstance(value_range, dict):
            raise ValueError("Google Sheets valueRange must be an object")
        actual_range = value_range.get("range")
        if actual_range and _normalize_a1_range(actual_range) != _normalize_a1_range(
            expected_range
        ):
            raise ValueError(
                f"Expected finance config range {expected_range}, got {actual_range}"
            )

    expenses, incomes, accounts = map(_single_column_values, value_ranges)
    if not expenses or not incomes or not accounts:
        raise ValueError("Google Sheets returned an incomplete finance configuration")

    return FinanceConfigSnapshot(
        expenses=expenses,
        incomes=incomes,
        accounts=accounts,
        loaded_at=datetime.now(timezone.utc),
    )


class FinanceConfigCache:
    def __init__(
        self,
        loader: Callable[[], FinanceConfigSnapshot] = _load_finance_config_snapshot,
        ttl_seconds: float = FINANCE_CONFIG_TTL_SECONDS,
        monotonic: Callable[[], float] = time.monotonic,
    ):
        self._loader = loader
        self._ttl_seconds = ttl_seconds
        self._monotonic = monotonic
        self._lock = threading.Lock()
        self._snapshot = None
        self._loaded_monotonic = None

    def get(self, force_refresh: bool = False) -> FinanceConfigResult:
        with self._lock:
            now = self._monotonic()
            if not force_refresh and self._is_fresh(now):
                return FinanceConfigResult(snapshot=self._snapshot)

            try:
                refreshed_snapshot = self._loader()
            except Exception as error:
                if self._snapshot is None:
                    raise FinanceConfigUnavailableError(
                        "Finance configuration has not been loaded"
                    ) from error

                LOGGER.exception(
                    "Finance configuration refresh failed. Using last known good snapshot."
                )
                return FinanceConfigResult(
                    snapshot=self._snapshot,
                    used_stale=True,
                    refresh_error=str(error),
                )

            self._snapshot = refreshed_snapshot
            self._loaded_monotonic = self._monotonic()
            LOGGER.info(
                "Finance configuration refreshed: expenses=%s, incomes=%s, accounts=%s",
                len(refreshed_snapshot.expenses),
                len(refreshed_snapshot.incomes),
                len(refreshed_snapshot.accounts),
            )
            return FinanceConfigResult(snapshot=refreshed_snapshot)

    def _is_fresh(self, now: float) -> bool:
        if self._snapshot is None or self._loaded_monotonic is None:
            return False
        return now - self._loaded_monotonic < self._ttl_seconds


_FINANCE_CONFIG_CACHE = FinanceConfigCache()


def get_finance_config() -> FinanceConfigResult:
    return _FINANCE_CONFIG_CACHE.get()


def reload_finance_config() -> FinanceConfigResult:
    return _FINANCE_CONFIG_CACHE.get(force_refresh=True)


class Category:
    """Compatibility facade for code that does not yet pass a snapshot."""

    def __init__(self):
        raise RuntimeError(
            "Создание экземпляров класса Category не допускается. "
            "Используйте методы и атрибуты напрямую."
        )

    @classmethod
    def get_expenses(cls) -> list[str]:
        return list(get_finance_config().snapshot.expenses)

    @classmethod
    def get_incomes(cls) -> list[str]:
        return list(get_finance_config().snapshot.incomes)

    @classmethod
    def get_accounts(cls) -> list[str]:
        return list(get_finance_config().snapshot.accounts)

    @classmethod
    def force_update(cls) -> FinanceConfigResult:
        return reload_finance_config()


class Formulas(str, _GoogleBaseEnumClass):
    """
    Класс-строка для хранения формул Google Tables, используемых в проекте.
    """

    # Месяц: 'Расходы'!B3:B | 'Переводы'!B3:B | 'Доходы'!B3:B
    month = """=LET(
  _date,
  INDEX($A:$A, ROW()),
  DATE(VALUE(TEXT(_date, "YYYY")), VALUE(TEXT(_date, "M")), 1)
  )
"""

    # Сумма (Валюта): 'Расходы'!F3:F | 'Переводы'!G3:G | 'Доходы'!F3:F
    sum_currency = """=IFERROR(
  VLOOKUP(
    INDEX($D:$D, ROW()),
    {_account_fullnames, _account_currency_codes},
    2,
    FALSE
    ),
  "?"
  )"""

    # Сумма пополнения в основной валюте: 'Переводы'!I3:
    replenishment_main_sum = """=IFERROR(
  VLOOKUP(
    INDEX($E:$E, ROW()),
    {_account_fullnames, _account_currency_codes},
    2,
    FALSE
    ),
  "?"
  )"""

    # Сумма пополнения (Валюта): 'Переводы'!I3:I
    replenishment_currency_sum = """=IFERROR(
  VLOOKUP(
    INDEX($E:$E, ROW()),
    {_account_fullnames, _account_currency_codes},
    2,
    FALSE
    ),
  "?"
  )"""

    # Сумма в основной валюте: 'Расходы'!H3:H | 'Доходы'!H3:H
    main_sum = """=IF(
  INDEX($D:$D, ROW())<>"",
  IFERROR(
    ROUND(
      INDEX($E:$E, ROW()) * VLOOKUP(VLOOKUP(INDEX($D:$D, ROW()), {_account_fullnames, _account_currency_codes}, 2, FALSE), _currencies, 3, FALSE), _userconfig_round_to),
    "ERROR"
  ),
  ""
)
"""

    # Сумма в основной валюте (Валюта): 'Расходы'!I3:I | 'Доходы'!I3:I
    main_sum_currency = """=IF(
    INDEX($D:$D, ROW())<>"",
    main_currency,
    "?"
    )"""


class OperationTypes(str, _GoogleBaseEnumClass):
    """
    Перечисление типов операций: расходы, переводы, корректировки, доходы.
    """
    expenses = "Расходы"
    transfers = "Переводы"
    adjustment = "Корректировка"
    incomes = "Доходы"


class ListName(str, _GoogleBaseEnumClass):
    """
    Перечисление названий листов для разных типов операций.
    """
    expenses = "↙️Расходы"
    transfers = "🔄Переводы"
    incomes = "↗️Доходы"
    memory = "#memory"
    expenses_status = "/expenses_status"


class Status(str, _GoogleBaseEnumClass):
    """
    Перечисление статусов операции: подтверждена, запланирована.
    """
    committed = "Committed"
    planned = "Planned"


class TransferType(str, _GoogleBaseEnumClass):
    """
    Перечисление типов переводов: перевод, корректировка.
    """
    transfer = "Transfer"
    adjustment = "Adjustment"


class ConfigRange(str, _GoogleBaseEnumClass):
    """
    Перечисление диапазонов ячеек для конфигурации Google Sheets.
    """
    incomes = "*data!AL7:AL199"
    expenses = "*data!AK7:AK199"
    accounts = "*data!M7:M199"
    # currencies = "*data!F5:I105"


class RequestData(BaseModel):
    """
    Дата-класс для хранения данных запроса к Google Sheets.
    """
    list_name: ListName
    date: int = Field(default_factory=get_google_sheets_current_date)
    incomes_category: Optional[str] = None
    expenses_category: Optional[str] = None
    transfer_type: Optional[TransferType] = None
    account: str  # also known as write_off_account
    replenishment_account: Optional[str] = None
    amount: Union[int, float]  # also known as write_off_amount
    replenishment_amount: Optional[Union[int, float]] = None
    status: Status = Status.committed
    comment: str = ""
    telegram_message_id: Optional[str] = None

    def validate_data(self) -> (bool, str):
        message = ""

        if self.list_name == ListName.transfers and self.replenishment_account is None:
            message = f"Please specify replenishment_account. It can't be {self.replenishment_account}"
            return False, message

        if self.list_name == ListName.transfers and self.amount is None:
            message = f"Please specify write_off_amount. It can't be {self.write_off_amount}"
            return False, message

        if self.transfer_type == "Adjustment" and self.account != self.replenishment_account:
            message = f"Using Adjustment transfer_type, account and replenishment_account must be equal."
            return False, message

        if self.list_name == ListName.expenses and not self.expenses_category:
            message = f"Please specify expenses_category category."
            return False, message

        if self.list_name == ListName.incomes and not self.incomes_category:
            message = f"Please specify incomes_category category."
            return False, message

        return True, message


def get_values(cell_range: str or ConfigRange, transform_to_single_list: bool = False) -> list:
    """
    Получает значения из Google Sheets по указанному диапазону.

    Args:
        cell_range (str | ConfigRange): Диапазон ячеек.
        transform_to_single_list (bool): Преобразовать в одномерный список.

    Returns:
        list: Список значений из Google Sheets.
    """
    result = _execute_read(
        lambda service: service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=cell_range,
        )
    )
    values = result.get("values", [])

    if transform_to_single_list:
        transformed_list = []
        for sublist in values:
            if value := sublist[0]:
                transformed_list.append(value)
        return transformed_list

    return values


def update_values(range_name: str, values: list[list], value_input_option: str = "USER_ENTERED") -> dict:
    """
    Обновляет значения в указанном диапазоне Google Sheets.

    Args:
        range_name (str): Диапазон для обновления (например, '⚙️Настройки!A18:B29').
        values (list[list]): Двумерный список значений.
        value_input_option (str): Способ записи ('USER_ENTERED' или 'RAW').

    Returns:
        dict: Ответ от Google Sheets API.
    """
    return _execute_write(
        lambda service: service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption=value_input_option,
            body={"values": values},
        )
    )


def batch_update(body: dict) -> dict:
    """Executes one Google Sheets batchUpdate without automatic write retries."""
    return _execute_write(
        lambda service: service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body=body,
        )
    )


def get_insert_row_above_request(list_name:  ListName, insert_above_row: int) -> dict:
    """
    Создает запрос для вставки новой строки в Google Sheets.

    Args:
        list_name (ListName): Название листа, в который нужно вставить строку.
        insert_above_row (int): Номер строки, выше которой нужно вставить новую строку.

    Returns:
        dict: Запрос для вставки строки в формате Google Sheets API.

    Raises:
        ValueError: Если ID листа не найден или равен 0.
    """
    sheet_ids = _get_sheet_ids()
    sheet_id = sheet_ids.get(str(list_name))
    
    # Подробное логирование для отладки
    if sheet_id is None or sheet_id == 0:
        # Если ID не найден или равен 0, выведем ошибку
        raise ValueError(
            f"Invalid sheet ID {sheet_id} for list name '{list_name}'. "
            f"Available sheets: {list(sheet_ids.keys())}"
        )
    
    insert_row_above_request = {
        "insertDimension": {
            "range": {"sheetId": sheet_id,
                      "dimension": "ROWS",
                      "startIndex": insert_above_row - 1,
                      "endIndex": insert_above_row},
            "inheritFromBefore": False
        }
    }
    return insert_row_above_request


def get_update_cells_request(list_name: ListName, values_to_update: list, row_index: int = 6, column_index: int = 0):
    """
    Создает запрос для обновления ячеек в Google Sheets.

    Args:
        list_name (ListName): Название листа для обновления.
        values_to_update (list): Список значений для обновления.
        row_index (int, optional): Индекс начальной строки. По умолчанию 6.
        column_index (int, optional): Индекс начального столбца. По умолчанию 0.

    Returns:
        dict: Запрос для обновления ячеек в формате Google Sheets API.
    """
    sheet_ids = _get_sheet_ids()
    update_cells_request = {
        "updateCells": {
            "start": {"sheetId": sheet_ids.get(str(list_name)),
                      "rowIndex": row_index,
                      "columnIndex": column_index},
            "rows": [{"values": values_to_update}],
            "fields": "userEnteredValue"
        }
    }
    return update_cells_request


def get_values_to_update_for_request(request_data: RequestData) -> list:
    """
    Формирует список значений для обновления в Google Sheets на основе данных запроса.

    Args:
        request_data (RequestData): Данные запроса, содержащие информацию для обновления.

    Returns:
        list: Список значений для обновления в формате Google Sheets API.
    """
    if request_data.list_name in (ListName.expenses, ListName.incomes):
        if request_data.list_name == ListName.expenses:
            categoty = request_data.expenses_category
        else:
            categoty = request_data.incomes_category
        values_to_update = [
            {"userEnteredValue": {"numberValue": request_data.date}},  # A3
            {"userEnteredValue": {"formulaValue": Formulas.month}},  # B3
            {"userEnteredValue": {"stringValue": categoty}},  # C3
            {"userEnteredValue": {"stringValue": request_data.account}},  # D3
            {"userEnteredValue": {"numberValue": request_data.amount}},  # E3
            {"userEnteredValue": {"formulaValue": Formulas.sum_currency}},  # F3
            {"userEnteredValue": {"stringValue": request_data.status}},  # G3
            {"userEnteredValue": {"formulaValue": Formulas.main_sum}},  # H3
            {"userEnteredValue": {"formulaValue": Formulas.main_sum_currency}},  # I3
            {"userEnteredValue": {"stringValue": request_data.comment}},  # J3
            # {"userEnteredValue": {"stringValue": request_data.debtor}},  # K3
        ]
        
        # Add Telegram message ID to appropriate column based on list type
        if request_data.telegram_message_id:
            if request_data.list_name == ListName.expenses:
                # Add empty cell for K3 (debtor) and telegram_message_id for L3
                values_to_update.extend([
                    {"userEnteredValue": {"stringValue": ""}},  # K3 - debtor
                    {"userEnteredValue": {"stringValue": request_data.telegram_message_id}}  # L3
                ])
            elif request_data.list_name == ListName.incomes:
                # Add telegram_message_id for K3
                values_to_update.append(
                    {"userEnteredValue": {"stringValue": request_data.telegram_message_id}}  # K3
                )
        return values_to_update

    elif request_data.list_name == ListName.transfers:
        values_to_update = [
            {"userEnteredValue": {"numberValue": request_data.date}},  # A3
            {"userEnteredValue": {"formulaValue": Formulas.month}},  # B3
            {"userEnteredValue": {"stringValue": request_data.transfer_type}},  # C3
            {"userEnteredValue": {"stringValue": request_data.account}},  # D3
            {"userEnteredValue": {"stringValue": request_data.replenishment_account}},  # E3
            {"userEnteredValue": {"numberValue": request_data.amount}},  # F3
            {"userEnteredValue": {"formulaValue": Formulas.sum_currency}},  # G3
            {"userEnteredValue": {"numberValue": request_data.replenishment_amount}},  # H3
            {"userEnteredValue": {"formulaValue": Formulas.replenishment_currency_sum}},  # I3
            {"userEnteredValue": {"stringValue": request_data.status}},  # J3
            {"userEnteredValue": {"stringValue": request_data.comment}},  # K3
        ]
        
        # Add Telegram message ID for transfers in column M
        if request_data.telegram_message_id:
            values_to_update.extend([
                {"userEnteredValue": {"boolValue": False}},  # L3 - "Долг возвращен"
                {"userEnteredValue": {"stringValue": request_data.telegram_message_id}}  # M3
            ])

        return values_to_update


def _telegram_id_column(list_name: ListName) -> str:
    columns = {
        ListName.expenses: "L",
        ListName.transfers: "M",
        ListName.incomes: "K",
    }
    try:
        return columns[list_name]
    except KeyError as error:
        raise ValueError(f"Unsupported list name: {list_name}") from error


def find_rows_by_telegram_id(
    list_name: ListName,
    telegram_message_id: str,
) -> tuple[int, ...]:
    column = _telegram_id_column(list_name)
    range_name = f"{list_name}!{column}:${column}"
    result = _execute_read(
        lambda service: service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
        )
    )
    expected_id = str(telegram_message_id)
    return tuple(
        row_index
        for row_index, row in enumerate(result.get("values", []), start=1)
        if row and str(row[0]) == expected_id
    )


def delete_row_by_telegram_id(list_name: ListName, telegram_message_id: str) -> bool:
    """
    Удаляет строку из Google Sheets по Telegram message ID.
    
    Args:
        list_name (ListName): Название листа для поиска.
        telegram_message_id (str): ID сообщения Telegram для поиска и удаления.
        
    Returns:
        bool: True если строка найдена и удалена, False если не найдена.
    """
    matching_rows = find_rows_by_telegram_id(list_name, telegram_message_id)
    if not matching_rows:
        LOGGER.warning(f"Row with telegram_message_id {telegram_message_id} not found in {list_name}")
        return False
    if len(matching_rows) > 1:
        LOGGER.error(
            "Refusing to delete duplicate telegram_message_id %s from %s: rows=%s",
            telegram_message_id,
            list_name,
            matching_rows,
        )
        return False

    row_to_delete = matching_rows[0]

    delete_request = {
        "deleteDimension": {
            "range": {
                "sheetId": _get_sheet_ids().get(str(list_name)),
                "dimension": "ROWS",
                "startIndex": row_to_delete - 1,
                "endIndex": row_to_delete,
            }
        }
    }

    _execute_write(
        lambda service: service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"requests": [delete_request]},
        )
    )

    LOGGER.info(
        "Successfully deleted row %s with telegram_message_id %s from %s",
        row_to_delete,
        telegram_message_id,
        list_name,
    )
    return True


def insert_and_update_row_batch_update(request_data: RequestData):
    """
    Выполняет пакетное обновление Google Sheets: вставляет новую строку и обновляет её значения.

    Args:
        request_data (RequestData): Данные для обновления таблицы.

    Returns:
        dict: Ответ от Google Sheets API с результатами выполнения запроса.

    Raises:
        ValueError: Если данные запроса не прошли валидацию.
    """
    data_ok, message = request_data.validate_data()
    if not data_ok:
        raise ValueError(message)

    insert_row_request = get_insert_row_above_request(list_name=request_data.list_name,
                                                      insert_above_row=7)

    update_cells_request = get_update_cells_request(list_name=request_data.list_name,
                                                    values_to_update=get_values_to_update_for_request(request_data))

    body = {"requests": [insert_row_request, update_cells_request]}

    response = _execute_write(
        lambda service: service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body=body,
        )
    )

    LOGGER.info(f"{response=}")

    return response


def reset_input_sheet_preserve_template(list_name: ListName) -> None:
    """
    Удаляет все заполненные строки на вводном листе, сохраняя нижнюю пустую шаблонную строку.

    Алгоритм:
    - читаем значения в колонке A, начиная с 7-й строки;
    - count = len(values); если count > 0 — удаляем строки [6, 6+count) (0-based);
    - пустая строка сразу под блоком останется и поднимется на 7-ю строку.
    """
    row_count = _get_sheet_row_count(list_name)
    if row_count <= 6:
        LOGGER.info(f"Sheet {list_name} has no data rows (row_count={row_count}), skip reset.")
        return

    range_name = f"{list_name}!A7:A{row_count}"
    result = _execute_read(
        lambda service: service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
        )
    )
    values = result.get("values", [])

    rows_to_delete = len(values)
    if rows_to_delete <= 0:
        LOGGER.info(f"No rows to reset for {list_name}")
        return

    delete_request = {
        "deleteDimension": {
            "range": {
                "sheetId": _get_sheet_ids().get(str(list_name)),
                "dimension": "ROWS",
                "startIndex": 6,
                "endIndex": 6 + rows_to_delete
            }
        }
    }

    body = {"requests": [delete_request]}
    try:
        _execute_write(
            lambda service: service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body=body,
            )
        )
        LOGGER.info(f"Reset {rows_to_delete} rows on sheet {list_name}, template preserved.")
    except HttpError as e:
        message = str(e)
        if "not possible to delete all non-frozen rows" in message:
            if rows_to_delete <= 1:
                LOGGER.warning(
                    f"Skip reset for {list_name}: cannot delete last non-frozen row (rows_to_delete={rows_to_delete})."
                )
                return
            adjusted_delete = rows_to_delete - 1
            LOGGER.warning(
                f"Retry reset for {list_name} with adjusted rows ({adjusted_delete}) "
                "to avoid deleting all non-frozen rows."
            )
            delete_request["deleteDimension"]["range"]["endIndex"] = 6 + adjusted_delete
            _execute_write(
                lambda service: service.spreadsheets().batchUpdate(
                    spreadsheetId=SPREADSHEET_ID,
                    body={"requests": [delete_request]},
                )
            )
            LOGGER.info(f"Reset {adjusted_delete} rows on sheet {list_name}, template preserved (adjusted).")
        else:
            LOGGER.error(f"Failed to reset sheet {list_name}: {e}")
            raise


def reset_dev_input_sheets():
    """
    Выполняет reset для всех вводных листов DEV: расходы, доходы, переводы.
    """
    for list_name in (ListName.expenses, ListName.incomes, ListName.transfers):
        reset_input_sheet_preserve_template(list_name)
    # После ресета гарантируем наличие хотя бы 7 строк (шапка + шаблонная строка)
    for list_name in (ListName.expenses, ListName.incomes, ListName.transfers):
        ensure_min_rows(list_name, 7)


def get_memories() -> list[str]:
    """
    Получает список сохранённых воспоминаний из ячейки A1 листа #memory.
    
    Returns:
        list[str]: Список воспоминаний. Пустой список, если воспоминаний нет.
    """
    try:
        cell_range = f"{ListName.memory}!A1"
        values = get_values(cell_range)
        
        if not values or not values[0] or not values[0][0]:
            return []
        
        memories_text = values[0][0]
        memories = [m.strip() for m in memories_text.split('\n') if m.strip()]
        return memories
    except Exception as e:
        LOGGER.error(f"Ошибка при получении воспоминаний: {e}")
        return []


def add_memory(memory_text: str) -> bool:
    """
    Добавляет новое воспоминание в ячейку A1 листа #memory.
    
    Args:
        memory_text (str): Текст воспоминания для добавления.
        
    Returns:
        bool: True если успешно добавлено, False в случае ошибки.
    """
    try:
        current_memories = get_memories()
        current_memories.append(memory_text.strip())
        
        new_memories_text = '\n'.join(current_memories)
        
        body = {
            "values": [[new_memories_text]]
        }
        
        cell_range = f"{ListName.memory}!A1"
        _execute_write(
            lambda service: service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=cell_range,
                valueInputOption="RAW",
                body=body,
            )
        )
        
        LOGGER.info(f"Воспоминание добавлено: {memory_text}")
        return True
    except Exception as e:
        LOGGER.error(f"Ошибка при добавлении воспоминания: {e}")
        return False


def delete_memory(memory_index: int) -> bool:
    """
    Удаляет воспоминание по индексу из ячейки A1 листа #memory.
    
    Args:
        memory_index (int): Индекс воспоминания для удаления (0-based).
        
    Returns:
        bool: True если успешно удалено, False в случае ошибки.
    """
    try:
        current_memories = get_memories()
        
        if memory_index < 0 or memory_index >= len(current_memories):
            LOGGER.error(f"Неверный индекс воспоминания: {memory_index}")
            return False
        
        deleted_memory = current_memories.pop(memory_index)
        
        new_memories_text = '\n'.join(current_memories) if current_memories else ""
        
        body = {
            "values": [[new_memories_text]]
        }
        
        cell_range = f"{ListName.memory}!A1"
        _execute_write(
            lambda service: service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=cell_range,
                valueInputOption="RAW",
                body=body,
            )
        )
        
        LOGGER.info(f"Воспоминание удалено: {deleted_memory}")
        return True
    except Exception as e:
        LOGGER.error(f"Ошибка при удалении воспоминания: {e}")
        return False
