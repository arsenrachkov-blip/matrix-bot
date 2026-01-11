import aiosqlite
from datetime import datetime
from config import DATABASE_PATH

async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                hwid TEXT,
                subscription_end DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        await db.commit()

async def create_user(telegram_id: int, username: str, password_hash: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            'INSERT INTO users (telegram_id, username, password_hash) VALUES (?, ?, ?)',
            (telegram_id, username, password_hash)
        )
        await db.commit()

async def get_user_by_username(username: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ) as cursor:
            return await cursor.fetchone()

async def get_user_by_telegram_id(telegram_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            'SELECT * FROM users WHERE telegram_id = ?', (telegram_id,)
        ) as cursor:
            return await cursor.fetchone()

async def update_hwid(username: str, hwid: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            'UPDATE users SET hwid = ? WHERE username = ?',
            (hwid, username)
        )
        await db.commit()

async def reset_hwid(username: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            'UPDATE users SET hwid = NULL WHERE username = ?',
            (username,)
        )
        await db.commit()

async def set_subscription(username: str, end_date: datetime):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            'UPDATE users SET subscription_end = ? WHERE username = ?',
            (end_date.isoformat(), username)
        )
        await db.commit()

async def check_subscription(username: str) -> bool:
    user = await get_user_by_username(username)
    if not user or not user['subscription_end']:
        return False
    end_date = datetime.fromisoformat(user['subscription_end'])
    return datetime.now() < end_date

async def get_all_users():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM users ORDER BY id DESC') as cursor:
            return await cursor.fetchall()

async def ban_user(username: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            'UPDATE users SET is_active = 0 WHERE username = ?',
            (username,)
        )
        await db.commit()
