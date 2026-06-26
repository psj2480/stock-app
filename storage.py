# storage.py
# ------------------------------------------------------------
# [5단계] 추천 기록 저장
#
# 매일의 추천 결과를 작은 데이터베이스(SQLite)에 저장합니다.
# 이 기록이 있어야 나중에 "내 추천이 실제로 맞았는지" 검증할 수 있습니다.
# SQLite는 파이썬에 기본 내장되어 있어 따로 설치할 필요가 없습니다.
# ------------------------------------------------------------

import sqlite3
import json
from datetime import date


def init_db(db_path: str):
    """데이터베이스와 테이블을 준비합니다(없으면 새로 만듦)."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date TEXT,
            code TEXT,
            name TEXT,
            score INTEGER,
            last_close REAL,
            rationale TEXT,
            mode TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_recommendations(db_path: str, recs: list[dict]):
    """오늘의 추천 목록을 저장합니다. 같은 날 다시 돌리면 그날 기록을 갱신합니다."""
    init_db(db_path)
    today = date.today().isoformat()
    conn = sqlite3.connect(db_path)
    # 같은 날짜 기록은 지우고 새로 저장 (중복 방지)
    conn.execute("DELETE FROM recommendations WHERE run_date = ?", (today,))
    for r in recs:
        conn.execute(
            "INSERT INTO recommendations "
            "(run_date, code, name, score, last_close, rationale, mode) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (today, r["code"], r["name"], r["score"],
             r["last_close"], r["rationale"], r["mode"]),
        )
    conn.commit()
    conn.close()


def load_history(db_path: str):
    """저장된 모든 추천 기록을 표로 불러옵니다."""
    import pandas as pd
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        "SELECT run_date, name, score, last_close, mode, rationale "
        "FROM recommendations ORDER BY run_date DESC, score DESC",
        conn,
    )
    conn.close()
    return df
