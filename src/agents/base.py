"""
Базовые классы для многоагентной архитектуры.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from telegram import Update
from telegram.ext import ContextTypes

from lib.utilities.log_utilities import get_logger


LOGGER = get_logger(__name__)


@dataclass
class AgentRequest:
    """Стандартизированный запрос к агенту."""
    operation_type: str
    user_message: str
    telegram_update: Update
    context: ContextTypes.DEFAULT_TYPE
    data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Логирование создания запроса."""
        LOGGER.info(f"AgentRequest created: operation_type={self.operation_type}")


@dataclass
class AgentResponse:
    """Стандартизированный ответ от агента."""
    success: bool
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    needs_clarification: bool = False
    clarification_message: Optional[str] = None
    
    def __post_init__(self):
        """Логирование создания ответа."""
        LOGGER.info(f"AgentResponse created: success={self.success}, errors={self.errors}")


class BaseAgent(ABC):
    """Базовый класс для всех агентов."""
    
    def __init__(self, name: str):
        """
        Инициализация базового агента.
        
        Args:
            name: Имя агента для логирования
        """
        self.name = name
        self.logger = get_logger(name)
        self.logger.info(f"{name} agent initialized")
    
    @abstractmethod
    async def process(self, request: AgentRequest) -> AgentResponse:
        """
        Обработать запрос и вернуть ответ.
        
        Args:
            request: Запрос к агенту
            
        Returns:
            AgentResponse: Ответ агента
        """
        pass
    
    async def validate_request(self, request: AgentRequest) -> Optional[str]:
        """
        Базовая валидация запроса.
        
        Args:
            request: Запрос для валидации
            
        Returns:
            Optional[str]: Сообщение об ошибке или None если всё ок
        """
        if not request.user_message:
            return "Пустое сообщение пользователя"
        
        if not request.operation_type:
            return "Не определён тип операции"
        
        return None
    
    def create_error_response(self, error_message: str) -> AgentResponse:
        """
        Создать стандартный ответ с ошибкой.
        
        Args:
            error_message: Сообщение об ошибке
            
        Returns:
            AgentResponse: Ответ с ошибкой
        """
        self.logger.error(f"Error in {self.name}: {error_message}")
        return AgentResponse(
            success=False,
            message=f"Ошибка в {self.name}: {error_message}",
            errors=[error_message]
        )
    
    def create_success_response(self, message: str, data: Dict[str, Any] = None) -> AgentResponse:
        """
        Создать стандартный успешный ответ.
        
        Args:
            message: Сообщение пользователю
            data: Дополнительные данные
            
        Returns:
            AgentResponse: Успешный ответ
        """
        self.logger.info(f"Success in {self.name}: {message}")
        return AgentResponse(
            success=True,
            message=message,
            data=data or {}
        )
