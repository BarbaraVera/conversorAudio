from enum import Enum
from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel, validator

from app.core.config import settings


class AudioFormat(str, Enum):
    MP3 = "mp3"


class VideoFormat(str, Enum):
    MP4 = "mp4"


class AudioQuality(str, Enum):
    B128 = "128"
    B192 = "192"
    B320 = "320"


class VideoQuality(str, Enum):
    P360 = "360"
    P720 = "720"
    P1080 = "1080"


class DownloadRequest(BaseModel):
    """Modelo de peticion para descargar contenido multimedia."""

    url: str
    format: AudioFormat | VideoFormat = AudioFormat.MP3
    quality: Optional[AudioQuality | VideoQuality] = None

    @validator("url")
    def validate_url(cls, v: str) -> str:
        return _validate_url_domain(v)

    @validator("quality", pre=True, always=True)
    def validate_quality(cls, v: Optional[str], values: dict) -> Optional[str]:
        if v is None:
            return v
        fmt = values.get("format", AudioFormat.MP3)
        if fmt == AudioFormat.MP3:
            allowed = tuple(q.value for q in AudioQuality)
        else:
            allowed = tuple(q.value for q in VideoQuality)
        if v not in allowed:
            raise ValueError(
                f"Calidad no soportada: {v}. Para {fmt.value}: {', '.join(allowed)}"
            )
        return v


def _validate_url_domain(url: str) -> str:
    """Valida estrictamente el dominio de una URL usando urllib.parse.

    Solo permite esquemas http/https y dominios en la lista permitida.
    """
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Esquema no permitido: {parsed.scheme}. Usa http o https")

    if not parsed.hostname:
        raise ValueError("URL sin dominio")

    hostname = parsed.hostname.lower()
    if hostname.startswith("www."):
        hostname = hostname[4:]

    allowed = settings.ALLOWED_DOMAINS
    if not any(hostname == d or hostname.endswith("." + d) for d in allowed):
        raise ValueError(
            f"Dominio no soportado: {parsed.hostname}. "
            f"Soportados: {', '.join(allowed)}"
        )

    return url


class DownloadResponse(BaseModel):
    """Modelo de respuesta al iniciar una descarga."""

    task_id: str
    status: str = "processing"
    message: str = "Descarga iniciada"


class StatusResponse(BaseModel):
    """Modelo de respuesta del estado de una descarga."""

    task_id: str
    status: str
    progress: int = 0
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[str] = None
    title: Optional[str] = None
    error: Optional[str] = None


class ErrorResponse(BaseModel):
    """Modelo de respuesta para errores."""

    detail: str
