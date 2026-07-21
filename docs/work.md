# 작업 기록 - 2026-07-21

## 1. 개발 환경 세팅
- Git 설치 (winget) → 이후 정상 동작 확인
- 저장소 clone: `https://github.com/kwonhyuktae06/logic_lecturenoteai`
  - 처음엔 `main` 브랜치로 받음
  - 내 역할(파이프라인 담당)에 맞춰 **`pipeline` 브랜치로 전환** (`git checkout -b pipeline origin/pipeline`)
- ffmpeg 설치
  - 직접 설치 시도했던 건 PATH 등록이 안 돼서 인식 안 됐음
  - winget으로 재설치 (`winget install ffmpeg`) → 정상 동작 확인 (버전 8.1.2)
- Python 확인: `python`/`python3` 명령은 윈도우 스토어 별칭이라 안 먹힘 → **`py` 명령으로 실행해야 함** (Python 3.14.6 설치되어 있음)

## 2. 노트북 사양 확인 및 개발 방향 결정
- GPU: NVIDIA 없음, AMD Radeon 840M 내장그래픽만 있음
- RAM: 16GB
- **결론**: Whisper-large-v3, Qwen3-VL-8B 같은 무거운 모델은 이 노트북에서 로컬 실행 불가/매우 느림
  → **로컬에서는 코드 구조/로직만 짜고, 무거운 모델 실행은 팀원 GPU 또는 Colab에서 진행하기로 함**

## 3. 프로젝트 구조 파악
- 브랜치가 팀원별로 분리되어 있음: `main`, `server`, `front`, `DataBase`, `pipeline`
- `pipeline` 브랜치에 있는 기존 파일들 (프로토타입 단계, 아직 서로 연결 안 됨):
  - `Whisper.py` — mp3 → 텍스트 변환 (전체 텍스트만 추출, 타임스탬프/신뢰도 점수는 아직 없음)
  - `opencv_json1.py` — 영상에서 슬라이드 전환 캡처 + Whisper 저신뢰도 구간 캡처 (`low_confidence_timestamps` 인자를 받는 구조)
  - `Qwen.py` — [이미지+텍스트] → 교차검증 후 최종 강의노트 생성 (현재는 `WhisperMockRunner`로 가짜 텍스트 사용 중)
  - `main.py` — 원래 비어 있었음 (파이프라인 통합 지점)
  - `gpu_test.py` — CUDA 인식 테스트용

## 4. 오늘 작성한 코드
- **`media_input.py` 신규 생성**
  - `load_media(file_path)`: 확장자로 음성(mp3/wav/m4a) vs 영상(mp4/mov/avi/mkv) 구분
  - `extract_audio(video_path)`: 영상이면 ffmpeg로 오디오만 추출 (wav, 16kHz, 모노 — Whisper 권장 포맷)
- **`main.py` 수정**
  - `run_pipeline(file_path)` 함수 추가, `load_media` 연결
  - Whisper / OpenCV / Qwen 연결 지점은 TODO 주석으로 표시해둠 (아직 미구현)

## 5. 테스트
- 카카오톡으로 받은 테스트 음성 파일(`test.m4a`)로 `load_media()` 실행 → 정상 동작 확인
  - 결과: `media_type: audio`, `video_path: None`, `audio_path`는 원본 그대로 반환됨

## 6. 논의 사항 (미결정)
- Whisper를 **로컬 오픈소스 모델** 대신 **OpenAI API**로 대체하는 방안 검토
  - 장점: 로컬 GPU/설치 부담 없음, 세그먼트별 타임스탬프+신뢰도(avg_logprob)도 받을 수 있음
  - 단점: 유료, 팀이 이미 정한 "오픈소스 모델" 방향과 다름, 강의 음성이 외부 서버로 전송됨
  - **→ 팀원들과 상의 후 결정하기로 함 (보류)**

## 다음에 할 일
- [ ] 팀원들과 Whisper API vs 로컬 오픈소스 모델 방향 논의
- [ ] (로컬 유지 시) Whisper 결과에 세그먼트별 타임스탬프 + 신뢰도 점수 추출 로직 추가
- [ ] Whisper 저신뢰도 구간 → `opencv_json1.py`로 연결
- [ ] OpenCV 캡처 이미지 → `Qwen.py` 입력으로 연결 (Mock 대신 실제 Whisper 결과 사용)
- [ ] `main.py`에서 전체 흐름 하나로 통합
- [ ] server 팀과 업로드 파일 경로 등 인터페이스 맞추기
