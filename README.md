# Currency Rates API with WebSocket and NATS

## Описание
Асинхронный backend для получения и управления курсами валют с real-time уведомлениями через WebSocket и интеграцией с NATS.

## Требования
- Python 3.8+
- NATS сервер

## Установка и запуск

### 1. Установите зависимости:
```bash
pip install -r requirements.txt
```
### 2. Запустите NATS сервер:
```bash
nats-server -m 8222
```
### 3. Запустите приложение:
```bash
uvicorn main:app --reload --port 8000
```
