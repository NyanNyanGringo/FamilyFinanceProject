"""
    # # # Расходы # # #
    # Дата A3 | Категория C3 | Счет D3 | Сумма E3 | Статус G3 | Комментарий J3

    # # # Переводы # # #
    # Дата A3 | Тип перевода C3 | Счет списания D3 | Счет пополнения E3 | Сумма списания F3 | Сумма пополнения I3 |
    # Статус L3 | Комментарий M3

    # # # Корректировки # # #
    # Дата A3 | Тип перевода C3 | Счет списания D3 | Счет пополнения E3 | Сумма корректировки I3 |
    # Статус L3 | Комментарий M3

    # # # Доходы # # #
    # Дата A3 | Категория C3 | Счет D3 | Сумма E3 | Статус G3 | Комментарий J3
"""
import logging

import os
import shutil
from datetime import datetime, timedelta
from enum import Enum
from typing import Union, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials, exceptions
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from lib.utilities.date_utilities import get_google_sheets_current_date
from lib.utilities.os_utilities import get_google_filepath, GoogleAuthType
from config import GOOGLE_SCOPES


# LOGGING


from lib.utilities.log_utilities import get_logger
LOGGER = get_logger(__name__)


load_dotenv()
SPREADSHEET_ID = os.getenv("GOOGLE_SPREADSHEET_ID")


def _authenticate_with_google():
    token_path = get_google_filepath(GoogleAuthType.TOKEN)
    credentials_path = get_google_filepath(GoogleAuthType.CREDENTIALS)
    old_tokens_path = get_google_filepath(GoogleAuthType.TOKEN_OLD)

    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, GOOGLE_SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except exceptions.RefreshError:
                os.makedirs(os.path.dirname(old_tokens_path), exist_ok=True)
                shutil.move(token_path, old_tokens_path)
                creds = None
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, GOOGLE_SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_path, "w") as token:
            token.write(creds.to_json())

    return creds


def _get_sheet_ids() -> dict:
    request = _SERVICE.spreadsheets().get(spreadsheetId=SPREADSHEET_ID)
    response = request.execute()

    sheet_ids = {}
    for sheet in (sheets := response.get('sheets', [])):
        title = sheet.get('properties', {}).get('title', 'No title found')
        sheet_id = sheet.get('properties', {}).get('sheetId', 'No ID found')

        sheet_ids[title] = sheet_id

    LOGGER.info(sheet_ids)

    return sheet_ids


_CREDS = _authenticate_with_google()
_SERVICE = build("sheets", "v4", credentials=_CREDS)
_SHEETS_IDS = _get_sheet_ids()


class _GoogleBaseEnumClass(Enum):
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
        else:
            LOGGER.info("Update not required: Less than 5 minutes since the last update.")


class Formulas(str, _GoogleBaseEnumClass):
    """Возвращает формулы из Google Tables, которые используются в FamilyFinanceProject"""

    # Месяц: 'Расходы'!B3:B | 'Переводы'!B3:B | 'Доходы'!B3:B
    month = """=DATE(TEXT($A3, "YYYY"), TEXT($A3, "M"), 1)"""

    # Сумма (Валюта): 'Расходы'!F3:F | 'Переводы'!G3:G | 'Доходы'!F3:F
    sum_currency = """=IF($D3<>"", VLOOKUP($D3, '*config'!J:K, 2, ""), "?")"""

    # Сумма списания в основной валюте: 'Переводы'!H3:H
    write_off_main_sum = """=IF(AND($D3<>"", $F3<>0), ROUND($F3 * VLOOKUP(VLOOKUP($D3, '*config'!J:K, 2, FALSE),
    '*config'!F:H, 3, FALSE), '*config'!$A$5), 0)"""

    # Сумма пополнения / Корректировки (Валюта): 'Переводы'!J3:J
    replenishment_currency_sum = """=IF($E3<>"", VLOOKUP($E3, '*config'!I:J, 2, ""), "?")"""

    # Сумма пополнения в основной валюте: 'Переводы'!K3:K
    replenishment_main_sum = """=IF(AND($E3<>"", $I3<>0), ROUND($I3 * VLOOKUP(VLOOKUP($E3, '*config'!J:K, 2, FALSE),
    '*config'!F:H, 3, FALSE), '*config'!$A$5), 0)"""

    # Сумма в основной валюте: 'Расходы'!H3:H | 'Доходы'!H3:H
    main_sum = """=IF($D3<>"", ROUND($E3 * VLOOKUP(VLOOKUP($D3, '*config'!J:K, 2, FALSE),
    '*config'!F:H, 3, FALSE), '*config'!$A$5), 0)"""

    # Сумма в основной валюте (Валюта): 'Расходы'!I3:I | 'Доходы'!I3:I
    main_sum_currency = """=IF($D3<>"", '*config'!$I$5, "?")"""


class OperationTypes(str, _GoogleBaseEnumClass):
    expenses = "Расходы"
    transfers = "Переводы"
    adjustment = "Корректировка"
    incomes = "Доходы"


class ListName(str, _GoogleBaseEnumClass):
    expenses = "Расходы"
    transfers = "Переводы"
    incomes = "Доходы"


class Status(str, _GoogleBaseEnumClass):
    committed = "Committed"
    planned = "Planned"


class TransferType(str, _GoogleBaseEnumClass):
    transfer = "Transfer"
    adjustment = "Adjustment"


class ConfigRange(str, _GoogleBaseEnumClass):
    incomes = "*config!B5:B105"
    expenses = "*config!C5:E105"
    currencies = "*config!F5:I105"
    accounts = "*config!J5:L105"


class RequestData(BaseModel):
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
    insert_row_above_request = {
        "insertDimension": {
            "range": {"sheetId": _SHEETS_IDS.get(list_name),
                      "dimension": "ROWS",
                      "startIndex": insert_above_row - 1,
                      "endIndex": insert_above_row},
            "inheritFromBefore": False
        }
    }
    return insert_row_above_request


def get_update_cells_request(list_name: ListName, values_to_update: list, row_index: int = 2, column_index: int = 0):
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
            {"userEnteredValue": {"stringValue": request_data.comment}}  # J3
        ]
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
            {"userEnteredValue": {"formulaValue": Formulas.write_off_main_sum}},  # H3
            {"userEnteredValue": {"numberValue": request_data.replenishment_amount}},  # I3
            {"userEnteredValue": {"formulaValue": Formulas.replenishment_currency_sum}},  # J3
            {"userEnteredValue": {"formulaValue": Formulas.replenishment_main_sum}},  # K3
            {"userEnteredValue": {"stringValue": request_data.status}},  # L3
            {"userEnteredValue": {"stringValue": request_data.comment}},  # M3
        ]

        return values_to_update


def insert_and_update_row_batch_update(request_data: RequestData):

    data_ok, message = request_data.validate_data()
    if not data_ok:
        raise ValueError(message)

    insert_row_request = get_insert_row_above_request(list_name=request_data.list_name,
                                                      insert_above_row=3)

    update_cells_request = get_update_cells_request(list_name=request_data.list_name,
                                                    values_to_update=get_values_to_update_for_request(request_data))

    body = {"requests": [insert_row_request, update_cells_request]}

    request = _SERVICE.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body)
    response = request.execute()

    LOGGER.info(f"{response=}")

    return response
