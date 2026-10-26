FROM python:3.10-slim

RUN python -m pip install --upgrade pip

RUN pip install "imdbinfo>=0.11.0" "fastapi" "uvicorn[standard]"

WORKDIR /app
COPY cinema_service.py /app/cinema_service.py

EXPOSE 5005
CMD ["uvicorn", "cinema_service:app", "--host", "0.0.0.0", "--port", "5005"]
