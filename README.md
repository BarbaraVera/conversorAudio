# conversorAudio

API REST asíncrona construida con **Python 3.12 + FastAPI** para extraer y descargar contenido multimedia desde **YouTube** como audio **MP3** o video **MP4**, con interfaz web integrada.

## Características

- Descarga de audio MP3 y video MP4 desde YouTube (incluye `youtu.be`).
- Conversión con `yt-dlp` + `static-ffmpeg` (FFmpeg integrado, sin instalación manual).
- Descargas asíncronas en segundo plano con seguimiento de progreso.
- Calidades configurables: audio `128` / `192` / `320` kbps y video `360` / `720` / `1080`p.
- Interfaz web retro (Tailwind CSS) servida en `/`.
- Validación estricta de URLs y dominios permitidos.
- Headers de seguridad y CORS configurable.
- Almacenamiento temporal centralizado (`StorageService`), preparado para migrar a S3/R2/Azure.

## Stack

| Capa | Tecnología |
|---|---|
| Lenguaje | Python 3.12 |
| Framework | FastAPI + Uvicorn (ASGI) |
| Configuración | `pydantic-settings` (soporte `.env`) |
| Procesamiento de medios | `yt-dlp` + `static-ffmpeg` |
| Cliente HTTP | `httpx` |
| Tests | `pytest` + `httpx` |

## Instalación

```bash
# 1. Crear y activar el entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/macOS

# 2. Instalar dependencias
pip install -r requirements.txt
```

## Uso

```bash
# Arrancar el servidor de desarrollo (recarga en vivo)
uvicorn app.main:app --reload
```

- Interfaz web: http://localhost:8000/
- Documentación interactiva (Swagger UI): http://localhost:8000/docs
- Documentación alternativa: http://localhost:8000/redoc

## Endpoints de la API

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/` | Redirige a la interfaz web |
| `GET` | `/api/health` | Estado y versión del servicio |
| `POST` | `/api/download` | Inicia una descarga y devuelve un `task_id` |
| `GET` | `/api/status/{task_id}` | Estado y progreso de una descarga |
| `GET` | `/api/download/{task_id}` | Descarga el archivo final (lo elimina de `temp`) |

### Ejemplo de descarga

```bash
curl -X POST http://localhost:8000/api/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "format": "mp3", "quality": "192"}'
```

Respuesta:

```json
{
  "task_id": "a1b2c3d4e5f6",
  "status": "processing",
  "message": "Descarga en progreso"
}
```

## Configuración

La configuración se realiza mediante variables de entorno o un archivo `.env`. Variables principales:

| Variable | Default | Descripción |
|---|---|---|
| `PROJECT_NAME` | `MediaGrab` | Nombre del proyecto |
| `API_PREFIX` | `/api` | Prefijo de los endpoints |
| `ALLOWED_ORIGINS` | localhost | Orígenes permitidos por CORS |
| `ALLOWED_DOMAINS` | youtube.com, youtu.be | Dominios permitidos para descarga |
| `MAX_DOWNLOAD_SIZE_MB` | `1024` | Tamaño máximo de descarga |
| `DOWNLOAD_TIMEOUT` | `300` | Timeout de descarga (segundos) |

## Estructura del proyecto

```
conversorAudio/
├── app/
│   ├── main.py                 # Punto de entrada, endpoints, middleware y CORS
│   ├── core/
│   │   └── config.py           # Configuración global (pydantic-settings)
│   ├── schemas/
│   │   └── download.py         # Modelos Pydantic de petición/respuesta
│   ├── services/
│   │   ├── downloader.py       # Lógica de descarga/conversión con yt-dlp
│   │   ├── storage.py          # StorageService: archivos temporales
│   │   └── tasks.py            # Almacén en memoria thread-safe
│   └── static/                 # Interfaz web (HTML, CSS, JS)
├── tests/
│   └── test_api.py             # Tests de endpoints y validaciones
├── temp/                       # Carpeta temporal (no versionada)
├── requirements.txt
└── README.md
```

## Tests

```bash
pytest
```

Los tests cubren validación de URLs/formatos, endpoints de estado y descarga, y el flujo de descarga con el servicio mockeado.

## Lint

```bash
ruff check .
```

## Notas

- Los archivos descargados se guardan en `temp/` y se eliminan automáticamente al iniciar la aplicación o tras servirlos al usuario.
- `static-ffmpeg` incluye FFmpeg dentro de las dependencias, por lo que no se requiere instalación en el sistema.
