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
        
        Args:
            request: Входящий запрос
            
        Returns:
            AgentResponse: Ответ от соответствующего агента
        """
        try:
            # Сохраняем сообщение о процессе обработки
            self._processing_message = await request.telegram_update.message.reply_text(
                "1/3 Определяю тип операции. Ожидайте..."
            )
            
            # Определяем тип операции через OpenAI
            operation_type = await self._determine_operation_type(request.user_message)
            
            if not operation_type:
                return self.create_error_response("Не удалось определить тип операции")
            
            # Обновляем тип операции в запросе
            request.operation_type = operation_type
            
            # Находим подходящего агента
            agent = self.agents.get(operation_type)
            if not agent:
                return self.create_error_response(
                    f"Не найден агент для операции типа: {operation_type}"
                )
            
            # Обновляем сообщение
            await self._update_processing_message(
                f"2/3 Обрабатываю операцию: {operation_type}. Ожидайте..."
            )
            
            # Делегируем обработку соответствующему агенту
            self.logger.info(f"Delegating to {agent.name}")
            response = await agent.process(request)
            
            # Удаляем сообщение о процессе обработки
            if self._processing_message:
                try:
                    await self._processing_message.delete()
                except Exception as e:
                    self.logger.warning(f"Could not delete processing message: {str(e)}")
            
            return response
            
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
