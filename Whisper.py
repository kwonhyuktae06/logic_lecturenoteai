import json
import whisper

# 1. Whisper 모델 로드
# openai-whisper 패키지 사용: transformers.pipeline과 달리 avg_logprob/no_speech_prob/
# compression_ratio가 segments에 기본으로 포함되어 나옴 (확신도 판단에 필요한 값들)
print("Calling Whisper models...")
model = whisper.load_model("large-v3")
print("Whisper Model Load Successful\n")

# 2. 저확신 판단 기준값 (Whisper 원본 transcribe.py의 기본값을 그대로 사용)
# 실제 한국어 강의 음성으로 값 분포를 확인한 뒤 재조정 필요
AVG_LOGPROB_THRESHOLD = -1.0        # 이보다 낮으면(더 음수면) 저확신
NO_SPEECH_THRESHOLD = 0.6           # 이보다 높으면 무음 구간 의심
COMPRESSION_RATIO_THRESHOLD = 2.4   # 이보다 높으면 반복(환각) 의심


def is_low_confidence(segment: dict) -> bool:
    # 세 지표 중 하나라도 기준을 넘으면 리뷰 대상으로 플래그.
    # 텍스트를 지우지 않고 표시만 하므로 넓게(OR) 잡아도 안전함.
    return (
        segment["avg_logprob"] < AVG_LOGPROB_THRESHOLD
        or segment["no_speech_prob"] > NO_SPEECH_THRESHOLD
        or segment["compression_ratio"] > COMPRESSION_RATIO_THRESHOLD
    )


# 3. 음성 인식 진행
audio_file = "test.mp3"  # 변환할 오디오 파일 경로
print(f"'{audio_file}' Converts the voice of the file to text,please wait.")
result = model.transcribe(audio_file, verbose=False)

# 4. 세그먼트별 확신도 정리
segments_data = []
low_confidence_count = 0
for segment in result["segments"]:
    flagged = is_low_confidence(segment)
    if flagged:
        low_confidence_count += 1
    segments_data.append({
        "start": round(segment["start"], 2),
        "end": round(segment["end"], 2),
        "text": segment["text"].strip(),
        "avg_logprob": round(float(segment["avg_logprob"]), 4),
        "no_speech_prob": round(float(segment["no_speech_prob"]), 4),
        "compression_ratio": round(float(segment["compression_ratio"]), 4),
        "low_confidence": flagged,  # 삭제 아님 - 리뷰용 표시만
    })

# 5. 저확신 구간 타임스탬프 목록
# opencv_json1.py의 generate_opencv_json_pipeline(video_path, low_confidence_timestamps)에
# 그대로 넘길 수 있는 형태(초 단위 float 리스트)로 준비해둠. 각 타임스탬프에 대응하는
# 확신도 점수(avg_logprob 등)는 위 segments_data 안에 이미 함께 저장되어 있음.
low_confidence_timestamps = [
    segment["start"] for segment in segments_data if segment["low_confidence"]
]

# 6. 결과 데이터 가공
output_data = {
    "source_audio": audio_file,
    "transcribed_text": result["text"],  # 변환된 텍스트 추출 (기존 필드 그대로 유지)
    "segments": segments_data,
    "low_confidence_segment_count": low_confidence_count,
    "low_confidence_timestamps": low_confidence_timestamps,
}

# 7. JSON 파일로 저장 (한글 깨짐 방지 및 들여쓰기 적용)
json_filename = "whisper_output.json"
with open(json_filename, "w", encoding="utf-8") as f:
    json.dump(output_data, f, ensure_ascii=False, indent=4)

# 8. 최종 결과 출력
print("\n===============================")
print("Complete conversion and JSON storage.")
print(f"saved file name: {json_filename}")
print(f"low-confidence segments: {low_confidence_count} / {len(segments_data)}")
print("converted content:")
print(result["text"])
print("===============================\n")
