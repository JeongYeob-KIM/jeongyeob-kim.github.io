"""
나라장터 입찰공고 크롤러 (최종)
- 필수 파라미터: bidNtceDt (등록일시)
- 응답 구조: nkoneps.com.response
"""

import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

API_KEY  = os.environ.get("G2B_API_KEY", "")
BASE_URL = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc"

INCLUDE_KEYWORDS = [
    "홍보", "소식지", "뉴스레터", "기관지", "홍보지", "홍보물",
    "백서", "연간보고서", "책자", "발간", "출판",
    "콘텐츠", "영상", "SNS", "카드뉴스", "사진",
    "광고", "PR", "언론", "미디어",
    "행사", "포럼", "세미나", "공청회", "이벤트",
    "교육", "문화", "인쇄", "편집", "디자인",
]
EXCLUDE_KEYWORDS = [
    "공사", "토목", "건설", "시설", "청소", "경비", "보안",
    "시스템", "개발", "유지보수", "서버", "네트워크",
    "의료", "법률", "회계", "감사", "세무",
    "물품", "구매", "납품", "장비", "기자재",
]
REVIEW_KEYWORDS = ["용역", "서비스", "운영", "지원", "관리"]
MIN_AMOUNT = 5_000_000

TAG_MAP = {
    "소식지·홍보물": ["홍보", "소식지", "뉴스레터", "기관지", "홍보지", "홍보물"],
    "백서·보고서":   ["백서", "연간보고서", "책자", "발간", "출판"],
    "콘텐츠 제작":   ["콘텐츠", "영상", "SNS", "카드뉴스", "사진"],
    "미디어·PR":     ["광고", "PR", "언론", "미디어"],
    "행사·포럼":     ["행사", "포럼", "세미나", "공청회", "이벤트"],
    "교육·문화":     ["교육", "문화"],
    "인쇄·편집":     ["인쇄", "편집", "디자인"],
}


def fetch_bids() -> list:
    today = datetime.now()
    # 필수값: bidNtceDt (7일 전부터 오늘까지)
    params = {
        "serviceKey": API_KEY,
        "pageNo":     1,
        "numOfRows":  100,
        "type":       "json",
        "inqryDiv":   "1",                                          # 용역
        "bidNtceDt":  (today - timedelta(days=7)).strftime("%Y%m%d"),  # 필수: 등록일시
    }

    print(f"[API] URL: {BASE_URL}")
    print(f"[API] bidNtceDt: {params['bidNtceDt']}")

    try:
        r = requests.get(BASE_URL, params=params, timeout=30)
        print(f"[API] HTTP: {r.status_code}")
        print(f"[API] 응답 앞 300자: {r.text[:300]}")
        r.raise_for_status()

        data = r.json()

        # ── 응답 구조 분기 처리 ──
        # 구조 1: nkoneps.com.response (조달청 자체 포맷)
        if "nkoneps.com.response" in data:
            root = data["nkoneps.com.response"]
            header = root.get("header", {})
            code   = header.get("resultCode", "")
            msg    = header.get("resultMsg", "")
            print(f"[API] resultCode: {code}, resultMsg: {msg}")

            if code != "00":
                print(f"[ERROR] API 오류: {msg}")
                return []

            body  = root.get("body", {})
            total = body.get("totalCount", 0)
            items = body.get("items", {}).get("item", [])

        # 구조 2: 공공데이터포털 표준 포맷
        elif "response" in data:
            body  = data["response"].get("body", {})
            total = body.get("totalCount", 0)
            items = body.get("items", [])

        else:
            print(f"[ERROR] 알 수 없는 응답 구조: {list(data.keys())}")
            return []

        if isinstance(items, dict):
            items = [items]
        elif not isinstance(items, list):
            items = []

        print(f"[API] totalCount: {total}, 수신: {len(items)}건")
        return items

    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        return []


def classify(title: str, amount: int) -> str:
    if amount < MIN_AMOUNT:
        return "exclude"
    for kw in EXCLUDE_KEYWORDS:
        if kw in title:
            return "exclude"
    for kw in INCLUDE_KEYWORDS:
        if kw in title:
            return "fit"
    for kw in REVIEW_KEYWORDS:
        if kw in title:
            return "review"
    return "exclude"


def get_tags(title: str) -> list:
    return [label for label, kws in TAG_MAP.items() if any(k in title for k in kws)] or ["기타"]


def fmt_amount(v: int) -> str:
    if v >= 100_000_000:
        eok = v // 100_000_000
        man = (v % 100_000_000) // 10_000
        return f"{eok}억 {man:,}만원" if man else f"{eok}억원"
    return f"{v // 10_000:,}만원"


def is_urgent(dl: str) -> bool:
    try:
        return (datetime.strptime(dl[:8], "%Y%m%d") - datetime.now()).days <= 3
    except Exception:
        return False


def run():
    today_str = datetime.now().strftime("%Y-%m-%d")

    if not API_KEY:
        print("[WARN] G2B_API_KEY 없음")

    raw = fetch_bids()

    fit, review, excluded = [], [], []
    for item in raw:
        title  = item.get("bidNtceNm", "")
        org    = item.get("ntceInsttNm", "")
        no     = item.get("bidNtceNo", "")
        dl     = item.get("bidClseDt", "")
        try:
            amount = int(float(item.get("presmptPrce", 0) or 0))
        except Exception:
            amount = 0

        status = classify(title, amount)
        record = {
            "no":           no,
            "title":        title,
            "org":          org,
            "deadline":     dl[:8] if dl else "",
            "amount":       amount,
            "amount_label": fmt_amount(amount),
            "urgent":       is_urgent(dl),
            "tags":         get_tags(title),
            "url":          f"https://www.g2b.go.kr/pt/menu/selectSubFrame.do?framesrc=/pt/menu/frameBidPblanc.do?bidno={no}",
            "status":       status,
        }
        if status == "fit":      fit.append(record)
        elif status == "review": review.append(record)
        else:                    excluded.append(record)

    fit.sort(key=lambda x: (not x["urgent"], x["deadline"]))

    output = {
        "date":         today_str,
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_reviewed": len(raw),
            "fit":            len(fit),
            "review":         len(review),
            "excluded":       len(excluded),
        },
        "fit":    fit,
        "review": review,
    }

    repo_root = Path(__file__).resolve().parent.parent
    out_dir   = repo_root / "etc" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    for fname in [f"bids_{today_str}.json", "bids_latest.json"]:
        path = out_dir / fname
        with open(path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"[저장] {path}")

    print(f"[완료] {today_str} | 전체 {len(raw)}건 | 적합 {len(fit)}건 | 검토 {len(review)}건")


if __name__ == "__main__":
    run()
