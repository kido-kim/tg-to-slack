#!/usr/bin/env python3
"""
Helper script to create Telegram session file.
Run this locally to authenticate and generate the session file.
"""

import os
import base64
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv()

API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')

if not API_ID or not API_HASH:
    print("❌ Please set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env file")
    exit(1)

async def create_session():
    """Create Telegram session file."""
    client = TelegramClient('tg_session', API_ID, API_HASH)
    
    print("🔐 Starting Telegram authentication...")
    print("You will receive a code on your Telegram app.")
    
    await client.start()
    
    print("✅ Successfully authenticated!")
    print("📁 Session file created: tg_session.session")
    
    # Read session file and encode to base64
    with open('tg_session.session', 'rb') as f:
        session_data = f.read()
        session_b64 = base64.b64encode(session_data).decode('utf-8')
    
    print("\n" + "="*60)
    print("📋 Add this to your GitHub Secrets as TELEGRAM_SESSION:")
    print("="*60)
    print(session_b64)
    print("="*60)
    
    await client.disconnect()

if __name__ == '__main__':
    import asyncio
    asyncio.run(create_session())
