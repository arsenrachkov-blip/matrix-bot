import asyncio
import threading
import uvicorn

from bot import main as run_bot
from api import app
from config import API_HOST, API_PORT

def run_api():
    uvicorn.run(app, host=API_HOST, port=API_PORT)

if __name__ == "__main__":
    # Запускаем API в отдельном потоке
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    
    # Запускаем бота в основном потоке
    run_bot()
