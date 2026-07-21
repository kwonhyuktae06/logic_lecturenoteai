"""
파이프라인 입력 단계
- 업로드된 파일이 음성(mp3/wav)인지 영상(mp4)인지 구분
- 영상이면 ffmpeg로 오디오만 추출해서 Whisper가 바로 쓸 수 있게 만듦

사전 조건: ffmpeg가 설치되어 PATH에 등록되어 있어야 함 (extract_audio 실행 시)
"""

import subprocess
from pathlib import Path

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}


def load_media(file_path: str) -> dict:
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext in AUDIO_EXTENSIONS:
        return {
            "media_type": "audio",
            "video_path": None,
            "audio_path": str(path),
        }

    if ext in VIDEO_EXTENSIONS:
        audio_path = extract_audio(path)
        return {
            "media_type": "video",
            "video_path": str(path),
            "audio_path": audio_path,
        }

    raise ValueError(f"지원하지 않는 파일 형식입니다: {ext}")


def extract_audio(video_path: Path) -> str:
    audio_path = video_path.with_suffix(".wav")

    command = [
        "ffmpeg",
        "-y",                   # 기존 파일 있으면 덮어쓰기
        "-i", str(video_path),
        "-vn",                  # 비디오 스트림 제외, 오디오만
        "-acodec", "pcm_s16le",
        "-ar", "16000",         # Whisper 권장 샘플레이트
        "-ac", "1",             # 모노 채널
        str(audio_path),
    ]

    subprocess.run(command, check=True, capture_output=True)
    return str(audio_path)


if __name__ == "__main__":
    # 테스트용 실행 (ffmpeg 설치 후 사용)
    test_file = "lecture_test4.mp4"
    result = load_media(test_file)
    print(result)
