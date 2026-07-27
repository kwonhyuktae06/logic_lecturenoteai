"""
담당자: 모까옹
담당 파트: Qwen AI

기능:
1. Whisper가 변환한 음성 텍스트 입력
2. Whisper의 낮은 확신도 단어 및 타임스탬프 입력
3. 강의자료 이미지 입력
4. Qwen3-VL-8B-Instruct를 이용한 강의 내용 정리
5. 프롬프트 양식 변경
6. UUID 기반 파이프라인 결과 생성
7. DB에 저장하기 쉬운 JSON 결과 생성

26.07.27 feedback & fix
작성자: 한동희
1. 각 라이브러리, 클래스, 함수의 기능을 한줄로 간단명료하게 작성해주셔야 합니다.
2. ai에게 프롬프트를 학습시킬때는 한국어보다는 영어가 정확도가 높습니다. 다음부터는 영어로 작성해주세요.
3. 기존 코드랑 새로 만든 코드가 너무 다릅니다. 수정할 부분이 많았던 것을 감안해도 아예 코드의 설계 방식 자체가 달라져서
기존 코드에서 수정했던 내용을 다시 여기다가 또 적용해야되는 번거로움이 있습니다. 
다음부터는 기존파일 내용을 수정하고 기존파일의 수정본을 보내주세요.
"""

import argparse
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import torch
from transformers import AutoProcessor, Qwen3VLForConditionalGeneration


MODEL_NAME = "Qwen/Qwen3-VL-8B-Instruct" #ai 모델명 지정

PROMPT_TEMPLATES = { #ai에게 강의정리 관련 프롬프트 학습. → 작성 시 영어로!
    "lecture_summary": """
당신은 대학 강의 내용을 정리하는 AI입니다.
아래 내용은 Whisper STT 모델이 음성을 텍스트로 변환한 결과입니다.

[강의 텍스트]
{transcript}

[Whisper 확신도가 낮은 단어]
{low_confidence_words}

다음 형식으로 강의 내용을 정리하세요.

1. 강의 제목
2. 핵심 내용 요약
3. 주요 개념
4. 중요한 용어와 설명
5. 시험에 나올 가능성이 높은 내용
6. 복습 문제 3개
7. Whisper 인식 오류로 의심되는 부분

Whisper 확신도가 낮은 단어가 있다면 문맥에 맞는 단어를 추정하되,
확실하지 않은 내용은 임의로 단정하지 말고 '확인 필요'라고 표시하세요.
""",
    "short_summary": """
다음 강의 내용을 짧고 이해하기 쉽게 요약하세요.

[강의 텍스트]
{transcript}

다음 형식을 사용하세요.

- 강의 주제
- 핵심 내용 5줄
- 핵심 키워드
- 한 줄 요약
""",
    "detailed_notes": """
다음 강의 내용을 학생이 복습하기 좋은 필기 형식으로 정리하세요.

[강의 텍스트]
{transcript}

[확신도가 낮은 단어]
{low_confidence_words}

다음 항목을 포함하세요.

1. 전체 강의 흐름
2. 단원별 상세 설명
3. 교수자가 강조한 것으로 보이는 내용
4. 개념 사이의 관계
5. 예시
6. 주의할 점
7. 추가로 공부해야 할 부분
""",
    "quiz": """
아래 강의 내용을 기준으로 학습 문제를 만드세요.

[강의 텍스트]
{transcript}

다음 형식으로 작성하세요.

1. 객관식 문제 5개
2. 단답형 문제 3개
3. 서술형 문제 2개
4. 모든 문제의 정답
5. 정답에 대한 간단한 해설
""",
    "error_check": """
다음 내용은 Whisper가 음성에서 변환한 텍스트입니다.

[전체 텍스트]
{transcript}

[확신도가 낮은 단어 및 타임스탬프]
{low_confidence_words}

문맥을 분석하여 다음 내용을 출력하세요.

1. 인식 오류로 의심되는 단어
2. 원래 단어로 예상되는 후보
3. 해당 단어가 포함된 문장
4. 오류라고 판단한 이유
5. 사람이 직접 확인해야 하는 타임스탬프

확실하지 않은 경우에는 반드시 '확인 필요'라고 표시하세요.
"""
}


class QwenLectureAnalyzer:
    def __init__(self, model_name: str = MODEL_NAME): #객체 default값 설정
        self.model_name = model_name

        print(f"[Qwen] 모델을 불러오는 중입니다: {model_name}")

        self.model = Qwen3VLForConditionalGeneration.from_pretrained(
            model_name,
            torch_dtype="auto",
            device_map="auto"
        )

        self.processor = AutoProcessor.from_pretrained(model_name)

        print("[Qwen] 모델 로딩이 완료되었습니다.")

    @staticmethod
    def format_low_confidence_words(
        words: Optional[List[Dict[str, Any]]]
    ) -> str:
        if not words:
            return "낮은 확신도 단어 없음"

        formatted_words = []

        for word_info in words:
            word = word_info.get("word", "알 수 없음")
            start = word_info.get("start", "알 수 없음")
            end = word_info.get("end", "알 수 없음")
            score = word_info.get(
                "confidence",
                word_info.get(
                    "probability",
                    word_info.get("logprob", "알 수 없음")
                )
            )

            formatted_words.append(
                f"- 단어: {word}, 시작: {start}초, "
                f"종료: {end}초, 확신도: {score}"
            )

        return "\n".join(formatted_words)

    def create_prompt(
        self,
        transcript: str,
        low_confidence_words: Optional[List[Dict[str, Any]]] = None,
        prompt_type: str = "lecture_summary",
        custom_prompt: Optional[str] = None
    ) -> str:
        if not transcript or not transcript.strip():
            raise ValueError("Whisper 변환 텍스트가 비어 있습니다.")

        formatted_words = self.format_low_confidence_words(
            low_confidence_words
        )

        if custom_prompt:
            selected_prompt = custom_prompt
        else:
            if prompt_type not in PROMPT_TEMPLATES:
                available = ", ".join(PROMPT_TEMPLATES.keys())
                raise ValueError(
                    f"지원하지 않는 프롬프트입니다: {prompt_type}\n"
                    f"사용 가능한 프롬프트: {available}"
                )

            selected_prompt = PROMPT_TEMPLATES[prompt_type]

        try:
            return selected_prompt.format(
                transcript=transcript,
                low_confidence_words=formatted_words
            )
        except KeyError as error:
            raise ValueError(
                f"프롬프트 변수 이름이 잘못되었습니다: {error}\n"
                "사용 가능한 변수는 "
                "{transcript}, {low_confidence_words}입니다."
            ) from error

    @staticmethod
    def validate_image_paths(
        image_paths: Optional[List[str]]
    ) -> List[str]:
        if not image_paths:
            return []

        validated_paths = []

        for image_path in image_paths:
            path = Path(image_path).expanduser().resolve()

            if not path.exists():
                raise FileNotFoundError(
                    f"강의자료 이미지를 찾을 수 없습니다: {path}"
                )

            if path.suffix.lower() not in {
                ".jpg", ".jpeg", ".png", ".webp", ".bmp"
            }:
                raise ValueError(
                    f"지원하지 않는 이미지 형식입니다: {path.suffix}"
                )

            validated_paths.append(str(path))

        return validated_paths

    def analyze(
        self,
        transcript: str,
        low_confidence_words: Optional[List[Dict[str, Any]]] = None,
        image_paths: Optional[List[str]] = None,
        prompt_type: str = "lecture_summary",
        custom_prompt: Optional[str] = None,
        max_new_tokens: int = 1500
    ) -> str:
        prompt = self.create_prompt(
            transcript=transcript,
            low_confidence_words=low_confidence_words,
            prompt_type=prompt_type,
            custom_prompt=custom_prompt
        )

        validated_images = self.validate_image_paths(image_paths)
        content = []

        for image_path in validated_images:
            content.append({
                "type": "image",
                "image": image_path
            })

        content.append({
            "type": "text",
            "text": prompt
        })

        messages = [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "당신은 Whisper 음성 인식 결과와 "
                            "강의자료를 분석하는 한국어 강의 정리 AI입니다."
                        )
                    }
                ]
            },
            {
                "role": "user",
                "content": content
            }
        ]

        inputs = self.processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt"
        )

        inputs = inputs.to(self.model.device)

        with torch.inference_mode():
            generated_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False
            )

        generated_ids_trimmed = [
            output_ids[len(input_ids):]
            for input_ids, output_ids
            in zip(inputs.input_ids, generated_ids)
        ]

        output_text = self.processor.batch_decode(
            generated_ids_trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False
        )

        if not output_text:
            raise RuntimeError("Qwen 분석 결과가 생성되지 않았습니다.")

        return output_text[0].strip()


def load_whisper_json(file_path: str) -> Dict[str, Any]:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Whisper JSON 파일을 찾을 수 없습니다: {file_path}"
        )

    if path.suffix.lower() != ".json":
        raise ValueError(
            "잘못된 파일 형식입니다. JSON 파일을 입력해주세요."
        )

    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if "transcript" not in data and "text" not in data:
        raise ValueError(
            "Whisper JSON에 transcript 또는 text 항목이 없습니다."
        )

    return data


def create_pipeline_result(
    whisper_data: Dict[str, Any],
    qwen_result: str,
    prompt_type: str,
    image_paths: Optional[List[str]] = None
) -> Dict[str, Any]:
    upload_id = (
        whisper_data.get("upload_id")
        or whisper_data.get("uuid")
        or str(uuid.uuid4())
    )

    transcript = whisper_data.get(
        "transcript",
        whisper_data.get("text", "")
    )

    low_confidence_words = whisper_data.get(
        "low_confidence_words",
        whisper_data.get("uncertain_words", [])
    )

    return {
        "upload_id": upload_id,
        "pipeline_version": "1.0",
        "status": "completed",
        "created_at": datetime.now().isoformat(),
        "input": {
            "transcript": transcript,
            "language": whisper_data.get("language", "ko"),
            "audio_file_name": whisper_data.get("audio_file_name"),
            "low_confidence_words": low_confidence_words,
            "lecture_images": image_paths or []
        },
        "qwen": {
            "model": MODEL_NAME,
            "prompt_type": prompt_type,
            "analysis_result": qwen_result
        }
    }


def save_result_json(
    result: Dict[str, Any],
    output_directory: str = "qwen_results"
) -> str:
    os.makedirs(output_directory, exist_ok=True)

    upload_id = result["upload_id"]
    output_path = os.path.join(
        output_directory,
        f"{upload_id}_qwen_result.json"
    )

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=4
        )

    return output_path


def run_qwen_pipeline(
    analyzer: QwenLectureAnalyzer,
    whisper_data: Dict[str, Any],
    prompt_type: str = "lecture_summary",
    custom_prompt: Optional[str] = None,
    image_paths: Optional[List[str]] = None
) -> Dict[str, Any]:
    transcript = whisper_data.get(
        "transcript",
        whisper_data.get("text", "")
    )

    low_confidence_words = whisper_data.get(
        "low_confidence_words",
        whisper_data.get("uncertain_words", [])
    )

    qwen_result = analyzer.analyze(
        transcript=transcript,
        low_confidence_words=low_confidence_words,
        image_paths=image_paths,
        prompt_type=prompt_type,
        custom_prompt=custom_prompt
    )

    return create_pipeline_result(
        whisper_data=whisper_data,
        qwen_result=qwen_result,
        prompt_type=prompt_type,
        image_paths=image_paths
    )


def main():
    parser = argparse.ArgumentParser(
        description="Whisper 결과를 Qwen으로 정리하는 파이프라인"
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Whisper 결과 JSON 파일 경로"
    )

    parser.add_argument(
        "--prompt-type",
        default="lecture_summary",
        choices=list(PROMPT_TEMPLATES.keys()),
        help="Qwen 분석 프롬프트 종류"
    )

    parser.add_argument(
        "--custom-prompt-file",
        help="사용자가 직접 작성한 프롬프트 TXT 파일"
    )

    parser.add_argument(
        "--images",
        nargs="*",
        default=[],
        help="강의자료 이미지 경로"
    )

    parser.add_argument(
        "--output-dir",
        default="qwen_results",
        help="Qwen 결과 JSON 저장 폴더"
    )

    args = parser.parse_args()

    try:
        whisper_data = load_whisper_json(args.input)

        custom_prompt = None

        if args.custom_prompt_file:
            with open(
                args.custom_prompt_file,
                "r",
                encoding="utf-8"
            ) as file:
                custom_prompt = file.read()

        analyzer = QwenLectureAnalyzer()

        result = run_qwen_pipeline(
            analyzer=analyzer,
            whisper_data=whisper_data,
            prompt_type=args.prompt_type,
            custom_prompt=custom_prompt,
            image_paths=args.images
        )

        output_path = save_result_json(
            result=result,
            output_directory=args.output_dir
        )

        print("\n========== Qwen 분석 완료 ==========")
        print(result["qwen"]["analysis_result"])
        print("====================================")
        print(f"UUID: {result['upload_id']}")
        print(f"결과 파일: {output_path}")

    except Exception as error:
        print(f"[Qwen 오류] {error}")
        raise


if __name__ == "__main__":
    main()
