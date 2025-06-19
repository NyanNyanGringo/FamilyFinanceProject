"""
Агент для обработки переводов и корректировок.
"""
from .base import BaseAgent, AgentRequest, AgentResponse
from lib.utilities.google_utilities import (
    RequestData, ListName, Category, Status, TransferType,
    insert_and_update_row_batch_update, OperationTypes
)
from lib.utilities.openai_utilities import (
    request_data, RequestBuilder, ResponseFormat, MessageRequest
)


class TransferAgent(BaseAgent):
    """Агент для обработки переводов между счетами и корректировок балансов."""
    
    def __init__(self):
        """Инициализация агента переводов."""
        super().__init__("TransferAgent")
    
    async def process(self, request: AgentRequest) -> AgentResponse:
        """
        Обработка запроса на перевод или корректировку.
        
        Args:
            request: Запрос с данными о переводе/корректировке
            
        Returns:
            AgentResponse: Результат обработки
        """
        try:
            # Валидация базового запроса
            validation_error = await self.validate_request(request)
            if validation_error:
                return self.create_error_response(validation_error)
            
            # Определяем тип операции (перевод или корректировка)
            is_adjustment = request.operation_type == OperationTypes.adjustment
            
            # Получаем детали операции через OpenAI
            if is_adjustment:
                operation_details = await self._extract_adjustment_details(request.user_message)
            else:
                operation_details = await self._extract_transfer_details(request.user_message)
            
            if not operation_details:
                return self.create_error_response(
                    f"Не удалось извлечь данные о {'корректировке' if is_adjustment else 'переводе'} из сообщения"
                )
            
            # Валидация данных
            validation_result = self._validate_operation_data(operation_details, is_adjustment)
            if not validation_result['valid']:
                return AgentResponse(
                    success=False,
                    message=validation_result['message'],
                    errors=validation_result['errors'],
                    needs_clarification=True,
                    clarification_message=validation_result['message']
                )
            
            # Создаём запрос для Google Sheets
            google_request = self._create_google_request(operation_details, is_adjustment)
            
            # Отправляем данные в Google Sheets
            insert_and_update_row_batch_update(google_request)
            
            # Формируем успешный ответ
            success_message = self._format_success_message(operation_details, is_adjustment)
            
            return self.create_success_response(
                message=success_message,
                data=operation_details
            )
            
        except Exception as e:
            self.logger.error(f"Error processing transfer/adjustment: {str(e)}")
            return self.create_error_response(f"Ошибка при обработке операции: {str(e)}")
    
    async def _extract_transfer_details(self, user_message: str) -> dict:
        """
        Извлечение деталей перевода из сообщения пользователя.
        
        Args:
            user_message: Сообщение пользователя
            
        Returns:
            dict: Детали перевода
        """
        try:
            response = request_data(
                RequestBuilder(
                    message_request=MessageRequest(
                        user_message=user_message
                    ).basic_request_message,
                    response_format=ResponseFormat().transfer_response_format
                )
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error extracting transfer details: {str(e)}")
            return {}
    
    async def _extract_adjustment_details(self, user_message: str) -> dict:
        """
        Извлечение деталей корректировки из сообщения пользователя.
        
        Args:
            user_message: Сообщение пользователя
            
        Returns:
            dict: Детали корректировки
        """
        try:
            response = request_data(
                RequestBuilder(
                    message_request=MessageRequest(
                        user_message=user_message
                    ).basic_request_message,
                    response_format=ResponseFormat().adjustment_response_format
                )
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error extracting adjustment details: {str(e)}")
            return {}    
    def _validate_operation_data(self, operation_data: dict, is_adjustment: bool) -> dict:
        """
        Валидация данных операции.
        
        Args:
            operation_data: Данные операции для валидации
            is_adjustment: True если это корректировка, False если перевод
            
        Returns:
            dict: Результат валидации с ключами 'valid', 'message', 'errors'
        """
        errors = []
        
        if is_adjustment:
            # Валидация корректировки
            if not operation_data.get('adjustment_amount'):
                errors.append("Не указана сумма корректировки")
            
            if not operation_data.get('adjustment_account'):
                errors.append("Не указан счёт для корректировки")
            elif operation_data['adjustment_account'] not in Category.get_accounts():
                errors.append(f"Неверный счёт: {operation_data['adjustment_account']}")
        else:
            # Валидация перевода
            if not operation_data.get('write_off_amount'):
                errors.append("Не указана сумма списания")
            
            if not operation_data.get('write_off_account'):
                errors.append("Не указан счёт списания")
            elif operation_data['write_off_account'] not in Category.get_accounts():
                errors.append(f"Неверный счёт списания: {operation_data['write_off_account']}")
            
            if not operation_data.get('replenishment_account'):
                errors.append("Не указан счёт зачисления")
            elif operation_data['replenishment_account'] not in Category.get_accounts():
                errors.append(f"Неверный счёт зачисления: {operation_data['replenishment_account']}")
            
            # Проверка, что счета разные
            if (operation_data.get('write_off_account') == 
                operation_data.get('replenishment_account')):
                errors.append("Счёт списания и зачисления не могут совпадать")
        
        if errors:
            return {
                'valid': False,
                'message': "Пожалуйста, уточните следующие данные:\n" + "\n".join(errors),
                'errors': errors
            }
        
        return {'valid': True, 'message': '', 'errors': []}    
    def _create_google_request(self, operation_data: dict, is_adjustment: bool) -> RequestData:
        """
        Создание запроса для Google Sheets.
        
        Args:
            operation_data: Данные операции
            is_adjustment: True если это корректировка
            
        Returns:
            RequestData: Объект запроса для Google Sheets
        """
        if is_adjustment:
            return RequestData(
                list_name=ListName.transfers,
                transfer_type=TransferType.adjustment,
                account=operation_data.get('adjustment_account'),
                replenishment_account=operation_data.get('adjustment_account'),
                amount=0,
                replenishment_amount=operation_data.get('adjustment_amount'),
                status=operation_data.get('status', Status.committed),
                comment=operation_data.get('comment', '')
            )
        else:
            return RequestData(
                list_name=ListName.transfers,
                transfer_type=TransferType.transfer,
                account=operation_data.get('write_off_account'),
                replenishment_account=operation_data.get('replenishment_account'),
                amount=operation_data.get('write_off_amount'),
                replenishment_amount=operation_data.get('replenishment_amount', 
                                                    operation_data.get('write_off_amount')),
                status=operation_data.get('status', Status.committed),
                comment=operation_data.get('comment', '')
            )    
    def _format_success_message(self, operation_data: dict, is_adjustment: bool) -> str:
        """
        Форматирование сообщения об успешной операции.
        
        Args:
            operation_data: Данные операции
            is_adjustment: True если это корректировка
            
        Returns:
            str: Отформатированное сообщение
        """
        if is_adjustment:
            return (
                f"✅ Корректировка выполнена:\n"
                f"💳 Счёт: {operation_data['adjustment_account']}\n"
                f"💰 Новый баланс: {operation_data['adjustment_amount']}\n"
                f"📝 Комментарий: {operation_data.get('comment', 'Нет')}\n"
                f"📊 Статус: {operation_data.get('status', Status.committed)}"
            )
        else:
            return (
                f"✅ Перевод выполнен:\n"
                f"➖ Списано: {operation_data['write_off_amount']} с {operation_data['write_off_account']}\n"
                f"➕ Зачислено: {operation_data.get('replenishment_amount', operation_data['write_off_amount'])} "
                f"на {operation_data['replenishment_account']}\n"
                f"📝 Комментарий: {operation_data.get('comment', 'Нет')}\n"
                f"📊 Статус: {operation_data.get('status', Status.committed)}"
            )