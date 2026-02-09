#!/usr/bin/env python3
"""
Telegram to Slack Daily Summary Bot
Fetches messages from Ahboyreads Telegram channel, summarizes them using Google Gemini,
and posts to Slack daily at 9 AM KST.
"""

import os
import sys
import base64
from datetime import datetime, timedelta
from typing import List, Dict
import pytz
from telethon import TelegramClient
from telethon.tl.types import Message
import google.generativeai as genai
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
TELEGRAM_CHANNEL = os.getenv('TELEGRAM_CHANNEL', 'Ahboyreads')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
TELEGRAM_SESSION_B64 = os.getenv('TELEGRAM_SESSION')

# Validate required environment variables
def validate_config():
    """Validate that all required environment variables are set."""
    required_vars = {
        'TELEGRAM_API_ID': TELEGRAM_API_ID,
        'TELEGRAM_API_HASH': TELEGRAM_API_HASH,
        'GEMINI_API_KEY': GEMINI_API_KEY,
        'SLACK_WEBHOOK_URL': SLACK_WEBHOOK_URL
    }
    
    missing = [var for var, value in required_vars.items() if not value]
    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)
    
    print("✅ All required environment variables are set")


def setup_session_file():
    """Setup Telegram session file from base64 encoded environment variable."""
    if TELEGRAM_SESSION_B64:
        try:
            session_data = base64.b64decode(TELEGRAM_SESSION_B64)
            with open('tg_session.session', 'wb') as f:
                f.write(session_data)
            print("✅ Telegram session file created from environment variable")
            return 'tg_session'
        except Exception as e:
            print(f"⚠️  Failed to decode session from environment: {e}")
            return 'tg_session'
    else:
        print("ℹ️  No session environment variable found, will create new session")
        return 'tg_session'


async def fetch_yesterday_messages(client: TelegramClient, channel: str) -> List[Dict]:
    """
    Fetch messages from the specified Telegram channel from yesterday.
    
    Args:
        client: Authenticated Telegram client
        channel: Channel username or ID
        
    Returns:
        List of message dictionaries with text, date, and link
    """
    # Calculate yesterday's date range in KST
    kst = pytz.timezone('Asia/Seoul')
    now_kst = datetime.now(kst)
    yesterday_start = (now_kst - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_end = yesterday_start.replace(hour=23, minute=59, second=59)
    
    print(f"📅 Fetching messages from {yesterday_start.strftime('%Y-%m-%d')} (KST)")
    
    messages = []
    try:
        # Get the channel entity
        entity = await client.get_entity(channel)
        
        # Fetch messages from yesterday
        async for message in client.iter_messages(
            entity,
            offset_date=yesterday_end,
            reverse=True
        ):
            # Convert message date to KST
            msg_date_kst = message.date.replace(tzinfo=pytz.UTC).astimezone(kst)
            
            # Check if message is from yesterday
            if msg_date_kst < yesterday_start:
                continue
            if msg_date_kst > yesterday_end:
                break
            
            # Extract text from message
            text = message.message or ""
            
            # If no text but has media with caption, use caption
            if not text and hasattr(message, 'media') and message.media:
                text = getattr(message, 'text', '') or ""
            
            # Skip empty messages
            if not text.strip():
                continue
            
            # Generate message link
            msg_link = f"https://t.me/{channel}/{message.id}"
            
            messages.append({
                'id': message.id,
                'text': text,
                'date': msg_date_kst,
                'link': msg_link
            })
        
        print(f"✅ Fetched {len(messages)} messages from yesterday")
        return messages
        
    except Exception as e:
        print(f"❌ Error fetching messages: {e}")
        return []


def summarize_with_gemini(text: str, api_key: str) -> str:
    """
    Summarize text using Google Gemini API.
    
    Args:
        text: Text to summarize
        api_key: Google Gemini API key
        
    Returns:
        Korean 3-line summary
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""다음은 암호화폐/크립토 산업 관련 뉴스입니다. 
이 내용을 한국어로 정확히 3줄로 요약해주세요. 
각 줄은 한 문장으로, 핵심 정보만 간결하게 담아주세요.
번호나 불릿 포인트 없이 각 줄만 작성해주세요.

뉴스 내용:
{text}

3줄 요약:"""
        
        response = model.generate_content(prompt)
        summary = response.text.strip()
        
        # Ensure we have exactly 3 lines
        lines = [line.strip() for line in summary.split('\n') if line.strip()]
        if len(lines) > 3:
            summary = '\n'.join(lines[:3])
        elif len(lines) < 3:
            # If less than 3 lines, pad with the original text
            summary = '\n'.join(lines)
        
        return summary
        
    except Exception as e:
        print(f"⚠️  Error summarizing with Gemini: {e}")
        # Fallback: return first 200 characters
        return text[:200] + "..." if len(text) > 200 else text


def send_to_slack(summaries: List[Dict], webhook_url: str, date: str):
    """
    Send summaries to Slack via webhook.
    
    Args:
        summaries: List of message summaries
        webhook_url: Slack webhook URL
        date: Date string for the header
    """
    if not summaries:
        print("ℹ️  No summaries to send to Slack")
        return
    
    # Build Slack message
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📰 Ahboyreads 일간 크립토 뉴스 요약 - {date}",
                "emoji": True
            }
        },
        {
            "type": "divider"
        }
    ]
    
    for idx, summary in enumerate(summaries, 1):
        # Add message section
        time_str = summary['date'].strftime('%H:%M')
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{idx}. [{time_str}] 뉴스*\n{summary['summary']}"
            }
        })
        
        # Add link button if available
        if summary.get('link'):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<{summary['link']}|📎 원문 보기>"
                }
            })
        
        # Add divider between messages (except after the last one)
        if idx < len(summaries):
            blocks.append({"type": "divider"})
    
    # Add footer
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"총 {len(summaries)}개의 뉴스 | Powered by Google Gemini"
            }
        ]
    })
    
    payload = {
        "blocks": blocks
    }
    
    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        print(f"✅ Successfully sent {len(summaries)} summaries to Slack")
    except Exception as e:
        print(f"❌ Error sending to Slack: {e}")


async def main():
    """Main function to orchestrate the workflow."""
    print("🚀 Starting Telegram to Slack Summary Bot")
    
    # Validate configuration
    validate_config()
    
    # Setup session file
    session_name = setup_session_file()
    
    # Initialize Telegram client
    client = TelegramClient(session_name, TELEGRAM_API_ID, TELEGRAM_API_HASH)
    
    try:
        # Connect to Telegram
        await client.start()
        print("✅ Connected to Telegram")
        
        # Fetch yesterday's messages
        messages = await fetch_yesterday_messages(client, TELEGRAM_CHANNEL)
        
        if not messages:
            print("ℹ️  No messages found from yesterday")
            # Send empty report to Slack
            kst = pytz.timezone('Asia/Seoul')
            yesterday = (datetime.now(kst) - timedelta(days=1)).strftime('%Y년 %m월 %d일')
            send_to_slack([], SLACK_WEBHOOK_URL, yesterday)
            return
        
        # Summarize each message
        print(f"🤖 Summarizing {len(messages)} messages with Google Gemini...")
        summaries = []
        for msg in messages:
            summary_text = summarize_with_gemini(msg['text'], GEMINI_API_KEY)
            summaries.append({
                'summary': summary_text,
                'date': msg['date'],
                'link': msg['link']
            })
            print(f"  ✓ Summarized message {msg['id']}")
        
        # Send to Slack
        kst = pytz.timezone('Asia/Seoul')
        yesterday = (datetime.now(kst) - timedelta(days=1)).strftime('%Y년 %m월 %d일')
        print(f"📤 Sending summaries to Slack...")
        send_to_slack(summaries, SLACK_WEBHOOK_URL, yesterday)
        
        print("✅ All done!")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise
    finally:
        await client.disconnect()
        print("👋 Disconnected from Telegram")


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
