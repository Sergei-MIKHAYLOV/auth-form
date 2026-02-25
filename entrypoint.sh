#!/bin/bash

export PYTHONPATH="/home/app:$PYTHONPATH"

# Ожидание запуска PostgreSQL
until pg_isready -h postgresDB -U "$DB_USER" -d "$DB_NAME"; do sleep 1; done

# Загрузка мок-данных в БД
python utils/csv_loader.py

# Запуск сервера для проверки orders_service
exec python -m uvicorn main:app --host 0.0.0.0 --port 8000 --loop asyncio
