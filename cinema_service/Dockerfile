FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends git \
  && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip

# Install cinemagoer + a tiny API server
RUN pip install "cinemagoer @ git+https://github.com/cinemagoer/cinemagoer" "fastapi" "uvicorn[standard]"

WORKDIR /app
COPY cinema_service.py /app/cinema_service.py

EXPOSE 5005
CMD ["uvicorn", "cinema_service:app", "--host", "0.0.0.0", "--port", "5005"]
