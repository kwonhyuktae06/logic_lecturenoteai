"""
제목: opencv_json1_easy.py
설명: 5초 간격 고정 캡처 및 Whisper AI 타깃 시간대 캡처를 수행하는 OpenCV 기반 동영상 처리 파이프라인
"""

import cv2      # 동영상 프레임 추출 및 이미지 저장을 위한 라이브러리
import json     # 결과를 JSON 데이터로 변환하기 위한 라이브러리
import os       # 폴더 생성 및 경로 관리를 위한 라이브러리

def format_timestamp(seconds):
    """
    [시간 변환 함수] 
    초(seconds) 단위 숫자를 받아 '시:분:초 (00:00:00)' 형태의 문자열로 변환합니다.
    """
    hours = int(seconds // 3600)               # 전체 초를 3600으로 나눠 '시간' 계산
    minutes = int((seconds % 3600) // 60)      # 남은 초를 60으로 나눠 '분' 계산
    secs = int(seconds % 60)                   # 최종 남은 '초' 계산
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def generate_opencv_json_pipeline(video_path, low_confidence_timestamps):
    # 캡처된 이미지를 저장할 'captures' 폴더가 없으면 자동 생성
    folder = "captures"
    os.makedirs(folder, exist_ok=True)

    # 비디오 파일 열기
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"비디오를 열 수 없습니다: {video_path}")
        return "[]"

    # 비디오의 초당 프레임 수(FPS) 가져오기
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        return "[]"

    results = []                           # 캡처 결과를 담을 리스트
    history = set()                        # 이미 처리한 Whisper 타깃 시간을 기록하는 집합

    # ------------------------------------------------------------------
    # 1. 영상의 맨 첫 프레임(0초 시점) 저장
    # ------------------------------------------------------------------
    ret, frame = cap.read()               # 영상의 첫 번째 프레임 읽기
    if not ret:
        return "[]"

    # 0초 첫 이미지 저장 및 경로 설정
    firstpath = f"{folder}/00_00_00_First_Frame.jpg"
    cv2.imwrite(firstpath, frame)          # 실물 JPG 파일로 저장

    # JSON 리스트에 0초 데이터 기록
    results.append({
        "timestamp_sec": 0.0,
        "timestamp_hms": "00:00:00",
        "capture_reason": "First_Frame",
        "image_path": firstpath
    })

    # ------------------------------------------------------------------
    # 2. 5초 고정 타이머 루프 설정
    # ------------------------------------------------------------------
    interval = 5.0  # 캡처 고정 간격 (5초)
    last = 0.0      # 가장 최근에 캡처한 시점 (초)
    count = 0       # 읽어온 프레임 누적 개수

    # 동영상 모든 프레임을 순회하는 메인 루프
    while True:
        ret, frame = cap.read()           # 다음 프레임 1장 읽어오기
        if not ret:                       # 더 이상 읽을 프레임이 없으면 종료
            break

        count += 1                        # 프레임 수 1 증가
        now = count / fps                 # 현재 프레임의 재생 시간(초) 계산
        clock = format_timestamp(now)     # 초를 '00:00:00' 포맷으로 변환

        # [조건 1] 마지막 캡처 시점으로부터 5초 이상 지났는지 판단
        timeout = (now - last) >= interval

        # [조건 2] 현재 시간이 Whisper AI 타깃 시간대인지 확인
        target = False
        for t in low_confidence_timestamps:
            # 현재 시점이 Whisper 타깃 시간과 0.2초 이내로 근접하고, 처리된 적이 없을 때
            if abs(now - t) < 0.2 and t not in history:
                target = True
                history.add(t)            # 중복 캡처 방지용 기록
                break

        # [캡처 실행 조건] 5초가 지났거나 Whisper 타깃 시점인 경우 캡처 실행
        if timeout or target:
            # 캡처 이유 구분 (Whisper 타깃 우선, 아니면 5초 고정 주기)
            reason = "WHISPER_TARGET" if target else "INTERVAL_5SEC"
            
            # 파일명에 콜론(:)을 사용할 수 없으므로 언더바(_)로 변경
            safehms = clock.replace(":", "_")
            path = f"{folder}/{safehms}_{reason}.jpg"

            # 해당 순간의 프레임을 실물 JPG 이미지로 저장
            cv2.imwrite(path, frame)

            # JSON 출력용 타임라인 결과 리스트에 캡처 정보 바인딩
            results.append({
                "timestamp_sec": round(now, 2),
                "timestamp_hms": clock,
                "capture_reason": reason,
                "image_path": path
            })
            # 5초 주기 캡처였던 경우, 타이머 기준 시간을 현재 시점으로 갱신
            if timeout:
                last = now

        # 실시간 모니터링 화면 출력
        cv2.imshow("Video Monitoring", frame)

        # 사용자가 모니터링 창을 닫으면 루프 종료
        if cv2.getWindowProperty("Video Monitoring", cv2.WND_PROP_VISIBLE) < 1:
            print("사용자가 X 버튼을 눌러 모니터링을 종료합니다.")
            break

    # 자원 해제 및 모니터링 창 닫기
    cap.release()
    cv2.destroyAllWindows()

    # 최종 추출 결과를 JSON 문자열로 반환
    return json.dumps(results, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # 분석할 동영상 파일 이름을 지정합니다. (파이썬 파일과 같은 폴더에 있어야 합니다)
    video_file = "lecture_test4.mp4" 
    fake_whisper_times = [5.0] 
    
    # 동영상과 테스트 시간을 전달하여 5초 고정 캡처 파이프라인 함수를 실행합니다.
    # 영상 파일이 없으면 내부에서 경고창만 뜨고 빈 결과([])만 바로 반환됩니다.
    json_result = generate_opencv_json_pipeline(video_file, fake_whisper_times)

    # 최종 결과 출력
    print(json_result)