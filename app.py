import os, yaml
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from datetime import datetime
from backend.data_store import init_db, query_latest_quotes, query_news, upsert_quote, insert_news_batch
from backend.finance import fetch_snapshot, fetch_price_history, get_company_name
from backend.news import fetch_news_for
from backend.kelly import kelly_fraction

st.set_page_config(page_title="나만의 주식 분석 툴", layout="wide")

if "FMP_API_KEY" in st.secrets:
    os.environ["FMP_API_KEY"] = st.secrets["FMP_API_KEY"]

CFG_PATH = "config.yaml"
with open(CFG_PATH, "r", encoding="utf-8") as f:
    CFG = yaml.safe_load(f)
DB_PATH = CFG.get("database_path", "stocks.db")
WATCHLIST = CFG.get("watchlist", [])
COMPANY_NAMES = CFG.get("company_names", {})
DEFAULT_PERIOD = CFG.get("default_price_period", "1y")

init_db(DB_PATH)

st.sidebar.title("⚙️ 설정")
watchlist = st.sidebar.text_area("워치리스트(TICKER, 줄바꿈 구분)", "\n".join(WATCHLIST)).splitlines()
watchlist = [w.strip().upper() for w in watchlist if w.strip()]
auto_refresh = st.sidebar.button("지금 즉시 전체 업데이트(뉴스+지표)")

if auto_refresh:
    for t in watchlist:
        snap = fetch_snapshot(t)
        now = datetime.utcnow().strftime("%Y-%m-%d")
        updated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        row = {
            "ticker": t, "asof": now, "price": snap.get("price"),
            "pe_ttm": snap.get("pe_ttm"), "pb": snap.get("pb"),
            "ev_ebitda": snap.get("ev_ebitda"), "market_cap": snap.get("market_cap"),
            "updated_at": updated_at
        }
        upsert_quote(DB_PATH, row)
        cname = COMPANY_NAMES.get(t) or get_company_name(t) or t
        news_rows = fetch_news_for(t, cname, days=7)
        insert_news_batch(DB_PATH, news_rows)
    st.sidebar.success("업데이트 완료!")

st.title("📊 나만의 주식 분석 툴")
st.write("워치리스트를 기준으로 핵심 지표 / 뉴스(한국어) / 차트를 한 곳에 모았습니다.")

tab1, tab2, tab3, tab4 = st.tabs(["기업 스냅샷", "뉴스 피드", "차트", "켈리 계산기"])

with tab1:
    st.subheader("기업 스냅샷 (PER/PBR/EV/EBITDA 등)")
    if watchlist:
        rows = query_latest_quotes(DB_PATH, watchlist)
        if rows:
            df = pd.DataFrame(rows).sort_values(["ticker","asof"], ascending=[True, False])
            df = df.drop_duplicates(subset=["ticker"], keep="first")
            df_display = df[["ticker","asof","price","pe_ttm","pb","ev_ebitda","market_cap","updated_at"]]
            st.dataframe(df_display, use_container_width=True)
        else:
            st.info("아직 저장된 스냅샷이 없습니다. 왼쪽에서 '지금 즉시 전체 업데이트'를 눌러주세요.")
    else:
        st.warning("워치리스트가 비어 있습니다. 좌측에서 티커를 추가하세요.")

with tab2:
    st.subheader("최신 뉴스 (한국어)")
    ticker = st.selectbox("티커 선택", options=watchlist, index=0 if watchlist else None)
    if ticker:
        if st.button("이 티커 뉴스 새로고침"):
            cname = COMPANY_NAMES.get(ticker) or get_company_name(ticker) or ticker
            rows = fetch_news_for(ticker, cname, days=7)
            insert_news_batch(DB_PATH, rows)
            st.success("뉴스 갱신 완료!")
        items = query_news(DB_PATH, ticker, limit=50)
        if not items:
            st.info("저장된 뉴스가 없습니다. 새로고침을 눌러 받아보세요.")
        else:
            for (published, source, title, url, summary) in items:
                st.write(f"**[{title}]({url})**  \n*{published} · {source}*")
                if summary:
                    st.caption(summary)

with tab3:
    st.subheader("가격 차트")
    ticker = st.selectbox("차트 티커", options=watchlist, index=0 if watchlist else None, key="chart_ticker")
    period = st.selectbox("기간", ["3mo","6mo","1y","2y","5y","10y","max"], index=["3mo","6mo","1y","2y","5y","10y","max"].index(DEFAULT_PERIOD) if DEFAULT_PERIOD in ["3mo","6mo","1y","2y","5y","10y","max"] else 2)
    interval = st.selectbox("간격", ["1d","1wk","1mo"], index=0)
    if ticker:
        hist = fetch_price_history(ticker, period=period, interval=interval)
        if hist is None or hist.empty:
            st.info("히스토리 데이터를 가져오지 못했습니다.")
        else:
            st.write(f"**{ticker}** 가격 ({period}, {interval})")
            fig, ax = plt.subplots()
            ax.plot(hist.index, hist['Close'])
            ax.set_xlabel("Date")
            ax.set_ylabel("Close")
            st.pyplot(fig, clear_figure=True)

with tab4:
    st.subheader("켈리 공식 계산기")
    st.caption("f* = p - (1-p)/r  (p: 승률 0~1, r: 승리 시 평균 이익 / 패배 시 평균 손실)")
    c1, c2, c3 = st.columns(3)
    with c1:
        p = st.number_input("승률 p (0~1)", value=0.5, min_value=0.0, max_value=1.0, step=0.01)
    with c2:
        r = st.number_input("이익/손실 비율 r (>0)", value=1.0, min_value=0.01, step=0.05)
    with c3:
        bankroll = st.number_input("총 투자자금 (원화)", value=3000000, min_value=0, step=10000)
    f = kelly_fraction(p, r)
    f_clipped = max(0.0, f)
    st.write(f"권장 투자비율 f*: **{f:.4f}**  → 현실적(0 이하 절삭) 비율: **{f_clipped:.4f}**")
    st.write(f"권장 투자금액(원): **{int(bankroll * f_clipped):,}**")

st.divider()
st.caption("""데이터 출처: Yahoo Finance(yfinance) 및 Google News RSS(ko-KR 기본). FMP API Key 지원.
연구/교육용 샘플입니다. 투자 조언이 아닙니다.""" )
