FROM python:3.13-slim
WORKDIR /app

# Установка зависимостей ОС
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Создание non-root пользователя
RUN useradd --create-home --shell /bin/bash app
USER app
WORKDIR /home/app

# Установка зависимостей python
COPY --chown=app:app requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY --chown=app:app . .

# Перевод entrypoint в исполняемый файл
RUN chmod +x entrypoint.sh

# Запуск БД -> загрузка мок-данных -> запуск uvicorn
ENTRYPOINT ["./entrypoint.sh"]