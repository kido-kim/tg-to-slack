#!/usr/bin/env python3
"""
Test script to fetch recent messages from the channel
"""

import os
from datetime import datetime, timedelta
import pytz
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
TELEGRAM_CHANNEL = os.getenv('TELEGRAM_CHANNEL', 'ahboyashreads')

async def test_fetch():
    """Fetch recent messages for testing"""
    client = TelegramClient('tg_session', TELEGRAM_API_ID, TELEGRAM_API_HASH)
    
    await client.start()
    print(f"✅ Connected to Telegram")
    
    try:
        entity = await client.get_entity(TELEGRAM_CHANNEL)
        print(f"✅ Found channel: {TELEGRAM_CHANNEL}")
        
        # Fetch last 10 messages
        messages = []
        async for message in client.iter_messages(entity, limit=10):
            if message.message:
                kst = pytz.timezone('Asia/Seoul')
                msg_date = message.date.replace(tzinfo=pytz.UTC).astimezone(kst)
                messages.append({
                    'id': message.id,
                    'date': msg_date,
                    'text': message.message[:100] + '...' if len(message.message) > 100 else message.message
                })
        
        print(f"\n📨 Found {len(messages)} recent messages:\n")
        for msg in messages:
            print(f"[{msg['date'].strftime('%Y-%m-%d %H:%M')}] Message {msg['id']}")
            print(f"   {msg['text']}\n")
        
        if not messages:
            print("⚠️  No messages found in this channel")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    import asyncio
    asyncio.run(test_fetch())
