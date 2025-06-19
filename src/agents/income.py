"""
Агент для обработки доходов.
"""
from .base import BaseAgent, AgentRequest, AgentResponse
from lib.utilities.google_utilities import (
    RequestData, ListName, Category, Status,
    insert_and_update_row_batch_update
)
from lib.utilities.openai_utilities import (
    request_data, RequestBuilder, ResponseFormat, MessageRequest
)


class IncomeAgent(BaseAgent):
    """Агент для обработки операций доходов."""
    
    def __init__(self):
        """Инициализация агента доходов."""
        super().__init__("IncomeAgent")
    
    async def process(self, request: AgentRequest) -> AgentResponse:
        """
        Обработка запроса на добавление дохода.
        
        Args:
            request: Запрос с данными о доходе
            
        Returns:
            AgentResponse: Результат обработки
        """
        try:
            # Валидация базового запроса
            validation_error = await self.validate_request(request)
            if validation_error:
                return self.create_error_response(validation_error)
            
            # Получаем детали дохода через OpenAI
            income_details = await self._extract_income_details(request.user_message)
            
            if not income_details:
                return self.create_error_response(
                    "Не удалось извлечь данные о доходе из сообщения"
                )
            
            # Валидация данных дохода
            validation_result = self._validate_income_data(income_details)
            if not validation_result['valid']:
                return AgentResponse(
                    success=False,
                    message=validation_result['message'],
                    errors=validation_result['errors'],
                    needs_clarification=True,
                    clarification_message=validation_result['message']
                )
            
            # Формируем успешный ответ
            success_message = self._format_success_message(income_details)
            
            # Сохраняем данные в контексте для отправки после получения message_id
            request.context.user_data['pending_income_data'] = income_details
            request.context.user_data['pending_operation_type'] = 'income'
            
            return self.create_success_response(
                message=success_message,
                data=income_details
            )
            
        except Exception as e:
            self.logger.error(f"Error processing income: {str(e)}")
            return self.create_error_response(f"Ошибка при обработке дохода: {str(e)}")
    
    async def _extract_income_details(self, user_message: str) -> dict:
        """
        Извлечение деталей дохода из сообщения пользователя через OpenAI.
        
        Args:
            user_message: Сообщение пользователя
            
        Returns:
            dict: Детали дохода
        """
        try:
            response = request_data(
                RequestBuilder(
                    message_request=MessageRequest(
                        user_message=user_message
                    ).basic_request_message,
                    response_format=ResponseFormat().incomes_response_format
                )
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error extracting income details: {str(e)}")
            return {}
    
    def _validate_income_data(self, income_data: dict) -> dict:
        """
        Валидация данных дохода.
        
        Args:
            income_data: Данные дохода для валидации
            
        Returns:
            dict: Результат валидации с ключами 'valid', 'message', 'errors'
        """
        errors = []
        
        # Проверка обязательных полей
        if not income_data.get('amount'):
            errors.append("Не указана сумма дохода")
        
        if not income_data.get('incomes_category'):
            errors.append("Не указана категория дохода")
        elif income_data['incomes_category'] not in Category.get_incomes():
            errors.append(f"Неверная категория: {income_data['incomes_category']}")
        
        if not income_data.get('account'):
            errors.append("Не указан счёт зачисления")
        elif income_data['account'] not in Category.get_accounts():
            errors.append(f"Неверный счёт: {income_data['account']}")
        
        if errors:
            return {
                'valid': False,
                'message': "Пожалуйста, уточните следующие данные:\n" + "\n".join(errors),
                'errors': errors
            }
        
        return {'valid': True, 'message': '', 'errors': []}
    
    def _create_google_request(self, income_data: dict) -> RequestData:
        """
        Создание запроса для Google Sheets.
        
        Args:
            income_data: Данные дохода
            
        Returns:
            RequestData: Объект запроса для Google Sheets
        """
        return RequestData(
            list_name=ListName.incomes,
            incomes_category=income_data.get('incomes_category'),
            account=income_data.get('account'),
            amount=income_data.get('amount'),
            status=income_data.get('status', Status.committed),
            comment=income_data.get('comment', '')
        )
    
    def _format_success_message(self, income_data: dict) -> str:
        """
        Форматирование сообщения об успешном добавлении дохода.
        
        Args:
            income_data: Данные дохода
            
        Returns:
            str: Отформатированное сообщение
        """
        return (
            f"✅ Доход добавлен:\n"
            f"💰 Сумма: {income_data['amount']}\n"
            f"📂 Категория: {income_data['incomes_category']}\n"
            f"💳 Счёт: {income_data['account']}\n"
            f"📝 Комментарий: {income_data.get('comment', 'Нет')}\n"
            f"📊 Статус: {income_data.get('status', Status.committed)}"
        )
