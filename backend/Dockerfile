# Fixed bookworm so apt package names stay stable (same reason as material-audit).
FROM python:3.12-slim-bookworm

# ffmpeg + ffprobe are required for mock-sample video generation and LeRobot H.264 export.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/run.py ./run.py

# The process must listen on all interfaces inside the compose network.
# Host publishing is done only by the frontend/nginx service on 127.0.0.1:18090.
ENV OPENDF_HOST=0.0.0.0
ENV OPENDF_PORT=8000

EXPOSE 8000

CMD ["python", "run.py"]
