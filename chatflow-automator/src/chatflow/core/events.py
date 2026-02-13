"""Event system for component communication."""

import asyncio
from collections import defaultdict
from typing import Any, Callable, Optional
import logging

logger = logging.getLogger(__name__)


class EventEmitter:
    """
    Simple event system for loose coupling between components.
    
    Supports both synchronous and asynchronous event handlers.
    """
    
    def __init__(self):
        self._listeners: dict[str, list[Callable]] = defaultdict(list)
        self._async_listeners: dict[str, list[Callable]] = defaultdict(list)
        self._once_listeners: dict[str, list[Callable]] = defaultdict(list)
    
    def on(self, event: str, callback: Callable) -> Callable:
        """
        Subscribe to an event.
        
        Args:
            event: Event name
            callback: Handler function (sync or async)
            
        Returns:
            The callback for chaining
        """
        if asyncio.iscoroutinefunction(callback):
            self._async_listeners[event].append(callback)
        else:
            self._listeners[event].append(callback)
        return callback
    
    def once(self, event: str, callback: Callable) -> Callable:
        """
        Subscribe to an event only once.
        
        Args:
            event: Event name
            callback: Handler function
            
        Returns:
            The callback for chaining
        """
        self._once_listeners[event].append(callback)
        return callback
    
    def off(self, event: str, callback: Optional[Callable] = None) -> None:
        """
        Unsubscribe from an event.
        
        Args:
            event: Event name
            callback: Specific handler to remove, or None to remove all
        """
        if callback is None:
            self._listeners[event].clear()
            self._async_listeners[event].clear()
            self._once_listeners[event].clear()
        else:
            if callback in self._listeners[event]:
                self._listeners[event].remove(callback)
            if callback in self._async_listeners[event]:
                self._async_listeners[event].remove(callback)
            if callback in self._once_listeners[event]:
                self._once_listeners[event].remove(callback)
    
    def emit(self, event: str, data: Any = None) -> None:
        """
        Emit an event synchronously.
        
        Args:
            event: Event name
            data: Event data to pass to handlers
        """
        # Call synchronous listeners
        for callback in self._listeners[event]:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in event handler for '{event}': {e}")
        
        # Call once listeners
        once_callbacks = self._once_listeners[event].copy()
        self._once_listeners[event].clear()
        for callback in once_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    # Schedule async once callbacks
                    asyncio.create_task(callback(data))
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Error in once handler for '{event}': {e}")
    
    async def emit_async(self, event: str, data: Any = None) -> None:
        """
        Emit an event asynchronously.
        
        Args:
            event: Event name
            data: Event data to pass to handlers
        """
        # First emit synchronously
        self.emit(event, data)
        
        # Then call async listeners
        for callback in self._async_listeners[event]:
            try:
                await callback(data)
            except Exception as e:
                logger.error(f"Error in async event handler for '{event}': {e}")
    
    def listeners(self, event: str) -> list[Callable]:
        """Get all listeners for an event."""
        return (
            self._listeners[event] + 
            self._async_listeners[event] + 
            self._once_listeners[event]
        )
    
    def clear(self) -> None:
        """Remove all listeners."""
        self._listeners.clear()
        self._async_listeners.clear()
        self._once_listeners.clear()


# Global event emitter instance
_global_emitter: Optional[EventEmitter] = None


def get_event_emitter() -> EventEmitter:
    """Get the global event emitter instance."""
    global _global_emitter
    if _global_emitter is None:
        _global_emitter = EventEmitter()
    return _global_emitter
