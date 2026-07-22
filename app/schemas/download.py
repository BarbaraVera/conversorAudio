from typing import Optional

from pydantic import BaseModel, HttpUrl, validator


class DownloadRequest(BaseModel):
    """Modelo de petición para descargar contenido multimedia."""

    url: HttpUrl
    format: str = "mp3"
    quality: Optional[str] = "192"

    @validator("format")
    def validate_format(cls, v: str) -> str:
        allowed = ("mp3", "mp4")
        if v.lower() not in allowed:
            raise ValueError(f"Formato no soportado: {v}. Usa: {', '.join(allowed)}")
        return v.lower()

    @validator("quality")
    def validate_quality(cls, v: Optional[str], values: dict) -> Optional[str]:
        if v is None:
            return v
        fmt = values.get("format", "mp3")
        if fmt == "mp3":
            allowed = ("128", "192", "320")
        else:
            allowed = ("360", "720", "1080")
        if v not in allowed:
            raise ValueError(f"Calidad no soportada: {v}. Para {fmt}: {', '.join(allowed)}")
        return v


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
    error: Optional[str] = None


class ErrorResponse(BaseModel):
    """Modelo de respuesta para errores."""

    detail: str
