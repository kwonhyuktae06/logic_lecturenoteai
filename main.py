from media_input import load_media


def run_pipeline(file_path: str):
    media = load_media(file_path)
    print(f"[입력 처리] media_type={media['media_type']}")
    print(f"  audio_path: {media['audio_path']}")
    print(f"  video_path: {media['video_path']}")

    # TODO: media["audio_path"] -> Whisper.py 로 STT + 타임스탬프/신뢰도 추출
    # TODO: media["video_path"] 가 있으면 -> opencv_json1.py 로 슬라이드 캡처
    # TODO: Whisper 결과 + 캡처 이미지 -> Qwen.py 로 교차 검증 및 최종 노트 생성

    return media


if __name__ == "__main__":
    run_pipeline("lecture_test4.mp4")
