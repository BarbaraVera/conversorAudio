import logging
import os
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """Servicio centralizado de manejo de archivos temporales.

    Encapsula toda interaccion con el disco para archivos de descarga.
    disenado para ser reemplazado facilmente por S3/R2/Azure Blob.
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._base_dir: Path = base_dir or settings.TEMP_DIR

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    def create_output_template(self, task_id: str) -> str:
        """Devuelve la plantilla de salida para yt-dlp (%(ext)s se resuelve solo)."""
        return str(self._base_dir / f"{task_id}.%(ext)s")

    def get_expected_path(self, task_id: str, ext: str) -> Path:
        """Devuelve la ruta esperada del archivo tras la conversion."""
        return self._base_dir / f"{task_id}.{ext}"

    def get_file(self, task_id: str) -> Optional[Path]:
        """Busca un archivo por task_id. Devuelve la primera coincidencia o None."""
        candidates = list(self._base_dir.glob(f"{task_id}.*"))
        if candidates:
            logger.info("Archivo encontrado: %s", candidates[0].name)
            return candidates[0]
        logger.warning("Archivo no encontrado para task_id=%s", task_id)
        return None

    def delete_file(self, file_path: str) -> bool:
        """Elimina un archivo temporal. Devuelve True si se elimino correctamente."""
        path = Path(file_path)
        if path.exists() and path.is_file():
            try:
                path.unlink()
                logger.info("Archivo eliminado: %s", path.name)
                return True
            except OSError as e:
                logger.error("Error al eliminar %s: %s", path.name, e)
                return False
        logger.debug("Archivo ya no existe: %s", file_path)
        return False

    def clean_temp(self) -> None:
        """Elimina todos los archivos de la carpeta temporal.

        No elimina carpetas. No falla si un archivo esta bloqueado.
        """
        if not self._base_dir.exists():
            return

        count = 0
        errors = 0
        for item in self._base_dir.iterdir():
            if item.is_file():
                try:
                    item.unlink()
                    count += 1
                except OSError as e:
                    errors += 1
                    logger.error("Error al eliminar %s: %s", item.name, e)

        logger.info(
            "Limpieza completada: %d eliminados, %d errores en %s",
            count, errors, self._base_dir,
        )


storage = StorageService()
