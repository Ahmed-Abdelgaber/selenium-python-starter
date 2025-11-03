FROM python:3.11-slim AS base

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies for Chrome + Selenium (Lambda-safe)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      # base
      wget \
      curl \
      ca-certificates \
      gnupg \
      unzip \
      # chromium deps
      chromium \
      chromium-driver \
      fonts-liberation \
      fonts-noto-core \
      fonts-noto-cjk \
      fonts-noto-color-emoji \
      libasound2 \
      libatk-bridge2.0-0 \
      libatspi2.0-0 \
      libcairo2 \
      libdbus-1-3 \
      libdrm2 \
      libgbm1 \
      libglib2.0-0 \
      libgtk-3-0 \
      libnss3 \
      libpango-1.0-0 \
      libx11-6 \
      libx11-xcb1 \
      libxcomposite1 \
      libxcursor1 \
      libxdamage1 \
      libxkbcommon0 \
      libxrandr2 \
      libxshmfence1 \
      libxi6 \
      libxtst6 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Runtime env for Chrome and Selenium in Lambda
ENV PYTHONPATH=/app \
    BROWSER=chromium \
    CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver \
    SELENIUM_MANAGER_DISABLE=1 \
    HEADLESS=true \
    # keep Chrome state under /tmp to avoid permission issues
    CHROME_TMP_BASE=/tmp/chrome \
    XDG_RUNTIME_DIR=/tmp

# Pre-create chrome temp dirs to avoid first-run races
RUN mkdir -p /tmp/chrome/data-path /tmp/chrome/cache /tmp/chrome/user-data

CMD ["python", "-m", "awslambdaric", "src.lambda_handler.handler"]
