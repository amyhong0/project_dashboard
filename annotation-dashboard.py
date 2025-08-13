# annotation-dashboard.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Annotation Dashboard", layout="wide")

# --- Sidebar: Parameters & CSV Upload ---
st.sidebar.header("프로젝트 파라미터 입력")
total_count = st.sidebar.number_input("데이터 총 수량", min_value=0, value=0)
open_date = st.sidebar.date_input("오픈일")
target_date = st.sidebar.date_input("목표 종료일")
daily_work_goal = st.sidebar.number_input("일일 작업 목표 건수", min_value=0, value=0)
daily_review_goal = st.sidebar.number_input("일일 검수 목표 건수", min_value=0, value=0)
work_rate = st.sidebar.number_input("작업 단가 (원/건)", min_value=0, value=0)
review_rate = st.sidebar.number_input("검수 단가 (원/건)", min_value=0, value=0)

csv_file = st.sidebar.file_uploader("원천 데이터 (.csv)", type="csv")
if not csv_file:
    st.warning("CSV 파일을 업로드하세요.")
    st.stop()

# --- Load raw data ---
raw = pd.read_csv(csv_file, parse_dates=["작업 종료일", "검수 종료일"])

# --- Compute project-level metrics ---
completed = raw["유효 오브젝트 수"].nunique()
remaining = total_count - completed
progress_pct = (completed / total_count * 100) if total_count else 0

today = pd.to_datetime(datetime.today().date())
days_elapsed = max((today - pd.to_datetime(open_date)).days, 1)
days_left = max((pd.to_datetime(target_date) - today).days, 0)

avg_work_per_day = completed / days_elapsed
predicted_completed = completed + avg_work_per_day * days_left
predicted_pct = (predicted_completed / total_count * 100) if total_count else 0

# --- Display metrics ---
st.title("프로젝트 대시보드")
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("총 수량", f"{total_count:,}")
m2.metric("완료 수량", f"{completed:,}", f"{progress_pct:.1f}%")
m3.metric("잔여 수량", f"{remaining:,}")
m4.metric("잔여일", days_left)
m5.metric("작업 일별 목표", f"{daily_work_goal:,}")
m6.metric("예상 완료율", f"{predicted_pct:.1f}%")

# --- Weekly progress chart ---
st.subheader("주별 진척률")
raw["week"] = raw["작업 종료일"].dt.isocalendar().week
weekly = raw.groupby("week").agg(
    work_done=("유효 오브젝트 수", "sum"),
    review_done=("유효 오브젝트 수", "sum")  # assume same field
).reset_index()
weekly["work_goal"] = daily_work_goal * 7
weekly["work_pct"] = weekly["work_done"] / weekly["work_goal"] * 100
fig_work = px.bar(
    weekly, x="week", y="work_done", text="work_pct",
    labels={"week":"주차","work_done":"작업 완료 건수"}
)
st.plotly_chart(fig_work, use_container_width=True)

# --- 작업자 현황 ---
st.subheader("작업자 현황")
workers = raw.groupby(["Worker ID", "작업자 닉네임"]).agg(
    total_tasks=("유효 오브젝트 수", "sum"),
    sessions=("작업 종료일", "nunique")
).reset_index()
workers["avg_tasks_per_session"] = workers["total_tasks"] / workers["sessions"]
workers["hourly_rate"] = work_rate
st.dataframe(
    workers.style.format({
        "total_tasks":"{:,}", "sessions":"{:,}",
        "avg_tasks_per_session":"{:.1f}", "hourly_rate":"{:,}"
    })
)

# --- 검수자 현황 ---
st.subheader("검수자 현황")
reviewers = raw.groupby(["Checker ID", "검수자 닉네임"]).agg(
    total_reviews=("유효 오브젝트 수", "sum"),
    sessions=("검수 종료일", "nunique")
).reset_index()
reviewers["avg_reviews_per_session"] = reviewers["total_reviews"] / reviewers["sessions"]
reviewers["hourly_rate"] = review_rate
st.dataframe(
    reviewers.style.format({
        "total_reviews":"{:,}", "sessions":"{:,}",
        "avg_reviews_per_session":"{:.1f}", "hourly_rate":"{:,}"
    })
)

# --- Raw data preview ---
st.subheader("원천 데이터 미리보기")
st.dataframe(raw.head(100))
