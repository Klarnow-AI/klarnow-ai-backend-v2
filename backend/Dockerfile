# Backend API only; frontend is built/deployed separately (e.g. frontend/Dockerfile).
# Build with: docker build -f backend/Dockerfile backend
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
# Install backend deps from the backend project root.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
