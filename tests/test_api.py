import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.main import app


client = TestClient(app)


class TestHealthEndpoint:
    """Tests del endpoint de salud."""

    def test_health_returns_ok(self) -> None:
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestRootRedirect:
    """Tests del endpoint raiz."""

    def test_root_redirects_to_static(self) -> None:
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]


class TestDownloadRequestValidation:
    """Tests de validacion del modelo DownloadRequest."""

    def test_valid_mp3_request_returns_processing(self) -> None:
        response = client.post(
            "/api/download",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "format": "mp3"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert "task_id" in data

    def test_invalid_format_rejected(self) -> None:
        response = client.post(
            "/api/download",
            json={"url": "https://www.youtube.com/watch?v=test", "format": "wav"},
        )
        assert response.status_code == 422

    def test_invalid_url_rejected(self) -> None:
        response = client.post(
            "/api/download",
            json={"url": "not-a-valid-url", "format": "mp3"},
        )
        assert response.status_code == 422

    def test_missing_url_rejected(self) -> None:
        response = client.post(
            "/api/download",
            json={"format": "mp3"},
        )
        assert response.status_code == 422

    def test_default_format_is_mp3(self) -> None:
        response = client.post(
            "/api/download",
            json={"url": "https://www.youtube.com/watch?v=test"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"

    def test_unsupported_domain_rejected(self) -> None:
        response = client.post(
            "/api/download",
            json={"url": "https://vimeo.com/123456", "format": "mp3"},
        )
        assert response.status_code == 422

    def test_ftp_scheme_rejected(self) -> None:
        response = client.post(
            "/api/download",
            json={"url": "ftp://youtube.com/watch?v=test", "format": "mp3"},
        )
        assert response.status_code == 422

    def test_youtu_be_domain_accepted(self) -> None:
        response = client.post(
            "/api/download",
            json={"url": "https://youtu.be/dQw4w9WgXcQ", "format": "mp3"},
        )
        assert response.status_code == 200


class TestStatusEndpoint:
    """Tests del endpoint de estado."""

    def test_nonexistent_task_returns_404(self) -> None:
        response = client.get("/api/status/abc123def456")
        assert response.status_code == 404
        assert "no encontrada" in response.json()["detail"]

    def test_invalid_task_id_format_rejected(self) -> None:
        response = client.get("/api/status/../../etc/passwd")
        assert response.status_code in (422, 404)

    def test_task_id_too_short_rejected(self) -> None:
        response = client.get("/api/status/abc123")
        assert response.status_code == 422

    def test_task_id_invalid_chars_rejected(self) -> None:
        response = client.get("/api/status/ZZZZZZZZZZZZ")
        assert response.status_code == 422


class TestDownloadFileEndpoint:
    """Tests del endpoint de descarga de archivo."""

    def test_nonexistent_file_returns_404(self) -> None:
        response = client.get("/api/download/abc123def456")
        assert response.status_code == 404

    def test_invalid_task_id_format_rejected(self) -> None:
        response = client.get("/api/download/../../etc/passwd")
        assert response.status_code in (422, 404)


class TestDownloadServiceMocked:
    """Tests del endpoint download con servicio mockeado."""

    @patch("app.main.downloader.download", new_callable=AsyncMock)
    def test_download_starts_and_returns_task_id(self, mock_download: AsyncMock) -> None:
        mock_download.return_value = {
            "task_id": "abc123",
            "file_path": "/tmp/abc123.mp3",
            "file_name": "abc123.mp3",
            "file_size": "3.5 MB",
            "duration": "3:45",
            "title": "Test Song",
            "status": "completed",
        }
        response = client.post(
            "/api/download",
            json={"url": "https://www.youtube.com/watch?v=test", "format": "mp3"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert "task_id" in data

    def test_status_polling_works(self) -> None:
        response = client.post(
            "/api/download",
            json={"url": "https://www.youtube.com/watch?v=test", "format": "mp3"},
        )
        task_id = response.json()["task_id"]
        status_response = client.get(f"/api/status/{task_id}")
        assert status_response.status_code == 200
        data = status_response.json()
        assert data["task_id"] == task_id
        assert data["status"] in ("processing", "completed", "error")
