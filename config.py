import os

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN", "8466010858:AAEN7z_DZjD4x-9VuHn9f6pJgFpKX1Kbt4Q")

# API
API_HOST = "0.0.0.0"
API_PORT = int(os.getenv("PORT", 8000))  # Railway даёт свой порт
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

# Client JAR URL
CLIENT_JAR_URL = os.getenv("CLIENT_JAR_URL", "https://github.com/arsenrachkov-blip/matirx-files/releases/download/v1.0/thunderhack-1.7.jar")

# Loader Update
LOADER_VERSION = "1.0.0"
LOADER_DOWNLOAD_URL = os.getenv("LOADER_DOWNLOAD_URL", "https://your-cloud-storage.com/MatrixLoader.exe")
LOADER_CHANGELOG = "Исправления и улучшения"

# Database
DATABASE_PATH = "delta.db"
