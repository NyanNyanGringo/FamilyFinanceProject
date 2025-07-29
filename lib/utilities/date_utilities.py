from datetime import datetime


def get_google_sheets_current_date() -> int:
    """
    Возвращает текущую дату в формате Google Sheets (количество дней с 30 декабря 1899).

    Returns:
        int: Количество дней с 30 декабря 1899 до текущей даты.
    """
    # (today - epoch_start).days
    return (datetime.now() - datetime(1899, 12, 30)).days
