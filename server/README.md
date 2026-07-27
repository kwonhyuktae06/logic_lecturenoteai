## 시작하기
1. git clone ...
2. cd server
3. python3 -m venv venv → 가상환경 생성
4. source venv/bin/activate → 가상환경 활성화(mac, Linux용)
5. pip install -r requirements.txt → 패키지 설치
6. cp .env.example .env   ← .env 복사 후 값 채우기
7. uvicorn app.main:app --reload
8. chrome → 127.0.0.1:8000(localhost) 접속
## 라이브러리 설치
1. pip install fastapi uvicorn[standard] python-multipart sqlalchemy pymysql pydantic pydantic-settings
