from datetime import datetime


def get_google_sheets_current_date() -> int:
    # (today - epoch_start).days
    return (datetime.now() - datetime(1899, 12, 30)).days
