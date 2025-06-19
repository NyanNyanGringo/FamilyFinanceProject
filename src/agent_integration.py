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
        text_from_audio: str,
        is_reply: bool = False
    ) -> bool:
        """
        Обработка голосового сообщения через систему агентов.
        
        Args:
            update: Telegram update
            context: Telegram context
            text_from_audio: Распознанный текст из аудио
            is_reply: True если это reply на сообщение
            
        Returns:
            bool: True если обработано агентами, False если нужно использовать старый код
        """
        if not self.enabled:
            LOGGER.info("Agent system disabled, falling back to legacy code")
            return False
        
        try:
            # Отправляем промежуточное сообщение
            processing_message = await update.message.reply_text(
                "Мой Господин, обрабатываю сообщение..."
            )
            
            # Сохраняем флаг, что сообщение было отправлено
            message_deleted = False
            # Если это reply, используем ReplyAgent
            if is_reply:
                from src.agents import ReplyAgent
                reply_agent = ReplyAgent()
                
                request = AgentRequest(
                    operation_type="reply",
                    user_message=text_from_audio,
                    telegram_update=update,
                    context=context
                )
                
                response = await reply_agent.process(request)
            else:
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
                # Удаляем промежуточное сообщение
                if not message_deleted:
                    try:
                        await processing_message.delete()
                        message_deleted = True
                    except Exception as e:
                        LOGGER.warning(f"Could not delete processing message: {e}")
                
                # Определяем, на какое сообщение отвечать
                reply_to_message_id = context.user_data.get('reply_to_message_id')
                LOGGER.info(f"reply_to_message_id from context: {reply_to_message_id}")
                LOGGER.info(f"is_reply flag: {is_reply}")
                
                # Для reply-сообщений всегда отвечаем на сообщение пользователя
                if is_reply:
                    # Отвечаем на текущее сообщение пользователя для создания цепочки
                    LOGGER.info("Sending reply to user message to maintain chain")
                    sent_message = await update.message.reply_text(
                        response.message,
                        parse_mode='HTML'
                    )
                elif reply_to_message_id:
                    # Для первичных операций отвечаем на исходное сообщение (если есть)
                    try:
                        sent_message = await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=response.message,
                            parse_mode='HTML',
                            reply_to_message_id=reply_to_message_id
                        )
                    except Exception as e:
                        LOGGER.warning(f"Could not reply to message {reply_to_message_id}: {e}")
                        # Fallback к обычному reply
                        sent_message = await update.message.reply_text(
                            response.message,
                            parse_mode='HTML'
                        )
                else:
                    # Обычный reply к текущему сообщению
                    sent_message = await update.message.reply_text(
                        response.message,
                        parse_mode='HTML'
                    )
                
                # Очищаем контекст
                context.user_data.pop('reply_to_message_id', None)
                
                # Если есть pending_expense_data, создаем запись в Google Sheets с message_id
                if context.user_data.get('pending_expense_data'):
                    expense_data = context.user_data['pending_expense_data']
                    
                    # Импортируем необходимые классы
                    from lib.utilities.google_utilities import (
                        RequestData, ListName, Status, insert_and_update_row_batch_update
                    )
                    
                    # Создаем запрос с message_id
                    google_request = RequestData(
                        list_name=ListName.expenses,
                        expenses_category=expense_data.get('expenses_category'),
                        account=expense_data.get('account'),
                        amount=expense_data.get('amount'),
                        status=expense_data.get('status', Status.committed),
                        comment=expense_data.get('comment', ''),
                        message_id=sent_message.message_id
                    )
                    
                    # Отправляем в Google Sheets
                    insert_and_update_row_batch_update(google_request)
                    
                    # Очищаем контекст
                    context.user_data.pop('pending_expense_data', None)
                    context.user_data.pop('pending_operation_type', None)
                
                # Аналогично для доходов
                elif context.user_data.get('pending_income_data'):
                    income_data = context.user_data['pending_income_data']
                    
                    from lib.utilities.google_utilities import (
                        RequestData, ListName, Status, insert_and_update_row_batch_update
                    )
                    
                    google_request = RequestData(
                        list_name=ListName.incomes,
                        incomes_category=income_data.get('incomes_category'),
                        account=income_data.get('account'),
                        amount=income_data.get('amount'),
                        status=income_data.get('status', Status.committed),
                        comment=income_data.get('comment', ''),
                        message_id=sent_message.message_id
                    )
                    
                    insert_and_update_row_batch_update(google_request)
                    
                    context.user_data.pop('pending_income_data', None)
                    context.user_data.pop('pending_operation_type', None)
                
                # И для переводов
                elif context.user_data.get('pending_transfer_data'):
                    transfer_data = context.user_data['pending_transfer_data']
                    
                    from lib.utilities.google_utilities import (
                        RequestData, ListName, Status, TransferType, insert_and_update_row_batch_update
                    )
                    
                    google_request = RequestData(
                        list_name=ListName.transfers,
                        transfer_type=TransferType[transfer_data.get('transfer_type', 'transfer')],
                        account=transfer_data.get('account'),
                        replenishment_account=transfer_data.get('replenishment_account'),
                        amount=transfer_data.get('amount', 0),
                        replenishment_amount=transfer_data.get('replenishment_amount', 0),
                        status=transfer_data.get('status', Status.committed),
                        comment=transfer_data.get('comment', ''),
                        message_id=sent_message.message_id
                    )
                    
                    insert_and_update_row_batch_update(google_request)
                    
                    context.user_data.pop('pending_transfer_data', None)
                    context.user_data.pop('pending_operation_type', None)
                
                LOGGER.info(f"Successfully processed by agents: {response.message}")
                return True
            else:
                # Если агенты не смогли обработать, показываем ошибку
                LOGGER.warning(f"Agent processing failed: {response.errors}")
                
                # Удаляем промежуточное сообщение
                if not message_deleted:
                    try:
                        await processing_message.delete()
                        message_deleted = True
                    except Exception as e:
                        LOGGER.warning(f"Could not delete processing message: {e}")
                
                if response.needs_clarification:
                    await update.message.reply_text(
                        response.clarification_message or response.message
                    )
                    return True
                else:
                    # При критических ошибках тоже возвращаем True,
                    # чтобы не использовать старый код
                    if not message_deleted:
                        try:
                            await processing_message.delete()
                            message_deleted = True
                        except Exception as e:
                            LOGGER.warning(f"Could not delete processing message: {e}")
                    
                    await update.message.reply_text(
                        "Произошла ошибка при обработке запроса. Попробуйте еще раз."
                    )
                    return True
                
        except Exception as e:
            LOGGER.error(f"Error in agent system: {str(e)}")
            # Удаляем промежуточное сообщение при критической ошибке
            if 'message_deleted' in locals() and not message_deleted:
                try:
                    await processing_message.delete()
                except Exception as e_del:
                    LOGGER.warning(f"Could not delete processing message: {e_del}")
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
