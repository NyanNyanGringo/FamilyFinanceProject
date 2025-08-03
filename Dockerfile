# syntax=docker/dockerfile:1.6

FROM python:3.11.6-slim

# Системные зависимости с кеш-mount, чтобы их обновление не инвалидировало слои
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        ffmpeg \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Переменные окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_HOME=/opt/poetry \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_NO_INTERACTION=1

# Poetry в отдельном venv
RUN python -m venv "$POETRY_HOME" \
    && "$POETRY_HOME/bin/pip" install --no-cache-dir poetry \
    && ln -s /opt/poetry/bin/poetry /usr/bin/poetry

# Файлы зависимостей
COPY pyproject.toml poetry.lock ./

# Установка зависимостей без пересборки пакета проекта
RUN poetry install --only=main --no-root

# Добавляем venv в PATH
ENV PATH="/app/.venv/bin:$PATH"

# Код приложения
COPY . .

# Скрипты и права
COPY docker/entrypoint.sh docker/healthcheck.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/healthcheck.sh

# Пользователь без root-прав
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN mkdir -p voice_messages && chown -R appuser:appuser /app
USER appuser

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["python", "run_server.py"]
