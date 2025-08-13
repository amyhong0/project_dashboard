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
total_count    = st.sidebar.number_input("데이터 총 수량", min_value=0, value=0)
open_date      = st.sidebar.date_input("오픈일")
target_date    = st.sidebar.date_input("목표 종료일")
daily_work_goal   = st.sidebar.number_input("일일 작업 목표 건수", min_value=0, value=0)
daily_review_goal = st.sidebar.number_input("일일 검수 목표 건수", min_value=0, value=0)
work_rate      = st.sidebar.number_input("작업 단가 (원/건)", min_value=0, value=0)
review_rate    = st.sidebar.number_input("검수 단가 (원/건)", min_value=0, value=0)

csv_file = st.sidebar.file_uploader("원천 데이터 (.csv)", type="csv")
if not csv_file:
    st.warning("CSV 파일을 업로드하세요.")
    st.stop()
raw = pd.read_csv(csv_file, parse_dates=["작업 종료일","검수 종료일"])

# --- Precompute date/week ranges ---
open_dt = pd.to_datetime(open_date)
target_dt = pd.to_datetime(target_date)
weeks = np.arange(open_dt.isocalendar().week, target_dt.isocalendar().week + 1)
num_weeks = len(weeks)
weekly_goal = total_count / num_weeks

# assign week numbers
raw["work_week"]   = raw["작업 종료일"].dt.isocalendar().week
raw["review_week"] = raw["검수 종료일"].dt.isocalendar().week

# --- 1. 주별 진행 상태: 전체 목표 vs 실제 ---
st.subheader("1) 주별 진행 현황")
weekly = raw.groupby("work_week").agg(actual=("유효 오브젝트 수","sum")).reindex(weeks, fill_value=0)
weekly["goal"] = weekly_goal
weekly = weekly.reset_index().rename(columns={"index":"week"})
fig = px.bar(weekly, x="week", y=["actual","goal"],
             labels={"value":"건수","week":"주차"}, barmode="group",
             title="주별 전체 진행: 목표 vs 실제")
st.plotly_chart(fig, use_container_width=True)

# --- 2. 작업자/검수자 주별 목표 달성 ---
st.subheader("2) 주별 작업자·검수자 달성률")
# workers
wk = raw.groupby(["work_week","Worker ID","작업자 닉네임"]).agg(done=("유효 오브젝트 수","sum")).reset_index()
wk["goal"] = daily_work_goal * 7
wk["pct"]  = wk["done"]/wk["goal"]*100
st.markdown("**작업자 주별 달성률**")
st.dataframe(wk.style.format({"done":"{:,}","goal":"{:,}","pct":"{:.1f}%"}))

# reviewers
rv = raw.groupby(["review_week","Checker ID","검수자 닉네임"]).agg(done=("유효 오브젝트 수","sum")).reset_index()
rv["goal"] = daily_review_goal * 7
rv["pct"]  = rv["done"]/rv["goal"]*100
st.markdown("**검수자 주별 달성률**")
st.dataframe(rv.style.format({"done":"{:,}","goal":"{:,}","pct":"{:.1f}%"}))

# --- 3. 이상 참여자 감지 ---
st.subheader("3) 이상 참여자/검수자 감지")

# worker abnormal: rework_rate ≥30% or activity_rate ≤0.5
wagg = raw.groupby("Worker ID").agg(
    tasks=("유효 오브젝트 수","sum"),
    sessions=("작업 종료일","nunique"),
    reworks=("수정 여부", lambda s: (s=="Y").sum())
).reset_index().rename(columns={"Worker ID":"user","tasks":"count"})
wagg["weeks_active"] = wagg["sessions"].apply(lambda x: min(x, num_weeks))
wagg["activity_rate"] = wagg["weeks_active"]/num_weeks
wagg["rework_rate"]   = wagg["reworks"]/wagg["count"]*100
abn_w = wagg[(wagg["rework_rate"]>=30) | (wagg["activity_rate"]<=0.5)]
st.markdown("**이상 작업자**")
st.dataframe(abn_w.style.format({
    "count":"{:,}","sessions":"{:,}",
    "activity_rate":"{:.2f}","rework_rate":"{:.1f}%"
}))

# reviewer abnormal: error_rate ≥10% or activity_rate ≤0.5
ragg = raw.groupby("Checker ID").agg(
    reviews=("유효 오브젝트 수","sum"),
    sessions=("검수 종료일","nunique"),
    errors=("작업 상태", lambda s: (s!="ALL_FINISHED").sum())
).reset_index().rename(columns={"Checker ID":"user","reviews":"count"})
ragg["weeks_active"]   = ragg["sessions"].apply(lambda x: min(x, num_weeks))
ragg["activity_rate"]  = ragg["weeks_active"]/num_weeks
ragg["error_rate"]     = ragg["errors"]/ragg["count"]*100
abn_r = ragg[(ragg["error_rate"]>=10) | (ragg["activity_rate"]<=0.5)]
st.markdown("**이상 검수자**")
st.dataframe(abn_r.style.format({
    "count":"{:,}","sessions":"{:,}",
    "activity_rate":"{:.2f}","error_rate":"{:.1f}%"
}))

