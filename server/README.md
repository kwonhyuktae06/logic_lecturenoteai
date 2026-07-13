## 시작하기
1. git clone ...
2. cd server
3. python3 -m venv venv
4. source venv/bin/activate
5. pip install -r requirements.txt
6. cp .env.example .env   ← .env 복사 후 값 채우기
7. uvicorn app.main:app --reload

## server/app/api/v1/upload.py
## 프론트에서 오는 HTTP 요청을 받는 곳

## server/app/core/config.py
## 환경변수 설정

## server/app/core/database.py
## DB 연결

## server/app/models/upload.py
## DB 테이블 구조 

## server/app/schemas/upload.py
## 비즈니스 로직

## server/requirements.txt
## 필요한 패키지 목록