"""
파이프라인 입력 단계
- 업로드된 파일이 음성(mp3/wav)인지 영상(mp4)인지 구분
- 영상이면 ffmpeg로 오디오만 추출해서 Whisper가 바로 쓸 수 있게 만듦

사전 조건: ffmpeg가 설치되어 PATH에 등록되어 있어야 함 (extract_audio 실행 시)
"""

import subprocess
import sys
from pathlib import Path

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}


# 지정된 확장자 목록(AUDIO_EXTENSIONS, VIDEO_EXTENSIONS)에 없는 파일이 들어왔을 때
# 발생시키는 전용 예외. ValueError 대신 써서 호출하는 쪽에서 명확히 구분해 잡을 수 있게 함
class UnsupportedMediaTypeError(Exception):
    """지정된 확장자 목록에 없는 파일이 입력됐을 때 발생하는 예외"""


def load_media(file_path: str) -> dict:
    # 파일 경로에서 확장자만 뽑아 소문자로 통일 (예: ".MP4" -> ".mp4")
    path = Path(file_path)
    ext = path.suffix.lower()

    # 이미 오디오 파일이면 추출 과정 없이 그대로 사용
    if ext in AUDIO_EXTENSIONS:
        return {
            "media_type": "audio",
            "video_path": None,
            "audio_path": str(path),
        }

    # 영상 파일이면 ffmpeg로 오디오만 뽑아낸 뒤 그 경로를 함께 반환
    if ext in VIDEO_EXTENSIONS:
        audio_path = extract_audio(path)
        return {
            "media_type": "video",
            "video_path": str(path),
            "audio_path": audio_path,
        }

    # 오디오도 영상도 아닌 확장자 -> 예외를 발생시켜 여기서 처리 중단
    raise UnsupportedMediaTypeError(f"지원하지 않는 파일 형식입니다: {ext}")


def extract_audio(video_path: Path) -> str:
    # 원본과 같은 이름에 확장자만 .wav로 바꾼 출력 경로
    audio_path = video_path.with_suffix(".wav")

    command = [
        "ffmpeg",
        "-y",                   # 기존 파일 있으면 덮어쓰기
        "-i", str(video_path),
        "-vn",                  # 비디오 스트림 제외, 오디오만
        "-acodec", "pcm_s16le",  # Whisper가 바로 읽을 수 있는 무압축 PCM 코덱
        "-ar", "16000",         # Whisper 권장 샘플레이트
        "-ac", "1",             # 모노 채널
        str(audio_path),
    ]

    # check=True: ffmpeg가 실패(0이 아닌 종료 코드)하면 CalledProcessError를 던짐
    subprocess.run(command, check=True, capture_output=True)
    return str(audio_path)


if __name__ == "__main__":
    # 테스트용 실행 (ffmpeg 설치 후 사용)
    test_file = "lecture_test4.mp4"
    try:
        result = load_media(test_file)
        print(result)
    except UnsupportedMediaTypeError as e:
        # 지원하지 않는 확장자인 경우: 에러 메시지 출력 후 0이 아닌 코드로 종료
        print(f"오류: {e}")
        sys.exit(1)
