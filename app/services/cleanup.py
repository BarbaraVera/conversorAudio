import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def cleanup_file(file_path: str, delay: int = 10) -> None:
    """Elimina un archivo temporal después de un retardo.

    Diseñado para usarse como BackgroundTask en FastAPI.
    """
    await asyncio.sleep(delay)
    path = Path(file_path)
    if path.exists():
        try:
            path.unlink()
            logger.info("Archivo eliminado: %s", file_path)
        except OSError as e:
            logger.error("Error al eliminar %s: %s", file_path, e)
