# Stage 1: Builder
FROM python:3.12-alpine AS builder

WORKDIR /build

# Install build dependencies (Alpine Linux uses apk, not apt-get)
RUN apk add --no-cache \
    gcc \
    musl-dev \
    linux-headers

# Copy requirements
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-alpine

WORKDIR /app

# Set timezone to Belarus (Europe/Minsk)
RUN apk add --no-cache tzdata && \
    cp /usr/share/zoneinfo/Europe/Minsk /etc/localtime && \
    echo "Europe/Minsk" > /etc/timezone

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Europe/Minsk

# Copy application code
COPY . .

# Run bot
CMD ["python", "-m", "src.main"]
