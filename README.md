# 📰 Telegram to Slack 크립토 뉴스 요약봇

Ahboyreads 텔레그램 채널의 크립토 뉴스를 매일 자동으로 수집하고, Google Gemini AI로 한국어 3줄 요약하여 Slack으로 전송하는 자동화 봇입니다.

## ✨ 주요 기능

- 🕒 **자동 실행**: 매일 오전 9시(KST)에 GitHub Actions로 자동 실행
- 📱 **텔레그램 연동**: Ahboyreads 채널의 전날 메시지 자동 수집
- 🤖 **AI 요약**: Google Gemini API로 각 뉴스를 한국어 3줄 요약
- 💬 **Slack 전송**: 깔끔하게 포맷된 요약을 Slack 채널에 자동 포스팅
- 💰 **완전 무료**: GitHub Actions, Gemini API 무료 tier 사용

## 🏗️ 아키텍처

```
GitHub Actions (Cron: Daily 9AM KST)
    ↓
Telegram API (Fetch yesterday's messages)
    ↓
Google Gemini API (Summarize to Korean 3-lines)
    ↓
Slack Webhook (Post formatted summary)
```

## 📋 사전 요구사항

1. Telegram API credentials (무료)
2. Google Gemini API key (무료)
3. Slack Incoming Webhook URL (무료)
4. GitHub repository (Public repo 권장, 무료 tier)

## 🚀 설치 및 설정 가이드

### 1. Repository 클론 및 설정

```bash
git clone https://github.com/YOUR_USERNAME/tg-to-slack.git
cd tg-to-slack
```

### 2. Telegram API Credentials 발급

1. [https://my.telegram.org/apps](https://my.telegram.org/apps) 접속
2. 로그인 후 "API development tools" 클릭
3. 앱 정보 입력 (이름, 플랫폼 등)
4. `api_id`와 `api_hash` 복사하여 저장

### 3. Google Gemini API Key 발급

1. [https://makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey) 접속
2. "Create API key" 클릭
3. API 키 복사하여 저장
4. 무료 tier: 분당 15 요청, 일일 1,500 요청 제한

### 4. Slack Incoming Webhook 생성

1. Slack workspace 설정 → "Add apps" → "Incoming Webhooks" 검색
2. "Add to Slack" 클릭
3. 메시지를 받을 채널 선택
4. Webhook URL 복사 (형식: `https://hooks.slack.com/services/...`)

### 5. 로컬에서 Telegram 세션 생성

로컬 환경에서 Telegram 인증을 완료하고 세션 파일을 생성합니다.

```bash
# 가상환경 생성 (선택사항)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 파일 생성
cat > .env << EOF
TELEGRAM_API_ID=your_api_id_here
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_CHANNEL=Ahboyreads
GEMINI_API_KEY=your_gemini_api_key_here
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
EOF

# 세션 생성 스크립트 실행
python setup_session.py
```

스크립트를 실행하면:
1. Telegram에서 인증 코드를 받습니다
2. 코드를 입력하면 `tg_session.session` 파일이 생성됩니다
3. Base64로 인코딩된 세션 문자열이 출력됩니다
4. 이 문자열을 복사해 두세요 (GitHub Secrets에 사용)

### 6. GitHub Secrets 설정

Repository → Settings → Secrets and variables → Actions → "New repository secret"

다음 4개의 Secret을 추가하세요:

| Secret Name | Value | 설명 |
|------------|-------|------|
| `TELEGRAM_API_ID` | 123456 | Telegram API ID |
| `TELEGRAM_API_HASH` | abcdef123456... | Telegram API Hash |
| `TELEGRAM_SESSION` | Base64 문자열 | setup_session.py 출력값 |
| `GEMINI_API_KEY` | AIza... | Google Gemini API Key |
| `SLACK_WEBHOOK_URL` | https://hooks.slack.com/... | Slack Webhook URL |

### 7. GitHub Actions 활성화

1. Repository → Actions 탭
2. "I understand my workflows, go ahead and enable them" 클릭
3. Workflow가 자동으로 활성화됩니다

### 8. 수동 테스트 실행 (선택사항)

자동 스케줄을 기다리지 않고 즉시 테스트하려면:

1. Actions 탭 → "Daily Crypto News Summary" 워크플로우 선택
2. "Run workflow" 버튼 클릭
3. "Run workflow" 다시 클릭하여 실행
4. 실행 로그에서 결과 확인

## 🔧 로컬에서 직접 실행

```bash
# .env 파일 설정 후
python main.py
```

## 📅 스케줄

- **실행 시간**: 매일 오전 9시 (한국 시간, KST)
- **수집 범위**: 전날 00:00 ~ 23:59에 올라온 메시지
- **GitHub Actions Cron**: `0 0 * * *` (UTC 기준)

## 🛠️ 문제 해결

### Telegram 인증 오류

```
Error: Could not find session file
```

→ `setup_session.py`를 다시 실행하여 세션 파일을 생성하고, GitHub Secrets에 Base64 문자열을 올바르게 등록했는지 확인

### Gemini API 할당량 초과

```
Error: Quota exceeded
```

→ Gemini API 무료 tier 제한 (분당 15 요청)을 초과했습니다. 메시지가 많은 날은 코드에서 요청 간 지연을 추가하거나 유료 플랜 고려

### Slack 메시지가 안 보임

→ Webhook URL이 올바른지, 해당 채널에 Incoming Webhooks 앱이 추가되어 있는지 확인

### GitHub Actions가 실행 안 됨

→ Public repository인지 확인 (Private는 제한된 무료 시간). Actions 탭에서 workflow가 활성화되어 있는지 확인

## 📝 커스터마이징

### 채널 변경

다른 텔레그램 채널을 모니터링하려면:

1. `.env` 파일 또는 GitHub Repository Variables에서 `TELEGRAM_CHANNEL` 값 변경
2. 채널이 비공개인 경우, 해당 채널에 가입되어 있어야 함

### 스케줄 변경

`.github/workflows/daily-summary.yml` 파일의 cron 표현식 수정:

```yaml
schedule:
  - cron: '0 0 * * *'  # 매일 9시 KST (0시 UTC)
```

예시:
- `0 15 * * *`: 매일 자정 KST (15시 UTC)
- `0 0 * * 1`: 매주 월요일 9시 KST

### 요약 스타일 변경

`main.py`의 `summarize_with_gemini()` 함수에서 프롬프트 수정

## 💡 팁

- **세션 보안**: Telegram 세션은 계정 접근 권한이 있으므로 절대 공개하지 마세요
- **API 제한**: Gemini 무료 tier는 충분하지만, 메시지가 매우 많은 날은 제한될 수 있습니다
- **로그 확인**: GitHub Actions 로그에서 실행 상태와 오류를 확인할 수 있습니다
- **백업**: 중요한 요약은 Slack에서 따로 저장해두세요

## 📄 라이선스

MIT License

## 🙏 기여

이슈와 PR은 언제나 환영합니다!

## 📞 문의

문제가 있거나 개선 아이디어가 있으면 Issue를 열어주세요.

---

Made with ❤️ for crypto enthusiasts
