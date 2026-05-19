"""K공감 호 크롤러: 호 URL → 모든 기사 → Apps Script API로 전송."""
import sys, os, re, requests, urllib3
from datetime import datetime
from urllib.parse import urljoin, unquote
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {'User-Agent': 'Mozilla/5.0'}
API_URL = os.environ['SHEETS_API_URL']
ISSUE_URL = sys.argv[1]


def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=30, verify=False)
    r.encoding = r.apparent_encoding
    return r


def meta(soup, prop):
    t = soup.find('meta', {'property': prop}) or soup.find('meta', {'name': prop})
    return t.get('content', '').strip() if t else ''


def parse_article(url):
    soup = BeautifulSoup(fetch(url).text, 'html.parser')
    title = meta(soup, 'og:title') or (soup.title.text.strip() if soup.title else '제목없음')

    content_el = (
        soup.find('div', class_=re.compile(r'(view_?cont|article|content|news_view|board_view)', re.I))
        or soup.find('article')
        or soup.find('div', id=re.compile(r'(content|article|news)', re.I))
    )
    body = content_el.get_text(' ', strip=True) if content_el else ''

    text = soup.get_text()
    m = re.search(r'(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})', text)
    date = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else datetime.now().strftime('%Y-%m-%d')
    issue = (re.search(r'(\d+)\s*호', text) or [None, ''])[1]
    section = re.search(r'section_id=([^&]+)', url)
    au = re.search(r'(?:글|기자)\s*([가-힣]{2,5})', text)

    return {
        'title': title.strip(),
        'url': url,
        'date': date,
        'category': unquote(section.group(1)) if section else '',
        'issue': issue + '호' if issue else '',
        'author': au.group(1) if au else '',
        'image': meta(soup, 'og:image'),
        'body': body[:49000]
    }


print(f"[INFO] 호 URL: {ISSUE_URL}")
issue_soup = BeautifulSoup(fetch(ISSUE_URL).text, 'html.parser')
links = {urljoin(ISSUE_URL, a['href']) for a in issue_soup.find_all('a', href=True)
         if 'newsContentView.es' in a['href']}
print(f"[INFO] {len(links)}개 기사 발견")

if not links:
    print("[ERROR] 기사 링크 없음. HTML 일부:")
    print(issue_soup.prettify()[:3000])
    sys.exit(1)

articles = []
for url in sorted(links):
    try:
        a = parse_article(url)
        articles.append(a)
        print(f"  [OK] {a['title']}")
    except Exception as e:
        print(f"  [FAIL] {url}: {e}")

if not articles:
    print("[ERROR] 파싱된 기사 없음")
    sys.exit(1)

r = requests.post(API_URL, json=articles, timeout=300, allow_redirects=True)
print(f"[DONE] API 응답({r.status_code}): {r.text[:300]}")
