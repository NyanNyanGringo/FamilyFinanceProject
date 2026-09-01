import asyncio
import json
import logging
import os
import uuid
from functools import partial

from telegram import (BotCommand, InlineKeyboardButton, InlineKeyboardMarkup,
                      Message, Update)
from telegram.error import BadRequest, TimedOut
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes, MessageHandler, filters)

from lib.utilities import google_utilities, telegram_utilities
from lib.utilities.ffmpeg_utilities import convert_oga_to_wav, get_wav_output_path
from lib.utilities.google_utilities import (FinanceConfigSnapshot,
                                            FinanceConfigUnavailableError,
                                            GoogleWriteOutcomeUnknownError,
                                            ListName, OperationTypes,
                                            RequestData, Status, TransferType,
                                            add_memory, delete_memory,
                                            delete_row_by_telegram_id,
                                            find_rows_by_telegram_id,
                                            get_finance_config,
                                            get_memories,
                                            insert_and_update_row_batch_update,
                                            reload_finance_config)
from lib.utilities.log_utilities import get_logger
from lib.utilities.openai_utilities import (MessageRequest, RequestBuilder,
                                            ResponseFormat,
                                            audio2text_for_finance,
                                            get_memory_context,
                                            request_data)
from lib.utilities.telegram_utilities import download_voice_message
from lib.utilities.vosk_utilities import audio2text

# LOGGING


LOGGER = get_logger()

# CONFIG


VALIDATION_TEXT = "(невалидное значение)"
TELEGRAM_CALLBACK_DATA_MAX_BYTES = 64
_LONGEST_OPERATION_CALLBACK_PREFIX = "delete_confirm_"


# CLASSES


class Audio2TextModels:
    """
    Класс для выбора модели преобразования аудио в текст.
    """

    whisper = "whisper"
    vosk = "vosk"


# FUNCTIONS


def build_operation_tracking_id(
    chat_id: int,
    source_message_id: int,
    operation_sequence: int,
) -> str:
    """Build a stable operation ID unique to a Telegram source message."""
    tracking_id = f"{chat_id}:{source_message_id}:{operation_sequence}"
    longest_callback_data = f"{_LONGEST_OPERATION_CALLBACK_PREFIX}{tracking_id}"
    if len(longest_callback_data.encode("utf-8")) <= TELEGRAM_CALLBACK_DATA_MAX_BYTES:
        return tracking_id

    compact_id = uuid.uuid5(uuid.NAMESPACE_URL, tracking_id).hex
    return f"op-{compact_id}"


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


async def _convert_audio_without_orphan_worker(oga_audio_file: str) -> None:
    conversion_task = asyncio.create_task(
        asyncio.to_thread(convert_oga_to_wav, oga_audio_file)
    )
    try:
        await asyncio.shield(conversion_task)
    except asyncio.CancelledError:
        try:
            await conversion_task
        except Exception:
            LOGGER.exception("Audio conversion failed after handler cancellation")
        raise


async def get_text_from_audio(
    update,
    context,
    audio2text_model: Audio2TextModels,
    config_snapshot: FinanceConfigSnapshot,
    custom_text: str = None,
):
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
    if custom_text:
        return custom_text

    oga_audio_file = None
    wav_audio_file = None
    try:
        oga_audio_file = await download_voice_message(update, context)
        wav_audio_file = get_wav_output_path(oga_audio_file)
        await _convert_audio_without_orphan_worker(oga_audio_file)

        if audio2text_model == Audio2TextModels.whisper:
            return await asyncio.to_thread(
                audio2text_for_finance,
                wav_audio_file,
                config_snapshot,
            )
        return await asyncio.to_thread(audio2text, wav_audio_file)
    finally:
        await asyncio.to_thread(
            _remove_audio_files,
            oga_audio_file,
            wav_audio_file,
        )


def _remove_audio_files(*paths: str) -> None:
    for path in paths:
        if not path:
            continue
        try:
            os.remove(path)
        except FileNotFoundError:
            continue
        except OSError:
            LOGGER.exception("Failed to remove temporary audio file: %s", path)


def _request_openai_data(
    user_message: str,
    response_format: dict,
    finance_operation: bool,
    memory_context: str,
) -> dict:
    messages = MessageRequest(
        user_message=user_message,
        memory_context=memory_context,
    )
    message_request = (
        messages.finance_operation_request_message
        if finance_operation
        else messages.basic_request_message
    )
    return request_data(
        RequestBuilder(
            message_request=message_request,
            response_format=response_format,
        )
    )


async def _write_finance_operation(request: RequestData) -> bool:
    try:
        await asyncio.to_thread(insert_and_update_row_batch_update, request)
        return True
    except GoogleWriteOutcomeUnknownError:
        LOGGER.exception(
            "Google Sheets write outcome is unknown for telegram_message_id=%s",
            request.telegram_message_id,
        )

    if not request.telegram_message_id:
        LOGGER.error("Cannot reconcile Google Sheets write without telegram_message_id")
        return False

    try:
        matching_rows = await asyncio.to_thread(
            find_rows_by_telegram_id,
            request.list_name,
            request.telegram_message_id,
        )
    except Exception:
        LOGGER.exception(
            "Failed to reconcile Google Sheets write for telegram_message_id=%s",
            request.telegram_message_id,
        )
        return False

    if len(matching_rows) == 1:
        LOGGER.info(
            "Reconciled Google Sheets write for telegram_message_id=%s at row=%s",
            request.telegram_message_id,
            matching_rows[0],
        )
        return True

    LOGGER.error(
        "Could not reconcile Google Sheets write for telegram_message_id=%s: rows=%s",
        request.telegram_message_id,
        matching_rows,
    )
    return False


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


async def edit_message(
    message: Message,
    text: str,
    user_message: str = None,
    status: str = None,
    reply_markup: InlineKeyboardMarkup = None,
):
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


async def create_request_data_from_message(
    operation_type: OperationTypes, request_message: dict, telegram_message_id: str
) -> RequestData:
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
        "telegram_message_id": telegram_message_id,
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
        data["replenishment_amount"] = request_message.get(
            "replenishment_amount", data["amount"]
        )

    return RequestData(**data)


async def clarify_operation_type(
    operation_type, processing_message, source_inputted_text
):
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
        await edit_message(
            message=processing_message,
            text=f'Тип операции "{operation_type}", который определил ChatGPT, неверный. '
            f"Попробуйте перезаписать голосовое сообщение.",
            user_message=source_inputted_text,
        )


def get_delete_button_keyboard(message_id: str) -> InlineKeyboardMarkup:
    """
    Создаёт клавиатуру с одной кнопкой "Удалить".

    Args:
        message_id (str): Уникальный идентификатор сообщения для callback_data.

    Returns:
        InlineKeyboardMarkup: Объект клавиатуры для Telegram.
    """
    keyboard = [
        [InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_{message_id}")]
    ]
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
            InlineKeyboardButton("❌ Нет", callback_data=f"delete_cancel_{message_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_reply_keyboard_markup(
    use_confirm_button: bool = True,
    use_reject_button: bool = True,
    message_id: str = None,
) -> InlineKeyboardMarkup:
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
        keyboard.append(
            [
                InlineKeyboardButton("Подтвердить", callback_data=confirm_data),
                InlineKeyboardButton("Отменить", callback_data=reject_data),
            ]
        )
    elif use_confirm_button:
        # Если только кнопка "Подтвердить" включена
        keyboard.append(
            [InlineKeyboardButton("Подтвердить", callback_data=confirm_data)]
        )
    elif use_reject_button:
        # Если только кнопка "Отменить" включена
        keyboard.append([InlineKeyboardButton("Отменить", callback_data=reject_data)])

    return InlineKeyboardMarkup(keyboard)


def get_response_format_according_to_operation_type(
    operation_type: str,
    response_formats: ResponseFormat,
) -> dict:
    """
    Возвращает формат ответа для указанного типа операции.

    Args:
        operation_type (str): Тип операции.

    Returns:
        dict: Формат ответа.
    """
    if operation_type == OperationTypes.expenses:
        return response_formats.expenses_response_format
    elif operation_type == OperationTypes.incomes:
        return response_formats.incomes_response_format
    elif operation_type == OperationTypes.transfers:
        return response_formats.transfer_response_format
    elif operation_type == OperationTypes.adjustment:
        return response_formats.adjustment_response_format

    raise ValueError(f"Operation type {operation_type} not supported.")


def clarify_request_message(
    request_message: dict,
    config_snapshot: FinanceConfigSnapshot,
) -> dict:
    """
    Валидирует и корректирует значения в сообщении запроса.

    Args:
        request_message (dict): Сообщение с данными для запроса.

    Returns:
        dict: Валидированное сообщение запроса.
    """
    # Pairs of keys from request_message and values that request_message key should contain.
    validation_dict = {
        "expenses_category": config_snapshot.expenses,
        "account": config_snapshot.accounts,
        # "amount": int,  # Эти значения требуют специальной обработки
        "status": Status.values(),
        # "comment": str,  # Эти значения могут быть любыми строками
        # "final_answer": str,
        "incomes_category": config_snapshot.incomes,
        "write_off_account": config_snapshot.accounts,
        "replenishment_account": config_snapshot.accounts,
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
                    if (
                        isinstance(supported_value, str)
                        and value.lower() == supported_value.lower()
                    ):
                        result[key] = supported_value
                        break
            else:
                raise ValueError(
                    f"Expected type of {key} is string, but got: {type(value)} {value}"
                )

        else:  # key doesn't need validation
            result[key] = value

        # Если валидация не прошла и значение не найдено в result, добавляем информацию о невалидности
        if key in validation_dict and key not in result:
            result[key] = f"{value} {VALIDATION_TEXT}"

    return result


# HANDLES


async def global_error_handler(
    update: object, context: ContextTypes.DEFAULT_TYPE
) -> None:
    LOGGER.error("Exception while handling an update:", exc_info=context.error)

    # send message to user about error
    try:
        if isinstance(update, Update):
            # Пытаемся отправить пользователю сообщение об ошибке
            message = None
            if update.callback_query and update.callback_query.message:
                message = update.callback_query.message
            elif update.message:
                message = update.message

            if message:
                await message.reply_text(
                    "Произошла ошибка при обработке вашего запроса. "
                    "Пожалуйста, попробуйте позже."
                )
    except Exception as e:
        LOGGER.error(f"Ошибка при отправке сообщения пользователю: {e}")


async def memory_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик кнопок для операций с памятью.
    Обрабатывает callback_data начинающиеся с "mem_".
    """
    query = update.callback_query
    callback_data = query.data

    if callback_data == "mem_done":
        await query.answer()
        await query.edit_message_text("✅ Готово")
        return

    if callback_data.startswith("mem_del_"):
        try:
            memory_index = int(callback_data.replace("mem_del_", ""))
            memories = await asyncio.to_thread(get_memories)

            if 0 <= memory_index < len(memories):
                deleted_memory = memories[memory_index]
                if await asyncio.to_thread(delete_memory, memory_index):
                    # Обновляем список
                    memories = await asyncio.to_thread(get_memories)
                    if memories:
                        keyboard = []
                        message_text = "📝 Сохранённые воспоминания:\n\n"
                        for i, memory in enumerate(memories):
                            message_text += f"{i + 1}. {memory}\n"
                            keyboard.append(
                                [
                                    InlineKeyboardButton(
                                        f"❌ Удалить {i + 1}",
                                        callback_data=f"mem_del_{i}",
                                    )
                                ]
                            )
                        keyboard.append(
                            [
                                InlineKeyboardButton(
                                    "✅ Готово", callback_data="mem_done"
                                )
                            ]
                        )
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await query.answer(f"✅ Удалено: {deleted_memory}")
                        await query.edit_message_text(
                            message_text + "\nВыберите воспоминание для удаления:",
                            reply_markup=reply_markup,
                        )
                    else:
                        await query.answer("Все воспоминания удалены")
                        await query.edit_message_text("📝 Все воспоминания удалены.")
                else:
                    await query.answer(
                        "❌ Ошибка при удалении воспоминания", show_alert=True
                    )
            else:
                await query.answer("❌ Неверный индекс воспоминания", show_alert=True)
        except Exception as e:
            LOGGER.error(f"Error in memory deletion: {e}")
            await query.answer("❌ Ошибка при удалении", show_alert=True)


async def operation_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик кнопок для финансовых операций.
    Обрабатывает callback_data для операций accept, reject, delete.
    """
    query = update.callback_query
    try:
        await query.answer()  # confirm button click
    except BadRequest as e:
        # Happens when user clicks an old button while previous updates are still processing
        if "Query is too old" in str(e) or "query id is invalid" in str(e):
            LOGGER.warning(f"Stale callback query ignored: {e}")
            if query.message:
                await query.message.reply_text(
                    "⚠️ Кнопка устарела. Нажмите кнопку ещё раз, если действие актуально."
                )
            return
        raise
    if query.message and query.message.reply_markup:
        await query.edit_message_reply_markup(reply_markup=None)  # remove buttons

    reply_message: Message = query.message
    callback_data = query.data

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

    tracking_id = message_id or f"{reply_message.message_id}-legacy"

    if action == "reject":
        await edit_message(
            message=reply_message,
            text=message_text,
            user_message=source_inputted_text,
            status="операция отменена 👀",
        )
        # Clean up message data after rejection
        if message_id:
            message_data_key = f"msg_{message_id}"
            if message_data_key in context.user_data:
                del context.user_data[message_data_key]
        return

    elif action == "delete":
        # Don't remove buttons yet - we need confirmation
        await query.edit_message_reply_markup(
            reply_markup=get_delete_confirmation_keyboard(message_id)
        )
        await edit_message(
            message=reply_message,
            text=message_text,
            user_message=source_inputted_text,
            status="🗑️ Вы уверены что хотите удалить?",
            reply_markup=get_delete_confirmation_keyboard(message_id),
        )
        return  # Don't clean up data yet

    elif action == "delete_confirm":
        # Confirmed deletion
        if saved_to_sheets and list_name and message_id:
            try:
                # Delete from Google Sheets
                deleted = await asyncio.to_thread(
                    delete_row_by_telegram_id,
                    list_name,
                    message_id,
                )
                if deleted:
                    await edit_message(
                        message=reply_message,
                        text=message_text,
                        user_message=source_inputted_text,
                        status="🗑️ Удалено из Google Sheets",
                    )
                else:
                    await edit_message(
                        message=reply_message,
                        text=message_text,
                        user_message=source_inputted_text,
                        status="❌ Запись не найдена в Google Sheets",
                    )
            except GoogleWriteOutcomeUnknownError:
                LOGGER.exception("Google Sheets delete outcome is unknown")
                await edit_message(
                    message=reply_message,
                    text=message_text,
                    user_message=source_inputted_text,
                    status=(
                        "Результат удаления неизвестен. "
                        "Проверьте Google Sheets."
                    ),
                )
                return
            except Exception:
                LOGGER.exception("Failed to delete Google Sheets operation")
                await edit_message(
                    message=reply_message,
                    text=message_text,
                    user_message=source_inputted_text,
                    status=(
                        "Не удалось удалить запись из Google Sheets. "
                        "Попробуйте позже."
                    ),
                )
                return
        else:
            await edit_message(
                message=reply_message,
                text=message_text,
                user_message=source_inputted_text,
                status="❌ Данные для удаления не найдены",
            )
        # Clean up message data after deletion
        if message_id:
            message_data_key = f"msg_{message_id}"
            if message_data_key in context.user_data:
                del context.user_data[message_data_key]
        return

    elif action == "delete_cancel":
        # Cancelled deletion - just remove confirmation buttons
        await edit_message(
            message=reply_message,
            text=message_text,
            user_message=source_inputted_text,
            status="✅ Сохранено в Google Sheets",
            reply_markup=get_delete_button_keyboard(message_id),
        )
        return  # Keep the data

    # Default case - accept operation
    if operation_type == OperationTypes.expenses:
        google_request_data = RequestData(
            list_name=ListName.expenses,
            expenses_category=request_message.get("expenses_category"),
            account=request_message.get("account"),
            amount=request_message.get("amount"),
            status=request_message.get("status"),
            comment=request_message.get("comment"),
            telegram_message_id=tracking_id,
        )
    elif operation_type == OperationTypes.incomes:
        google_request_data = RequestData(
            list_name=ListName.incomes,
            incomes_category=request_message.get("incomes_category"),
            account=request_message.get("account"),
            amount=request_message.get("amount"),
            status=request_message.get("status"),
            comment=request_message.get("comment"),
            telegram_message_id=tracking_id,
        )
    elif operation_type == OperationTypes.transfers:
        google_request_data = RequestData(
            list_name=ListName.transfers,
            transfer_type=TransferType.transfer,
            account=request_message.get("write_off_account"),
            replenishment_account=request_message.get("replenishment_account"),
            amount=request_message.get("write_off_amount"),
            replenishment_amount=request_message.get("replenishment_amount"),
            status=request_message.get("status"),
            comment=request_message.get("comment"),
            telegram_message_id=tracking_id,
        )
    elif operation_type == OperationTypes.adjustment:
        google_request_data = RequestData(
            list_name=ListName.transfers,
            transfer_type=TransferType.adjustment,
            account=request_message.get("adjustment_account"),
            replenishment_account=request_message.get("adjustment_account"),
            amount=0,
            replenishment_amount=request_message.get("adjustment_amount"),
            status=request_message.get("status"),
            comment=request_message.get("comment"),
            telegram_message_id=tracking_id,
        )
    else:
        raise ValueError(f"Unsupported operation type: {operation_type}")

    LOGGER.info(f"{google_request_data=}")

    try:
        saved = await _write_finance_operation(google_request_data)
    except Exception:
        LOGGER.exception("Failed to save confirmed Google Sheets operation")
        await edit_message(
            message=reply_message,
            text=message_text,
            user_message=source_inputted_text,
            status="Не удалось сохранить операцию.",
        )
        return

    if not saved:
        await edit_message(
            message=reply_message,
            text=message_text,
            user_message=source_inputted_text,
            status=(
                "Результат сохранения неизвестен. "
                "Проверьте Google Sheets перед повторной отправкой."
            ),
        )
        return

    await edit_message(
        message=reply_message,
        text=message_text,
        user_message=source_inputted_text,
        status="подтверждено 👍",
    )

    # Clean up message data after processing
    if message_id:
        message_data_key = f"msg_{message_id}"
        if message_data_key in context.user_data:
            del context.user_data[message_data_key]


async def button_click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Главный обработчик кнопок. Распределяет вызовы между специализированными обработчиками.
    """
    LOGGER.info(f"Button clicked.")
    LOGGER.info(f"{update=}")
    LOGGER.info(f"{context=}")

    callback_data = update.callback_query.data

    # Направляем в соответствующий обработчик
    if callback_data.startswith("mem_"):
        await memory_button_handler(update, context)
    else:
        await operation_button_handler(update, context)


async def expenses_status_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Обработчик команды /expenses_status.
    Читает данные из листа /expenses_status в Google Sheets и отправляет форматированное сообщение.
    """
    try:
        # Отправляем начальное сообщение и сохраняем его для редактирования
        processing_message = await update.message.reply_text(
            "Загружаю данные о расходах..."
        )

        # Читаем данные из Google Sheets
        # A2 - currency code
        currency_range = f"{ListName.expenses_status}!A2"
        currency_data = await asyncio.to_thread(
            google_utilities.get_values,
            currency_range,
        )
        currency_code = (
            currency_data[0][0] if currency_data and currency_data[0] else "RUB"
        )

        # B2:B - expense categories (without header)
        categories_range = f"{ListName.expenses_status}!B2:B"
        categories_data = await asyncio.to_thread(
            google_utilities.get_values,
            categories_range,
            True,
        )

        # C2:C - amounts per category (without header)
        amounts_range = f"{ListName.expenses_status}!C2:C"
        amounts_data = await asyncio.to_thread(
            google_utilities.get_values,
            amounts_range,
            True,
        )

        # D2:D - expected amounts per category (without header)
        expected_range = f"{ListName.expenses_status}!D2:D"
        expected_data = await asyncio.to_thread(
            google_utilities.get_values,
            expected_range,
            True,
        )

        # E2 - total amount
        total_range = f"{ListName.expenses_status}!E2"
        total_data = await asyncio.to_thread(
            google_utilities.get_values,
            total_range,
        )
        total_amount = total_data[0][0] if total_data and total_data[0] else "0"

        # Формируем сообщение
        message = "Господин, траты по категориям в этом месяце:\n\n"

        # Добавляем категории и суммы
        if categories_data and amounts_data and expected_data:
            for i in range(
                min(len(categories_data), len(amounts_data), len(expected_data))
            ):
                if (
                    categories_data[i] and amounts_data[i] and expected_data[i]
                ):  # Пропускаем пустые строки
                    message += f"{categories_data[i]} - {amounts_data[i]} из {expected_data[i]} {currency_code}\n"

        # Добавляем итоговую сумму
        message += f"\nВсего: {total_amount} {currency_code}"

        # Редактируем начальное сообщение вместо отправки нового
        await processing_message.edit_text(message)

    except Exception as e:
        LOGGER.error(f"Error in expenses_status_handler: {e}")
        await update.message.reply_text(
            "Произошла ошибка при получении данных о расходах. "
            "Пожалуйста, проверьте настройки Google Sheets и попробуйте позже."
        )


async def memory_text_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Обработчик текстовых сообщений, начинающихся с "#".
    Сохраняет текст после "#" в лист #memory в Google Sheets.
    """
    try:
        text = update.message.text

        if not text or not text.startswith("#"):
            return

        memory_text = text[1:].strip()

        if not memory_text:
            await update.message.reply_text(
                "Пожалуйста, добавьте текст после # для сохранения в памяти."
            )
            return

        if await asyncio.to_thread(add_memory, memory_text):
            await update.message.reply_text(f"✅ Память сохранена: {memory_text}")
            LOGGER.info(f"Memory added: {memory_text}")
        else:
            await update.message.reply_text(
                "❌ Ошибка при сохранении памяти. Попробуйте позже."
            )

    except Exception as e:
        LOGGER.error(f"Error in memory_text_handler: {e}")
        await update.message.reply_text(
            "Произошла ошибка при обработке команды памяти."
        )


async def memory_command_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Обработчик команды /memory.
    Показывает сохранённые воспоминания с возможностью их удаления.
    """
    try:
        memories = await asyncio.to_thread(get_memories)

        if not memories:
            await update.message.reply_text(
                "📝 Нет сохранённых воспоминаний.\n\nОтправьте сообщение, начинающееся с #, чтобы добавить воспоминание."
            )
            return

        # Создаём клавиатуру с кнопками для удаления
        keyboard = []
        message_text = "📝 Сохранённые воспоминания:\n\n"

        for i, memory in enumerate(memories):
            message_text += f"{i + 1}. {memory}\n"
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"❌ Удалить {i + 1}", callback_data=f"mem_del_{i}"
                    )
                ]
            )

        keyboard.append([InlineKeyboardButton("✅ Готово", callback_data="mem_done")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            message_text + "\nВыберите воспоминание для удаления:",
            reply_markup=reply_markup,
        )

    except Exception as e:
        LOGGER.error(f"Error in memory_command_handler: {e}")
        await update.message.reply_text("Произошла ошибка при получении воспоминаний.")


def _format_config_timestamp(config_snapshot: FinanceConfigSnapshot) -> str:
    return config_snapshot.loaded_at.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def _stale_config_message(config_snapshot: FinanceConfigSnapshot) -> str:
    loaded_at = _format_config_timestamp(config_snapshot)
    return (
        "Не удалось обновить категории и счета из Google Sheets. "
        f"Для этой операции использую последнюю успешную версию от {loaded_at}."
    )


async def voice_message_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    audio2text_model: Audio2TextModels = Audio2TextModels.whisper,
    custom_text: str = None,
) -> None:
    # Step I. Convert voice message to text.
    processing_message = None
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            processing_message = await update.message.reply_text(
                "1/3 Конвертирую аудио в текст. Ожидайте..."
            )
            break
        except TimedOut:
            if attempt < max_retries - 1:
                LOGGER.warning(
                    f"Timeout sending message, attempt {attempt + 1}/{max_retries}. Retrying in {retry_delay}s..."
                )
                await asyncio.sleep(retry_delay)
            else:
                LOGGER.error("Failed to send message after all retries")
                await update.message.reply_text(
                    "Не удалось отправить сообщение. Попробуйте позже."
                )
                return

    if not processing_message:
        return

    context.user_data["reply_message"] = (
        processing_message  # save message for next usage
    )

    try:
        config_result = await asyncio.to_thread(get_finance_config)
    except FinanceConfigUnavailableError:
        LOGGER.exception("Finance configuration is unavailable for voice processing")
        await edit_message(
            message=processing_message,
            text=(
                "Не удалось загрузить категории и счета из Google Sheets. "
                "Выполните /reload_config и повторите сообщение."
            ),
        )
        return

    config_snapshot = config_result.snapshot
    if config_result.used_stale:
        await update.message.reply_text(_stale_config_message(config_snapshot))

    voice_memory_context = await asyncio.to_thread(get_memory_context)
    text_from_audio = await get_text_from_audio(
        update,
        context,
        audio2text_model,
        config_snapshot,
        custom_text,
    )
    response_formats = ResponseFormat(config_snapshot)

    # Step II. First request to ChatGPT: get json data with operation type and text validity.
    # Text will be divided into parts if user ask for few request in one voice message.
    await edit_message(
        message=processing_message,
        text="2/3 Определяю тип операции и валидность текста. Ожидайте...",
        user_message=text_from_audio,
    )
    finance_operation_request_message = await asyncio.to_thread(
        _request_openai_data,
        text_from_audio,
        response_formats.finance_operation_response,
        True,
        voice_memory_context,
    )
    LOGGER.info(f"{finance_operation_request_message=}")

    # Step III. Second requests to ChatGPT: get json data that will be added to Google Tables.
    operation_sequence = 0
    for _, finance_operations in finance_operation_request_message.items():
        for finance_operation in finance_operations:
            operation_sequence += 1
            operation_message = processing_message
            if operation_sequence > 1:
                operation_message = await update.message.reply_text(
                    "3/3 Обрабатываю следующую операцию. Ожидайте..."
                )

            LOGGER.info(f"{finance_operation=}")

            operation_type: str = finance_operation.get("operation_type")
            source_inputted_text: str = finance_operation.get("source_inputted_text")
            message_to_user: str = finance_operation.get("message_to_user")
            user_request_is_correct: bool = finance_operation.get(
                "user_request_is_relevant"
            )

            operation_type = await clarify_operation_type(
                operation_type, operation_message, source_inputted_text
            )
            if not operation_type:
                continue

            if not user_request_is_correct:
                await edit_message(
                    message=operation_message,
                    text=f'Запрос некорректен. Ответ ChatGPT: "{message_to_user}"',
                    user_message=source_inputted_text,
                )
                continue

            await edit_message(
                message=operation_message,
                text=f"3/3 Определяю данные для Google Tables. Ожидайте...",
                user_message=source_inputted_text,
            )

            response_format = get_response_format_according_to_operation_type(
                operation_type,
                response_formats,
            )
            request_message = await asyncio.to_thread(
                _request_openai_data,
                source_inputted_text,
                response_format,
                False,
                voice_memory_context,
            )

            LOGGER.info(f"(RAW) {request_message=}")

            request_message = clarify_request_message(
                request_message,
                config_snapshot,
            )

            LOGGER.info(f"{request_message=}")

            # save operation_type and request_message to use in button_click_handler()
            body_text = format_json_to_telegram_text(request_message)

            # Tie every operation to the originating user message and chat.
            message_id = build_operation_tracking_id(
                update.message.chat_id,
                update.message.message_id,
                operation_sequence,
            )

            # Store message-specific data with unique key
            message_data_key = f"msg_{message_id}"
            context.user_data[message_data_key] = {
                "operation_type": operation_type,
                "request_message": request_message,
                "body_text": body_text,
                "source_inputted_text": source_inputted_text,
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

                    saved = await _write_finance_operation(data)
                    if saved:
                        context.user_data[message_data_key]["saved_to_sheets"] = True
                        context.user_data[message_data_key]["list_name"] = data.list_name
                        keyboard = get_delete_button_keyboard(message_id)
                        status_text = "✅ Сохранено в Google Sheets"
                    else:
                        keyboard = None
                        status_text = (
                            "Результат сохранения неизвестен. "
                            "Проверьте Google Sheets перед повторной отправкой."
                        )
                except Exception as e:
                    LOGGER.error(f"Failed to auto-save to Google Sheets: {e}")
                    keyboard = None
                    status_text = "Не удалось сохранить операцию."

            # send message with buttons
            await edit_message(
                message=operation_message,
                text=body_text,
                user_message=source_inputted_text,
                status=status_text,
                reply_markup=keyboard,
            )


async def set_bot_commands(application: Application) -> None:
    """
    Регистрирует команды бота для автодополнения в Telegram.
    """
    commands = [
        BotCommand("expenses_status", "Показать расходы за текущий месяц"),
        BotCommand("memory", "Управление сохранёнными воспоминаниями"),
        BotCommand("reload_config", "Обновить категории и счета из Google Sheets"),
    ]

    await application.bot.set_my_commands(commands)
    LOGGER.info("Bot commands have been set")


async def initialize_bot(application: Application) -> None:
    try:
        config_result = await asyncio.to_thread(reload_finance_config)
        if config_result.used_stale:
            LOGGER.warning(
                "Startup finance configuration refresh failed. Last known good snapshot remains active."
            )
    except FinanceConfigUnavailableError:
        LOGGER.exception(
            "Startup finance configuration load failed. Bot will retry on the next operation."
        )

    await set_bot_commands(application)


async def reload_config_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    del context
    try:
        config_result = await asyncio.to_thread(reload_finance_config)
    except FinanceConfigUnavailableError:
        LOGGER.exception("Manual finance configuration reload failed without a cache")
        await update.message.reply_text(
            "Не удалось загрузить категории и счета из Google Sheets. Попробуйте позже."
        )
        return

    config_snapshot = config_result.snapshot
    loaded_at = _format_config_timestamp(config_snapshot)
    if config_result.used_stale:
        await update.message.reply_text(
            "Обновить категории и счета не удалось. "
            f"Продолжает действовать версия от {loaded_at}."
        )
        return

    await update.message.reply_text(
        "Категории и счета обновлены. "
        f"Расходы: {len(config_snapshot.expenses)}, "
        f"доходы: {len(config_snapshot.incomes)}, "
        f"счета: {len(config_snapshot.accounts)}. "
        f"Версия от {loaded_at}."
    )


def run() -> None:
    dev_mode = os.getenv("DEV", "").strip().lower() in {"1", "true", "yes", "on"}
    token_env_var = "TELEGRAM_TOKEN_DEV" if dev_mode else "TELEGRAM_TOKEN"
    token = os.getenv(token_env_var)
    if not token:
        raise ValueError(f"Missing required environment variable: {token_env_var}")

    if dev_mode:
        LOGGER.warning("!!! RUNNING IN DEV MODE !!!")

    application = Application.builder().token(token).build()

    # Устанавливаем глобальный обработчик ошибок
    application.add_error_handler(global_error_handler)

    # Регистрируем команды бота при старте
    application.post_init = initialize_bot

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
        MessageHandler(filters.VOICE & ~filters.COMMAND, handler_with_vosk)
    )

    # Обработчик для нажатий на кнопки
    application.add_handler(CallbackQueryHandler(button_click_handler))

    # Обработчик для команды /expenses_status
    application.add_handler(CommandHandler("expenses_status", expenses_status_handler))

    # Обработчик для команды /memory
    application.add_handler(CommandHandler("memory", memory_command_handler))

    application.add_handler(CommandHandler("reload_config", reload_config_handler))

    # Обработчик для текстовых сообщений, начинающихся с #
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, memory_text_handler)
    )

    # run
    application.run_polling(allowed_updates=Update.ALL_TYPES)
