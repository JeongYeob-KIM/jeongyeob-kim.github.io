"""
나라장터 API 응답 구조 확인용 스크립트
"""

import os
import json
import requests
from datetime import datetime, timedelta

API_KEY  = os.environ.get("G2B_API_KEY", "")
BASE_URL = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc"

today = datetime.now()
d30   = (today - timedelta(days=30)).strftime("%Y%m%d")

print(f"API 키 앞 10자: {API_KEY[:10]}")
print("=" * 60)

# 가장 단순한 파라미터로 응답 원문 확인
params = {
    "serviceKey": API_KEY,
    "pageNo":     1,
    "numOfRows":  5,
    "type":       "json",
}

try:
    r = requests.get(BASE_URL, params=params, timeout=30)
    print(f"HTTP 상태코드: {r.status_code}")
    print(f"\n===== 응답 원문 전체 =====")
    print(r.text[:2000])
    print("=" * 60)

    # JSON 파싱 시도
    try:
        data = r.json()
        print("\n===== JSON 파싱 결과 =====")
        print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])
    except Exception as e:
        print(f"JSON 파싱 실패: {e}")

except Exception as e:
    print(f"요청 실패: {e}")
