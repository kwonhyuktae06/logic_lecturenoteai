import os 
# 환경 변수 설정을 위해 사용하는 모듈 
# bitsandbytes가 아직 CUDA 13.2 버전을 제대로 지원하지 못하기 때문에, CUDA 13.0 버젼으로 강제 설정
os.environ.setdefault("BNB_CUDA_VERSION","130") 
# 환경 변수(운영체제) 설정을 통해 bitsandbytes가 CUDA 13.0 버전을 사용하도록 강제

import json 
# JSON 데이터 입출력 처리

from dataclasses import dataclass, asdict 
# 데이터 클래스 정의 및 객체를 딕셔너리로 변환

from typing import List, Optional, Dict, Any 
# 타입 힌트 정의 (리스트, 딕셔너리, 선택적 값 등)

import torch
# PyTorch 라이브러리 -> 딥러닝 모델 로딩 및 추론에 사용

from PIL import Image 
# 이미지 처리 및 로딩을 위한 Pillow 라이브러리

from transformers import AutoProcessor, AutoModelForImageTextToText 
# Hugging Face Transformers 라이브러리 -> 모델 로딩 및 전처리

from transformers import BitsAndBytesConfig 
# 4bit 양자화를 위한 객체 추가 -> 원본 ai의 모든 parameter를 메모리에 다 넣지 못하기 때문

# 🚨 [7/6 오류 수정 완료] 상단 import 구문 사이사이에 있던 복사 오류 원인인 말줄임표(...)를 모두 제거하였습니다.


@dataclass 
class PipelineConfig:
    qwen_model_name: str = "Qwen/Qwen3-VL-8B-Instruct"
    max_new_tokens: int = 2048 #최대 토큰 생성 한도
    temperature: float = 0.7 #답변의 창의성 정도를 조절하는 hyperparameter
    top_p: float = 0.8 #정답 생성 시 확률분포의 합이 0.8 이상인 토큰만 출력
    do_sample: bool = True #다양한 정답을 채택하기 위해 무작위로 다음 토큰을 뽑음


@dataclass
class PipelineInput:
    audio_file: str
    whisper_text: str
    lecture_images: List[str]
    task_instruction: str


@dataclass
class PipelineOutput:
    audio_file: str
    lecture_images: List[str]
    whisper_text: str
    qwen_summary: str
    output_type: str


class WhisperMockRunner:
    def run(self, audio_file: str) -> str:
        whisper_text = (
            "오늘 강의에서는 운영체제의 프로세스와 스레드에 대해 설명합니다. "
            "프로세스는 실행 중인 프로그램이고, 스레드는 프로세스 안에서 실행되는 작업 단위입니다."
        )
        return whisper_text


class Qwen3VLRunner:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.processor = AutoProcessor.from_pretrained(config.qwen_model_name)
        #4bit 양자화를 위한 객체 생성
        quant_config = BitsAndBytesConfig( 
            load_in_4bit=True,                      # 4비트로 양자화
            bnb_4bit_compute_dtype=torch.float16,   # 계산은 16비트로 수행
            bnb_4bit_quant_type="nf4",              # 양자화 방식 (일반적으로 nf4 권장)
            bnb_4bit_use_double_quant=True,         # 이중 양자화로 메모리 추가 절약
            llm_int8_enable_fp32_cpu_offload=True   # CPU 오프로딩 활성화 (GPU 메모리 부족 시에만 CPU로 연산)
        )

        self.model = AutoModelForImageTextToText.from_pretrained(
            config.qwen_model_name,
            quantization_config=quant_config, #모델의 양자화 설정 -> quant_config 양자화 객체 대입
            torch_dtype="auto",
            device_map="auto"
        )

    def load_images(self, image_paths: List[str]) -> List[Image.Image]:
        images = []
        for image_path in image_paths:
            image = Image.open(image_path).convert("RGB")
            images.append(image)
        return images

    def build_messages(self, pipeline_input: PipelineInput) -> List[Dict[str, Any]]:
        content = []

        # 기존 코드의 ValueError 유발 로직을 해결.
        # "image": image_path 로 단순히 문자열 파일명을 넘겨서 컴퓨터가 이미지를 인식하지 못했었음.
        # 아래 run 메서드에서 로드한 '이미지 객체 리스트(loaded_images)'를 순서대로 매핑하도록 연동 구조를 맞춤.
        loaded_images = self.load_images(pipeline_input.lecture_images)
        for img in loaded_images:
            content.append({
                "type": "image",
                "image": img  # 파일 이름 글자가 아니라, 실제 PIL 이미지 객체가 직접 들어감.
            })

        content.append({
            "type": "text",
            "text": (
                f"다음은 강의 음성과 강의자료를 함께 분석하는 작업입니다.\n\n"
                f"[Whisper 음성 인식 결과]\n"
                f"{pipeline_input.whisper_text}\n\n"
                f"[수행할 작업]\n"
                f"{pipeline_input.task_instruction}\n\n"
                f"아래 형식으로 정리해 주세요.\n"
                f"1. 강의 전체 요약\n"
                f"2. 강의자료 이미지에서 확인한 핵심 내용\n"
                f"3. 음성 텍스트에서 확인한 핵심 내용\n"
                f"4. 강의자료와 음성 텍스트의 공통 내용\n"
                f"5. 음성 텍스트에서 누락되었을 가능성이 있는 내용\n"
                f"6. 핵심 키워드"
            )
        })

        messages = [
            {
                "role": "system",
                "content": "You are an assistant that summarizes lectures using both audio transcription and lecture images."
            },
            {
                "role": "user",
                "content": content
            }
        ]
        return messages

    def run(self, pipeline_input: PipelineInput) -> str:
        # build_messages 내부에서 이미지를 정상 로드하여 구조를 짤 수 있도록 수정.
        messages = self.build_messages(pipeline_input)

        text = self.processor.apply_chat_template(
            messages,
            tokenize=False, 
            add_generation_prompt=True
        )

        images = self.load_images(pipeline_input.lecture_images)

        inputs = self.processor(
            text=[text],
            images=images,
            return_tensors="pt"
        ).to(self.model.device)

        with torch.no_grad():
            generated_ids = self.model.generate(
                **inputs,
                max_new_tokens=self.config.max_new_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                do_sample=self.config.do_sample
            )

        generated_ids = [
            output_ids[len(input_ids):]
            for input_ids, output_ids in zip(inputs.input_ids, generated_ids)
        ]

        answer = self.processor.batch_decode(
            generated_ids,
            skip_special_tokens=True
        )[0]

        return answer


def save_result(result: PipelineOutput, file_path: str = "lecture_pipeline_result.json") -> None:
    result_dict = asdict(result)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(result_dict, f, ensure_ascii=False, indent=4)


def print_result(result: PipelineOutput) -> None:
    print("=" * 60)
    print("[입력 음성 파일]")
    print(result.audio_file)

    print("\n[입력 강의자료 이미지]")
    for image in result.lecture_images:
        print(image)

    print("\n[Whisper 음성 텍스트 결과]")
    print(result.whisper_text)

    print("\n[Qwen3-VL 강의 정리 결과]")
    print(result.qwen_summary)
    print("=" * 60)


# 기존에 유실되어 작동하지 않던 메인 실행부 전체를 정상 구현.
def main():
    config = PipelineConfig() #config 객체 생성
    audio_file = "lecture_audio.wav"
    lecture_images = [
        "lecture_slide_1.png",
        "lecture_slide_2.png"
    ]

    task_instruction = (
        "강의자료 이미지와 음성 인식 텍스트를 함께 분석해서 "
        "강의 내용을 보기 쉽게 요약하고 핵심 키워드를 정리해 주세요."
    )

    whisper_runner = WhisperMockRunner()
    whisper_text = whisper_runner.run(audio_file)

    pipeline_input = PipelineInput(
        audio_file=audio_file,
        whisper_text=whisper_text,
        lecture_images=lecture_images,
        task_instruction=task_instruction
    )

    qwen_runner = Qwen3VLRunner(config) #객체 생성 -> self로 호출되고 사용됨
    qwen_summary = qwen_runner.run(pipeline_input)

    result = PipelineOutput(
        audio_file=audio_file,
        lecture_images=lecture_images,
        whisper_text=whisper_text,
        qwen_summary=qwen_summary,
        output_type="text"
    )

    print_result(result)
    save_result(result)


if __name__ == "__main__":
    main() #main함수가 없어서 아무 실행결과가 안나왔었음. 
