import os
import asyncpg
from dotenv import load_dotenv
import json

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

import ssl

_pool = None

async def get_db_pool():
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL is not set in environment variables.")
        
        # asyncpg doesn't like ssl=require in the connection string, we must pass it explicitly
        clean_url = DATABASE_URL.replace("?ssl=require", "")
        
        if "database.azure.com" in clean_url:
            ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            _pool = await asyncpg.create_pool(clean_url, ssl=ctx)
        else:
            _pool = await asyncpg.create_pool(clean_url)
    return _pool

async def init_db():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS analyses (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                resource_group VARCHAR(255) NOT NULL,
                resources_scanned INTEGER,
                issues_found INTEGER,
                estimated_savings VARCHAR(255),
                analysis_result JSONB,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
    print("Database tables initialized.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())
