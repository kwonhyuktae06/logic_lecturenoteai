"""
제목: main.py
작성자: 한동희
내용: 강의노트 AI 통합 파이프라인 (지휘자)

이 파일은 AI를 직접 돌리지 않는다. 각 담당자가 만든 모듈을 순서대로 부르고
데이터만 넘겨준다. 그래서 여기서 하는 일은 세 가지다.
  1. 단계 사이에 오가는 데이터의 규격을 확정한다
  2. 아직 규격에 안 맞는 모듈은 어댑터로 감싸서 붙인다
  3. 어느 단계에서 왜 실패했는지 분명하게 알린다 (조용히 실패하지 않는다)

실행:
    python main.py lecture_test4.mp4
    python main.py lecture_test4.mp4 --skip-stage transcribe --skip-stage note
    python main.py lecture_test4.mp4 --allow-gui --prompt-type error_check

단계 사이 데이터 규격:
    1단계 출력  {"media_type": "video"|"audio", "video_path": str|None, "audio_path": str}
    2단계 출력  {"transcript": str, "segments": [...],
                 "low_confidence_words": [...], "low_confidence_timestamps": [float]}
    3단계 출력  [{"timestamp_sec": float, "timestamp_hms": str,
                 "capture_reason": str, "image_path": str}, ...]
    4단계 출력  run_qwen_pipeline()이 주는 dict 그대로
"""

import argparse
import importlib
import inspect
import json
import math
import sys
from datetime import datetime
from pathlib import Path

# 이 파일이 있는 폴더. 다른 모듈 파일을 찾을 때 기준으로 쓴다.
BASE_DIR = Path(__file__).resolve().parent

# Qwen에 한 번에 넘길 이미지 최대 장수. 너무 많으면 VRAM이 부족해진다.
DEFAULT_MAX_IMAGES = 8

# --skip-stage 로 건너뛸 수 있는 단계 이름
SKIPPABLE_STAGES = ["transcribe", "capture", "note"]

# 3단계에서 쓸 캡처 모듈 후보. 앞에 있는 것부터 찾는다.
# _easy 를 먼저 두는 이유: 캡처 시점마다 별개의 이미지 파일을 저장한다.
# opencv_json1.py 는 첫 프레임 한 장만 저장하고 모든 캡처가 그 경로를 가리켜서,
# Qwen에게 매번 같은 이미지가 전달된다.
CAPTURE_MODULE_CANDIDATES = ["opencv_json1_easy", "opencv_json1"]
CAPTURE_FUNCTION = "generate_opencv_json_pipeline"

# Qwen 프롬프트 종류 (qwen_pipeline.PROMPT_TEMPLATES 의 키와 같아야 한다)
PROMPT_TYPES = ["lecture_summary", "short_summary", "detailed_notes", "quiz", "error_check"]


class PipelineError(Exception):
    """파이프라인 단계가 실행 중 실패했을 때 발생. 어느 단계인지 stage에 담는다."""

    def __init__(self, stage, message):
        super().__init__(f"[{stage} 단계] {message}")
        self.stage = stage
        self.message = message


class StageNotReadyError(PipelineError):
    """담당 모듈이 아직 약속한 인터페이스를 제공하지 않을 때 발생."""


def log(stage, message):
    """진행 상황 출력. flush=True 라서 오래 걸리는 작업 중에도 바로 보인다."""
    print(f"[{stage}] {message}", flush=True)


def module_defines(module_filename, func_name):
    """모듈을 import하지 않고 소스만 읽어서 함수가 정의돼 있는지 확인.

    import 안하는 이유: Whisper.py 처럼 최상단에 실행 코드가 있는 파일은
    import하는 순간 모델을 내려받고 추론을 시작해버린다. try/except로 감싸도
    소용없다. 본문이 다 실행된 뒤에야 이름을 찾기 때문이다.
    그래서 '함수가 있는지'만 볼 때는 소스를 글자로 읽어서 확인한다.
    """
    path = BASE_DIR / module_filename
    if not path.exists():
        return False

    source = path.read_text(encoding="utf-8")
    return f"def {func_name}(" in source


# ---------------------------------------------------------------------------
# 1단계 - 입력 파일 분리 (media_input.py)
# ---------------------------------------------------------------------------

def stage_media(file_path):
    """영상/오디오를 구분하고, 영상이면 ffmpeg로 오디오를 뽑아낸다."""
    from media_input import load_media, UnsupportedMediaTypeError

    # media_input.load_media() 는 오디오 파일일 때 존재 확인을 하지 않는다.
    # 여기서 미리 막아두지 않으면 2단계에 가서야 엉뚱한 곳에서 터진다.
    if not Path(file_path).exists():
        raise PipelineError("media", f"파일을 찾을 수 없습니다: {file_path}")

    try:
        media = load_media(file_path)
    except UnsupportedMediaTypeError as exc:
        raise PipelineError("media", str(exc)) from exc
    except FileNotFoundError as exc:
        raise PipelineError(
            "media",
            f"ffmpeg를 찾을 수 없습니다. 설치 후 PATH에 등록되었는지 확인하세요: {exc}",
        ) from exc
    except Exception as exc:
        # ffmpeg 실행 실패(CalledProcessError)가 여기로 온다.
        # 원인을 감추지 않고 그대로 붙여서 올린다.
        raise PipelineError(
            "media",
            f"오디오 추출에 실패했습니다. 원인: {exc}",
        ) from exc

    log("1/4 media", f"종류={media['media_type']}")
    log("1/4 media", f"  audio={media['audio_path']}")
    log("1/4 media", f"  video={media['video_path']}")
    return media


# ---------------------------------------------------------------------------
# 2단계 - 음성 인식 (Whisper.py)
# ---------------------------------------------------------------------------

WHISPER_REQUEST = (
    "Whisper.py 에 transcribe(audio_path) -> dict 함수가 없습니다.\n"
    "        지금 Whisper.py 는 최상단에 실행 코드가 그대로 있어서, import하면\n"
    "        large-v3 모델을 내려받고 test.mp3 를 변환해버립니다.\n"
    "        담당자에게 아래를 요청하세요:\n"
    "          1) 모델 로딩과 29~65번 줄을 def transcribe(audio_path) -> dict 안으로 옮기고\n"
    "          2) 마지막에 output_data 를 return 할 것\n"
    "        지금 나머지 단계만 확인하려면 --skip-stage transcribe 를 쓰세요."
)


def adapt_whisper_result(raw, audio_path):
    """Whisper.py가 준 값을 이 파이프라인의 2단계 규격으로 맞춘다.

    Whisper.py 는 transcribed_text / low_confidence_timestamps 라는 이름을 쓰는데,
    qwen_pipeline 은 transcript / low_confidence_words 를 찾는다. 그 차이를
    여기서 흡수한다. 남의 파일을 고치게 하는 대신 부르는 쪽이 맞춰주는 것이다.
    """
    if isinstance(raw, str):
        raw = {"transcript": raw}

    if not isinstance(raw, dict):
        raise PipelineError(
            "transcribe",
            f"transcribe()가 dict가 아니라 {type(raw).__name__} 을 반환했습니다.",
        )

    # 이름이 셋 중 무엇으로 오든 받아준다.
    transcript = raw.get("transcript") or raw.get("text") or raw.get("transcribed_text")
    if not transcript or not transcript.strip():
        raise PipelineError("transcribe", "결과에 transcript(또는 text)가 비어 있습니다.")

    segments = raw.get("segments", [])

    # 확신도 낮은 구간을 Qwen이 읽을 수 있는 형태로 조립한다.
    # avg_logprob 은 로그 확률이라 -0.42 같은 음수다. 그대로 넘기면 프롬프트에
    # "확신도: -0.42" 로 찍혀 모델이 헷갈리므로 exp()로 0~1 값으로 바꾼다.
    low_confidence_words = raw.get("low_confidence_words") or raw.get("uncertain_words") or []
    if not low_confidence_words and segments:
        for seg in segments:
            if not seg.get("low_confidence"):
                continue
            logprob = seg.get("avg_logprob")
            low_confidence_words.append({
                "word": seg.get("text", "").strip(),
                "start": seg.get("start"),
                "end": seg.get("end"),
                "confidence": round(math.exp(logprob), 3) if logprob is not None else None,
            })

    # 3단계(캡처)에 넘길 초 단위 시각 목록. Whisper.py가 이미 만들어 주면 그걸 쓰고,
    # 없으면 위에서 조립한 목록에서 뽑아낸다.
    timestamps = raw.get("low_confidence_timestamps")
    if timestamps is None:
        timestamps = [w["start"] for w in low_confidence_words if w.get("start") is not None]

    return {
        "source_audio": raw.get("source_audio", audio_path),
        "transcript": transcript.strip(),
        "segments": segments,
        "low_confidence_words": low_confidence_words,
        "low_confidence_timestamps": timestamps,
    }


def stage_transcribe(audio_path):
    """Whisper.py 의 transcribe()를 불러 음성을 텍스트로 바꾼다.

    반환 규격:
        {"transcript": str,
         "segments": [{"start", "end", "text", ...}, ...],
         "low_confidence_words": [{"word", "start", "end", "confidence"}, ...],
         "low_confidence_timestamps": [float, ...]}
    """
    # import 하기 전에 소스를 글자로 먼저 확인한다. module_defines() 주석 참고.
    if not module_defines("Whisper.py", "transcribe"):
        raise StageNotReadyError("transcribe", WHISPER_REQUEST)

    log("2/4 whisper", "모델 로딩 및 음성 인식 시작 (수 분 걸릴 수 있음)")
    from Whisper import transcribe  # 함수가 있는 것을 확인한 뒤에만 import

    try:
        raw = transcribe(audio_path)
    except Exception as exc:
        raise PipelineError("transcribe", f"음성 인식 중 오류: {exc}") from exc

    data = adapt_whisper_result(raw, audio_path)

    preview = data["transcript"][:60].replace("\n", " ")
    log("2/4 whisper", f"완료 - {len(data['transcript'])}자, 미리보기: {preview}...")
    log("2/4 whisper", f"  세그먼트 {len(data['segments'])}개, "
                       f"확신도 낮은 구간 {len(data['low_confidence_words'])}개")
    return data


def empty_whisper_data(reason):
    """2단계를 건너뛸 때 쓸 빈 껍데기. 뒷 단계가 키를 찾다 터지지 않게 한다."""
    return {
        "source_audio": None,
        "transcript": f"({reason})",
        "segments": [],
        "low_confidence_words": [],
        "low_confidence_timestamps": [],
    }


# ---------------------------------------------------------------------------
# 3단계 - 슬라이드 캡처 (opencv_json1_easy.py / opencv_json1.py)
# ---------------------------------------------------------------------------

def resolve_capture_module():
    """쓸 수 있는 캡처 모듈을 찾는다. (모듈명, 함수객체) 를 돌려준다."""
    for module_name in CAPTURE_MODULE_CANDIDATES:
        if not module_defines(f"{module_name}.py", CAPTURE_FUNCTION):
            continue
        module = importlib.import_module(module_name)
        return module_name, getattr(module, CAPTURE_FUNCTION)

    raise StageNotReadyError(
        "capture",
        f"{' 또는 '.join(CAPTURE_MODULE_CANDIDATES)} 에서 "
        f"{CAPTURE_FUNCTION}() 을 찾지 못했습니다.",
    )


def stage_capture(video_path, low_confidence_timestamps, allow_gui=False):
    """영상에서 슬라이드 전환 시점을 잡아 이미지로 저장하고 타임라인을 만든다."""
    module_name, capture_func = resolve_capture_module()

    # 함수가 show_window 인자를 받는지 확인한다.
    # inspect.signature() 는 함수의 인자 목록을 들여다보는 파이썬 표준 도구다.
    params = inspect.signature(capture_func).parameters
    supports_headless = "show_window" in params

    if not supports_headless and not allow_gui:
        raise StageNotReadyError(
            "capture",
            f"{module_name}.py 의 {CAPTURE_FUNCTION}() 이 show_window 인자를 받지 않습니다.\n"
            "        지금 구조로는 cv2.imshow 창이 뜨고, 영상 길이만큼 실시간으로 재생됩니다.\n"
            "        (10분짜리 강의면 캡처에만 10분이 걸리고, 화면 없는 서버에서는 죽습니다.)\n"
            "        담당자에게 show_window: bool = False 인자 추가를 요청하세요.\n"
            "        지금 로컬에서 창을 띄워서라도 확인하려면 --allow-gui 를 붙이세요.",
        )

    mode = "헤드리스" if supports_headless and not allow_gui else "창 표시"
    log("3/4 opencv", f"{module_name} 사용 ({mode})")
    if low_confidence_timestamps:
        log("3/4 opencv", f"  확신도 낮은 시각 {len(low_confidence_timestamps)}곳을 타겟 캡처")

    try:
        if supports_headless:
            raw = capture_func(video_path, low_confidence_timestamps, show_window=allow_gui)
        else:
            raw = capture_func(video_path, low_confidence_timestamps)
    except Exception as exc:
        raise PipelineError("capture", f"영상 분석 중 오류: {exc}") from exc

    captures = parse_capture_result(raw)
    log("3/4 opencv", f"완료 - 캡처 {len(captures)}건")
    return captures


def parse_capture_result(raw):
    """캡처 모듈이 준 JSON 문자열(또는 리스트)을 리스트로 정규화한다."""
    if isinstance(raw, str):
        try:
            captures = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise PipelineError("capture", f"반환된 JSON을 읽을 수 없습니다: {exc}") from exc
    elif isinstance(raw, list):
        captures = raw
    else:
        raise PipelineError("capture", f"예상치 못한 반환 타입: {type(raw).__name__}")

    if not captures:
        # 파일이 없거나 열지 못하면 캡처 모듈이 "[]" 를 반환한다.
        raise PipelineError(
            "capture",
            "캡처 결과가 비어 있습니다. 영상 경로가 맞는지, 파일이 열리는지 확인하세요.",
        )

    return captures


def collect_image_paths(captures, max_images):
    """캡처 목록에서 Qwen에 넘길 이미지 경로를 고른다.

    같은 경로가 반복되면 한 장으로 합친다. opencv_json1.py 는 첫 프레임 한 장만
    저장하고 모든 캡처가 그 경로를 가리키는 상태라, 중복을 걸러내지 않으면
    같은 이미지를 수십 장 보내게 된다.
    """
    unique = []
    missing = 0
    for item in captures:
        path = item.get("image_path")
        if not path or path in unique:
            continue
        if not Path(path).exists():
            missing += 1
            continue
        unique.append(path)

    if missing:
        log("3/4 opencv", f"경고: 경로는 있는데 실제 파일이 없는 캡처 {missing}건을 건너뜁니다.")

    if not unique:
        log("3/4 opencv", "경고: 넘길 이미지가 하나도 없습니다. 이미지 없이 진행합니다.")
        return []

    if len(unique) == 1 and len(captures) > 1:
        log("3/4 opencv",
            f"경고: 캡처 {len(captures)}건이 전부 같은 이미지({unique[0]})를 가리킵니다. "
            "캡처 모듈이 시점별로 별개 파일을 저장하는지 확인하세요.")

    if len(unique) > max_images:
        # 앞뒤로 치우치지 않게 고르게 솎아낸다.
        step = len(unique) / max_images
        picked = [unique[int(i * step)] for i in range(max_images)]
        log("3/4 opencv", f"이미지 {len(unique)}장 중 {max_images}장만 균등 추출")
        return picked

    log("3/4 opencv", f"이미지 {len(unique)}장을 Qwen에 넘깁니다")
    return unique


# ---------------------------------------------------------------------------
# 4단계 - 교차 검증 및 노트 생성 (qwen_pipeline.py)
# ---------------------------------------------------------------------------

def stage_note(whisper_data, image_paths, prompt_type, custom_prompt=None):
    """Whisper 텍스트와 캡처 이미지를 Qwen에 함께 넘겨 최종 노트를 만든다."""
    try:
        # torch / transformers 로딩이 무거워서 파일 맨 위가 아니라 여기서 import한다.
        # 위에서 하면 --help 만 쳐도, 1단계에서 실패해도 로딩이 먼저 일어난다.
        from qwen_pipeline import QwenLectureAnalyzer, run_qwen_pipeline
    except ImportError as exc:
        raise StageNotReadyError(
            "note",
            f"qwen_pipeline.py 를 불러올 수 없습니다: {exc}\n"
            "        torch / transformers / bitsandbytes 설치 상태를 확인하세요.",
        ) from exc

    label = "직접 작성한 프롬프트" if custom_prompt else prompt_type
    log("4/4 qwen", f"모델 로딩 시작 (프롬프트={label}, 이미지={len(image_paths)}장)")

    try:
        analyzer = QwenLectureAnalyzer()
        result = run_qwen_pipeline(
            analyzer=analyzer,
            whisper_data=whisper_data,
            prompt_type=prompt_type,
            custom_prompt=custom_prompt,
            image_paths=image_paths,
        )
    except FileNotFoundError as exc:
        raise PipelineError("note", f"이미지 파일 문제: {exc}") from exc
    except Exception as exc:
        raise PipelineError("note", f"노트 생성 중 오류: {exc}") from exc

    log("4/4 qwen", "완료")
    return result


# ---------------------------------------------------------------------------
# 전체 흐름
# ---------------------------------------------------------------------------

def run_pipeline(
    file_path,
    prompt_type="lecture_summary",
    custom_prompt=None,
    low_confidence_timestamps=None,
    max_images=DEFAULT_MAX_IMAGES,
    allow_gui=False,
    skip_stages=None,
):
    """강의 영상 하나를 받아 최종 노트까지 만들고 결과 dict를 반환한다."""
    skip = set(skip_stages or [])
    started_at = datetime.now()

    # 1단계 - 입력 분리
    media = stage_media(file_path)

    # 2단계 - 음성 인식
    if "transcribe" in skip:
        log("2/4 whisper", "건너뜀 (--skip-stage transcribe)")
        whisper_data = empty_whisper_data("음성 인식 단계를 건너뛰었습니다")
    else:
        whisper_data = stage_transcribe(media["audio_path"])

    # 3단계에 넘길 타겟 시각을 정한다.
    # --low-confidence-json 으로 직접 준 값이 있으면 그것이 우선이고,
    # 없으면 2단계가 뽑아낸 확신도 낮은 구간을 그대로 쓴다.
    targets = low_confidence_timestamps
    if targets is None:
        targets = whisper_data.get("low_confidence_timestamps", [])

    # 3단계 - 슬라이드 캡처 (영상일 때만)
    captures = []
    image_paths = []
    if media["video_path"] is None:
        log("3/4 opencv", "오디오 입력이라 캡처할 영상이 없습니다.")
    elif "capture" in skip:
        log("3/4 opencv", "건너뜀 (--skip-stage capture)")
    else:
        captures = stage_capture(media["video_path"], targets, allow_gui=allow_gui)
        image_paths = collect_image_paths(captures, max_images)

    # 4단계 - 교차 검증 및 노트 생성
    if "note" in skip:
        log("4/4 qwen", "건너뜀 (--skip-stage note)")
        note_result = {}
    else:
        note_result = stage_note(whisper_data, image_paths, prompt_type, custom_prompt)

    elapsed = (datetime.now() - started_at).total_seconds()
    return {
        "input_file": file_path,
        "media_type": media["media_type"],
        "audio_path": media["audio_path"],
        "video_path": media["video_path"],
        "transcript": whisper_data["transcript"],
        "segments": whisper_data["segments"],
        "low_confidence_words": whisper_data["low_confidence_words"],
        "captures": captures,
        "images_sent_to_qwen": image_paths,
        "note": note_result,
        "skipped_stages": sorted(skip),
        "elapsed_sec": round(elapsed, 1),
        "created_at": started_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# 명령줄 실행
# ---------------------------------------------------------------------------

def load_low_confidence_timestamps(path):
    """확신도 낮은 시각 목록을 JSON 파일에서 읽는다. 없으면 None(=2단계 결과 사용)."""
    if not path:
        return None

    data = json.loads(Path(path).read_text(encoding="utf-8"))

    # {"low_confidence_timestamps": [...]} 와 [12.5, 30.0] 와
    # [{"start": 12.5, ...}] 세 가지 형태를 모두 받아준다.
    if isinstance(data, dict):
        data = data.get("low_confidence_timestamps", [])
    if data and isinstance(data[0], dict):
        return [float(item["start"]) for item in data if "start" in item]
    return [float(x) for x in data]


def build_parser():
    parser = argparse.ArgumentParser(
        description="강의 영상 → 슬라이드 캡처 + 음성 인식 → 교차 검증 강의노트",
    )
    parser.add_argument("input", help="강의 영상 또는 오디오 파일 경로")
    parser.add_argument(
        "--prompt-type",
        default="lecture_summary",
        choices=PROMPT_TYPES,
        help="Qwen에 쓸 프롬프트 종류 (기본: lecture_summary)",
    )
    parser.add_argument(
        "--custom-prompt-file",
        help="직접 작성한 프롬프트 TXT 파일. 주면 --prompt-type 은 무시된다",
    )
    parser.add_argument("--out", help="결과 JSON 저장 경로 (생략하면 자동 생성)")
    parser.add_argument(
        "--max-images",
        type=int,
        default=DEFAULT_MAX_IMAGES,
        help=f"Qwen에 넘길 이미지 최대 장수 (기본: {DEFAULT_MAX_IMAGES})",
    )
    parser.add_argument(
        "--low-confidence-json",
        help="확신도 낮은 시각 목록 JSON. 생략하면 2단계 결과를 그대로 쓴다",
    )
    parser.add_argument(
        "--allow-gui",
        action="store_true",
        help="캡처 모듈이 창을 띄워도 진행 (로컬 확인용)",
    )
    parser.add_argument(
        "--skip-stage",
        action="append",
        default=[],
        choices=SKIPPABLE_STAGES,
        help="건너뛸 단계. 여러 번 쓸 수 있음 (예: --skip-stage transcribe)",
    )
    return parser


def main():
    # 윈도우 기본 인코딩(cp949)은 일부 기호를 표현하지 못한다. 화면에 그냥 찍을
    # 때는 괜찮지만 `python main.py ... > log.txt` 처럼 파일이나 파이프로 넘기면
    # UnicodeEncodeError로 죽는다. 출력을 UTF-8로 고정해 그 사고를 막는다.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    args = build_parser().parse_args()

    try:
        custom_prompt = None
        if args.custom_prompt_file:
            custom_prompt = Path(args.custom_prompt_file).read_text(encoding="utf-8")

        targets = load_low_confidence_timestamps(args.low_confidence_json)

        result = run_pipeline(
            file_path=args.input,
            prompt_type=args.prompt_type,
            custom_prompt=custom_prompt,
            low_confidence_timestamps=targets,
            max_images=args.max_images,
            allow_gui=args.allow_gui,
            skip_stages=args.skip_stage,
        )
    except StageNotReadyError as exc:
        print(f"\n아직 준비되지 않은 단계입니다.\n  {exc}", file=sys.stderr)
        return 2
    except PipelineError as exc:
        print(f"\n파이프라인 실패.\n  {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"\n파일을 찾을 수 없습니다.\n  {exc}", file=sys.stderr)
        return 1

    out_path = Path(args.out) if args.out else Path(
        f"pipeline_result_{datetime.now():%Y%m%d_%H%M%S}.json"
    )
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n완료 - {result['elapsed_sec']}초")
    print(f"결과 저장: {out_path}")
    if result["skipped_stages"]:
        print(f"건너뛴 단계: {', '.join(result['skipped_stages'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
