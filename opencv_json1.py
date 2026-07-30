""" 
제목: opencv_json1.py(수정본)
작성자: 이효정

[수정 및 보완 사항]
- 원본 FPS 기반 waitKey 지연시간 연산으로 0.5배속 렉 현상 해결
- 마우스 창 크기 변경에 맞춘 동적 폰트/테두리 리사이징 처리
- Whisper 타겟 시간대 중복 캡처 방지 로직 적용 (processed_whisper_timestamps 사용)
- captures 폴더 자동 생성 및 실물 JPG 파일 저장 기능 연동
"""

import cv2      # OpenCV 라이브러리 (컴퓨터 비전 및 비디오 처리)
import json     # JSON 데이터 가공을 위한 라이브러리
import base64   # 이미지를 텍스트 데이터(문자열)로 인코딩하기 위한 라이브러리
import numpy as np # 행렬(Matrix) 연산을 위한 라이브러리 (OpenCV 이미지 데이터 핸들링 필수)
import os       # [추가] 폴더 유무 확인 및 자동 생성을 위한 라이브러리
import tkinter as tk  
from tkinter import messagebox

def image_to_base64(frame_bgr):
    """
    [1단계] BGR -> RGB 변환 후 JPG 압축하여 Base64 텍스트로 인코딩
    """
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    _, buffer = cv2.imencode('.jpg', frame_rgb)
    base64_string = base64.b64encode(buffer).decode('utf-8')
    return base64_string

def format_timestamp(seconds):
    """
    [2단계] 초 데이터를 '시:분:초' 형식
    """
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def generate_opencv_json_pipeline(video_path, low_confidence_timestamps):
    """
    [3단계] 영상 화면 전환 및 Whisper AI 취약 구간을 분석하고 실시간 모니터링 제공 최종 JSON 데이터 출력
    """
    # [추가] 캡처한 이미지들이 들어갈 실제 폴더 경로 지정 및 자동 생성
    output_dir = "captures"
    os.makedirs(output_dir, exist_ok=True)  # [추가] 폴더가 없으면 자동 생성하여 저장 에러 방지

    # 파일 존재 여부 확인
    if not os.path.exists(video_path):
        root = tk.Tk()
        root.withdraw()  # 불필요한 메인 윈도우 창 숨기기
        messagebox.showerror("파일 오류", f"지정한 동영상 파일을 찾을 수 없습니다.\n경로를 확인해 주세요:\n{video_path}")
        root.destroy()
        return "[]"

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning("열기 실패", f"동영상 파일을 열 수 없습니다.\n파일이 손상되었거나 지원하지 않는 형식입니다:\n{video_path}")
        root.destroy()
        return "[]"

    orig_fps = cap.get(cv2.CAP_PROP_FPS)
    if orig_fps <= 0:
        print(" 비디오 FPS 정보를 가져올 수 없습니다.")
        return "[]"
    
    # ------------------------------------------------------------------
    # [수정] 창 크기 지정 및 모드 설정
    window_name = "OpenCV Pipeline Monitoring"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)  # 마우스로 크기 조절이 가능하도록 창 모드 변경
    cv2.resizeWindow(window_name, 1280, 720)        # 최초 기본 창 크기를 1280x720으로 지정
    # ------------------------------------------------------------------

    # 캡처 결과 데이터 객체들을 누적시킬 마스터 리스트 배열
    video_timeline_results = []
    processed_whisper_timestamps = set()  # [추가] Whisper 중복 캡처 방지용 저장 집합
    
    # 영상의 가장 첫 번째 프레임을 읽어와서 이전 기준점으로 삼음
    ret, prev_frame = cap.read()
    if not ret:
        print(" 첫 번째 프레임을 읽어올 수 없습니다.")
        return "[]"
    
    # [수정] 화면 변동 분석용 표준 해상도 정의 (1280x720 고정 연산)
    analysis_size = (1280, 720)
    prev_frame_resized = cv2.resize(prev_frame, analysis_size, interpolation=cv2.INTER_AREA)

    # ------------------------------------------------------------------
   # [수정] 원본 이미지 1장만 captures 폴더에 저장 후 경로만 기록
    first_img_path = f"{output_dir}/00_00_00_First_Frame.jpg"
    cv2.imwrite(first_img_path, prev_frame_resized)
    print("[전처리 레이어] 첫 화면 실물 이미지 파일로 캡처 성공")
    # ------------------------------------------------------------------

    first_capture = {
        "timestamp_sec": 0.0, 
        "timestamp_hms": "00:00:00",
        "capture_reason": "First_Frame",
        "image_data": first_img_path  # [수정] 실물 파일 경로만 기록 (Base64 인코딩 제거)
    }
    video_timeline_results.append(first_capture)

    # 그레이스케일 및 블러 필터 적용
    prev_gray = cv2.cvtColor(prev_frame_resized, cv2.COLOR_BGR2GRAY)
    prev_gray = cv2.GaussianBlur(prev_gray, (21, 21), 0)
    
    frame_count = 0        # 현재 처리 중인 전체 프레임 카운트 변수
    scene_threshold = 8.0  # 화면 전환 감지 민감도 임계값 (%)
    
    # [수정] 동영상 원본 FPS에 맞춘 waitKey 대기시간 연산 (0.5배속 렉 현상 해결의 핵심)
    delay_ms = max(1, int(1000 / orig_fps))

    # 비디오의 모든 프레임을 끝까지 순회하는 루프
    while True:
        ret, frame = cap.read()
        if not ret: # 영상을 끝까지 다 읽었으면 루프 종료
            break

        frame_count += 1
        current_sec = frame_count / orig_fps
        hms_string = format_timestamp(current_sec) # 시분초 텍스트 변환

        # ------------------------------------------------------------------
        # [추가/수정] 실시간 마우스 창 크기 감지 및 디스플레이 프레임 동적 리사이징
        # ------------------------------------------------------------------
        window_rect = cv2.getWindowImageRect(window_name)  # 사용자가 바꾼 창 크기 획득 (x, y, w, h)
        win_w = window_rect[2] if window_rect[2] > 100 else 1280
        win_h = window_rect[3] if window_rect[3] > 100 else 720
        dynamic_size = (win_w, win_h)

        # 사용자가 조절한 창 크기에 딱 맞춰 화면 출력용 프레임 생성
        display_frame = cv2.resize(frame, dynamic_size, interpolation=cv2.INTER_AREA)
        # ------------------------------------------------------------------
        
        # [A] 화면 변화 감지 연산 (연산 정확도를 위해 1280x720 규격으로 통일 연산)
        calc_frame = cv2.resize(frame, analysis_size, interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(calc_frame, cv2.COLOR_BGR2GRAY)               # 흑백 변환
        gray = cv2.GaussianBlur(gray, (21, 21), 0)                    # 블러 처리
        frame_delta = cv2.absdiff(prev_gray, gray)                   # 차이 연산
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1] # 이진화
        
        # 전체 픽셀 대비 변화율(%) 계산
        change_percentage = (cv2.countNonZero(thresh) / (gray.shape[0] * gray.shape[1])) * 100
        is_scene_changed = change_percentage > scene_threshold
        
        # [B] [수정] Whisper AI 신뢰도 미달 구간 체크 및 중복 캡처 방지 로직
        is_whisper_target = False
        for t in low_confidence_timestamps:
            # 타겟 시간대 오차범위 0.2초 이내이면서, 아직 캡처된 적 없는 타임스탬프인 경우만 캡처
            if abs(current_sec - t) < 0.2 and t not in processed_whisper_timestamps:
                is_whisper_target = True
                processed_whisper_timestamps.add(t)  # [추가] 처리 완료 집합에 기록하여 중복 방지
                break
        
       # 화면 전환이 감지되었거나 Whisper 타겟 시간일 경우 캡처 실행
        if is_scene_changed or is_whisper_target:
            reason = "WHISPER_TARGET" if is_whisper_target else "PPT_SCENE_CHANGE"
            
            # [수정] 실물 파일 중복 저장(cv2.imwrite)은 제거하고, 원본 경로(first_img_path)만 참조
            capture_item = {
                "timestamp_sec": round(current_sec, 2),
                "timestamp_hms": hms_string,
                "capture_reason": reason,
                "image_path": first_img_path # <-- 원본 이미지 경로만 전달
            }
            video_timeline_results.append(capture_item)
            
            # [수정] 창 크기에 비례하는 테두리 및 텍스트 시각 효과 적용
            thickness = max(4, int(win_w * 0.015))
            offset = thickness // 2
            cv2.rectangle(display_frame, (offset, offset), (win_w - offset, win_h - offset), (0, 255, 0), thickness)
            
            font_scale = max(0.5, win_w / 1000.0)
            cv2.putText(display_frame, f"CAP ({reason})", (thickness + 20, thickness + int(40 * font_scale)), 
                        cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), max(1, int(font_scale * 2)))
            
            if is_scene_changed:
                prev_gray = gray  # 다음 비교를 위한 기준 프레임 갱신

        # [수정] 창 크기에 맞춘 좌측 하단 재생 시간 표시
        font_scale_sub = max(0.4, win_w / 1200.0)
        cv2.putText(display_frame, f"Time: {hms_string}", (30, win_h - 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale_sub, (255, 255, 255), 2)

        # 화면 출력
        cv2.imshow(window_name, display_frame)

        # [수정] 원본 FPS 대기시간(delay_ms) 적용으로 동영상 배속 정상화
        cv2.waitKey(delay_ms)

        # X 버튼 클릭 시 종료
        if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
            print("영상 창이 X 버튼으로 닫혀 프로그램을 종료합니다.")
            break

    cap.release()
    cv2.destroyAllWindows() 
    
    return json.dumps(video_timeline_results, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    video_file = "lecture_test4.mp4" 
    fake_whisper_times = [5.0] 
    
    json_result = generate_opencv_json_pipeline(video_file, fake_whisper_times)
if json_result != "[]":
        print("\n전처리 분석 완료!")
else:
        print("\n파일이 없습니다 지정 파일을 확인하세요.")