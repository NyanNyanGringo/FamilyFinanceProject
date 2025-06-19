"""
Интеграция многоагентной архитектуры с существующим кодом.
Позволяет постепенно мигрировать функционал.
"""
from telegram import Update
from telegram.ext import ContextTypes

from src.agents import (
    MainOrchestrator, ExpenseAgent, IncomeAgent, 
    TransferAgent, AgentRequest
)
from lib.utilities.google_utilities import OperationTypes
from lib.utilities.log_utilities import get_logger


LOGGER = get_logger(__name__)


class AgentSystemIntegration:
    """Класс для интеграции агентов с существующей системой."""
    
    def __init__(self):
        """Инициализация системы агентов."""
        self.orchestrator = MainOrchestrator()
        self._setup_agents()
        self.enabled = True  # Флаг для включения/выключения агентов
        LOGGER.info("Agent system initialized")
    
    def _setup_agents(self):
        """Настройка и регистрация всех агентов."""
        # Создаём экземпляры агентов
        expense_agent = ExpenseAgent()
        income_agent = IncomeAgent()
        transfer_agent = TransferAgent()
        
        # Регистрируем агентов в оркестраторе
        self.orchestrator.register_agent(OperationTypes.expenses, expense_agent)
        self.orchestrator.register_agent(OperationTypes.incomes, income_agent)
        self.orchestrator.register_agent(OperationTypes.transfers, transfer_agent)
        self.orchestrator.register_agent(OperationTypes.adjustment, transfer_agent)
        
        LOGGER.info("All agents registered successfully")
    
    async def process_voice_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text_from_audio: str
    ) -> bool:
        """
        Обработка голосового сообщения через систему агентов.
        
        Args:
            update: Telegram update
            context: Telegram context
            text_from_audio: Распознанный текст из аудио
            
        Returns:
            bool: True если обработано агентами, False если нужно использовать старый код
        """
        if not self.enabled:
            LOGGER.info("Agent system disabled, falling back to legacy code")
            return False
        
        try:
            # Создаём запрос для агентов
            request = AgentRequest(
                operation_type="",  # Будет определено оркестратором
                user_message=text_from_audio,
                telegram_update=update,
                context=context
            )
            
            # Обрабатываем через оркестратор
            response = await self.orchestrator.process(request)
            
            # Отправляем результат пользователю
            if response.success:
                await update.message.reply_text(
                    response.message,
                    parse_mode='HTML'
                )
                LOGGER.info(f"Successfully processed by agents: {response.message}")
                return True
            else:
                # Если агенты не смогли обработать, логируем и используем старый код
                LOGGER.warning(f"Agent processing failed: {response.errors}")
                if response.needs_clarification:
                    await update.message.reply_text(
                        response.clarification_message or response.message
                    )
                    return True
                return False
                
        except Exception as e:
            LOGGER.error(f"Error in agent system: {str(e)}")
            return False
    
    def enable(self):
        """Включить систему агентов."""
        self.enabled = True
        LOGGER.info("Agent system enabled")
    
    def disable(self):
        """Выключить систему агентов (использовать старый код)."""
        self.enabled = False
        LOGGER.info("Agent system disabled")


# Глобальный экземпляр для использования в server.py
agent_system = AgentSystemIntegration()
