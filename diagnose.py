"""
나라장터 API 파라미터 진단 스크립트
200은 뜨는데 0건인 경우 → 파라미터 조합 탐색
"""

import os
import requests
from datetime import datetime, timedelta

API_KEY  = os.environ.get("G2B_API_KEY", "")
BASE_URL = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc"

today = datetime.now()
d7    = (today - timedelta(days=7)).strftime("%Y%m%d")
d30   = (today - timedelta(days=30)).strftime("%Y%m%d")
today_str = today.strftime("%Y%m%d")

TESTS = [
    ("기본만",          {"pageNo":1,"numOfRows":10,"type":"json"}),
    ("inqryDiv=1",     {"pageNo":1,"numOfRows":10,"type":"json","inqryDiv":"1"}),
    ("inqryDiv=2",     {"pageNo":1,"numOfRows":10,"type":"json","inqryDiv":"2"}),
    ("inqryDiv=3",     {"pageNo":1,"numOfRows":10,"type":"json","inqryDiv":"3"}),
    ("날짜(7일)",       {"pageNo":1,"numOfRows":10,"type":"json","bidNtceDt":d7}),
    ("날짜(30일)",      {"pageNo":1,"numOfRows":10,"type":"json","bidNtceDt":d30}),
    ("rgstDt(7일)",    {"pageNo":1,"numOfRows":10,"type":"json","rgstDt":d7}),
    ("용역+날짜(7일)", {"pageNo":1,"numOfRows":10,"type":"json","inqryDiv":"1","bidNtceDt":d7}),
    ("용역+날짜(30일)",{"pageNo":1,"numOfRows":10,"type":"json","inqryDiv":"1","bidNtceDt":d30}),
]

print(f"API 키 앞 10자: {API_KEY[:10]}")
print(f"오늘: {today_str}, 7일전: {d7}, 30일전: {d30}")
print("=" * 60)

for label, extra in TESTS:
    params = {"serviceKey": API_KEY, **extra}
    try:
        r = requests.get(BASE_URL, params=params, timeout=15)
        if r.status_code == 200:
            body = r.json().get("response", {}).get("body", {})
            total = body.get("totalCount", "?")
            items = body.get("items", [])
            cnt   = len(items) if isinstance(items, list) else (1 if items else 0)
            mark  = "✅" if int(total or 0) > 0 else "⬜"
            print(f"{mark} [{label}] totalCount={total}, items={cnt}")
            if int(total or 0) > 0:
                print(f"   첫 공고명: {items[0].get('bidNtceNm','?') if isinstance(items,list) and items else '?'}")
        else:
            print(f"❌ [{label}] HTTP {r.status_code} → {r.text[:80]}")
    except Exception as e:
        print(f"💥 [{label}] {e}")

print("=" * 60)
