import logging
import json
import uuid
import os
from functools import partial

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import Application, ContextTypes, MessageHandler, filters, CallbackQueryHandler

from lib.utilities import google_utilities
from lib.utilities.google_utilities import OperationTypes, Category, Status, RequestData, ListName, TransferType, insert_and_update_row_batch_update, delete_row_by_telegram_id
from lib.utilities.openai_utilities import request_data, RequestBuilder, ResponseFormat, MessageRequest, \
    audio2text_for_finance
from lib.utilities.telegram_utilities import download_voice_message
from lib.utilities.ffmpeg_utilities import convert_oga_to_wav
from lib.utilities.vosk_utilities import audio2text

# LOGGING


from lib.utilities.log_utilities import get_logger

LOGGER = get_logger()

# CONFIG


VALIDATION_TEXT = "(невалидное значение)"


# CLASSES


class Audio2TextModels:
    """
    Класс для выбора модели преобразования аудио в текст.
    """
    whisper = "whisper"
    vosk = "vosk"


# FUNCTIONS


def replace_last_string(original_text: str, text_to_add: str):
    """
    Заменяет последнюю строку в тексте на новую строку.

    Args:
        original_text (str): Исходный текст.
        text_to_add (str): Строка для замены последней строки.

    Returns:
        str: Текст с заменённой последней строкой.
    """
    texts = original_text.split("\n")
    if len(texts) == 1:
        return text_to_add
    else:
        return "\n".join(texts[:-1] + [text_to_add])


async def get_text_from_audio(update, context, audio2text_model: Audio2TextModels, custom_text: str = None):
    """
    Получает текст из аудиосообщения с помощью выбранной модели.

    Args:
        update: Объект обновления Telegram.
        context: Контекст Telegram.
        audio2text_model (Audio2TextModels): Модель для преобразования аудио в текст.
        custom_text (str, optional): Пользовательский текст вместо распознавания.

    Returns:
        str: Распознанный текст.
    """
    oga_audio_file = await download_voice_message(update, context)
    wav_audio_file = convert_oga_to_wav(oga_audio_file)

    if custom_text:
        text_from_audio = custom_text
    elif audio2text_model == Audio2TextModels.whisper:
        text_from_audio = audio2text_for_finance(wav_audio_file)
    else:
        text_from_audio = audio2text(wav_audio_file)

    return text_from_audio


def format_json_to_telegram_text(json: dict) -> str:
    """
    Форматирует JSON-словарь в текст для Telegram.

    Args:
        json (dict): Словарь с данными.

    Returns:
        str: Отформатированный текст для Telegram.
    """
    text = ""
    for key, value in json.items():
        if value and key not in ["final_answer"]:
            text += f"<i>{key}</i>: <b>{value}</b>\n"
    return text.strip()


def is_text_has_status(text: str) -> bool:
    """
    Проверяет, есть ли в тексте строка, начинающаяся с "Статус: ".

    Args:
        text (str): Текст для проверки.

    Returns:
        bool: True, если статус найден, иначе False.
    """
    text_parts = text.split("\n")
    return any(part.startswith("Статус: ") for part in text_parts)


def remove_status_in_text(text: str) -> str:
    """
    Удаляет строку со статусом из текста, если она существует и находится в последней строке.

    Args:
        text (str): Текст для обработки.

    Returns:
        str: Текст без строки статуса.
    """
    text_parts = text.split("\n")

    # Проверяем, есть ли статус в последней строке
    if text_parts and text_parts[-1].startswith("Статус: "):
        return "\n".join(text_parts[:-1]).strip()

    return text.strip()


def set_status_to_text(text: str, status: str) -> str:
    """
    Устанавливает новый статус в текст. Если статус уже есть, заменяет его.

    Args:
        text (str): Исходный текст.
        status (str): Новый статус.

    Returns:
        str: Текст с обновлённым статусом.
    """
    if is_text_has_status(text):
        # Удаляем старый статус, если он есть
        text = remove_status_in_text(text)

    # Добавляем новый статус к тексту
    text += f"\n\nСтатус: {status}"
    return text.strip()


async def edit_message(message: Message, text: str, user_message: str = None, status: str = None,
                       reply_markup: InlineKeyboardMarkup = None):
    """
    Редактирует сообщение Telegram, добавляя текст, статус и разметку.

    Args:
        message (Message): Сообщение Telegram для редактирования.
        text (str): Новый текст сообщения.
        user_message (str, optional): Исходное сообщение пользователя.
        status (str, optional): Статус для добавления.
        reply_markup (InlineKeyboardMarkup, optional): Клавиатура для сообщения.

    Returns:
        None
    """
    new_text = ""
    if user_message:
        new_text += f"<code>{user_message}</code>\n\n"
    new_text += text

    LOGGER.info(f"Text before status: {new_text}")

    if status:
        new_text = set_status_to_text(new_text, status)

    LOGGER.info(f"Text after status: {new_text}")

    await message.edit_text(new_text, parse_mode="HTML", reply_markup=reply_markup)


async def create_request_data_from_message(operation_type: OperationTypes, request_message: dict, telegram_message_id: str) -> RequestData:
    """
    Создаёт объект RequestData из сообщения запроса.
    
    Args:
        operation_type (OperationTypes): Тип операции.
        request_message (dict): Словарь с данными запроса.
        telegram_message_id (str): ID сообщения Telegram.
        
    Returns:
        RequestData: Объект данных для Google Sheets.
    """
    # Base data common to all operations
    # Map operation type to list name
    if operation_type == OperationTypes.expenses:
        list_name = ListName.expenses
    elif operation_type == OperationTypes.incomes:
        list_name = ListName.incomes
    else:  # transfers or adjustment
        list_name = ListName.transfers
    
    # Handle different field names for transfers
    if operation_type == OperationTypes.transfers:
        account_field = request_message.get("write_off_account")
        amount_field = request_message.get("write_off_amount")
    else:
        account_field = request_message.get("account")
        amount_field = request_message.get("amount")
    
    data = {
        "list_name": list_name,
        "amount": amount_field,
        "account": account_field,
        "status": Status.get_item(request_message.get("status", "совершено")),
        "comment": request_message.get("comment", ""),
        "telegram_message_id": telegram_message_id
    }
    
    # Only add date if it exists in request_message
    if request_message.get("date") is not None:
        data["date"] = request_message.get("date")
    
    # Operation-specific fields
    if operation_type == OperationTypes.expenses:
        data["expenses_category"] = request_message.get("expenses_category")
    elif operation_type == OperationTypes.incomes:
        data["incomes_category"] = request_message.get("incomes_category")
    elif operation_type == OperationTypes.transfers:
        # Default to "Transfer" if transfer_type is not provided
        transfer_type = request_message.get("transfer_type", "Transfer")
        data["transfer_type"] = TransferType.get_item(transfer_type)
        data["replenishment_account"] = request_message.get("replenishment_account")
        data["replenishment_amount"] = request_message.get("replenishment_amount", data["amount"])
    
    return RequestData(**data)


async def clarify_operation_type(operation_type, processing_message, source_inputted_text):
    """
    Проверяет и возвращает корректный тип операции или сообщает об ошибке.

    Args:
        operation_type: Тип операции для проверки.
        processing_message: Сообщение Telegram для вывода ошибок.
        source_inputted_text: Исходный текст пользователя.

    Returns:
        OperationTypes | None: Корректный тип операции или None при ошибке.
    """
    try:
        operation_type = OperationTypes.get_item(operation_type)
        return operation_type
    except ValueError:
        await edit_message(message=processing_message,
                           text=f'Тип операции "{operation_type}", который определил ChatGPT, неверный. '
                                f'Попробуйте перезаписать голосовое сообщение.',
                           user_message=source_inputted_text)


def get_delete_button_keyboard(message_id: str) -> InlineKeyboardMarkup:
    """
    Создаёт клавиатуру с одной кнопкой "Удалить".
    
    Args:
        message_id (str): Уникальный идентификатор сообщения для callback_data.
        
    Returns:
        InlineKeyboardMarkup: Объект клавиатуры для Telegram.
    """
    keyboard = [[InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_{message_id}")]]
    return InlineKeyboardMarkup(keyboard)


def get_delete_confirmation_keyboard(message_id: str) -> InlineKeyboardMarkup:
    """
    Создаёт клавиатуру для подтверждения удаления.
    
    Args:
        message_id (str): Уникальный идентификатор сообщения для callback_data.
        
    Returns:
        InlineKeyboardMarkup: Объект клавиатуры для Telegram.
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ Да", callback_data=f"delete_confirm_{message_id}"),
            InlineKeyboardButton("❌ Нет", callback_data=f"delete_cancel_{message_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_reply_keyboard_markup(use_confirm_button: bool = True, use_reject_button: bool = True, message_id: str = None) -> InlineKeyboardMarkup:
    """
    Создаёт клавиатуру для Telegram с двумя кнопками: "Подтвердить" и "Отменить".

    Args:
        use_confirm_button (bool): Включить кнопку "Подтвердить" (по умолчанию True).
        use_reject_button (bool): Включить кнопку "Отменить" (по умолчанию True).
        message_id (str): Уникальный идентификатор сообщения для callback_data.

    Returns:
        InlineKeyboardMarkup: Объект клавиатуры для Telegram.
    """
    keyboard = []
    
    # Используем message_id в callback_data для уникальной идентификации
    confirm_data = f"confirm_{message_id}" if message_id else "confirm"
    reject_data = f"reject_{message_id}" if message_id else "reject"

    # Добавляем кнопки в зависимости от параметров
    if use_confirm_button and use_reject_button:
        # Если обе кнопки включены, размещаем их в одном ряду
        keyboard.append([
            InlineKeyboardButton("Подтвердить", callback_data=confirm_data),
            InlineKeyboardButton("Отменить", callback_data=reject_data)
        ])
    elif use_confirm_button:
        # Если только кнопка "Подтвердить" включена
        keyboard.append([InlineKeyboardButton("Подтвердить", callback_data=confirm_data)])
    elif use_reject_button:
        # Если только кнопка "Отменить" включена
        keyboard.append([InlineKeyboardButton("Отменить", callback_data=reject_data)])

    return InlineKeyboardMarkup(keyboard)


def get_response_format_according_to_operation_type(operation_type: str) -> dict:
    """
    Возвращает формат ответа для указанного типа операции.

    Args:
        operation_type (str): Тип операции.

    Returns:
        dict: Формат ответа.
    """
    if operation_type == OperationTypes.expenses:
        return ResponseFormat().expenses_response_format
    elif operation_type == OperationTypes.incomes:
        return ResponseFormat().incomes_response_format
    elif operation_type == OperationTypes.transfers:
        return ResponseFormat().transfer_response_format
    elif operation_type == OperationTypes.adjustment:
        return ResponseFormat().adjustment_response_format

    raise ValueError(f"Operation type {operation_type} not supported.")


def clarify_request_message(request_message: dict) -> dict:
    """
    Валидирует и корректирует значения в сообщении запроса.

    Args:
        request_message (dict): Сообщение с данными для запроса.

    Returns:
        dict: Валидированное сообщение запроса.
    """
    # Pairs of keys from request_message and values that request_message key should contain.
    validation_dict = {
        "expenses_category": Category.get_expenses(),
        "account": Category.get_accounts(),
        # "amount": int,  # Эти значения требуют специальной обработки
        "status": Status.values(),
        # "comment": str,  # Эти значения могут быть любыми строками
        # "final_answer": str,
        "incomes_category": Category.get_incomes(),
        "write_off_account": Category.get_accounts(),
        "replenishment_account": Category.get_accounts(),
        # "write_off_amount": int,
        # "replenishment_amount": int,
    }

    result = {}
    for key, value in request_message.items():

        # get list of valid values that request_message.key should contain
        if key in validation_dict:  # check if key needs validation

            if isinstance(value, str):  # check if value is string
                valid_values = validation_dict.get(key)
                # iterate through list of valid values
                for supported_value in valid_values:
                    if isinstance(supported_value, str) and value.lower() == supported_value.lower():
                        result[key] = supported_value
                        break
            else:
                raise ValueError(f"Expected type of {key} is string, but got: {type(value)} {value}")

        else:  # key doesn't need validation
            result[key] = value

        # Если валидация не прошла и значение не найдено в result, добавляем информацию о невалидности
        if key in validation_dict and key not in result:
            result[key] = f"{value} {VALIDATION_TEXT}"

    return result


# HANDLES


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    LOGGER.error("Exception while handling an update:", exc_info=context.error)

    # send message to user about error
    try:
        if isinstance(update, Update):
            # Пытаемся отправить пользователю сообщение об ошибке
            message = update.callback_query.message or update.message
            await message.reply_text("Произошла ошибка при обработке вашего запроса. "
                                     "Пожалуйста, попробуйте позже.")
    except Exception as e:
        LOGGER.error(f"Ошибка при отправке сообщения пользователю: {e}")


async def button_click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    LOGGER.info(f"Button clicked.")
    LOGGER.info(f"{update=}")
    LOGGER.info(f"{context=}")

    query = update.callback_query
    await query.answer()  # confirm button click
    await query.edit_message_reply_markup(reply_markup=None)  # remove buttons

    reply_message: Message = update.callback_query.message
    callback_data = update.callback_query.data
    
    # Extract action and message_id from callback_data
    parts = callback_data.split("_")
    action = parts[0]
    
    if len(parts) >= 2:
        if action == "delete" and len(parts) >= 3:
            # Handle delete_confirm_ID or delete_cancel_ID
            sub_action = parts[1]
            message_id = parts[2]
            action = f"{action}_{sub_action}"
        else:
            message_id = parts[1]
    else:
        # Fallback for old format
        message_id = None
    
    # Get message-specific data
    if message_id:
        message_data_key = f"msg_{message_id}"
        message_data = context.user_data.get(message_data_key, {})
        operation_type = message_data.get("operation_type")
        request_message = message_data.get("request_message")
        source_inputted_text = message_data.get("source_inputted_text")
        message_text = message_data.get("body_text")
        saved_to_sheets = message_data.get("saved_to_sheets", False)
        list_name = message_data.get("list_name")
    else:
        # Fallback to old format
        operation_type = context.user_data.get("operation_type")
        request_message = context.user_data.get("request_message")
        source_inputted_text = context.user_data.get("source_inputted_text")
        message_text = context.user_data.get("body_text")
        saved_to_sheets = False
        list_name = None

    if action == "reject":
        await edit_message(message=reply_message,
                           text=message_text,
                           user_message=source_inputted_text,
                           status="операция отменена 👀")
        # Clean up message data after rejection
        if message_id:
            message_data_key = f"msg_{message_id}"
            if message_data_key in context.user_data:
                del context.user_data[message_data_key]
        return
    
    elif action == "delete":
        # Don't remove buttons yet - we need confirmation
        await query.edit_message_reply_markup(reply_markup=get_delete_confirmation_keyboard(message_id))
        await edit_message(message=reply_message,
                           text=message_text,
                           user_message=source_inputted_text,
                           status="🗑️ Вы уверены что хотите удалить?",
                           reply_markup=get_delete_confirmation_keyboard(message_id))
        return  # Don't clean up data yet
    
    elif action == "delete_confirm":
        # Confirmed deletion
        if saved_to_sheets and list_name and message_id:
            try:
                # Delete from Google Sheets
                deleted = delete_row_by_telegram_id(list_name, message_id)
                if deleted:
                    await edit_message(message=reply_message,
                                       text=message_text,
                                       user_message=source_inputted_text,
                                       status="🗑️ Удалено из Google Sheets")
                else:
                    await edit_message(message=reply_message,
                                       text=message_text,
                                       user_message=source_inputted_text,
                                       status="❌ Запись не найдена в Google Sheets")
            except Exception as e:
                LOGGER.error(f"Error deleting from Google Sheets: {e}")
                await edit_message(message=reply_message,
                                   text=message_text,
                                   user_message=source_inputted_text,
                                   status=f"❌ Ошибка удаления: {e}")
        else:
            await edit_message(message=reply_message,
                               text=message_text,
                               user_message=source_inputted_text,
                               status="❌ Данные для удаления не найдены")
        # Clean up message data after deletion
        if message_id:
            message_data_key = f"msg_{message_id}"
            if message_data_key in context.user_data:
                del context.user_data[message_data_key]
        return
    
    elif action == "delete_cancel":
        # Cancelled deletion - just remove confirmation buttons
        await edit_message(message=reply_message,
                           text=message_text,
                           user_message=source_inputted_text,
                           status="✅ Сохранено в Google Sheets",
                           reply_markup=get_delete_button_keyboard(message_id))
        return  # Don't clean up data, user might delete later

    # The code below handles old confirm/reject flow - only runs for confirm action
    if action != "confirm":
        return
        
    if operation_type == OperationTypes.expenses:
        google_request_data = RequestData(list_name=ListName.expenses,
                                          expenses_category=request_message.get("expenses_category"),
                                          account=request_message.get("account"),
                                          amount=request_message.get("amount"),
                                          status=request_message.get("status"),
                                          comment=request_message.get("comment"))
    elif operation_type == OperationTypes.incomes:
        google_request_data = RequestData(list_name=ListName.incomes,
                                          incomes_category=request_message.get("incomes_category"),
                                          account=request_message.get("account"),
                                          amount=request_message.get("amount"),
                                          status=request_message.get("status"),
                                          comment=request_message.get("comment"))
    elif operation_type == OperationTypes.transfers:
        google_request_data = RequestData(list_name=ListName.transfers,
                                          transfer_type=TransferType.transfer,
                                          account=request_message.get("write_off_account"),
                                          replenishment_account=request_message.get("replenishment_account"),
                                          amount=request_message.get("write_off_amount"),
                                          replenishment_amount=request_message.get("replenishment_amount"),
                                          status=request_message.get("status"),
                                          comment=request_message.get("comment"))
    elif operation_type == OperationTypes.adjustment:
        google_request_data = RequestData(list_name=ListName.transfers,
                                          transfer_type=TransferType.adjustment,
                                          account=request_message.get("adjustment_account"),
                                          replenishment_account=request_message.get("adjustment_account"),
                                          amount=0,
                                          replenishment_amount=request_message.get("adjustment_amount"),
                                          status=request_message.get("status"),
                                          comment=request_message.get("comment"))
    else:
        raise ValueError(f"Unsupported operation type: {operation_type}")

    LOGGER.info(f"{google_request_data=}")

    google_utilities.insert_and_update_row_batch_update(google_request_data)

    await edit_message(message=reply_message,
                       text=message_text,
                       user_message=source_inputted_text,
                       status="подтверждено 👍")
    
    # Clean up message data after processing
    if message_id:
        message_data_key = f"msg_{message_id}"
        if message_data_key in context.user_data:
            del context.user_data[message_data_key]


async def voice_message_handler(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        audio2text_model: Audio2TextModels = Audio2TextModels.whisper,
        custom_text: str = None) -> None:
    # Step I. Convert voice message to text.
    processing_message = await update.message.reply_text("1/3 Конвертирую аудио в текст. Ожидайте...")
    context.user_data["reply_message"] = processing_message  # save message for next usage
    text_from_audio = await get_text_from_audio(update, context, audio2text_model, custom_text)

    # Step II. First request to ChatGPT: get json data with operation type and text validity.
    # Text will be divided into parts if user ask for few request in one voice message.
    await edit_message(message=processing_message,
                       text="2/3 Определяю тип операции и валидность текста. Ожидайте...",
                       user_message=text_from_audio)
    finance_operation_request_message = request_data(
        RequestBuilder(
            message_request=MessageRequest(user_message=text_from_audio).finance_operation_request_message,
            response_format=ResponseFormat().finance_operation_response
        )
    )
    LOGGER.info(f"{finance_operation_request_message=}")

    # Step III. Second requests to ChatGPT: get json data that will be added to Google Tables.
    for _, finance_operations in finance_operation_request_message.items():
        for finance_operation in finance_operations:

            LOGGER.info(f"{finance_operation=}")

            operation_type: str = finance_operation.get("operation_type")
            source_inputted_text: str = finance_operation.get("source_inputted_text")
            message_to_user: str = finance_operation.get("message_to_user")
            user_request_is_correct: bool = finance_operation.get("user_request_is_relevant")

            operation_type = await clarify_operation_type(operation_type, processing_message, source_inputted_text)
            if not operation_type:
                continue

            if not user_request_is_correct:
                await edit_message(message=processing_message,
                                   text=f'Запрос некорректен. Ответ ChatGPT: "{message_to_user}"',
                                   user_message=source_inputted_text)
                continue

            await edit_message(message=processing_message,
                               text=f"3/3 Определяю данные для Google Tables. Ожидайте...",
                               user_message=source_inputted_text)

            request_message = request_data(
                RequestBuilder(
                    message_request=MessageRequest(
                        user_message=source_inputted_text).basic_request_message,
                    response_format=get_response_format_according_to_operation_type(operation_type))
            )

            LOGGER.info(f"(RAW) {request_message=}")

            request_message = clarify_request_message(request_message)

            LOGGER.info(f"{request_message=}")

            # save operation_type and request_message to use in button_click_handler()
            body_text = format_json_to_telegram_text(request_message)
            
            # Generate unique message ID for this specific message
            message_id = str(processing_message.message_id)
            
            # Store message-specific data with unique key
            message_data_key = f"msg_{message_id}"
            context.user_data[message_data_key] = {
                "operation_type": operation_type,
                "request_message": request_message,
                "body_text": body_text,
                "source_inputted_text": source_inputted_text
            }

            if VALIDATION_TEXT in str(request_message):
                # Data has validation errors - show old Accept/Decline buttons
                keyboard = get_reply_keyboard_markup(False, True, message_id)
                status_text = "ожидание ответа пользователя."
            else:
                # Data is valid - auto-save to Google Sheets
                try:
                    # Create RequestData and add telegram_message_id
                    data = await create_request_data_from_message(
                        operation_type, request_message, message_id
                    )
                    
                    # Auto-save to Google Sheets
                    insert_and_update_row_batch_update(data)
                    
                    # Store that data was saved for potential deletion
                    context.user_data[message_data_key]["saved_to_sheets"] = True
                    context.user_data[message_data_key]["list_name"] = data.list_name
                    
                    # Show Delete button and success status
                    keyboard = get_delete_button_keyboard(message_id)
                    status_text = "✅ Сохранено в Google Sheets"
                except Exception as e:
                    LOGGER.error(f"Failed to auto-save to Google Sheets: {e}")
                    # On error, show old Accept/Decline buttons
                    keyboard = get_reply_keyboard_markup(True, True, message_id)
                    status_text = "❌ Ошибка сохранения."

            # send message with buttons
            await edit_message(message=processing_message,
                               text=body_text,
                               user_message=source_inputted_text,
                               status=status_text,
                               reply_markup=keyboard)


def run() -> None:
    application = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()

    # Устанавливаем глобальный обработчик ошибок
    application.add_error_handler(global_error_handler)

    # Используем functools.partial для передачи дополнительного аргумента
    handler_with_vosk = partial(
        voice_message_handler,
        audio2text_model=Audio2TextModels.whisper,
        # custom_text="1500 динар накопления кофе"
        # custom_text="300 динар кофе"
        # custom_text="2280 минус 400 динар накопления продукты"
    )

    # Привязываем обработчики для разных моделей
    application.add_handler(
        MessageHandler(
            filters.VOICE & ~filters.COMMAND,
            handler_with_vosk
        )
    )

    # Обработчик для нажатий на кнопки
    application.add_handler(CallbackQueryHandler(button_click_handler))

    # run
    application.run_polling(allowed_updates=Update.ALL_TYPES)
