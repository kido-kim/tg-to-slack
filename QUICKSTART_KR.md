# 🚀 빠른 시작 가이드

## 1단계: API 키 발급 (5분)

### Telegram API
1. https://my.telegram.org/apps 접속
2. 전화번호로 로그인
3. 앱 만들기 (이름 아무거나)
4. `api_id`와 `api_hash` 복사

### Google Gemini API (무료)
1. https://makersuite.google.com/app/apikey 접속
2. "Create API key" 클릭
3. API 키 복사

### Slack Webhook
1. Slack workspace 설정
2. "Apps" → "Incoming Webhooks" 검색하여 추가
3. 메시지 받을 채널 선택
4. Webhook URL 복사

## 2단계: 로컬 세팅 (5분)

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp env.example .env
# .env 파일을 열어서 위에서 받은 API 키들 입력

# Telegram 세션 생성
python setup_session.py
# Telegram에서 받은 인증 코드 입력
# 출력되는 Base64 문자열 복사 (다음 단계에서 사용)
```

## 3단계: GitHub 설정 (3분)

### Repository 생성
1. GitHub에서 새 repository 생성 (Public 권장)
2. 코드 푸시:
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/tg-to-slack.git
git push -u origin main
```

### Secrets 설정
Repository → Settings → Secrets and variables → Actions

다음 5개의 Secret 추가:
- `TELEGRAM_API_ID`: 1단계에서 받은 api_id
- `TELEGRAM_API_HASH`: 1단계에서 받은 api_hash
- `TELEGRAM_SESSION`: 2단계에서 복사한 Base64 문자열
- `GEMINI_API_KEY`: 1단계에서 받은 Gemini API 키
- `SLACK_WEBHOOK_URL`: 1단계에서 받은 Slack Webhook URL

## 4단계: 테스트 실행 (1분)

1. GitHub → Actions 탭
2. "I understand my workflows, go ahead and enable them" 클릭
3. "Daily Crypto News Summary" 워크플로우 선택
4. "Run workflow" 버튼으로 수동 실행
5. Slack에서 메시지 확인! 🎉

## 완료!

이제 매일 오전 9시에 자동으로 요약이 Slack으로 전송됩니다.

## 로컬 테스트

GitHub Actions 없이 바로 테스트하려면:
```bash
python main.py
```

## 문제 해결

### "No messages found"
→ 전날 Ahboyreads 채널에 메시지가 없었을 수 있습니다. 수동으로 다른 날짜를 테스트하려면 `main.py`의 날짜 로직을 수정하세요.

### Telegram 인증 오류
→ `setup_session.py`를 다시 실행하고 TELEGRAM_SESSION을 GitHub Secrets에 정확히 입력했는지 확인

### Gemini API 오류
→ API 키가 올바른지, 무료 할당량(분당 15 요청)을 초과하지 않았는지 확인

### Slack에 메시지가 안 옴
→ Webhook URL이 정확한지, 채널에 Incoming Webhooks 앱이 설치되어 있는지 확인

## 다음 단계

- 다른 텔레그램 채널 추가
- 요약 스타일 변경 (프롬프트 수정)
- 실행 시간 변경 (cron 스케줄 수정)
- 여러 Slack 채널에 전송

즐거운 크립토 뉴스 읽기 되세요! 📰✨
