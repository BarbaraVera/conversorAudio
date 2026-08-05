import threading
from typing import Optional


class TaskStore:
    """Almacén en memoria para el estado de las descargas.

    Thread-safe para uso con BackgroundTasks.
    """

    def __init__(self) -> None:
        self._store: dict = {}
        self._lock = threading.Lock()

    def create(self, task_id: str) -> None:
        """Crea una nueva tarea con estado inicial."""
        with self._lock:
            self._store[task_id] = {
                "task_id": task_id,
                "status": "processing",
                "progress": 0,
                "file_path": None,
                "file_name": None,
                "file_size": None,
                "duration": None,
                "error": None,
            }

    def update(self, task_id: str, **kwargs) -> None:
        """Actualiza campos de una tarea existente."""
        with self._lock:
            if task_id in self._store:
                self._store[task_id].update(kwargs)

    def get(self, task_id: str) -> Optional[dict]:
        """Obtiene el estado actual de una tarea."""
        with self._lock:
            return self._store.get(task_id)

    def complete(self, task_id: str, **kwargs) -> None:
        """Marca una tarea como completada."""
        self.update(
            task_id,
            status="completed",
            progress=100,
            **kwargs,
        )

    def fail(self, task_id: str, error: str) -> None:
        """Marca una tarea como fallida."""
        self.update(
            task_id,
            status="error",
            error=error,
        )


tasks = TaskStore()
