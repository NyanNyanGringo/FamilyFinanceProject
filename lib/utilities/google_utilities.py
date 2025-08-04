import logging

import os
from datetime import datetime, timedelta
from enum import Enum
from typing import Union, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from lib.utilities.date_utilities import get_google_sheets_current_date
from config import GOOGLE_SCOPES
from lib.utilities.os_utilities import _get_root_path


# LOGGING


from lib.utilities.log_utilities import get_logger
LOGGER = get_logger(__name__)


load_dotenv()
SPREADSHEET_ID = os.getenv("GOOGLE_SPREADSHEET_ID")


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


def _get_sheet_ids() -> dict:
    """
    Получает идентификаторы всех листов в Google Spreadsheet.

    Returns:
        dict: Словарь с названиями листов и их идентификаторами.
    """
    request = _SERVICE.spreadsheets().get(spreadsheetId=SPREADSHEET_ID)
    response = request.execute()

    sheet_ids = {}
    for sheet in (sheets := response.get('sheets', [])):
        title = sheet.get('properties', {}).get('title', 'No title found')
        sheet_id = sheet.get('properties', {}).get('sheetId', 'No ID found')

        sheet_ids[title] = sheet_id

    LOGGER.info(f"Sheet IDs: {sheet_ids}")
    
    # Подробное логирование для отладки
    for name, id in sheet_ids.items():
        LOGGER.info(f"Sheet: '{name}', ID: {id}")

    return sheet_ids


_CREDS = _authenticate_with_google()
_SERVICE = build("sheets", "v4", credentials=_CREDS)
_SHEETS_IDS = _get_sheet_ids()


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


class Category:
    """
    Класс для работы с категориями расходов, доходов и счетов.
    """
    _expenses = []  # категории расходов
    _incomes = []  # категории доходов
    _accounts = []  # счета
    _last_update_time = None  # последнее обновление

    def __init__(self):
        raise RuntimeError("Создание экземпляров класса Category не допускается. "
                           "Используйте методы и атрибуты напрямую.")

    @classmethod
    def get_expenses(cls):
        cls._update()
        return cls._expenses

    @classmethod
    def get_incomes(cls):
        cls._update()
        return cls._incomes

    @classmethod
    def get_accounts(cls) -> list:
        cls._update()
        return cls._accounts

    @classmethod
    def _update(cls):
        LOGGER.info("Update started.")
        if cls._last_update_time is None or datetime.now() - cls._last_update_time >= timedelta(minutes=5):
            LOGGER.info("Updating categories...")  # Для демонстрации, что метод вызывается
            cls._expenses = get_values(cell_range=ConfigRange.expenses, transform_to_single_list=True)
            cls._incomes = get_values(cell_range=ConfigRange.incomes, transform_to_single_list=True)
            cls._accounts = get_values(cell_range=ConfigRange.accounts, transform_to_single_list=True)
            cls._last_update_time = datetime.now()
            LOGGER.info(f"{cls._expenses=}")
            LOGGER.info(f"{cls._incomes=}")
            LOGGER.info(f"{cls._accounts=}")
        else:
            LOGGER.info("Update not required: Less than 5 minutes since the last update.")


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
    sheet = _SERVICE.spreadsheets()
    result = (
        sheet.values()
        .get(spreadsheetId=SPREADSHEET_ID, range=cell_range)
        .execute()
    )
    values = result.get("values", [])

    if transform_to_single_list:
        transformed_list = []
        for sublist in values:
            if value := sublist[0]:
                transformed_list.append(value)
        return transformed_list

    return values


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
    sheet_id = _SHEETS_IDS.get(list_name)
    
    # Подробное логирование для отладки
    LOGGER.info(f"Getting sheet_id for list_name: '{list_name}' (type: {type(list_name)})")
    LOGGER.info(f"Available sheet keys: {list(_SHEETS_IDS.keys())}")
    LOGGER.info(f"Sheet ID found: {sheet_id}")
    
    if sheet_id is None or sheet_id == 0:
        # Если ID не найден или равен 0, выведем ошибку
        raise ValueError(f"Invalid sheet ID {sheet_id} for list name '{list_name}'. Available sheets: {list(_SHEETS_IDS.keys())}")
    
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
    update_cells_request = {
        "updateCells": {
            "start": {"sheetId": _SHEETS_IDS.get(list_name),
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


def delete_row_by_telegram_id(list_name: ListName, telegram_message_id: str) -> bool:
    """
    Удаляет строку из Google Sheets по Telegram message ID.
    
    Args:
        list_name (ListName): Название листа для поиска.
        telegram_message_id (str): ID сообщения Telegram для поиска и удаления.
        
    Returns:
        bool: True если строка найдена и удалена, False если не найдена.
    """
    try:
        # Определяем столбец с Telegram ID в зависимости от типа листа
        if list_name == ListName.expenses:
            column = 'L'
        elif list_name == ListName.transfers:
            column = 'M'
        elif list_name == ListName.incomes:
            column = 'K'
        else:
            LOGGER.error(f"Unsupported list name: {list_name}")
            return False
            
        # Получаем все значения из столбца с Telegram IDs
        range_name = f"{list_name}!{column}:${column}"
        result = _SERVICE.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        # Ищем строку с нужным telegram_message_id
        row_to_delete = None
        for i, row in enumerate(values):
            if row and row[0] == telegram_message_id:
                row_to_delete = i + 1  # +1 так как индексация в Sheets начинается с 1
                break
                
        if row_to_delete is None:
            LOGGER.warning(f"Row with telegram_message_id {telegram_message_id} not found in {list_name}")
            return False
            
        # Удаляем строку
        delete_request = {
            "deleteDimension": {
                "range": {
                    "sheetId": _SHEETS_IDS.get(list_name),
                    "dimension": "ROWS",
                    "startIndex": row_to_delete - 1,  # -1 так как API использует 0-based индексы
                    "endIndex": row_to_delete
                }
            }
        }
        
        batch_update_request = {
            "requests": [delete_request]
        }
        
        response = _SERVICE.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body=batch_update_request
        ).execute()
        
        LOGGER.info(f"Successfully deleted row {row_to_delete} with telegram_message_id {telegram_message_id} from {list_name}")
        return True
        
    except Exception as e:
        LOGGER.error(f"Error deleting row by telegram_message_id: {e}")
        return False


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

    request = _SERVICE.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body)
    response = request.execute()

    LOGGER.info(f"{response=}")

    return response


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
        request = _SERVICE.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=cell_range,
            valueInputOption="RAW",
            body=body
        )
        response = request.execute()
        
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
        request = _SERVICE.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=cell_range,
            valueInputOption="RAW",
            body=body
        )
        response = request.execute()
        
        LOGGER.info(f"Воспоминание удалено: {deleted_memory}")
        return True
    except Exception as e:
        LOGGER.error(f"Ошибка при удалении воспоминания: {e}")
        return False
