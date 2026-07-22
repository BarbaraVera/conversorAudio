import logging
import re
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def _sanitize_filename(name: str) -> str:
    """Limpia un titulo para usarlo como nombre de archivo seguro."""
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = name.strip(". ")
    return name[:100] if name else "descarga"


class StorageService:
    """Servicio centralizado de manejo de archivos temporales.

    Encapsula toda interaccion con el disco para archivos de descarga.
    disenado para ser reemplazado facilmente por S3/R2/Azure Blob.
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._base_dir: Path = (base_dir or settings.TEMP_DIR).resolve()

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    def _is_within_base(self, path: Path) -> bool:
        """Verifica que una ruta resuelta este dentro de la carpeta base."""
        try:
            return path.resolve().is_relative_to(self._base_dir)
        except (OSError, ValueError):
            return False

    def create_output_template(self, title: str) -> str:
        """Devuelve la plantilla de salida para yt-dlp basada en el titulo."""
        name = _sanitize_filename(title)
        return str(self._base_dir / f"{name}.%(ext)s")

    def get_file(self, file_path: str) -> Optional[Path]:
        """Devuelve la ruta del archivo si existe y esta dentro de la carpeta base."""
        path = Path(file_path)
        if not self._is_within_base(path):
            logger.warning("Ruta fuera de temp: %s", file_path)
            return None
        if path.exists() and path.is_file():
            logger.info("Archivo encontrado: %s", path.name)
            return path
        logger.warning("Archivo no encontrado: %s", file_path)
        return None

    def delete_file(self, file_path: str) -> bool:
        """Elimina un archivo temporal. Verifica que este dentro de la carpeta base."""
        path = Path(file_path)
        if not self._is_within_base(path):
            logger.warning("Intento de eliminar archivo fuera de temp: %s", file_path)
            return False
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
