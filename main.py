from media_input import load_media


def run_pipeline(file_path: str):
    media = load_media(file_path) # 입력된 파일 분석
    print(f"[입력 처리] media_type={media['media_type']}") # 입력된 파일이 영상 또는 오디오인지 확인하기 위해 출력
    print(f"  audio_path: {media['audio_path']}") # Whisper가 사용할 오디오 위치 출력
    print(f"  video_path: {media['video_path']}") # OpenCV가 사용할 영상 위치 출력

    # 아직 구현하지 않은 기능
    # TODO: media["audio_path"] -> Whisper.py 로 STT + 타임스탬프/신뢰도 추출
    # TODO: media["video_path"] 가 있으면 -> opencv_json1.py 로 슬라이드 캡처
    # TODO: Whisper 결과 + 캡처 이미지 -> Qwen.py 로 교차 검증 및 최종 노트 생성

    return media # 정리된 입력 데이터를 다른 프로그램에서도 사용할 수 있도록 반환


if __name__ == "__main__": # 이 파일을 직접 실행했을 때만 아래 코드 실행
    run_pipeline("lecture_test4.mp4") # 테스트용으로 lecture_teat4.mp4를 입력하여 파이프라인이 정상적으로 동작하는지 확인

