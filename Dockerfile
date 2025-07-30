# 베이스 이미지로 Python 3.9 슬림 버전을 사용합니다.
FROM python:3.9-slim

# 작업 디렉토리를 /app으로 설정합니다.
WORKDIR /app

# requirements.txt를 복사하고 의존성을 설치합니다.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드를 작업 디렉토리로 복사합니다.
COPY . .

# 앱이 실행될 포트를 7860으로 노출합니다.
EXPOSE 7860

# 컨테이너가 시작될 때 실행할 명령어를 설정합니다.
CMD ["python", "app.py"]