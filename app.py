# app.py
# ------------------------------------------------------------
#  한국 주식 뉴스/트렌드 분석 대시보드  (실행 진입점)
#
#  실행 방법 (터미널에서):
#     streamlit run app.py
#  그러면 자동으로 웹브라우저에 대시보드가 열립니다.
# ------------------------------------------------------------

import streamlit as st
import pandas as pd

import config
import data_collector
import news_collector
import analyzer
import storage

# ----- 페이지 기본 설정 -----
st.set_page_config(page_title="주식 뉴스/트렌드 분석", page_icon="📈", layout="wide")

# ----- 면책 안내 (매우 중요) -----
st.title("📈 한국 주식 뉴스·트렌드 분석 대시보드")
st.warning(
    "⚠️ 이 도구는 정보를 정리해 판단을 돕는 보조 도구일 뿐, **투자 자문이 아닙니다.** "
    "여기의 점수와 근거는 수익을 보장하지 않으며, 모든 투자 결정과 책임은 본인에게 있습니다."
)

# ----- 사이드바: 실행 버튼과 안내 -----
with st.sidebar:
    st.header("⚙️ 설정")
    st.write(f"관심종목 **{len(config.WATCHLIST)}개** 분석")
    run = st.button("🔄 오늘 데이터 분석하기", type="primary", use_container_width=True)
    st.divider()
    st.caption(
        "API 키(ANTHROPIC_API_KEY)를 설정하면 뉴스 맥락까지 읽는 "
        "Claude AI 근거 설명이 켜집니다. 없으면 규칙기반으로 작동합니다."
    )

# ----- 탭 구성: 오늘의 분석 / 지난 기록 -----
tab_today, tab_history = st.tabs(["📊 오늘의 분석", "🗂️ 지난 추천 기록"])

with tab_today:
    if run:
        # 1) 시세 + 지표
        with st.spinner("시세 데이터를 가져오는 중..."):
            snapshot, price_frames = data_collector.get_market_snapshot(
                config.WATCHLIST, config.PRICE_LOOKBACK_DAYS
            )

        if snapshot.empty:
            st.error("시세 데이터를 가져오지 못했습니다. 인터넷 연결을 확인하세요.")
            st.stop()

        # 2) 뉴스
        with st.spinner("최신 뉴스를 모으는 중..."):
            news_map = news_collector.collect_all_news(
                config.WATCHLIST, config.NEWS_PER_STOCK
            )

        # 3) 분석 + 추천
        with st.spinner("분석하고 근거를 정리하는 중..."):
            recs = analyzer.recommend(snapshot, news_map, config.TOP_N)
            storage.save_recommendations(config.DB_PATH, recs)  # 기록 저장

        st.success(f"분석 완료! 오늘의 상위 {len(recs)}개 종목입니다.")

        # ----- 추천 결과 카드로 표시 -----
        for i, r in enumerate(recs, 1):
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.subheader(f"{i}. {r['name']} ({r['code']})")
                    st.caption(f"분석 방식: {r['mode']}")
                with c2:
                    st.metric("주목도 점수", f"{r['score']}/100")

                st.write(f"**근거:** {r['rationale']}")

                m1, m2, m3 = st.columns(3)
                m1.metric("현재가", f"{r['last_close']:,.0f}원")
                m2.metric("RSI", r["rsi"])
                m3.metric("5일 수익률", f"{r['ret5']}%")

                # 차트
                pf = price_frames.get(r["code"])
                if pf is not None and not pf.empty:
                    st.line_chart(pf["Close"].tail(60))

                # 관련 뉴스
                if r["news"]:
                    with st.expander(f"관련 뉴스 {len(r['news'])}건 보기"):
                        for n in r["news"]:
                            st.markdown(f"- [{n['title']}]({n['link']})")
    else:
        st.info("👈 왼쪽의 **'오늘 데이터 분석하기'** 버튼을 누르면 시작합니다.")

with tab_history:
    st.subheader("지난 추천 기록")
    st.caption(
        "매번 분석할 때마다 결과가 여기에 쌓입니다. "
        "시간이 지난 뒤 '그때 점수가 높았던 종목이 실제로 올랐는지' 확인하는 데 쓰세요."
    )
    hist = storage.load_history(config.DB_PATH)
    if hist.empty:
        st.write("아직 기록이 없습니다. 먼저 분석을 한 번 실행해 보세요.")
    else:
        st.dataframe(hist, use_container_width=True)
