# data_collector.py
# ------------------------------------------------------------
# [1단계] 시세 데이터 수집 + 기술적 지표 계산
#
# 한국 주식 데이터를 FinanceDataReader 로 가져오고,
# 이동평균, 거래량 급증 여부, RSI, 최근 수익률 등을 계산합니다.
# ------------------------------------------------------------

from datetime import datetime, timedelta
import pandas as pd

try:
    import FinanceDataReader as fdr
except ImportError:
    fdr = None  # 라이브러리가 아직 설치 안 됐을 때를 대비


def get_price_data(code: str, lookback_days: int = 150) -> pd.DataFrame:
    """종목코드 하나의 최근 주가 데이터를 가져옵니다.

    반환: 날짜를 인덱스로 갖고 Open/High/Low/Close/Volume 컬럼을 가진 표(DataFrame)
    실패하면 빈 DataFrame을 반환합니다.
    """
    if fdr is None:
        raise RuntimeError(
            "FinanceDataReader가 설치되지 않았습니다. "
            "터미널에서 'pip install finance-datareader' 를 실행하세요."
        )

    start = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    try:
        df = fdr.DataReader(code, start)
        return df
    except Exception as e:
        print(f"[경고] {code} 시세 수집 실패: {e}")
        return pd.DataFrame()


def _rsi(close: pd.Series, period: int = 14) -> float:
    """RSI(상대강도지수)를 계산합니다. 0~100 사이 값이며,
    보통 70 이상이면 과열, 30 이하면 과매도로 봅니다."""
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, 1e-9)  # 0으로 나누기 방지
    rsi = 100 - (100 / (1 + rs))
    last = rsi.iloc[-1]
    return float(last) if pd.notna(last) else 50.0


def compute_indicators(df: pd.DataFrame) -> dict:
    """주가 표 하나를 받아 분석에 쓸 핵심 지표들을 딕셔너리로 계산합니다."""
    if df is None or df.empty or len(df) < 20:
        return {}

    close = df["Close"]
    volume = df["Volume"]

    last_close = float(close.iloc[-1])
    ma5 = float(close.rolling(5).mean().iloc[-1])
    ma20 = float(close.rolling(20).mean().iloc[-1])
    ma60 = float(close.rolling(60).mean().iloc[-1]) if len(df) >= 60 else ma20

    # 최근 거래량이 20일 평균 대비 몇 배인지 (1.5 이상이면 거래 활발)
    avg_vol20 = float(volume.rolling(20).mean().iloc[-1])
    last_vol = float(volume.iloc[-1])
    vol_ratio = last_vol / avg_vol20 if avg_vol20 > 0 else 1.0

    # 최근 5거래일 수익률(%)
    if len(close) >= 6:
        ret5 = (last_close / float(close.iloc[-6]) - 1) * 100
    else:
        ret5 = 0.0

    return {
        "last_close": round(last_close, 1),
        "ma5": round(ma5, 1),
        "ma20": round(ma20, 1),
        "ma60": round(ma60, 1),
        "above_ma20": last_close > ma20,           # 20일선 위에 있는가
        "ma5_over_ma20": ma5 > ma20,               # 단기선이 중기선 위 (상승 추세 신호)
        "vol_ratio": round(vol_ratio, 2),          # 거래량 배율
        "rsi": round(_rsi(close), 1),
        "ret5": round(ret5, 2),                    # 5일 수익률(%)
    }


def get_market_snapshot(watchlist: dict, lookback_days: int = 150) -> pd.DataFrame:
    """관심종목 전체의 지표를 한 번에 계산해 표로 만듭니다.
    또한 차트 그리기에 쓰도록 종목별 원본 주가도 함께 반환합니다."""
    rows = []
    price_frames = {}  # 종목코드 -> 주가 DataFrame (차트용)

    for code, name in watchlist.items():
        df = get_price_data(code, lookback_days)
        price_frames[code] = df
        ind = compute_indicators(df)
        if not ind:
            print(f"[건너뜀] {name}({code}) 데이터 부족")
            continue
        ind["code"] = code
        ind["name"] = name
        rows.append(ind)

    snapshot = pd.DataFrame(rows)
    return snapshot, price_frames
