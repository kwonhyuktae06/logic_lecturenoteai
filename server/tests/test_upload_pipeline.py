from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_pipeline_requires_audio_and_images():
    response = client.post(
        "/api/v1/upload/pipeline",
        files=[("audio", ("sample.wav", b"fake-audio", "audio/wav"))],
        data={"image_count": "1"},
    )
    assert response.status_code == 422
