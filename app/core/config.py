import os
from pathlib import Path


class Settings:
    """Configuración global de la aplicación."""

    PROJECT_NAME: str = "MediaGrab"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"

    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    TEMP_DIR: Path = BASE_DIR / "temp"

    ALLOWED_ORIGINS: list = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    DEFAULT_AUDIO_QUALITY: str = "192"
    DEFAULT_VIDEO_QUALITY: str = "720"
    ALLOWED_AUDIO_FORMATS: list = ["mp3"]
    ALLOWED_VIDEO_FORMATS: list = ["mp4"]

    DOWNLOAD_TIMEOUT: int = 300
    CLEANUP_DELAY: int = 10

    def ensure_temp_dir(self) -> None:
        """Crea el directorio temporal si no existe."""
        self.TEMP_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_temp_dir()
