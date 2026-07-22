import asyncio
import uuid
from pathlib import Path
from typing import Optional

import yt_dlp
from static_ffmpeg import add_paths

from app.core.config import settings
from app.services.storage import _sanitize_filename, storage
from app.services.tasks import tasks


class MediaDownloader:
    """Servicio de descarga y conversion de medios con yt-dlp."""

    def __init__(self) -> None:
        add_paths()

    def _build_opts(
        self,
        output_path: str,
        fmt: str,
        quality: Optional[str],
        task_id: str,
    ) -> dict:
        """Construye las opciones de yt-dlp."""

        base_opts: dict = {
            "outtmpl": output_path,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": "mp4",
            "prefer_ffmpeg": True,
            "max_filesize": settings.MAX_DOWNLOAD_SIZE_MB * 1024 * 1024,
            "progress_hooks": [
                self._make_progress_hook(task_id)
            ],
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/137.0 Safari/537.36"
                )
            },
        }

        if fmt == "mp3":
            bitrate = quality or "192"
            base_opts["format"] = "bestaudio/best"
            base_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": bitrate,
                }
            ]
        else:
            if quality:
                res = quality.replace("p", "")
                base_opts["format"] = (
                    f"bv*[height<={res}]+ba/"
                    f"b[height<={res}]"
                )
            else:
                base_opts["format"] = "bv*+ba/b"

        return base_opts

    @staticmethod
    def _make_progress_hook(task_id: str):
        """Crea un hook de progreso para yt-dlp."""
        def hook(d: dict) -> None:
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                downloaded = d.get("downloaded_bytes", 0)
                if total > 0:
                    progress = int(downloaded / total * 100)
                    tasks.update(task_id, progress=min(progress, 99))
            elif d["status"] == "finished":
                tasks.update(task_id, progress=99)
        return hook

    def _sync_download(self, url: str, opts: dict) -> dict:
        """Funcion sincrona auxiliar para ejecutar en un hilo separado."""
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=True)

    @staticmethod
    def _sync_extract_info(url: str, opts: dict) -> dict:
        """Extrae info del video sin descargarlo."""
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    async def download(
        self,
        url: str,
        fmt: str,
        quality: Optional[str],
        task_id: Optional[str] = None,
    ) -> dict:
        """Descarga y convierte el contenido multimedia."""
        if not task_id:
            task_id = uuid.uuid4().hex[:12]
            tasks.create(task_id)
        tasks.update(task_id, progress=5)

        ext = "mp3" if fmt == "mp3" else "mp4"

        try:
            tasks.update(task_id, progress=10)

            info_opts = {"quiet": True, "no_warnings": True, "noplaylist": True}
            info = await asyncio.to_thread(self._sync_extract_info, url, info_opts)
            title = (info or {}).get("title", "descarga")

            output_template = storage.create_output_template(title)
            expected_path = storage.base_dir / f"{_sanitize_filename(title)}.{ext}"

            opts = self._build_opts(output_template, fmt, quality, task_id)
            await asyncio.to_thread(self._sync_download, url, opts)

            final_path = expected_path
            if not final_path.exists():
                for f in storage.base_dir.iterdir():
                    if f.suffix == f".{ext}" and storage._is_within_base(f):
                        final_path = f
                        break

            if not final_path.exists():
                raise RuntimeError("El archivo no fue generado")

            file_size = final_path.stat().st_size
            duration = (info or {}).get("duration", 0)

            tasks.complete(
                task_id,
                file_path=str(final_path),
                file_name=final_path.name,
                file_size=self._format_size(file_size),
                duration=self._format_duration(duration),
                title=title,
            )

            return {
                "task_id": task_id,
                "file_path": str(final_path),
                "file_name": final_path.name,
                "file_size": self._format_size(file_size),
                "duration": self._format_duration(duration),
                "title": title,
                "status": "completed",
            }

        except yt_dlp.utils.ExtractorError as e:
            tasks.fail(task_id, str(e))
            raise ValueError(f"Error al extraer el contenido: {e}")
        except yt_dlp.utils.DownloadError as e:
            tasks.fail(task_id, str(e))
            raise ValueError(f"Error durante la descarga: {e}")
        except Exception as e:
            tasks.fail(task_id, str(e))
            raise

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Formatea bytes a unidades legibles."""
        for unit in ("B", "KB", "MB", "GB"):
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    @staticmethod
    def _format_duration(seconds: Optional[int]) -> str:
        """Formatea segundos a MM:SS."""
        if not seconds:
            return "0:00"
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins}:{secs:02d}"


downloader = MediaDownloader()
