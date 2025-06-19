"""
Агент для обработки расходов.
"""
from .base import BaseAgent, AgentRequest, AgentResponse
from lib.utilities.google_utilities import (
    RequestData, ListName, Category, Status, 
    insert_and_update_row_batch_update
)
from lib.utilities.openai_utilities import (
    request_data, RequestBuilder, ResponseFormat, MessageRequest
)


class ExpenseAgent(BaseAgent):
    """Агент для обработки операций расходов."""
    
    def __init__(self):
        """Инициализация агента расходов."""
        super().__init__("ExpenseAgent")
    
    async def process(self, request: AgentRequest) -> AgentResponse:
        """
        Обработка запроса на добавление расхода.
        
        Args:
            request: Запрос с данными о расходе
            
        Returns:
            AgentResponse: Результат обработки
        """
        try:
            # Валидация базового запроса
            validation_error = await self.validate_request(request)
            if validation_error:
                return self.create_error_response(validation_error)
            
            # Получаем детали расхода через OpenAI
            expense_details = await self._extract_expense_details(request.user_message)
            
            if not expense_details:
                return self.create_error_response(
                    "Не удалось извлечь данные о расходе из сообщения"
                )
            
            # Валидация данных расхода
            validation_result = self._validate_expense_data(expense_details)
            if not validation_result['valid']:
                return AgentResponse(
                    success=False,
                    message=validation_result['message'],
                    errors=validation_result['errors'],
                    needs_clarification=True,
                    clarification_message=validation_result['message']
                )
            
            # Формируем успешный ответ
            success_message = self._format_success_message(expense_details)
            
            # Сохраняем данные в контексте для отправки после получения message_id
            request.context.user_data['pending_expense_data'] = expense_details
            request.context.user_data['pending_operation_type'] = 'expense'
            
            return self.create_success_response(
                message=success_message,
                data=expense_details
            )
            
        except Exception as e:
            self.logger.error(f"Error processing expense: {str(e)}")
            return self.create_error_response(f"Ошибка при обработке расхода: {str(e)}")
    
    async def _extract_expense_details(self, user_message: str) -> dict:
        """
        Извлечение деталей расхода из сообщения пользователя через OpenAI.
        
        Args:
            user_message: Сообщение пользователя
            
        Returns:
            dict: Детали расхода
        """
        try:
            response = request_data(
                RequestBuilder(
                    message_request=MessageRequest(
                        user_message=user_message
                    ).basic_request_message,
                    response_format=ResponseFormat().expenses_response_format
                )
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error extracting expense details: {str(e)}")
            return {}
    
    def _validate_expense_data(self, expense_data: dict) -> dict:
        """
        Валидация данных расхода.
        
        Args:
            expense_data: Данные расхода для валидации
            
        Returns:
            dict: Результат валидации с ключами 'valid', 'message', 'errors'
        """
        errors = []
        
        # Проверка обязательных полей
        if not expense_data.get('amount'):
            errors.append("Не указана сумма расхода")
        
        if not expense_data.get('expenses_category'):
            errors.append("Не указана категория расхода")
        elif expense_data['expenses_category'] not in Category.get_expenses():
            errors.append(f"Неверная категория: {expense_data['expenses_category']}")
        
        if not expense_data.get('account'):
            errors.append("Не указан счёт списания")
        elif expense_data['account'] not in Category.get_accounts():
            errors.append(f"Неверный счёт: {expense_data['account']}")
        
        if errors:
            return {
                'valid': False,
                'message': "Пожалуйста, уточните следующие данные:\n" + "\n".join(errors),
                'errors': errors
            }
        
        return {'valid': True, 'message': '', 'errors': []}
    
    def _create_google_request(self, expense_data: dict, message_id: int = None) -> RequestData:
        """
        Создание запроса для Google Sheets.
        
        Args:
            expense_data: Данные расхода
            message_id: ID сообщения Telegram
            
        Returns:
            RequestData: Объект запроса для Google Sheets
        """
        return RequestData(
            list_name=ListName.expenses,
            expenses_category=expense_data.get('expenses_category'),
            account=expense_data.get('account'),
            amount=expense_data.get('amount'),
            status=expense_data.get('status', Status.committed),
            comment=expense_data.get('comment', ''),
            message_id=message_id
        )
    
    def _format_success_message(self, expense_data: dict) -> str:
        """
        Форматирование сообщения об успешном добавлении расхода.
        
        Args:
            expense_data: Данные расхода
            
        Returns:
            str: Отформатированное сообщение
        """
        return (
            f"✅ Расход добавлен:\n"
            f"💰 Сумма: {expense_data['amount']}\n"
            f"📂 Категория: {expense_data['expenses_category']}\n"
            f"💳 Счёт: {expense_data['account']}\n"
            f"📝 Комментарий: {expense_data.get('comment', 'Нет')}\n"
            f"📊 Статус: {expense_data.get('status', Status.committed)}"
        )
