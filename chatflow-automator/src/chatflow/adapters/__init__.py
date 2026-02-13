"""
ChatFlow Adapters - адаптеры для различных AI чатов.
"""
from typing import Dict, Type, Optional, List

from .base import ChatAdapter
from .generic import GenericAdapter, GenericSelectors
from .qwen import QwenAdapter
from .chatgpt import ChatGPTAdapter
from .genspark import GensparkAdapter

__all__ = [
    'ChatAdapter',
    'GenericAdapter', 
    'GenericSelectors',
    'QwenAdapter',
    'ChatGPTAdapter',
    'GensparkAdapter',
    'get_adapter',
    'list_adapters',
    'list_adapter_names',
    'register_adapter',
]

# Реестр адаптеров
_ADAPTERS: Dict[str, Type[ChatAdapter]] = {
    'generic': GenericAdapter,
    'qwen': QwenAdapter,
    'chatgpt': ChatGPTAdapter,
    'genspark': GensparkAdapter,
}


def register_adapter(name: str, adapter_class: Type[ChatAdapter]) -> None:
    """
    Зарегистрировать новый адаптер.
    
    Args:
        name: Имя адаптера
        adapter_class: Класс адаптера
    """
    _ADAPTERS[name.lower()] = adapter_class


def get_adapter(name: str) -> Optional[Type[ChatAdapter]]:
    """
    Получить класс адаптера по имени.
    
    Args:
        name: Имя адаптера
        
    Returns:
        Класс адаптера или None
    """
    return _ADAPTERS.get(name.lower())


def list_adapters() -> List[Dict[str, str]]:
    """
    Получить список всех адаптеров с информацией.
    
    Returns:
        Список словарей с информацией об адаптерах
    """
    result = []
    for name, adapter_class in _ADAPTERS.items():
        result.append({
            'name': name,
            'description': getattr(adapter_class, 'description', ''),
        })
    return result


def list_adapter_names() -> List[str]:
    """
    Получить список имён доступных адаптеров.
    
    Returns:
        Список имён адаптеров
    """
    return list(_ADAPTERS.keys())
