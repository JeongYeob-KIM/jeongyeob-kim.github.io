"""보유 종목 뉴스 수집 → Claude 요약 → 텔레그램 발송."""
import os, time, requests, feedparser
from urllib.parse import quote
from datetime import datetime, timezone, timedelta
import anthropic

# 보유 종목 검색어 (결과 보고 자유롭게 조정)
STOCKS = [
    "삼성전자",
    "하나금융지주",
    "우리금융지주",
    "인벤티지랩",
    "솔리드파워 OR SLDP",
    "알파벳 OR GOOGL",
]

DAYS = 3  # 최근 며칠 이내 뉴스만 포함

TG_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
TG_CHAT = os.environ['TELEGRAM_CHAT_ID']
client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])


def get_news(query, limit=5):
    url = f"https://news.google.com/rss/search?q={quote(query)}&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(url)
    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS)
    items = []
    for e in feed.entries:
        pub = None
        if getattr(e, 'published_parsed', None):
            pub = datetime.fromtimestamp(time.mktime(e.published_parsed), tz=timezone.utc)
            if pub < cutoff:
                continue  # 오래된 뉴스 제외
        date_str = pub.astimezone().strftime('%m-%d') if pub else '?'
        items.append(f"- ({date_str}) {e.title}")
        if len(items) >= limit:
            break
    return items


# 1. 종목별 뉴스 수집
collected = []
for stock in STOCKS:
    news = get_news(stock)
    name = stock.split(' OR ')[0]
    if news:
        collected.append(f"[{name}]\n" + "\n".join(news))
    else:
        collected.append(f"[{name}]\n- (최근 {DAYS}일 내 뉴스 없음)")
raw = "\n\n".join(collected)

# 2. Claude 요약
prompt = (
    "다음은 내가 보유한 주식 종목별 최근 뉴스 제목 목록입니다. 각 줄 앞의 (MM-DD)는 발행일입니다.\n"
    "각 종목별로 주가에 영향을 줄 만한 핵심 내용을 2~3문장으로 한국어로 요약해주세요.\n"
    "종목과 무관한 뉴스는 제외하고, 종목명은 대괄호 [] 안의 이름을 그대로 【】로 감싸 표시하세요.\n"
    "⚠️ 종목명은 절대 변형하거나 영문을 섞지 말고 입력된 한글 그대로 사용하세요.\n"
    "최근 뉴스가 없는 종목은 '특이사항 없음'으로 적어주세요.\n\n"
    f"{raw}"
)
resp = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=2000,
    messages=[{"role": "user", "content": prompt}]
)
summary = resp.content[0].text

# 3. 텔레그램 발송
today = datetime.now().strftime('%Y-%m-%d')
message = f"📈 {today} 보유종목 뉴스 요약 (최근 {DAYS}일)\n\n{summary}"

r = requests.post(
    f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
    json={"chat_id": TG_CHAT, "text": message, "disable_web_page_preview": True}
)
print(f"전송 결과: {r.status_code} {r.text[:200]}")
