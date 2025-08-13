# annotation-dashboard.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Annotation Dashboard", layout="wide")
st.title("프로젝트 대시보드")

# --- Sidebar: Parameters & CSV Upload ---
st.sidebar.header("프로젝트 파라미터 입력")
total_count       = st.sidebar.number_input("데이터 총 수량", min_value=0, value=0)
open_date         = st.sidebar.date_input("오픈일")
target_date       = st.sidebar.date_input("목표 종료일")
daily_work_goal   = st.sidebar.number_input("일일 작업 목표 건수", min_value=0, value=0)
daily_review_goal = st.sidebar.number_input("일일 검수 목표 건수", min_value=0, value=0)
work_rate         = st.sidebar.number_input("작업 단가 (원/건)", min_value=0, value=0)
review_rate       = st.sidebar.number_input("검수 단가 (원/건)", min_value=0, value=0)

csv_file = st.sidebar.file_uploader("원천 데이터 (.csv)", type="csv")
if not csv_file:
    st.warning("CSV 파일을 업로드하세요.")
    st.stop()

raw = pd.read_csv(csv_file, parse_dates=["작업 종료일", "검수 종료일"])

# --- Compute weeks and goals ---
open_dt = pd.to_datetime(open_date)
target_dt = pd.to_datetime(target_date)
start_week = open_dt.isocalendar().week
end_week = target_dt.isocalendar().week
weeks = list(range(start_week, end_week + 1))
num_weeks = len(weeks)
weekly_goal = total_count / num_weeks if num_weeks else 0

# assign week numbers
raw["work_week"] = raw["작업 종료일"].dt.isocalendar().week
raw["review_week"] = raw["검수 종료일"].dt.isocalendar().week

# --- 1) 주별 전체 프로젝트 진행: 목표 vs 실제 ---
st.subheader("1) 주별 전체 진행 현황")
# actual per week
actual = raw.groupby("work_week")["유효 오브젝트 수"].sum().reset_index()
# build full weeks frame
weekly_df = pd.DataFrame({"week": weeks})
weekly_df = weekly_df.merge(actual.rename(columns={"유효 오브젝트 수": "actual"}), how="left", on="week")
weekly_df["actual"] = weekly_df["actual"].fillna(0)
weekly_df["goal"] = weekly_goal

fig = px.bar(
    weekly_df,
    x="week",
    y=["actual", "goal"],
    labels={"value": "건수", "week": "주차"},
    barmode="group",
    title="주별 전체 진행: 목표 vs 실제"
)
st.plotly_chart(fig, use_container_width=True)

# --- 2) 주별 작업자·검수자 목표 달성률 ---
st.subheader("2) 주별 작업자·검수자 달성률")

# 작업자
wk = (
    raw.groupby(["work_week", "Worker ID", "작업자 닉네임"])["유효 오브젝트 수"]
    .sum()
    .reset_index(name="done")
)
wk["goal"] = daily_work_goal * 7
wk["pct"] = wk["done"] / wk["goal"] * 100
st.markdown("**작업자 주별 달성률**")
st.dataframe(
    wk.sort_values(["work_week", "pct"], ascending=[True, False])
      .style.format({"done":"{:,}", "goal":"{:,}", "pct":"{:.1f}%"})
)

# 검수자
rv = (
    raw.groupby(["review_week", "Checker ID", "검수자 닉네임"])["유효 오브젝트 수"]
    .sum()
    .reset_index(name="done")
)
rv["goal"] = daily_review_goal * 7
rv["pct"] = rv["done"] / rv["goal"] * 100
st.markdown("**검수자 주별 달성률**")
st.dataframe(
    rv.sort_values(["review_week", "pct"], ascending=[True, False])
      .style.format({"done":"{:,}", "goal":"{:,}", "pct":"{:.1f}%"})
)

# --- 3) 이상 참여자/검수자 감지 ---
st.subheader("3) 이상 참여자/검수자 감지")

# 이상 작업자: 반려율 ≥30% 또는 활동률 ≤0.5
wagg = (
    raw.assign(rework=lambda df: df["수정 여부"] == "Y")
       .groupby("Worker ID")
       .agg(
           count=("유효 오브젝트 수", "sum"),
           sessions=("작업 종료일", "nunique"),
           reworks=("rework", "sum")
       )
       .reset_index()
)
wagg["weeks_active"] = wagg["sessions"].clip(upper=num_weeks)
wagg["activity_rate"] = wagg["weeks_active"] / num_weeks
wagg["rework_rate"] = wagg["reworks"] / wagg["count"] * 100
abn_w = wagg[(wagg["rework_rate"] >= 30) | (wagg["activity_rate"] <= 0.5)]
st.markdown("**이상 작업자**")
st.dataframe(
    abn_w.style.format({
        "count":"{:,}", "sessions":"{:,}",
        "activity_rate":"{:.2f}", "rework_rate":"{:.1f}%"
    })
)

# 이상 검수자: 오류율 ≥10% 또는 활동률 ≤0.5
ragg = (
    raw.assign(error=lambda df: df["작업 상태"] != "ALL_FINISHED")
       .groupby("Checker ID")
       .agg(
           count=("유효 오브젝트 수", "sum"),
           sessions=("검수 종료일", "nunique"),
           errors=("error", "sum")
       )
       .reset_index()
)
ragg["weeks_active"] = ragg["sessions"].clip(upper=num_weeks)
ragg["activity_rate"] = ragg["weeks_active"] / num_weeks
ragg["error_rate"] = ragg["errors"] / ragg["count"] * 100
abn_r = ragg[(ragg["error_rate"] >= 10) | (ragg["activity_rate"] <= 0.5)]
st.markdown("**이상 검수자**")
st.dataframe(
    abn_r.style.format({
        "count":"{:,}", "sessions":"{:,}",
        "activity_rate":"{:.2f}", "error_rate":"{:.1f}%"
    })
)

