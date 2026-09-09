-- ================================================
-- Whisper + Qwen3-VL Lecture Pipeline Database Schema
-- ================================================

CREATE DATABASE IF NOT EXISTS lecture_pipeline_db;
USE lecture_pipeline_db;

-- ================================================
-- 1. 유저 테이블
-- ================================================
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- ================================================
-- 2. 강의 세션 테이블 (유저가 업로드한 작업 단위)
-- ================================================
CREATE TABLE lecture_sessions (
    session_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    lecture_title VARCHAR(255) NOT NULL,
    lecture_description TEXT,
    processing_status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- ================================================
-- 3. 비디오 파일 테이블 (원본 강의 영상)
-- ================================================
CREATE TABLE video_files (
    video_id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT,
    duration_seconds INT,
    format VARCHAR(50),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES lecture_sessions(session_id) ON DELETE CASCADE
);

-- ================================================
-- 4. 오디오 파일 테이블 (비디오에서 추출한 음성)
-- ================================================
CREATE TABLE audio_files (
    audio_id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    video_id INT,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT,
    duration_seconds INT,
    format VARCHAR(50),
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES lecture_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (video_id) REFERENCES video_files(video_id) ON DELETE SET NULL
);

-- ================================================
-- 5. 캡처 이미지 파일 테이블 (OpenCV 캡처 프레임)
-- ================================================
CREATE TABLE captured_images (
    image_id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    video_id INT,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT,
    width INT,
    height INT,
    format VARCHAR(50),
    capture_timestamp_seconds INT,
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES lecture_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (video_id) REFERENCES video_files(video_id) ON DELETE SET NULL
);

-- ================================================
-- 6. Whisper 음성인식 결과 테이블
-- ================================================
CREATE TABLE whisper_results (
    whisper_id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    audio_id INT,
    transcribed_text LONGTEXT NOT NULL,
    avg_logprob FLOAT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES lecture_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (audio_id) REFERENCES audio_files(audio_id) ON DELETE SET NULL
);

-- ================================================
-- 7. 매핑 데이터 테이블 (이미지-텍스트 타임라인 연결)
-- ================================================
CREATE TABLE mapped_data (
    mapping_id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    image_id INT,
    whisper_id INT,
    timestamp_seconds INT,
    image_text_relation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES lecture_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (image_id) REFERENCES captured_images(image_id) ON DELETE SET NULL,
    FOREIGN KEY (whisper_id) REFERENCES whisper_results(whisper_id) ON DELETE SET NULL
);

-- ================================================
-- 8. Qwen3-VL / Gemini 분석 결과 테이블 (최종 요약 노트)
-- ================================================
CREATE TABLE qwen_results (
    result_id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    whisper_id INT,
    lecture_summary LONGTEXT NOT NULL,
    key_content_from_images LONGTEXT,
    key_content_from_audio LONGTEXT,
    common_content LONGTEXT,
    potential_missing_content LONGTEXT,
    keywords TEXT,
    raw_output JSON,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES lecture_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (whisper_id) REFERENCES whisper_results(whisper_id) ON DELETE SET NULL
);

-- ================================================
-- 9. 처리 로그 테이블 (파이프라인 모니터링)
-- ================================================
CREATE TABLE processing_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    step_name VARCHAR(100),
    status ENUM('started', 'completed', 'failed') DEFAULT 'started',
    error_message TEXT,
    duration_seconds FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES lecture_sessions(session_id) ON DELETE CASCADE
);

-- ================================================
-- 10. 인덱스 생성 (성능 및 조회 속도 최적화)
-- ================================================
CREATE INDEX idx_user_id ON lecture_sessions(user_id);
CREATE INDEX idx_session_id_video ON video_files(session_id);
CREATE INDEX idx_session_id_audio ON audio_files(session_id);
CREATE INDEX idx_session_id_image ON captured_images(session_id);
CREATE INDEX idx_session_id_whisper ON whisper_results(session_id);
CREATE INDEX idx_session_id_mapped ON mapped_data(session_id);
CREATE INDEX idx_session_id_qwen ON qwen_results(session_id);
CREATE INDEX idx_session_status ON lecture_sessions(processing_status);
CREATE INDEX idx_created_at ON lecture_sessions(created_at);
