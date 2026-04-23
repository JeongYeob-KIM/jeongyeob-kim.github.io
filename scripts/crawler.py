"""
나라장터 입찰공고 크롤러
저장 경로: etc/data/bids_YYYY-MM-DD.json  &  etc/data/bids_latest.json
"""

import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

API_KEY  = os.environ.get("G2B_API_KEY", "")
BASE_URL = "https://apis.data.go.kr/1230000/BidPublicInfoService04/getBidPblancListInfoServc"

# ── 분류 키워드 ────────────────────────────────────────────────────
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
    "시스템", "개발", "유지보수", "서버", "네트워크", "DB",
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


def fetch_bids(page: int = 1, rows: int = 100) -> list:
    today = datetime.now()
    params = {
        "serviceKey": API_KEY,
        "pageNo":     page,
        "numOfRows":  rows,
        "type":       "json",
        "inqryDiv":   "1",
        "opengBgnDt": (today - timedelta(days=1)).strftime("%Y%m%d%H%M"),
        "opengEndDt": today.strftime("%Y%m%d%H%M"),
    }
    try:
        r = requests.get(BASE_URL, params=params, timeout=30)
        r.raise_for_status()
        items = r.json().get("response", {}).get("body", {}).get("items", [])
        return items if isinstance(items, list) else ([items] if items else [])
    except Exception as e:
        print(f"[ERROR] API 실패: {e}")
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
        if status == "fit":
            fit.append(record)
        elif status == "review":
            review.append(record)
        else:
            excluded.append(record)

    fit.sort(key=lambda x: (not x["urgent"], x["deadline"]))

    output = {
        "date":         today_str,
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_reviewed": len(raw),
            "fit":     len(fit),
            "review":  len(review),
            "excluded":len(excluded),
        },
        "fit":    fit,
        "review": review,
    }

    # ── etc/data/ 에 저장 (레포 루트 기준) ──
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
