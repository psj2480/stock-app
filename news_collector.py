# news_collector.py
# ------------------------------------------------------------
# [2단계] 뉴스 수집
#
# 네이버 뉴스 검색에서 종목 관련 최신 뉴스 제목/요약을 가져옵니다.
# 크롤링은 사이트 구조가 바뀌면 깨질 수 있으므로,
# 실패해도 프로그램 전체가 멈추지 않도록 안전하게 처리합니다.
# ------------------------------------------------------------

import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

# 일반 브라우저인 척 해야 차단을 덜 당합니다.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}


def get_news(query: str, limit: int = 5) -> list[dict]:
    """검색어(보통 종목 이름)로 최신 뉴스를 가져옵니다.

    반환: [{"title": 제목, "summary": 요약, "link": 링크}, ...]
    실패하면 빈 리스트를 반환합니다.
    """
    url = (
        "https://search.naver.com/search.naver"
        f"?where=news&query={quote(query)}&sort=1"  # sort=1: 최신순
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"[경고] '{query}' 뉴스 수집 실패: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    # 네이버 뉴스 검색 결과의 제목 링크를 모읍니다.
    # (네이버가 구조를 바꾸면 아래 선택자를 수정해야 할 수 있습니다.)
    for a in soup.select("a.news_tit"):
        title = a.get_text(strip=True)
        link = a.get("href", "")
        if title:
            results.append({"title": title, "summary": "", "link": link})
        if len(results) >= limit:
            break

    # 위 선택자가 안 먹히면 대체 방법으로 한 번 더 시도
    if not results:
        for a in soup.select("a[href]"):
            txt = a.get_text(strip=True)
            if len(txt) > 15 and query[:2] in txt:
                results.append({"title": txt, "summary": "", "link": a.get("href", "")})
            if len(results) >= limit:
                break

    return results


def collect_all_news(watchlist: dict, per_stock: int = 5) -> dict:
    """관심종목 전체의 뉴스를 모아 {종목코드: [뉴스들]} 형태로 반환합니다."""
    news_map = {}
    for code, name in watchlist.items():
        news_map[code] = get_news(name, per_stock)
    return news_map
