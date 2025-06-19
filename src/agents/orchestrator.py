"""
Главный оркестратор для маршрутизации запросов между агентами.
"""
from typing import Dict, Type, Optional
from telegram import Update, Message
from telegram.ext import ContextTypes

from .base import BaseAgent, AgentRequest, AgentResponse
from lib.utilities.google_utilities import OperationTypes
from lib.utilities.openai_utilities import request_data, RequestBuilder, ResponseFormat, MessageRequest
from lib.utilities.log_utilities import get_logger


LOGGER = get_logger(__name__)


class MainOrchestrator(BaseAgent):
    """Главный агент-диспетчер."""
    
    def __init__(self):
        """Инициализация оркестратора."""
        super().__init__("MainOrchestrator")
        self.agents: Dict[str, BaseAgent] = {}
        self._processing_message: Optional[Message] = None
    
    def register_agent(self, operation_type: str, agent: BaseAgent):
        """
        Регистрация агента для определённого типа операции.
        
        Args:
            operation_type: Тип операции (expenses, incomes, transfers, adjustment)
            agent: Экземпляр агента
        """
        self.agents[operation_type] = agent
        self.logger.info(f"Registered {agent.name} for operation type: {operation_type}")
    
    async def process(self, request: AgentRequest) -> AgentResponse:
        """
        Обработка запроса: определение намерения и делегирование соответствующему агенту.
        Поддерживает множественные операции.
        
        Args:
            request: Входящий запрос
            
        Returns:
            AgentResponse: Ответ от соответствующего агента
        """
        try:
            # Определяем операции через OpenAI
            operations = await self._extract_operations(request.user_message)
            
            if not operations:
                return self.create_error_response("Не удалось определить операции")
            
            # Если только одна операция - обрабатываем напрямую без множественной логики
            if len(operations) == 1:
                operation = operations[0]
                operation_type = operation.get("operation_type")
                
                # Валидация типа операции
                try:
                    validated_type = OperationTypes.get_item(operation_type)
                except ValueError:
                    return self.create_error_response(f"Неверный тип операции: {operation_type}")
                
                # Обновляем тип операции в запросе
                request.operation_type = validated_type
                
                # Находим подходящего агента
                agent = self.agents.get(validated_type)
                if not agent:
                    return self.create_error_response(
                        f"Не найден агент для операции типа: {validated_type}"
                    )
                
                # Делегируем обработку соответствующему агенту
                self.logger.info(f"Delegating to {agent.name}")
                response = await agent.process(request)
                
                return response
            
            # Для множественных операций используем существующую логику
            results = []
            for idx, operation in enumerate(operations):
                operation_type = operation.get("operation_type")
                source_text = operation.get("source_inputted_text")
                
                if not operation_type or operation_type == "None":
                    continue
                
                # Валидация типа операции
                try:
                    validated_type = OperationTypes.get_item(operation_type)
                except ValueError:
                    self.logger.error(f"Invalid operation type: {operation_type}")
                    continue
                
                # Создаем новый запрос для этой операции
                operation_request = AgentRequest(
                    operation_type=validated_type,
                    user_message=source_text,
                    telegram_update=request.telegram_update,
                    context=request.context
                )
                
                # Находим подходящего агента
                agent = self.agents.get(validated_type)
                if not agent:
                    results.append({
                        "success": False,
                        "message": f"Не найден агент для операции типа: {validated_type}"
                    })
                    continue
                
                # Делегируем обработку соответствующему агенту
                self.logger.info(f"Delegating operation {idx + 1} to {agent.name}")
                response = await agent.process(operation_request)
                
                # Отправляем результат как отдельное сообщение
                if response.success:
                    sent_message = await request.telegram_update.message.reply_text(
                        response.message,
                        parse_mode='HTML'
                    )
                
                results.append({
                    "success": response.success,
                    "message": response.message,
                    "data": response.data
                })
            
            # Формируем итоговый ответ
            if results:
                success_count = sum(1 for r in results if r['success'])
                total_count = len(results)
                
                if success_count == total_count:
                    return self.create_success_response(
                        f"Обработано операций: {success_count}/{total_count}"
                    )
                else:
                    return AgentResponse(
                        success=True,  # Частичный успех
                        message=f"Обработано операций: {success_count}/{total_count}",
                        data={"results": results}
                    )
            else:
                return self.create_error_response("Не найдено операций для обработки")
            
        except Exception as e:
            self.logger.error(f"Error in orchestrator: {str(e)}")
            return self.create_error_response(f"Ошибка оркестратора: {str(e)}")
    
    async def _determine_operation_type(self, user_message: str) -> Optional[str]:
        """
        Определение типа операции через OpenAI.
        
        Args:
            user_message: Сообщение пользователя
            
        Returns:
            Optional[str]: Тип операции или None
        """
        try:
            # Используем существующую логику определения типа операции
            finance_operation_request = request_data(
                RequestBuilder(
                    message_request=MessageRequest(
                        user_message=user_message
                    ).finance_operation_request_message,
                    response_format=ResponseFormat().finance_operation_response
                )
            )
            
            # Извлекаем тип операции из ответа
            for _, operations in finance_operation_request.items():
                if operations and len(operations) > 0:
                    operation = operations[0]
                    operation_type = operation.get("operation_type")
                    
                    # Валидация типа операции
                    try:
                        validated_type = OperationTypes.get_item(operation_type)
                        return validated_type
                    except ValueError:
                        self.logger.error(f"Invalid operation type: {operation_type}")
                        return None
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error determining operation type: {str(e)}")
            return None
    
    async def _update_processing_message(self, text: str):
        """
        Обновление сообщения о процессе обработки.
        
        Args:
            text: Новый текст сообщения
        """
        if self._processing_message:
            try:
                await self._processing_message.edit_text(text)
            except Exception as e:
                self.logger.warning(f"Could not update message: {str(e)}")
    
    async def _extract_operations(self, user_message: str) -> list:
        """
        Извлечение всех операций из сообщения пользователя.
        
        Args:
            user_message: Сообщение пользователя
            
        Returns:
            list: Список операций
        """
        try:
            # Используем существующую логику с поддержкой множественных операций
            finance_operation_request = request_data(
                RequestBuilder(
                    message_request=MessageRequest(
                        user_message=user_message
                    ).finance_operation_request_message,
                    response_format=ResponseFormat().finance_operation_response
                )
            )
            
            # Извлекаем все операции
            all_operations = []
            for _, operations in finance_operation_request.items():
                if operations:
                    for operation in operations:
                        if operation.get("user_request_is_relevant", False):
                            all_operations.append(operation)
            
            return all_operations
            
        except Exception as e:
            self.logger.error(f"Error extracting operations: {str(e)}")
            return []    
