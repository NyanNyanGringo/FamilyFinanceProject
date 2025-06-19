"""
Агент для обработки reply-сообщений и редактирования существующих операций.
"""
from typing import Optional, Dict, Any
from telegram import Message

from .base import BaseAgent, AgentRequest, AgentResponse
from lib.utilities.google_utilities import (
    get_values, ListName, Category, Status
)
from lib.utilities.openai_utilities import (
    request_data, RequestBuilder, MessageRequest, text2text
)
from lib.utilities.log_utilities import get_logger


LOGGER = get_logger(__name__)


class ReplyAgent(BaseAgent):
    """Агент для обработки редактирования операций через reply."""
    
    def __init__(self):
        """Инициализация агента reply."""
        super().__init__("ReplyAgent")
    
    def _get_reply_chain(self, message: Message) -> list:
        """
        Собирает простую цепочку reply-сообщений.
        
        Args:
            message: Начальное сообщение
            
        Returns:
            list: Список сообщений от первого к последнему
        """
        chain = []
        current_message = message
        
        # Идем вверх по цепочке reply
        while current_message:
            chain.append({
                'message_id': current_message.message_id,
                'text': current_message.text or '',
                'from_user': current_message.from_user.username if current_message.from_user else 'Unknown',
                'is_bot': current_message.from_user.is_bot if current_message.from_user else False
            })
            
            # Получаем сообщение, на которое был reply
            current_message = current_message.reply_to_message
        
        # Разворачиваем, чтобы первое сообщение было в начале
        chain.reverse()
        
        return chain
    
    def _get_full_reply_chain(self, message: Message) -> list:
        """
        Собирает полную цепочку всех связанных сообщений.
        
        Args:
            message: Начальное сообщение
            
        Returns:
            list: Список всех связанных сообщений
        """
        all_messages = []
        visited_ids = set()
        
        # Простой итеративный подход - идем вверх по цепочке
        current = message
        while current and current.message_id not in visited_ids:
            visited_ids.add(current.message_id)
            
            msg_info = {
                'message_id': current.message_id,
                'text': current.text or '',
                'from_user': current.from_user.username if current.from_user else 'Unknown',
                'is_bot': current.from_user.is_bot if current.from_user else False,
            }
            all_messages.append(msg_info)
            
            self.logger.info(f"Collected: {msg_info['from_user']} (id={current.message_id}): {msg_info['text'][:50]}...")
            
            # Переходим к следующему сообщению в цепочке
            if current.reply_to_message:
                self.logger.info(f"  -> Has reply_to_message id={current.reply_to_message.message_id}")
                current = current.reply_to_message
            else:
                break
        
        # Разворачиваем список, чтобы он шел от первого сообщения к последнему
        all_messages.reverse()
        
        self.logger.info(f"Full reply chain collected: {len(all_messages)} messages")
        
        # Выводим полную цепочку для отладки
        self.logger.info("=== FULL CHAIN SUMMARY ===")
        for i, msg in enumerate(all_messages):
            self.logger.info(f"  [{i}] {msg['from_user']} (bot={msg['is_bot']}, id={msg['message_id']}): {msg['text'][:50]}...")
        self.logger.info("=== END CHAIN SUMMARY ===")
        
        return all_messages
    
    def _find_operation_in_chain(self, chain: list) -> Optional[Dict[str, Any]]:
        """
        Ищет операцию в цепочке сообщений.
        
        Args:
            chain: Цепочка сообщений
            
        Returns:
            Dict с информацией об операции или None
        """
        self.logger.info(f"Searching for operation in chain of {len(chain)} messages")
        
        # Сначала ищем скрытую информацию об операции в сообщениях бота
        import re
        for msg in chain:
            if msg['is_bot'] and '\u200B[op:' in msg['text']:
                # Извлекаем message_id из скрытой информации
                match = re.search(r'\u200B\[op:(\d+)\]', msg['text'])
                if match:
                    hidden_message_id = int(match.group(1))
                    self.logger.info(f"Found hidden operation reference: message_id={hidden_message_id}")
                    operation_info = self._find_operation_by_message_id(hidden_message_id)
                    if operation_info:
                        self.logger.info(f"Found operation through hidden reference")
                        operation_info['message_id'] = hidden_message_id
                        return operation_info
        
        # Идем по всем сообщениям от бота в обратном порядке (от новых к старым)
        bot_messages = [msg for msg in chain if msg['is_bot']]
        bot_messages.reverse()  # Начинаем с самых новых сообщений
        
        self.logger.info(f"Found {len(bot_messages)} bot messages in chain")
        
        for i, msg in enumerate(bot_messages):
            if msg['message_id']:
                self.logger.info(f"[{i}] Checking bot message with id {msg['message_id']}: {msg['text'][:50]}...")
                
                # Сначала проверяем - не является ли это сообщением об обновлении
                update_indicators = ['✅ Операция обновлена', '✅ Операция удалена', 'Ваш запрос:']
                is_update_message = any(indicator in msg['text'] for indicator in update_indicators)
                
                if is_update_message:
                    self.logger.info(f"  -> This is an update message, skipping direct search")
                    # Продолжаем поиск дальше по цепочке
                    continue
                
                # Пытаемся найти операцию по message_id
                operation_info = self._find_operation_by_message_id(msg['message_id'])
                if operation_info:
                    self.logger.info(f"  -> Found operation for message_id {msg['message_id']}")
                    # Добавляем message_id в результат
                    operation_info['message_id'] = msg['message_id']
                    return operation_info
                else:
                    self.logger.info(f"  -> No operation found for message_id {msg['message_id']}")
        
        # Если не нашли операцию напрямую, ищем сообщения с признаками операции
        self.logger.info("No operation found by message_id, checking for operation keywords...")
        operation_keywords = ['✅ Расход добавлен:', '✅ Доход добавлен:', '✅ Перевод выполнен:', '✅ Корректировка выполнена:']
        
        for i, msg in enumerate(bot_messages):
            # Пропускаем сообщения об обновлении
            if any(indicator in msg['text'] for indicator in ['✅ Операция обновлена', '✅ Операция удалена', 'Ваш запрос:']):
                continue
                
            if any(keyword in msg['text'] for keyword in operation_keywords):
                self.logger.info(f"[{i}] Found operation message by keywords: {msg['text'][:100]}...")
                
                # Пытаемся найти операцию по message_id еще раз
                # (на случай если операция была создана с этим message_id)
                if msg['message_id']:
                    operation_info = self._find_operation_by_message_id(msg['message_id'])
                    if operation_info:
                        self.logger.info(f"  -> Found operation after keyword match for message_id {msg['message_id']}")
                        operation_info['message_id'] = msg['message_id']
                        return operation_info
        
        self.logger.warning("No operation found in the entire chain")
        return None
    
    async def process(self, request: AgentRequest) -> AgentResponse:
        """
        Обработка reply-запроса на редактирование операции.
        
        Args:
            request: Запрос с данными для редактирования
            
        Returns:
            AgentResponse: Результат обработки
        """
        try:
            self.logger.info("ReplyAgent processing started")
            
            # Получаем текущее сообщение
            current_message = request.telegram_update.message
            
            # Собираем полную цепочку reply
            chain = self._get_full_reply_chain(current_message)
            
            self.logger.info("Chain summary:")
            for i, msg in enumerate(chain):
                self.logger.info(f"  [{i}] id={msg['message_id']} {msg['from_user']} (bot={msg['is_bot']}): {msg['text'][:50]}...")
            
            if len(chain) < 2:
                return self.create_error_response("Не найдена цепочка сообщений для обработки")
            
            # Ищем операцию в цепочке
            operation_info = self._find_operation_in_chain(chain)
            
            if not operation_info:
                return self.create_error_response(
                    "Не найдена операция для редактирования. Возможно, она была создана до добавления поддержки редактирования."
                )
            
            # Сохраняем message_id операции для последующих reply
            operation_message_id = operation_info.get('message_id')
            self.logger.info(f"Found operation with message_id: {operation_message_id}")
            
            # Добавляем в контекст для использования при отправке ответа
            request.context.user_data['reply_to_message_id'] = operation_message_id
            self.logger.info(f"Saved reply_to_message_id to context: {operation_message_id}")
            
            # Собираем контекст из всей цепочки
            context_messages = []
            # Сортируем сообщения по message_id для хронологического порядка
            sorted_chain = sorted(chain, key=lambda x: x['message_id'])
            
            for msg in sorted_chain:
                if msg['text']:
                    prefix = "→ " if msg.get('reply_to_message') else ""
                    context_messages.append(f"{prefix}{msg['from_user']}: {msg['text']}")
            
            # Анализируем запрос пользователя с учетом контекста
            edit_request = await self._analyze_edit_request(
                request.user_message,
                operation_info,
                context_messages
            )
            
            if edit_request.get('action') == 'delete':
                # Удаление операции
                result = self._delete_operation(operation_info)
                if result:
                    return self.create_success_response("✅ Операция удалена")
                else:
                    return self.create_error_response("Ошибка при удалении операции")
            
            # Применяем изменения
            result = self._apply_changes(operation_info, edit_request)
            
            if result:
                success_message = self._format_edit_success_message(
                    edit_request,
                    user_message=request.user_message,
                    operation_message_id=operation_message_id
                )
                return self.create_success_response(
                    message=success_message,
                    data=edit_request
                )
            else:
                return self.create_error_response("Ошибка при обновлении операции")
            
        except Exception as e:
            self.logger.error(f"Error processing reply: {str(e)}")
            return self.create_error_response(f"Ошибка при обработке: {str(e)}")
    
    def _find_operation_by_message_id(self, message_id: int) -> Optional[Dict[str, Any]]:
        """
        Поиск операции по message_id в Google Sheets.
        
        Args:
            message_id: ID сообщения Telegram
            
        Returns:
            Dict с информацией об операции или None
        """
        try:
            # Проверяем все три листа
            sheets_config = [
                {
                    'list_name': ListName.expenses,
                    'range': 'L7:L2000',  # Столбец L для расходов
                    'data_range': 'A7:L'
                },
                {
                    'list_name': ListName.incomes,
                    'range': 'K7:K2000',  # Столбец K для доходов
                    'data_range': 'A7:K'
                },
                {
                    'list_name': ListName.transfers,
                    'range': 'M7:M2000',  # Столбец M для переводов
                    'data_range': 'A7:M'
                }
            ]
            
            for config in sheets_config:
                # Получаем столбец с message_id
                range_name = f"{config['list_name']}!{config['range']}"
                self.logger.info(f"Getting message_ids from range: {range_name}")
                
                try:
                    message_ids = get_values(range_name, True)
                except Exception as e:
                    self.logger.warning(f"Error getting values from {range_name}: {e}")
                    continue
                
                if not message_ids:
                    self.logger.info(f"No message_ids found in {config['list_name']}")
                    continue
                    
                self.logger.info(f"Found {len(message_ids)} message_ids in {config['list_name']}")
                
                # Ищем нужный message_id
                for idx, msg_id in enumerate(message_ids):
                    if msg_id:
                        try:
                            msg_id_value = int(float(msg_id))  # float() для обработки дробных чисел
                            self.logger.info(f"Checking message_id at index {idx}: {msg_id} -> {msg_id_value}")
                            if msg_id_value == message_id:  
                                # Нашли! Получаем данные строки
                                row_number = 7 + idx
                                self.logger.info(f"Found message_id {message_id} at row {row_number}")
                                
                                try:
                                    row_data = get_values(f"{config['list_name']}!A{row_number}:M{row_number}")[0]
                                    self.logger.info(f"Row data: {row_data}")
                                except Exception as e:
                                    self.logger.error(f"Error getting row data: {e}")
                                    continue
                                
                                return {
                                    'list_name': config['list_name'],
                                    'row_number': row_number,
                                    'data': row_data,
                                    'operation_type': self._get_operation_type(config['list_name']),
                                    'message_id': message_id  # Добавляем message_id
                                }
                        except (ValueError, TypeError) as e:
                            self.logger.warning(f"Error converting message_id '{msg_id}': {e}")
                            continue
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding operation: {str(e)}")
            return None    
    def _get_operation_type(self, list_name: ListName) -> str:
        """Определение типа операции по имени листа."""
        mapping = {
            ListName.expenses: "expenses",
            ListName.incomes: "incomes",
            ListName.transfers: "transfers"
        }
        return mapping.get(list_name, "unknown")
    
    async def _analyze_edit_request(self, user_message: str, operation_info: Dict, context_messages: list = None) -> Dict:
        """
        Анализ запроса пользователя на редактирование через OpenAI.
        
        Args:
            user_message: Сообщение пользователя
            operation_info: Информация о текущей операции
            context_messages: История сообщений из цепочки reply
            
        Returns:
            Dict с изменениями
        """
        # Формируем контекст из цепочки сообщений
        context = ""
        if context_messages:
            context = "История изменений:\n" + "\n".join(context_messages[-5:])  # Последние 5 сообщений
        
        prompt = f"""
        Пользователь хочет изменить финансовую операцию.
        
        Текущие данные операции:
        Тип: {operation_info['operation_type']}
        Данные: {operation_info['data']}
        
        {context}
        
        Последний запрос пользователя: {user_message}
        
        Определи, что именно нужно изменить. Возможные действия:
        1. Изменить сумму
        2. Изменить категорию
        3. Изменить счёт
        4. Изменить комментарий
        5. Изменить статус
        6. Удалить операцию (если пользователь просит удалить)
        
        ВАЖНО: Возвращай ТОЛЬКО те поля, которые нужно изменить. Не включай поля, которые должны остаться без изменений.
        
        Верни JSON в формате:
        {{
            "action": "edit" или "delete",
            "changes": {{
                // Включай ТОЛЬКО измененные поля
                // Например, если меняется только сумма, то только:
                "amount": новая_сумма
                // НЕ включай остальные поля
            }}
        }}
        
        Пример: если пользователь написал "замени 410 на 500", верни:
        {{
            "action": "edit",
            "changes": {{
                "amount": 500
            }}
        }}
        """
        
        response = text2text(prompt)
        try:
            import json
            result = json.loads(response)
            # Удаляем пустые значения из changes
            if 'changes' in result:
                result['changes'] = {k: v for k, v in result['changes'].items() if v is not None and v != ''}
            return result
        except:
            return {"action": "edit", "changes": {}}    
    def _delete_operation(self, operation_info: Dict) -> bool:
        """
        Удаление операции из Google Sheets.
        
        Args:
            operation_info: Информация об операции
            
        Returns:
            bool: Успешность удаления
        """
        try:
            sheet_id = self._get_sheet_id(operation_info['list_name'])
            
            request = {
                "deleteDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": operation_info['row_number'] - 1,
                        "endIndex": operation_info['row_number']
                    }
                }
            }
            
            # Используем _SERVICE и SPREADSHEET_ID напрямую из google_utilities
            from lib.utilities.google_utilities import _SERVICE, SPREADSHEET_ID
            
            response = _SERVICE.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body={"requests": [request]}
            ).execute()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting operation: {str(e)}")
            return False
    
    def _apply_changes(self, operation_info: Dict, edit_request: Dict) -> bool:
        """
        Применение изменений к операции.
        
        Args:
            operation_info: Информация об операции
            edit_request: Запрос на изменение
            
        Returns:
            bool: Успешность обновления
        """
        try:
            changes = edit_request.get('changes', {})
            if not changes:
                return True
            
            self.logger.info(f"Applying changes: {changes}")
            self.logger.info(f"Current data: {operation_info['data']}")
            
            # Подготавливаем запросы на обновление
            requests = []
            sheet_id = self._get_sheet_id(operation_info['list_name'])
            row_index = operation_info['row_number'] - 1
            
            # Маппинг полей к индексам столбцов
            column_mapping = self._get_column_mapping(operation_info['list_name'])
            
            for field, value in changes.items():
                if field in column_mapping:
                    col_index = column_mapping[field]
                    requests.append({
                        "updateCells": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": row_index,
                                "endRowIndex": row_index + 1,
                                "startColumnIndex": col_index,
                                "endColumnIndex": col_index + 1
                            },
                            "rows": [{
                                "values": [{
                                    "userEnteredValue": self._get_cell_value(field, value)
                                }]
                            }],
                            "fields": "userEnteredValue"
                        }
                    })
            
            if requests:
                # Используем _SERVICE и SPREADSHEET_ID напрямую из google_utilities
                from lib.utilities.google_utilities import _SERVICE, SPREADSHEET_ID
                
                response = _SERVICE.spreadsheets().batchUpdate(
                    spreadsheetId=SPREADSHEET_ID,
                    body={"requests": requests}
                ).execute()
                
                self.logger.info(f"Successfully updated row {operation_info['row_number']}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error applying changes: {str(e)}")
            return False    
    def _get_sheet_id(self, list_name: ListName) -> int:
        """Получение ID листа по имени."""
        from lib.utilities.google_utilities import _get_sheet_ids
        sheet_ids = _get_sheet_ids()
        return sheet_ids.get(list_name)
    
    def _get_column_mapping(self, list_name: ListName) -> Dict[str, int]:
        """Маппинг полей к индексам столбцов."""
        if list_name == ListName.expenses:
            return {
                'amount': 4,  # E
                'category': 2,  # C
                'account': 3,  # D
                'status': 6,  # G
                'comment': 9  # J
            }
        elif list_name == ListName.incomes:
            return {
                'amount': 4,  # E
                'category': 2,  # C
                'account': 3,  # D
                'status': 6,  # G
                'comment': 9  # J
            }
        elif list_name == ListName.transfers:
            return {
                'amount': 5,  # F (write_off_amount)
                'replenishment_amount': 7,  # H
                'account': 3,  # D (write_off_account)
                'replenishment_account': 4,  # E
                'status': 9,  # J
                'comment': 10  # K
            }
        return {}
    
    def _get_cell_value(self, field: str, value: Any) -> Dict:
        """Преобразование значения в формат Google Sheets."""
        if field in ['amount', 'replenishment_amount']:
            return {"numberValue": float(value)}
        else:
            return {"stringValue": str(value)}
    
    def _format_edit_success_message(self, edit_request: Dict, user_message: str = None, operation_message_id: int = None) -> str:
        """
        Форматирование сообщения об успешном редактировании.
        
        Args:
            edit_request: Данные изменений
            user_message: Исходное сообщение пользователя для контекста
            operation_message_id: ID сообщения с исходной операцией
            
        Returns:
            str: Отформатированное сообщение
        """
        changes = edit_request.get('changes', {})
        if not changes:
            return "✅ Операция обновлена"
        
        message = "✅ Операция обновлена:\n"
        
        field_names = {
            'amount': '💰 Сумма',
            'category': '📂 Категория',
            'account': '💳 Счёт',
            'comment': '📝 Комментарий',
            'status': '📊 Статус',
            'replenishment_amount': '💰 Сумма зачисления',
            'replenishment_account': '💳 Счёт зачисления'
        }
        
        # Показываем только измененные поля
        for field, value in changes.items():
            if field in field_names and value is not None and value != '':
                message += f"{field_names[field]}: {value}\n"
        
        # Добавляем контекст из сообщения пользователя
        if user_message:
            message += f"\n📝 Ваш запрос: {user_message}"
            
        # Добавляем скрытую информацию об операции (zero-width space)
        if operation_message_id:
            message += f"\n\u200B[op:{operation_message_id}]"
        
        return message.strip()