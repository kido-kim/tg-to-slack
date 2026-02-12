#!/usr/bin/env python3
"""
Telegram to Slack Daily Summary Bot
Fetches messages from Ahboyreads Telegram channel, summarizes them using Google Gemini,
and posts to Slack daily at 9 AM KST.
"""

import os
import sys
import base64
import re
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pytz
from telethon import TelegramClient
from telethon.tl.types import Message
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
# Support multiple channels
TELEGRAM_CHANNELS = {
    'ahboyashreads': 'scrape',  # Scrape article content
    'shoalresearch': 'translate'  # Translate message directly
}
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
        
        # Fetch messages from yesterday (get last 100 messages and filter)
        async for message in client.iter_messages(
            entity,
            limit=100
        ):
            # Convert message date to KST
            msg_date_kst = message.date.replace(tzinfo=pytz.UTC).astimezone(kst)
            
            # Check if message is from yesterday
            if msg_date_kst < yesterday_start:
                # Older than our target date, stop searching
                break
            if msg_date_kst > yesterday_end:
                # Newer than our target date, skip
                continue
            
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


def extract_urls(text: str) -> List[str]:
    """
    Extract URLs from text.
    
    Args:
        text: Text containing URLs
        
    Returns:
        List of URLs found in text
    """
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, text)
    return urls


def fetch_article_content(url: str) -> Optional[str]:
    """
    Fetch and extract main content from a URL.
    
    Args:
        url: URL to fetch
        
    Returns:
        Extracted text content or None if failed
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Try to find main content
        content = None
        
        # Try common article selectors
        article_selectors = [
            'article',
            '[role="article"]',
            '.article-content',
            '.post-content',
            '.entry-content',
            'main',
        ]
        
        for selector in article_selectors:
            element = soup.select_one(selector)
            if element:
                content = element.get_text(separator='\n', strip=True)
                break
        
        # Fallback to body
        if not content:
            body = soup.find('body')
            if body:
                content = body.get_text(separator='\n', strip=True)
        
        if content:
            # Clean up excessive whitespace
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            content = '\n'.join(lines)
            
            # Check minimum length (300 chars)
            if len(content) < 300:
                return None
            
            # Detect paywalls and subscription prompts
            paywall_keywords = [
                'sign up', 'subscribe', 'subscription', 'premium',
                '유료', '구독', 'become a member', 'join now',
                'create account', 'log in to read', 'members only'
            ]
            content_lower = content.lower()
            if any(keyword in content_lower for keyword in paywall_keywords):
                # Check if most of the content is paywall message
                if len(content) < 1000:  # Short content with paywall = likely blocked
                    return None
            
            # Limit content length
            if len(content) > 5000:
                content = content[:5000]
            return content
        
        return None
        
    except Exception as e:
        print(f"  ⚠️  Error fetching {url}: {e}")
        return None


def translate_to_korean(text: str, api_key: str) -> str:
    """
    Translate English text to Korean using Google Gemini API.
    
    Args:
        text: Text to translate
        api_key: Google Gemini API key
        
    Returns:
        Korean translation
    """
    try:
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
        
        prompt = f"""다음 영문 텍스트를 자연스러운 한국어로 번역해주세요.
암호화폐/크립토 산업 용어는 원문 그대로 유지하면서 번역해주세요.

영문:
{text[:3000]}

한국어 번역:"""
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }
        
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        translation = result['candidates'][0]['content']['parts'][0]['text'].strip()
        
        # Add delay to avoid rate limiting
        time.sleep(4.5)
        
        return translation
        
    except Exception as e:
        print(f"  ⚠️  Error translating with Gemini: {e}")
        # Return None to indicate translation failure (will skip message)
        return None


def summarize_with_gemini(text: str, api_key: str, title: str = "") -> str:
    """
    Summarize text using Google Gemini API via REST.
    
    Args:
        text: Text to summarize
        api_key: Google Gemini API key
        title: Optional title for context
        
    Returns:
        Korean 3-line summary
    """
    try:
        # Use REST API directly for better compatibility
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
        
        prompt = f"""다음은 암호화폐/크립토 산업 관련 뉴스입니다. 
이 내용을 한국어로 정확히 3줄로 요약해주세요. 
각 줄은 한 문장으로, 핵심 정보만 간결하게 담아주세요.
각 줄 앞에 1️⃣ 2️⃣ 3️⃣ 이모티콘을 붙여주세요.

뉴스 내용:
{text[:3000]}

3줄 요약 (예시: 1️⃣ 첫번째 요약...\n2️⃣ 두번째 요약...\n3️⃣ 세번째 요약...):"""
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }
        
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        summary = result['candidates'][0]['content']['parts'][0]['text'].strip()
        
        # Add delay to avoid rate limiting (Gemini free tier: 15 RPM)
        time.sleep(4.5)  # 60s / 15 requests = 4s per request, add buffer
        
        # Ensure we have exactly 3 lines
        lines = [line.strip() for line in summary.split('\n') if line.strip()]
        if len(lines) > 3:
            summary = '\n'.join(lines[:3])
        elif len(lines) < 3:
            # If less than 3 lines, just use what we have
            summary = '\n'.join(lines)
        
        return summary
        
    except Exception as e:
        print(f"  ⚠️  Error summarizing with Gemini: {e}")
        # Fallback: return first 200 characters
        return text[:200] + "..." if len(text) > 200 else text


def send_to_slack(summaries: List[Dict], webhook_url: str, date: str):
    """
    Send summaries to Slack via webhook.
    Split into multiple messages if needed to avoid Slack's 50 block limit.
    
    Args:
        summaries: List of message summaries
        webhook_url: Slack webhook URL
        date: Date string for the header
    """
    if not summaries:
        print("ℹ️  No summaries to send to Slack")
        return
    
    # Determine channel name from summaries
    channel_name = summaries[0].get('channel', 'Unknown')
    channel_display = {
        'ahboyashreads': 'Ahboyreads',
        'shoalresearch': 'Shoal Research'
    }.get(channel_name, channel_name)
    
    # Split summaries into chunks (max 15 per message to stay under 50 blocks)
    # Each summary = 3 blocks (section + link + divider)
    chunk_size = 15
    chunks = [summaries[i:i + chunk_size] for i in range(0, len(summaries), chunk_size)]
    
    for chunk_idx, chunk in enumerate(chunks, 1):
        # Build Slack message for this chunk
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📰 {channel_display} 일간 크립토 뉴스 요약 - {date}" + (f" ({chunk_idx}/{len(chunks)})" if len(chunks) > 1 else ""),
                    "emoji": True
                }
            },
            {
                "type": "divider"
            }
        ]
        
        start_idx = (chunk_idx - 1) * chunk_size
        for idx, summary in enumerate(chunk, start_idx + 1):
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
            if idx < start_idx + len(chunk):
                blocks.append({"type": "divider"})
        
        # Add footer
        if chunk_idx == len(chunks):
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
            if len(chunks) > 1:
                print(f"✅ Successfully sent chunk {chunk_idx}/{len(chunks)} ({len(chunk)} summaries)")
            else:
                print(f"✅ Successfully sent {len(summaries)} summaries to Slack")
        except Exception as e:
            print(f"❌ Error sending chunk {chunk_idx} to Slack: {e}")


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
        
        # Process messages from all channels
        all_summaries = []
        
        for channel_name, process_type in TELEGRAM_CHANNELS.items():
            print(f"\n📡 Processing channel: @{channel_name}")
            messages = await fetch_yesterday_messages(client, channel_name)
            
            if not messages:
                print(f"  ℹ️  No messages found from {channel_name}")
                continue
            
            print(f"🤖 Processing {len(messages)} messages from @{channel_name}...")
            
            for msg in messages:
                summary_text = None
                article_url = None
                
                if process_type == 'scrape':
                    # For ahboyashreads: scrape article content
                    urls = extract_urls(msg['text'])
                    
                    if urls:
                        # Try to fetch and summarize content from each URL
                        for url in urls:
                            # Skip X.com and t.me links (require JavaScript/login)
                            if 'x.com' in url or 't.me' in url or 'twitter.com' in url:
                                continue
                            
                            print(f"  🔗 Fetching content from: {url[:60]}...")
                            content = fetch_article_content(url)
                            
                            if content and len(content) >= 300:
                                # Summarize the article content (only if sufficient content)
                                print(f"      ✓ Fetched {len(content)} chars")
                                summary_text = summarize_with_gemini(content, GEMINI_API_KEY)
                                article_url = url
                                break  # Use first successful article
                            elif content:
                                print(f"      ⚠️  Content too short ({len(content)} chars), skipping")
                    
                    # Skip if no article could be scraped
                    if not summary_text:
                        print(f"  ⏭️  Skipped message {msg['id']} (no scrapeable content)")
                        continue
                        
                elif process_type == 'translate':
                    # For shoalresearch: just translate the message
                    print(f"  🌐 Translating message {msg['id']}...")
                    summary_text = translate_to_korean(msg['text'], GEMINI_API_KEY)
                    
                    # Skip if translation failed
                    if not summary_text:
                        print(f"  ⏭️  Skipped message {msg['id']} (translation failed)")
                        continue
                    
                    urls = extract_urls(msg['text'])
                    article_url = urls[0] if urls else msg['link']
                
                if summary_text:
                    all_summaries.append({
                        'summary': summary_text,
                        'date': msg['date'],
                        'link': article_url or msg['link'],
                        'channel': channel_name
                    })
                    print(f"  ✓ Processed message {msg['id']}")
        
        summaries = all_summaries
        
        # Send to Slack
        kst = pytz.timezone('Asia/Seoul')
        yesterday = (datetime.now(kst) - timedelta(days=1)).strftime('%Y년 %m월 %d일')
        
        if summaries:
            print(f"\n📤 Sending {len(summaries)} summaries to Slack...")
            send_to_slack(summaries, SLACK_WEBHOOK_URL, yesterday)
        else:
            print("ℹ️  No summaries to send to Slack")
            send_to_slack([], SLACK_WEBHOOK_URL, yesterday)
        
        print("✅ All done!")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise
    finally:
        await client.disconnect()
        print("👋 Disconnected from Telegram")


if __name__ == '__main__':
    import asyncio
    import sys
    
    # Support channel filtering from command line
    if len(sys.argv) > 1:
        channel_filter = sys.argv[1]
        if channel_filter in TELEGRAM_CHANNELS:
            # Filter to only process specified channel
            TELEGRAM_CHANNELS = {channel_filter: TELEGRAM_CHANNELS[channel_filter]}
        else:
            print(f"Unknown channel: {channel_filter}")
            print(f"Available channels: {', '.join(TELEGRAM_CHANNELS.keys())}")
            sys.exit(1)
    
    asyncio.run(main())
