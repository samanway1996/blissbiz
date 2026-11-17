ARG PYTHON_IMAGE=python:3.13-slim
FROM ${PYTHON_IMAGE}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /opt/blissbiz/backend
COPY backend/requirements.lock backend/pyproject.toml ./
RUN python3 -m pip install --no-cache-dir -r requirements.lock
COPY backend/app ./app
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./
RUN python3 -m pip install --no-deps . && useradd --uid 10001 --create-home blissbiz \
    && mkdir -p /data/uploads && chown -R blissbiz:blissbiz /data/uploads
USER blissbiz
EXPOSE 8000
CMD ["python3", "-m", "uvicorn", "app.main:app", "--no-proxy-headers", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
