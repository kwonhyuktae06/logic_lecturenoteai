# logic_lecturenoteai
#  (AI 기반 강의 노트 자동 생성 및 오타 교정 파이프라인)

오픈소스 멀티모달 AI를 활용하여 대학교 강의 영상 등으로부터 슬라이드별 핵심 요약 노트를 자동 생성하고, 음성 인식 오타를 화면 정보를 통해 교차 검증하는 시스템입니다.

---

##  핵심 기술 스택
* **Language:** Python
* **Computer Vision:** OpenCV (Frame Differencing 기반 화면 전환 감지)
* **Speech-to-Text:** OpenAI Whisper (Hugging Face)
* **Vision-Language Model:** Qwen-VL (Qwen2.5-VL-7B-Instruct)

##  주요 파이프라인 프로세스
1. **오디오/비디오 분리:** 업로드된 영상에서  오디오 추출 후 **Whisper** 구동 (타임스탬프 텍스트 추출).
2. **화면 감지 엔진:** **OpenCV**를 활용해 PPT 슬라이드가 넘어가는 프레임 전환 시점을 포착하여 자동 캡처 및 타임라인 기록.
3. **시간대별 데이터 매칭:** 캡처된 이미지의 시간축과 Whisper 대사의 시간축을 통합하여 세트 데이터 구축.
4. **교차 검증 및 업그레이드:** **Qwen-VL**에 [이미지 + 대사]를 프롬프트와 함께 입력하여, 음성 오타 교정 및 마크다운 형식의 완성도 높은 강의 노트 생성.

##  개발 시작하기
```bash
git clone [https://github.com/](https://github.com/)[본인계정]/[레포-이름].git
cd [레포-이름]
pip install -r requirements.txt  # (추후 라이브러리 추가 예정)
