# annotation-dashboard.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Annotation Dashboard", layout="wide")

# --- Sidebar: Uploads & Parameters ---
st.sidebar.header("데이터 입력 및 파라미터")
xlsx_file = st.sidebar.file_uploader("대시보드 관리 파일 (.xlsx)", type="xlsx")
csv_file = st.sidebar.file_uploader("Raw 데이터 파일 (.csv)", type="csv")

# 프로젝트 파라미터
if xlsx_file:
    info_df = pd.read_excel(xlsx_file, sheet_name="정보", header=0)
    row = info_df.iloc[0]
    total_count = int(row["총 수량"])
    completed = int(row["완료\n수량"])
    open_date = pd.to_datetime(row["오픈일"])
    target_date = pd.to_datetime(row["목표 \n종료일"])
    daily_goal = int(row["1일 처리\n목표 건수"])
else:
    st.error("먼저 .xlsx 파일을 업로드하세요.")
    st.stop()

if csv_file:
    raw = pd.read_csv(csv_file)
else:
    st.warning("Raw .csv 파일을 업로드하세요.")
    raw = pd.DataFrame()

# --- 계산 지표 ---
today = pd.to_datetime(datetime.today().date())
remaining = total_count - completed
progress_pct = completed / total_count * 100
days_left = (target_date - today).days
days_elapsed = (today - open_date).days or 1
avg_per_day = completed / days_elapsed
predicted_total = completed + avg_per_day * days_left
predicted_pct = predicted_total / total_count * 100

# 대시보드 상단 메트릭
st.title("프로젝트 대시보드")
col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("총 수량", f"{total_count:,}")
col2.metric("완료 수량", f"{completed:,}", f"{progress_pct:.1f}%")
col3.metric("잔여 수량", f"{remaining:,}")
col4.metric("잔여일", days_left)
col5.metric("일별 목표", f"{daily_goal:,}")
col6.metric("예상 완료율", f"{predicted_pct:.1f}%")

# --- 주별 진척률 ---
st.subheader("주별 진척률")
if not raw.empty:
    raw["work_date"] = pd.to_datetime(raw["작업 종료일"]).dt.date
    raw["week"] = pd.to_datetime(raw["work_date"]).dt.isocalendar().week
    weekly = raw.groupby("week").agg(
        completed=("유효 오브젝트 수", "sum"),
        count=("데이터 ID", "nunique")
    ).reset_index()
    weekly["goal"] = daily_goal * 7
    weekly["pct"] = weekly["completed"] / weekly["goal"] * 100
    fig = px.bar(weekly, x="week", y="completed", text="pct",
                 labels={"week":"주차","completed":"완료 건수"})
    st.plotly_chart(fig, use_container_width=True)

# --- 작업자 현황 ---
st.subheader("작업자 현황")
if not raw.empty:
    agg = raw.groupby(["Worker ID","작업자 닉네임"]).agg(
        tasks=("유효 오브젝트 수","sum"),
        sessions=("작업 종료일", "nunique"),
        avg_time_min=("작업 수정 시간", "mean")
    ).reset_index()
    agg["hourly_rate"] = st.sidebar.number_input("작업 단가", value=1000)
    agg["tasks_per_session"] = agg["tasks"] / agg["sessions"]
    agg["avg_time_hr"] = agg["avg_time_min"] / 60
    st.dataframe(agg.style.format({
        "tasks": "{:,.0f}", "sessions": "{:,.0f}", "avg_time_hr":"{:.1f}",
        "tasks_per_session":"{:.1f}", "hourly_rate":"{:,}"
    }))

# --- 검수자 현황 ---
st.subheader("검수자 현황")
if not raw.empty:
    rev = raw.groupby(["Checker ID","검수자 닉네임"]).agg(
        reviews=("유효 오브젝트 수","sum"),
        sessions=("검수 종료일", "nunique")
    ).reset_index()
    rev["hourly_rate"] = st.sidebar.number_input("검수 단가", value=1500)
    rev["reviews_per_session"] = rev["reviews"] / rev["sessions"]
    st.dataframe(rev.style.format({
        "reviews": "{:,.0f}", "sessions": "{:,.0f}",
        "reviews_per_session":"{:.1f}", "hourly_rate":"{:,}"
    }))

# --- Raw 데이터 탭 ---
st.subheader("Raw 데이터 미리보기")
if not raw.empty:
    st.dataframe(raw.head(100))
