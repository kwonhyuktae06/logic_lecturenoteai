import json
from transformers import pipeline

# 1. Whisper 모델 로드 (CPU 환경)
print("Calling Whisper models...")
pipe = pipeline(
    task="automatic-speech-recognition",
    model="openai/whisper-large-v3",
    device="cpu",
    chunk_length_s=30, #긴 오디오 30초씩 잘라서 처리하게 함.(메모리 부족 방지)
)
print("Whisper Model Load Successful\n")

# 2. 음성 인식 진행
audio_file = "test.mp3"  # 변환할 오디오 파일 경로
print(f"'{audio_file}' Converts the voice of the file to text,please wait.")
result = pipe(audio_file)

# 3. 결과 데이터 가공
output_data = {
    "source_audio": audio_file,
    "transcribed_text": result["text"],  # 변환된 텍스트 추출
}

# 4. JSON 파일로 저장 (한글 깨짐 방지 및 들여쓰기 적용)
json_filename = "whisper_output.json"
with open(json_filename, "w", encoding="utf-8") as f:
    json.dump(output_data, f, ensure_ascii=False, indent=4)

# 5. 최종 결과 출력
print("\n===============================")
print("Complete conversion and JSON storage.")
print(f"saved file name: {json_filename}")
print("converted content:")
print(result["text"])
print("===============================\n")
