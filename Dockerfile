FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8010
ENV HOST=0.0.0.0

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY web ./web
COPY config ./config
COPY tests ./tests

EXPOSE 8010

CMD ["python", "app/scripts/run_viewer_api.py", "--host", "0.0.0.0"]
