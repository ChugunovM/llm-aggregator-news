#!/bin/bash
# setup.sh

echo "🚀 News Aggregator - установка"

# 1. Проверка зависимостей
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker и повторите."
    exit 1
fi

if ! command -v ollama &> /dev/null; then
    echo "⚠️ Ollama не найден. Установите вручную https://ollama.com"
    echo "Затем выполните: ollama pull mistral:7b-instruct-q4_K_M"
fi

# 2. Копирование .env
if [ ! -f .env ]; then
    cp .env.example .env
    echo "📝 Создан файл .env. Отредактируйте его перед запуском!"
    echo "Обязательно укажите TELEGRAM_API_ID/HASH и OLLAMA_HOST"
fi

# 3. Запуск
echo "🐳 Запуск сервисов..."
docker-compose up --build d

echo ""
echo "✅ Установка завершена!"
echo "API: http://localhost:8000"
echo "UI:  http://localhost:8502"
echo "Отсановка: docker-compose down"