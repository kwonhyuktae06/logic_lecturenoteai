import cv2      # OpenCV 라이브러리 (컴퓨터 비전 및 비디오 처리)
import json     # JSON 데이터 가공을 위한 라이브러리
import base64   # 이미지를 텍스트 데이터(문자열)로 인코딩하기 위한 라이브러리
import numpy as np # 행렬(Matrix) 연산을 위한 라이브러리 (OpenCV 이미지 데이터 핸들링 필수)

def image_to_base64(frame_bgr):
    """
    [1단계] OpenCV가 읽은 이미지 행렬(BGR)을 Qwen AI 포맷인 RGB로 변환하고,
    JSON 파일 내부에 텍스트 형태로 집어넣을 수 있게 Base64 문자열로 압축 변환하는 함수
    """
    # Qwen AI는 색상 포맷으로 RGB를 표준으로 사용하므로 BGR인 OpenCV 기본값을 RGB로
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    
    # 전송 용량 및 네트워크 효율성을 위해 메모리 상에서 .jpg 포맷으로 압축 수행
    # buffer 변수 안에 압축된 바이너리 이미지 데이터가 담김
    # buffer 변수는 데이터를 한 곳에서 다른 곳으로 전송하거나 처리하는 동안 일시적으로 데이터를 보관하는 메모리 공간
    _, buffer = cv2.imencode('.jpg', frame_rgb) #OpenCV 값이 RGB로 변환되지 않는 문제 수정
    
    # 바이너리 이미지 버퍼를 텍스트 문자열(ASCII) 형태로 변환하여 읽을 수 있게 최종 직렬화
    base64_string = base64.b64encode(buffer).decode('utf-8')
    return base64_string

def format_timestamp(seconds):
    """
    [2단계] 소수점 형태의 초(sec) 데이터를 받아서 
    UI 프레임에 직관적으로 매핑할 수 있게 '시:분:초' 문자열 형식으로 변환하는 함수
    """
    h = int(seconds // 3600)       # 3600초로 나누어 '시' 계산
    m = int((seconds % 3600) // 60) # 남은 초를 60으로 나누어 '분' 계산
    s = int(seconds % 60)          # 최종 남은 '초' 계산
    return f"{h:02d}:{m:02d}:{s:02d}" # 두 자리 정수 형태로 포맷팅 (예: 00:14:20)

def generate_opencv_json_pipeline(video_path, low_confidence_timestamps):
    """
    [3단계] 영상의 화면 전환 및 Whisper AI 취약 구간을 분석하고 
    실시간 모니터링 팝업창을 제공하며 최종 JSON 데이터를 출력하는 핵심 파이프라인
    """
    # OpenCV 비디오 캡처 객체 생성 (노트북에 위치한 비디오 파일 스트림 연결)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        # 오류 처리: 비디오 파일을 열 수 없는 경우 
        print(" 비디오 파일을 열 수 없습니다. 경로 또는 파일명을 다시 확인하세요.")
        return "[]"

    # 원본 비디오의 초당 프레임 수(FPS) 추출 (시간 계산의 기준점)
    orig_fps = cap.get(cv2.CAP_PROP_FPS)
    if orig_fps <= 0:
        # 오류 처리: FPS가 0 이하이면 비디오 정보를 가져올 수 없는 경우
        print(" 비디오 FPS 정보를 가져올 수 없습니다. 파일이 손상되었거나 지원되지 않는 코덱인지 확인하십시오.")
        return "[]"
    
    # 캡처 결과 데이터 객체들을 차곡차곡 누적시킬 마스터 리스트 배열
    video_timeline_results = []
    
    # [루틴 A: 화면 전환 감지 전처리 시작]
    # 영상의 가장 첫 번째 프레임을 읽어와서 이전 기준점으로 삼음
    ret, prev_frame = cap.read()
    if not ret:
        print(" 첫 번째 프레임을 읽어올 수 없습니다.")
        return "[]"
        
    # 컴퓨터가 화면 변화를 오차 없이 이해하도록 그레이스케일 변환
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    # 강사의 미세한 떨림이나 비디오 지지직거리는 노이즈를 지우기 위해 블러(Blur) 필터 적용
    prev_gray = cv2.GaussianBlur(prev_gray, (21, 21), 0)
    
    frame_count = 0     # 현재 처리 중인 전체 프레임 카운트 변수
    capture_count = 0   # 캡처 성공 횟수 기록 변수
    scene_threshold = 8.0  # 화면 전환 감지 민감도 임계값 (노트북에서 돌려보며 숫자를 낮추거나 높여 조절 가능)

    print(" OpenCV 영상 재생 및 JSON 데이터 빌드 시작... (종료하려면 영상 창에서 'q'를 누르세요)")

    # 비디오의 모든 프레임을 끝까지 순회하는 루프 프레임워크
    while True:
        # 다음 프레임을 읽어옴 (ret은 성공 여부 True/False, frame은 이미지 데이터)
        ret, frame = cap.read()
        if not ret: # 영상을 끝까지 다 읽었으면 루프 종료
            break
            
        frame_count += 1
        # 현재 읽어온 프레임이 원본 영상에서 정확히 '몇 초' 지점인지 계산
        current_sec = frame_count / orig_fps
        hms_string = format_timestamp(current_sec) # 시분초 텍스트 변환
        
        # 원본 frame 이미지는 변환 연산용으로 쓰고, 
        # 노트북 화면에 띄울 팝업창은 가공용으로 따로 복사본을 생성 (메시지나 사각형을 덧그리기 위함)
        display_frame = frame.copy()
        
        # [루틴 A] 컴퓨터가 이전 화면과 현재 화면의 변화량을 인지하는 핵심 연산 부분
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)              # 현재 프레임 흑백 변환
        gray = cv2.GaussianBlur(gray, (21, 21), 0)                   # 현재 프레임 블러 처리
        frame_delta = cv2.absdiff(prev_gray, gray)                  # 이전 흑백 이미지와 현재 흑백 이미지의 '절대적 차이' 연산
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1] # 변동이 감지된 영역을 흰색(255)으로 이진화
        
        # 화면의 전체 픽셀 면적 중 흰색(화면이 바뀐 부분)이 차지하는 비율(%) 계산
        change_percentage = (cv2.countNonZero(thresh) / (gray.shape[0] * gray.shape[1])) * 100
        
        # 계산된 변화율이 설정한 임계값(8.0%)을 넘으면 PPT 슬라이드 전환으로 판단
        is_scene_changed = change_percentage > scene_threshold
        
        # [루틴 B] 백엔드가 연동해준 Whisper AI의 확신도 낮음 구간(타겟 시간) 오차범위 0.2초 내 도달 여부 체크
        is_whisper_target = any(abs(current_sec - t) < 0.2 for t in low_confidence_timestamps)
        
        # 화면 전환이 감지되었거나, 오역 위험 취약 구간 타이밍에 딱 부합하는 순간 캡처 실행
        if is_scene_changed or is_whisper_target:
            capture_count += 1
            # 캡처가 된 원인을 텍스트로 라벨링하여 저장
            reason = "WHISPER_TARGET" if is_whisper_target else "PPT_SCENE_CHANGE"
            
            # 딕셔너리 구조를 생성하여 JSON으로 출력할 정보들을 개별 규격 패키징 수행
            capture_item = {
                "timestamp_sec": round(current_sec, 2), # 소수점 두자리 초 정보
                "timestamp_hms": hms_string,            # 시:분:초 텍스트 정보
                "capture_reason": reason,               # 캡처 사유
                "image_data": image_to_base64(frame)    # 1단계에서 텍스트로 압축 완료한 이미지 인코딩 데이터
            }
            video_timeline_results.append(capture_item) # 마스터 타임라인 배열에 누적 저장
            
            #  [실시간 모니터링 기능 추가] 캡처 조건 충족 시 화면 가장자리에 두꺼운 초록색 사각형(테두리)을 그리기
            cv2.rectangle(display_frame, (0, 0), (display_frame.shape[1], display_frame.shape[0]), (0, 255, 0), 20)
            #  영상 상단에 캡처 완료 메시지와 어떤 원인으로 찍혔는지 텍스트 주입
            cv2.putText(display_frame, f"캡쳐 ({reason})", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
            print(f" [전처리 레이어] 캡처 성공: [{hms_string}] 사유: {reason}")
            
            # 일반 화면 전환(PPT 변경)이었을 경우에만 다음 화면 비교를 위해 기준점(prev_gray)을 현재 프레임으로 리셋
            if is_scene_changed:
                prev_gray = gray

        #  [실시간 모니터링 기능 추가] 캡처 여부와 상관없이 비디오 좌측 하단에 상시 흘러가는 현재 재생 시간 표시
        cv2.putText(display_frame, f"Time: {hms_string}", (50, display_frame.shape[0] - 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)

        #  [실시간 모니터링 기능 추가] 내 개인 노트북 모니터 화면에 실제 윈도우 팝업창을 생성하여 동영상 출력
        cv2.imshow("OpenCV Pipeline Monitoring (Press 'q' to Quit)", display_frame)
        
        #  매우 중요: 동영상이 너무 빠르거나 느리게 재생되지 않도록 원본 FPS 속도만큼 연산을 지연 대기시킴
        # 대기하는 동안 사용자가 팝업창을 선택하고 키보드의 알파벳 'q'를 누르면 즉시 강제 중단 처리
        if cv2.waitKey(int(1000 / orig_fps)) & 0xFF == ord('q'):
            print(" 사용자가 'q' 키를 입력하여 모니터링 및 영상 처리를 중단했습니다.")
            break

    # 모든 프레임 분석이 끝나거나 중단되면 열려있던 비디오 파일 연결 자원을 반납 해제
    cap.release()
    # 화면에 띄워두었던 OpenCV 전용 모니터링 팝업창들을 깔끔하게 파괴하고 닫음
    cv2.destroyAllWindows() 
    
    # [4단계] 파이썬 List 객체로 쌓아둔 데이터 구조들을 최종 표준 직렬화 규격인 JSON 형태 문자열로 변환 출력
    # 한글 깨짐을 완벽 방지하고(ensure_ascii=False), 문서 가독성을 높이기 위해 들여쓰기(indent=2) 처리 규칙 포함
    return json.dumps(video_timeline_results, ensure_ascii=False, indent=2)
#===========================================================================================================================
# 또 다른 영상 수정 할 수 있는 부분
# 파이썬 스크립트가 직접 단독 실행되었을 때 가동되는 메인 엔트리 포인트
if __name__ == "__main__":
    # 바탕화면 혹은 작업 공간에 준비한 샘플 강의 비디오 파일명 지정
    video_file = "lecture_test2.mp4" 
    # 기획서 상의 흐름을 연동 검증하기 위해 5초 지점에 Whisper AI의 신뢰도 미달 구간이 생겼다고 임의 가정
    fake_whisper_times = [5.0] 
    
    # 파이프라인 함수를 구동하고 최종 생성된 규격화 JSON 데이터 텍스트 문자열을 리턴받음
    json_result = generate_opencv_json_pipeline(video_file, fake_whisper_times)
    
    print("\n 전처리 분석 완료!")
    print(" 백엔드 및 Qwen API 패키징에 즉시 투입 가능한 최종 JSON 데이터 크기:", len(json_result), "자")
