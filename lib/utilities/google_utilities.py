import logging
import os
import enum

from dotenv import load_dotenv

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from lib.utilities.os_utilities import get_google_filepath, GoogleAuthType
from config import GOOGLE_SCOPES


# public


SPREADSHEET_ID = os.getenv("GOOGLE_SPREADSHEET_ID")


# private


def _authenticate_with_google():
    token_path = get_google_filepath(GoogleAuthType.TOKEN)
    credentials_path = get_google_filepath(GoogleAuthType.CREDENTIALS)

    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, GOOGLE_SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
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

    logging.info(sheet_ids)

    return sheet_ids


_CREDS = _authenticate_with_google()
_SERVICE = build("sheets", "v4", credentials=_CREDS)
_SHEETS_IDS = _get_sheet_ids()


# public


class FamilyFinanceData(enum.Enum):
    # ranges
    incomes_category_range = "*config!B5:B105"
    expenses_category_range = "*config!C5:E105"
    currencies_range = "*config!F5:H105"
    accounts_range = "*config!I5:K105"

    # sheet_names
    expenses_sheet_name = "Расходы"
    transfers_sheet_name = "Переводы"
    incomes_sheet_name = "Доходы"
    balance_sheet_name = "Баланс"
    config_sheet_name = "*config"


def get_values(cell_range: str or FamilyFinanceData):
    sheet = _SERVICE.spreadsheets()
    result = (
        sheet.values()
        .get(spreadsheetId=SPREADSHEET_ID, range=cell_range)
        .execute()
    )
    return result.get("values", [])


def insert_new_row():
    batch_update_spreadsheet_request_body = {
        "requests": [
            {
                "insertDimension": {
                    "range": {
                        # ID листа, можно узнать из URL, если не известен
                        "sheetId": _SHEETS_IDS.get(FamilyFinanceData.expenses_sheet_name.value),
                        "dimension": "ROWS",
                        "startIndex": 2,  # Строка перед которой вставить новую строку (нумерация с нуля)
                        "endIndex": 3   # startIndex + 1 для вставки одной строки
                    }
                }
            }
        ]
    }

    request = _SERVICE.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID,
                                                  body=batch_update_spreadsheet_request_body)
    response = request.execute()

    logging.info(response)
