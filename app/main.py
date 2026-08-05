import logging
import re
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import BackgroundTasks, FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import settings
from app.schemas.download import (
    DownloadRequest,
    DownloadResponse,
    ErrorResponse,
    StatusResponse,
)
from app.services.downloader import downloader
from app.services.storage import storage
from app.services.tasks import tasks

logger = logging.getLogger(__name__)

_TASK_ID_RE = re.compile(r"^[a-f0-9]{12}$")


def _sanitize_filename(name: str) -> str:
    """Limpia un titulo para usarlo como nombre de archivo seguro."""
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = name.strip(". ")
    return name[:100] if name else "descarga"


class SecurityHeadersMiddleware:
    """Middleware ASGI que agrega headers de seguridad a toda respuesta."""

    _HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        ),
    }

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        async def send_with_headers(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                for key, value in self._HEADERS.items():
                    headers.append((key.lower().encode(), value.encode()))
                message["headers"] = headers
            await send(message)

        await self._app(scope, receive, send_with_headers)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gestiona el ciclo de vida de la aplicacion.

    En startup: limpia archivos temporales residuales.
    En shutdown: no requiere accion.
    """
    storage.clean_temp()
    logger.info("Aplicacion iniciada — temp limpio")
    yield
    logger.info("Aplicacion detenida")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SecurityHeadersMiddleware)

app.mount(
    "/static",
    StaticFiles(directory=str(settings.BASE_DIR / "app" / "static")),
    name="static",
)


@app.get("/")
async def root() -> RedirectResponse:
    """Redirige a la interfaz web."""
    return RedirectResponse(url="/static/index.html")


@app.get(
    f"{settings.API_PREFIX}/health",
    tags=["Health"],
)
async def health_check() -> dict:
    """Endpoint de verificacion de salud del API."""
    return {"status": "ok", "version": settings.VERSION}


@app.post(
    f"{settings.API_PREFIX}/download",
    response_model=DownloadResponse,
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    tags=["Download"],
)
async def request_download(
    request: DownloadRequest,
    background_tasks: BackgroundTasks,
) -> DownloadResponse:
    """Descarga contenido multimedia de YouTube.

    Acepta una URL, formato (mp3/mp4) y calidad opcional.
    Retorna el task_id de inmediato; la descarga corre en segundo plano.
    """
    task_id = uuid.uuid4().hex[:12]
    tasks.create(task_id)

    background_tasks.add_task(
        _run_download,
        task_id=task_id,
        url=str(request.url),
        fmt=request.format,
        quality=request.quality,
    )

    return DownloadResponse(
        task_id=task_id,
        status="processing",
        message="Descarga en progreso",
    )


async def _run_download(
    task_id: str,
    url: str,
    fmt: str,
    quality: str,
) -> None:
    """Ejecuta la descarga en segundo plano."""
    try:
        await downloader.download(
            url=url,
            fmt=fmt,
            quality=quality,
            task_id=task_id,
        )
    except Exception as e:
        tasks.fail(task_id, str(e))


@app.get(
    f"{settings.API_PREFIX}/status/{{task_id}}",
    response_model=StatusResponse,
    responses={404: {"model": ErrorResponse}},
    tags=["Download"],
)
async def get_status(
    task_id: str = Path(..., pattern=r"^[a-f0-9]{12}$"),
) -> StatusResponse:
    """Obtiene el estado actual de una descarga en progreso."""
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return StatusResponse(**task)


@app.get(
    f"{settings.API_PREFIX}/download/{{task_id}}",
    response_class=FileResponse,
    tags=["Download"],
)
async def download_file(
    task_id: str = Path(..., pattern=r"^[a-f0-9]{12}$"),
) -> FileResponse:
    """Sirve el archivo descargado para su descarga final."""
    task = tasks.get(task_id)
    if not task or not task.get("file_path"):
        raise HTTPException(
            status_code=404,
            detail="Archivo no encontrado o ya fue descargado",
        )

    file_path = storage.get_file(task["file_path"])
    if not file_path:
        raise HTTPException(
            status_code=404,
            detail="Archivo no encontrado o ya fue descargado",
        )

    title = task.get("title") or file_path.stem
    download_name = f"{_sanitize_filename(title)}.{file_path.suffix.lstrip('.')}"

    return FileResponse(
        path=str(file_path),
        filename=download_name,
        media_type="application/octet-stream",
        background=BackgroundTask(
            storage.delete_file,
            str(file_path),
        ),
    )
