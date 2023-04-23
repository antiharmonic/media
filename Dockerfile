FROM python:3.8


RUN apt update && apt install tzdata -y
RUN pip install pipenv
EXPOSE 5001
WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY Pipfile* ./
RUN pipenv install --system --deploy
COPY . .

ENV APP_CONFIG_FILE config.docker.ini
ENV FLASK_DEBUG 1
ENV TZ="America/Chicago"
cmd ["python", "media_app/__init__.py"]
