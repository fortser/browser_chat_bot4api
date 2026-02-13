"""Async worker for running Playwright operations in a separate thread."""

import asyncio
import logging
from typing import Optional, Any, Callable, Coroutine
from queue import Queue
from threading import Event

from PyQt6.QtCore import QThread, pyqtSignal, QObject

logger = logging.getLogger(__name__)


class AsyncWorker(QThread):
    """
    Worker thread that maintains a persistent event loop for async operations.
    """
    
    task_completed = pyqtSignal(object)
    task_error = pyqtSignal(str)
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = Event()
        self._task_queue: Queue = Queue()
        self._stop_requested = False
    
    @property
    def loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """Get the event loop."""
        return self._loop
    
    def run(self) -> None:
        """Thread main function."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        logger.info("AsyncWorker started")
        self._running.set()
        
        try:
            self._loop.run_until_complete(self._process_tasks())
        except Exception as e:
            logger.error(f"AsyncWorker error: {e}")
        finally:
            try:
                pending = asyncio.all_tasks(self._loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self._loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
                self._loop.close()
            except Exception as e:
                logger.error(f"Error closing event loop: {e}")
            self._loop = None
            logger.info("AsyncWorker stopped")
    
    async def _process_tasks(self) -> None:
        """Process tasks from the queue."""
        while not self._stop_requested:
            try:
                if not self._task_queue.empty():
                    coro, callback = self._task_queue.get_nowait()
                    try:
                        result = await coro
                        if callback:
                            callback(result, None)
                        self.task_completed.emit(result)
                    except Exception as e:
                        logger.error(f"Task error: {e}")
                        if callback:
                            callback(None, e)
                        self.task_error.emit(str(e))
                else:
                    await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f"Error processing task: {e}")
                await asyncio.sleep(0.1)
    
    def run_coroutine(
        self,
        coro: Coroutine,
        callback: Optional[Callable[[Any, Optional[Exception]], None]] = None
    ) -> None:
        """Schedule a coroutine to run."""
        if not self._running.is_set():
            raise RuntimeError("AsyncWorker not running")
        self._task_queue.put((coro, callback))
    
    def wait_ready(self, timeout: float = 5.0) -> bool:
        """Wait for the worker to be ready."""
        return self._running.wait(timeout)
    
    def stop(self) -> None:
        """Request the worker to stop."""
        self._stop_requested = True
        self._running.clear()
        if self.isRunning():
            self.wait(5000)


class AsyncBridge(QObject):
    """Bridge for running async operations from the main thread."""
    
    operation_completed = pyqtSignal(str, object)
    operation_failed = pyqtSignal(str, str)
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._worker = AsyncWorker(self)
        self._operation_counter = 0
    
    def start(self) -> None:
        """Start the async worker."""
        if not self._worker.isRunning():
            self._worker.start()
            self._worker.wait_ready()
    
    def stop(self) -> None:
        """Stop the async worker."""
        self._worker.stop()
    
    def run_async(
        self,
        coro: Coroutine,
        on_success: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[str], None]] = None
    ) -> str:
        """Run an async operation."""
        self._operation_counter += 1
        op_id = f"op_{self._operation_counter}"
        
        def callback(result, error):
            if error:
                if on_error:
                    on_error(str(error))
                self.operation_failed.emit(op_id, str(error))
            else:
                if on_success:
                    on_success(result)
                self.operation_completed.emit(op_id, result)
        
        self._worker.run_coroutine(coro, callback)
        return op_id
