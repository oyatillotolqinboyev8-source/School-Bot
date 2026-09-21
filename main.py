import os
import threading
import asyncio
from flask import Flask
import school

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot faol ishlamoqda!"

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Aiogram 3 da polling signal ishlovchilarisiz (handle_signals=False) ishga tushishi kerak
    try:
        loop.run_until_complete(school.dp.start_polling(school.bot, handle_signals=False))
    except Exception as e:
        print(f"Botda xatolik: {e}")

if __name__ == "__main__":
    # Botni alohida potokda ishga tushirish
    threading.Thread(target=run_bot, daemon=True).start()
    
    # Render beradigan PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)