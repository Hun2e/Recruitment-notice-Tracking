"""
자소설닷컴 채용공고 트래커
- 공고 1행 / 직무별 작성자 수는 텍스트로 표시
  예) 영업관리: 69명, 상품계리: 8명, 자산운용: 6명
- 알림은 노션 리마인더 기능 사용 (마감일 3일 전)
"""

import os
import re
import json
import time
import requests
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup

NOTION_API_KEY = os.environ["NOTION_API_KEY"]
NOTION_DB_ID   = os.environ["NOTION_DB_ID"]
TRACK_URLS     = json.loads(os.environ.get("TRACK_URLS", "[]"))

KST = timezone(timedelta(hours=9))

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


def crawl_job(url: str) -> dict | None:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] 페이지 요청 실패: {url} → {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    text = soup.get_text(" ", strip=True)

    # ── 회사명: h2 태그
    company = "회사명 없음"
    h2 = soup.find("h2")
    if h2:
        company = h2.get_text(strip=True)

    # ── 공고명: h1 태그
    title = "제목 없음"
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True)

    # ── 마감일: "~ YYYY년 MM월 DD일" 패턴
    deadline = None
    match = re.search(r"~\s*(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", text)
    if match:
        y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
        deadline = datetime(y, m, d, 23, 59, tzinfo=KST)

    # ── 직무별 작성자 수: li 태그에서 "직무명 N명 작성" 추출
    job_writers = {}
    for li in soup.find_all("li"):
        li_text = li.get_text(" ", strip=True)
        m = re.search(r"(\d+)명\s*작성", li_text)
        if m:
            count = int(m.group(1))
            job_name = li_text[:m.start()].strip()
            job_name = re.sub(r"신입|경력|신입/경력", "", job_name).strip()
            if job_name:
                job_writers[job_name] = count

    # 직무별 작성자 수 텍스트: "영업관리: 69명, 상품계리: 8명, ..."
    if job_writers:
        job_writer_text = ", ".join(f"{job}: {cnt}명" for job, cnt in job_writers.items())
        total_count = sum(job_writers.values())
    else:
        counts = re.findall(r"(\d+)명\s*작성", text)
        job_writer_text = None
        total_count = sum(int(c) for c in counts) if counts else None

    return {
        "id":              url.rstrip("/").split("/")[-1],
        "url":             url,
        "company":         company,
        "title":           title,
        "job_writer_text": job_writer_text,
        "total_count":     total_count,
        "deadline":        deadline,
        "crawled_at":      datetime.now(KST),
    }


def find_notion_page(job_id: str) -> str | None:
    r = requests.post(
        f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query",
        headers=NOTION_HEADERS,
        json={"filter": {"property": "공고ID", "rich_text": {"equals": job_id}}},
        timeout=15,
    )
    results = r.json().get("results", [])
    return results[0]["id"] if results else None


def upsert_notion_page(data: dict):
    now = datetime.now(KST)

    props = {
        "공고명":        {"title":     [{"text": {"content": f"[{data['company']}] {data['title']}"}}]},
        "회사명":        {"rich_text": [{"text": {"content": data["company"]}}]},
        "공고ID":        {"rich_text": [{"text": {"content": data["id"]}}]},
        "공고 URL":      {"url": data["url"]},
        "최근 업데이트": {"date": {"start": data["crawled_at"].isoformat()}},
    }

    if data["total_count"] is not None:
        props["작성자 수"] = {"number": data["total_count"]}

    if data["job_writer_text"]:
        props["직무별 작성자 수"] = {"rich_text": [{"text": {"content": data["job_writer_text"]}}]}

    if data["deadline"]:
        diff_days = (data["deadline"].date() - now.date()).days
        if diff_days < 0:    status = "마감됨"
        elif diff_days == 0: status = "오늘 마감"
        elif diff_days <= 3: status = f"D-{diff_days}"
        else:                status = "진행중"

        props["마감일"]    = {"date": {"start": data["deadline"].isoformat()}}
        props["마감 상태"] = {"select": {"name": status}}

    page_id = find_notion_page(data["id"])

    if page_id:
        r = requests.patch(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers=NOTION_HEADERS,
            json={"properties": props},
            timeout=15,
        )
        action = "업데이트"
    else:
        r = requests.post(
            "https://api.notion.com/v1/pages",
            headers=NOTION_HEADERS,
            json={"parent": {"database_id": NOTION_DB_ID}, "properties": props},
            timeout=15,
        )
        action = "신규 등록"

    if r.status_code in (200, 201):
        print(f"  ✅ Notion {action}: [{data['company']}] {data['title']}")
        if data["job_writer_text"]:
            print(f"     직무별: {data['job_writer_text']}")
        if data["deadline"]:
            print(f"     마감일: {data['deadline'].strftime('%Y-%m-%d')} ({props['마감 상태']['select']['name']})")
    else:
        print(f"  ❌ Notion 오류: {r.status_code} {r.text[:200]}")


def main():
    print(f"\n{'='*50}")
    print(f"🚀 트래커 실행: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')}")
    print(f"📌 추적 공고 수: {len(TRACK_URLS)}개")
    print(f"{'='*50}\n")

    if not TRACK_URLS:
        print("⚠️  TRACK_URLS가 비어있습니다.")
        return

    for url in TRACK_URLS:
        print(f"🔍 크롤링: {url}")
        data = crawl_job(url)
        if not data:
            print("  ⚠️  크롤링 실패, 건너뜁니다.\n")
            continue
        upsert_notion_page(data)
        print()
        time.sleep(2)

    print("✅ 모든 공고 업데이트 완료!\n")


if __name__ == "__main__":
    main()
