import uuid

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask

from app.core.config import settings
from app.schemas.download import DownloadRequest, DownloadResponse, ErrorResponse, StatusResponse
from app.services.cleanup import cleanup_file
from app.services.downloader import downloader
from app.services.tasks import tasks

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/static",
    StaticFiles(directory=str(settings.BASE_DIR / "app" / "static")),
    name="static",
)


@app.get("/")
async def root() -> dict:
    """Redirige a la interfaz web."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")


@app.get(
    f"{settings.API_PREFIX}/health",
    tags=["Health"],
)
async def health_check() -> dict:
    """Endpoint de verificación de salud del API."""
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
    """Descarga contenido multimedia de YouTube o TikTok.

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
async def get_status(task_id: str) -> StatusResponse:
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
async def download_file(task_id: str) -> FileResponse:
    """Sirve el archivo descargado para su descarga final.

    Después de servir el archivo, lo elimina en segundo plano.
    """
    candidates = list(settings.TEMP_DIR.glob(f"{task_id}.*"))

    if not candidates:
        raise HTTPException(
            status_code=404,
            detail="Archivo no encontrado o ya fue descargado",
        )

    file_path = candidates[0]

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
        background=BackgroundTask(
            cleanup_file,
            str(file_path),
            settings.CLEANUP_DELAY,
        ),
    )
