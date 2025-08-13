# app.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="프로젝트 대시보드", layout="wide")
st.title("프로젝트 종합 대시보드")

# --- Sidebar: 프로젝트 설정 및 CSV 업로드 ---
st.sidebar.header("프로젝트 파라미터")
total_count       = st.sidebar.number_input("데이터 총 수량", min_value=1, value=1000)
open_date         = st.sidebar.date_input("오픈일", value=datetime.today().date())
target_date       = st.sidebar.date_input("목표 종료일", value=datetime.today().date())
daily_work_goal   = st.sidebar.number_input("일일 작업 목표 건수", min_value=0, value=100)
daily_review_goal = st.sidebar.number_input("일일 검수 목표 건수", min_value=0, value=100)
work_rate         = st.sidebar.number_input("작업 단가 (원/건)", min_value=0, value=500)
review_rate       = st.sidebar.number_input("검수 단가 (원/건)", min_value=0, value=800)

csv_file = st.sidebar.file_uploader("원천 데이터 CSV 업로드", type="csv")
if not csv_file:
    st.warning("원천 데이터(.csv)를 업로드해주세요.")
    st.stop()

# --- 데이터 로드 & 전처리 ---
raw = pd.read_csv(csv_file, parse_dates=["작업 종료일", "검수 종료일"])
raw["work_week"]   = raw["작업 종료일"].dt.isocalendar().week
raw["review_week"] = raw["검수 종료일"].dt.isocalendar().week

# 주 차이 계산
start_wk = raw["work_week"].min()
end_wk   = raw["work_week"].max()
weeks     = list(range(start_wk, end_wk + 1))
num_weeks = len(weeks)
weekly_project_goal = total_count / num_weeks

# --- 1. 주별 전체 목표 vs 실제 진행 상황 ---
st.subheader("1) 주별 전체 진행 현황")
df_proj = (
    raw.groupby("work_week")["유효 오브젝트 수"]
       .sum()
       .reindex(weeks, fill_value=0)
       .reset_index()
       .rename(columns={"work_week":"week", "유효 오브젝트 수":"actual"})
)
df_proj["goal"] = weekly_project_goal
fig1 = px.bar(
    df_proj, x="week", y=["actual","goal"],
    labels={"value":"건수","week":"주차"},
    barmode="group", title="주별 전체 프로젝트 진행: 목표 vs 실제"
)
st.plotly_chart(fig1, use_container_width=True)

# --- 2. 주별 작업자·검수자 목표 달성률 ---
st.subheader("2) 주별 작업자·검수자 달성률")

# 작업자 달성률
df_work = (
    raw.groupby(["work_week","Worker ID","작업자 닉네임"])["유효 오브젝트 수"]
       .sum().reset_index(name="done")
)
df_work["goal"] = daily_work_goal * 7
df_work["pct"]  = df_work["done"] / df_work["goal"] * 100
st.markdown("**작업자 주별 달성률**")
st.dataframe(
    df_work.sort_values(["work_week","pct"], ascending=[True,False])
           .style.format({"done":"{:,}","goal":"{:,}","pct":"{:.1f}%"})
)

# 검수자 달성률
df_rev = (
    raw.groupby(["review_week","Checker ID","검수자 닉네임"])["유효 오브젝트 수"]
       .sum().reset_index(name="done")
)
df_rev["goal"] = daily_review_goal * 7
df_rev["pct"]  = df_rev["done"] / df_rev["goal"] * 100
st.markdown("**검수자 주별 달성률**")
st.dataframe(
    df_rev.sort_values(["review_week","pct"], ascending=[True,False])
          .style.format({"done":"{:,}","goal":"{:,}","pct":"{:.1f}%"})
)

# --- 3. 이상 참여자/검수자 감지 ---
st.subheader("3) 이상 참여자/검수자 감지")

# 이상 작업자: 반려율 ≥30% 또는 활동률 ≤50%
wagg = (
    raw.assign(rework=lambda df: df["수정 여부"]=="Y")
       .groupby(["Worker ID","작업자 닉네임"])
       .agg(total=("유효 오브젝트 수","sum"),
            weeks_active=("작업 종료일", lambda s: s.dt.isocalendar().week.nunique()),
            reworks=("rework","sum"))
       .reset_index()
)
wagg["activity_rate"] = wagg["weeks_active"]/num_weeks
wagg["rework_rate"]   = wagg["reworks"]/wagg["total"]*100
abn_w = wagg[(wagg["rework_rate"]>=30)|(wagg["activity_rate"]<=0.5)]
st.markdown("**이상 작업자**")
st.dataframe(
    abn_w.style.format({
        "total":"{:,}", "weeks_active":"{:,}",
        "activity_rate":"{:.2f}", "rework_rate":"{:.1f}%"
    })
)

# 이상 검수자: 오류율 ≥10% 또는 활동률 ≤50%
ragg = (
    raw.assign(error=lambda df: df["작업 상태"]!="ALL_FINISHED")
       .groupby(["Checker ID","검수자 닉네임"])
       .agg(total=("유효 오브젝트 수","sum"),
            weeks_active=("검수 종료일", lambda s: s.dt.isocalendar().week.nunique()),
            errors=("error","sum"))
       .reset_index()
)
ragg["activity_rate"] = ragg["weeks_active"]/num_weeks
ragg["error_rate"]     = ragg["errors"]/ragg["total"]*100
abn_r = ragg[(ragg["error_rate"]>=10)|(ragg["activity_rate"]<=0.5)]
st.markdown("**이상 검수자**")
st.dataframe(
    abn_r.style.format({
        "total":"{:,}", "weeks_active":"{:,}",
        "activity_rate":"{:.2f}", "error_rate":"{:.1f}%"
    })
)

# --- 원천 데이터 미리보기 ---
st.subheader("원천 데이터 미리보기")
st.dataframe(raw.head(50))
