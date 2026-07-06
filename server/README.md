## 시작하기
1. git clone ...
2. cd server
3. python3 -m venv venv
4. source venv/bin/activate
5. pip install -r requirements.txt
6. cp .env.example .env   ← .env 복사 후 값 채우기
7. uvicorn app.main:app --reload