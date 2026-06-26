# analyzer.py
# ------------------------------------------------------------
# [3,4단계] 분석 → 점수화 → 추천 근거 생성  (이 프로그램의 핵심)
#
# 두 가지 모드로 작동합니다.
#   1) 규칙 기반(rule-based): API 키가 없어도 즉시 작동. 지표로 점수를 매김.
#   2) LLM 기반(Claude API): 환경변수 ANTHROPIC_API_KEY 가 있으면 자동 사용.
#      뉴스 맥락까지 읽어 사람처럼 '근거'를 설명해 줌.
# ------------------------------------------------------------

import os
import json

# ----- (1) 규칙 기반 분석 : API 키 없이도 작동하는 기본 모드 -----

def analyze_rule_based(ind: dict, news_count: int) -> dict:
    """기술적 지표만으로 0~100점 점수와 근거 문장을 만듭니다."""
    score = 50  # 기본 50점에서 가감
    reasons = []

    if ind.get("above_ma20"):
        score += 10
        reasons.append("현재가가 20일 이동평균선 위에 있어 단기 흐름이 양호합니다.")
    else:
        score -= 10
        reasons.append("현재가가 20일선 아래에 있어 단기적으로 약세입니다.")

    if ind.get("ma5_over_ma20"):
        score += 10
        reasons.append("5일선이 20일선을 넘어 상승 추세 신호가 보입니다.")

    vr = ind.get("vol_ratio", 1.0)
    if vr >= 1.5:
        score += 10
        reasons.append(f"거래량이 평소의 {vr}배로 늘어 시장 관심이 높아졌습니다.")

    rsi = ind.get("rsi", 50)
    if rsi >= 75:
        score -= 10
        reasons.append(f"RSI가 {rsi}로 과열 구간이라 단기 조정 위험이 있습니다.")
    elif 50 <= rsi < 70:
        score += 5
        reasons.append(f"RSI가 {rsi}로 적절한 상승 탄력을 보입니다.")

    ret5 = ind.get("ret5", 0)
    if ret5 > 0:
        reasons.append(f"최근 5거래일 수익률은 +{ret5}%입니다.")
    else:
        reasons.append(f"최근 5거래일 수익률은 {ret5}%입니다.")

    if news_count >= 3:
        score += 5
        reasons.append(f"최근 관련 뉴스가 {news_count}건으로 뉴스 흐름이 활발합니다.")

    score = max(0, min(100, score))  # 0~100 범위로 고정
    return {"score": score, "rationale": " ".join(reasons), "mode": "규칙기반"}


# ----- (2) LLM(Claude API) 기반 분석 : 더 똑똑한 근거 설명 -----

def analyze_with_llm(name: str, ind: dict, news_list: list) -> dict | None:
    """Claude API로 뉴스 맥락까지 반영한 점수/근거를 생성합니다.
    API 키가 없거나 호출에 실패하면 None을 반환합니다."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic
    except ImportError:
        print("[안내] anthropic 패키지가 없습니다. 'pip install anthropic' 후 LLM 모드 사용 가능.")
        return None

    news_titles = "\n".join(f"- {n['title']}" for n in news_list) or "(관련 뉴스 없음)"

    prompt = f"""당신은 한국 주식 데이터를 객관적으로 정리하는 분석 보조 도구입니다.
아래 종목의 지표와 최신 뉴스 제목을 보고, 0~100점의 '주목도 점수'와 그 근거를 정리하세요.
이것은 매수/매도 권유가 아니라 정보 정리이며, 불확실성을 솔직히 표현하세요.

[종목] {name}
[지표] {json.dumps(ind, ensure_ascii=False)}
[최신 뉴스 제목]
{news_titles}

아래 JSON 형식으로만 답하세요(다른 말 없이):
{{"score": 정수, "rationale": "근거를 3~4문장으로, 호재/악재와 위험요인을 균형있게"}}"""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in msg.content if hasattr(b, "text"))
        text = text.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        return {
            "score": int(data["score"]),
            "rationale": str(data["rationale"]),
            "mode": "Claude AI",
        }
    except Exception as e:
        print(f"[경고] LLM 분석 실패({name}), 규칙기반으로 대체: {e}")
        return None


# ----- (3) 두 방식을 합쳐 최종 추천 목록 생성 -----

def recommend(snapshot, news_map: dict, top_n: int = 5) -> list[dict]:
    """관심종목 전체를 분석해 점수 높은 순으로 추천 목록을 만듭니다."""
    results = []
    for _, row in snapshot.iterrows():
        ind = {
            "last_close": row["last_close"], "ma5": row["ma5"], "ma20": row["ma20"],
            "ma60": row["ma60"], "above_ma20": bool(row["above_ma20"]),
            "ma5_over_ma20": bool(row["ma5_over_ma20"]), "vol_ratio": row["vol_ratio"],
            "rsi": row["rsi"], "ret5": row["ret5"],
        }
        news_list = news_map.get(row["code"], [])

        # 먼저 LLM 시도 → 없으면 규칙기반
        analysis = analyze_with_llm(row["name"], ind, news_list)
        if analysis is None:
            analysis = analyze_rule_based(ind, len(news_list))

        results.append({
            "code": row["code"],
            "name": row["name"],
            "score": analysis["score"],
            "rationale": analysis["rationale"],
            "mode": analysis["mode"],
            "last_close": row["last_close"],
            "rsi": row["rsi"],
            "ret5": row["ret5"],
            "news": news_list,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]
