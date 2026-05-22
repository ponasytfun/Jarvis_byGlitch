from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable

from PySide6.QtCore import QObject, Signal, Slot


class WorkerSignals(QObject):
    taskStarted = Signal(str)
    taskFinished = Signal(str, object)
    taskFailed = Signal(str, str)
    successCallbackRequested = Signal(object, object)
    errorCallbackRequested = Signal(object, str)


class WorkerManager(QObject):
    def __init__(self, max_workers: int = 4) -> None:
        super().__init__()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.signals = WorkerSignals()
        self._futures: set[Future] = set()
        self.signals.successCallbackRequested.connect(self._invoke_success_callback)
        self.signals.errorCallbackRequested.connect(self._invoke_error_callback)

    def submit(
        self,
        name: str,
        function: Callable[..., Any],
        *args: Any,
        on_success: Callable[[Any], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        self.signals.taskStarted.emit(name)
        future = self.executor.submit(function, *args, **kwargs)
        self._futures.add(future)

        def _done(done_future: Future) -> None:
            self._futures.discard(done_future)
            try:
                result = done_future.result()
            except Exception as exc:
                message = str(exc)
                self.signals.taskFailed.emit(name, message)
                if on_error is not None:
                    self.signals.errorCallbackRequested.emit(on_error, message)
                return

            self.signals.taskFinished.emit(name, result)
            if on_success is not None:
                self.signals.successCallbackRequested.emit(on_success, result)

        future.add_done_callback(_done)

    def shutdown(self) -> None:
        self.executor.shutdown(wait=True, cancel_futures=True)

    @Slot(object, object)
    def _invoke_success_callback(self, callback: Callable[[Any], None], result: Any) -> None:
        callback(result)

    @Slot(object, str)
    def _invoke_error_callback(self, callback: Callable[[str], None], message: str) -> None:
        callback(message)
