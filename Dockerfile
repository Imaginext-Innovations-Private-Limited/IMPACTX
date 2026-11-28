FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr espeak-ng ffmpeg libgl1 libglib2.0-0 libraqm0 libfribidi0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python scripts/fetch_voices.py || echo "neural voices not downloaded; espeak-ng will be used"
EXPOSE 8000
CMD ["uvicorn", "kk.api:app", "--host", "0.0.0.0", "--port", "8000"]
