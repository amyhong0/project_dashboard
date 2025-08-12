# annotation-dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import date, timedelta

st.set_page_config(page_title="Project Dashboard", layout="wide")

# ===== HEADER =====
st.markdown("""
<style>
.main-header {
    background: #0176d3;
    padding: 1rem;
    border-radius: 0.5rem;
    color: white;
    text-align: center;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)
st.markdown('<div class="main-header"><h1>Project Dashboard</h1></div>', unsafe_allow_html=True)

# ===== SIDEBAR: DATA & PROJECT PARAMETERS =====
st.sidebar.header("📁 데이터 업로드 및 설정")
uploaded = st.sidebar.file_uploader("Raw CSV 선택", type="csv")
use_sample = st.sidebar.checkbox("샘플 데이터 사용")
if use_sample:
    raw = pd.DataFrame([{
        "프로젝트ID":"P001","데이터 ID":"T001","작업 상태":"완료","작업불가여부":"N",
        "최종 오브젝트 수":20,"수정 여부":2,"유효 오브젝트 수":18,
        "Worker ID":"W001","작업자 닉네임":"김민수","Checker ID":"C001","검수자 닉네임":"이영희",
        "작업 종료일":"2025-08-01","검수 종료일":"2025-08-02","작업 수정 시간":120,
        "CO 모니터링 URL":"http://example.com"
    } for _ in range(100)])
elif uploaded:
    raw = pd.read_csv(uploaded, dtype=str)
else:
    st.info("CSV를 업로드하거나 샘플 데이터를 선택하세요.")
    st.stop()

# ===== PARAMETER INPUTS =====
st.sidebar.header("⚙️ 프로젝트 설정")
total_qty       = st.sidebar.number_input("작업 총 수량", min_value=0, value=1000)
completed_qty   = st.sidebar.number_input("완료 수량", min_value=0, value=400)
open_date       = st.sidebar.date_input("오픈일", value=date.today() - timedelta(days=30))
target_end_date = st.sidebar.date_input("목표 종료일", value=date.today() + timedelta(days=30))
daily_target    = st.sidebar.number_input("1일 처리 목표 건수", min_value=1, value=20)

# ===== DATA CLEANING =====
STANDARD_COLUMNS = {
    "프로젝트ID":"project_id","데이터 ID":"task_id","작업 상태":"status","작업불가여부":"blocked",
    "최종 오브젝트 수":"annotations_completed","수정 여부":"rework_required","유효 오브젝트 수":"valid_count",
    "Worker ID":"annotator_id","작업자 닉네임":"annotator_name","Checker ID":"checker_id",
    "검수자 닉네임":"checker_name","작업 종료일":"date","검수 종료일":"review_date",
    "작업 수정 시간":"time_spent_minutes","CO 모니터링 URL":"monitor_url"
}
df = raw.rename(columns=STANDARD_COLUMNS)[list(STANDARD_COLUMNS.values())].copy()
df["date"]         = pd.to_datetime(df["date"], errors="coerce")
df["review_date"]  = pd.to_datetime(df["review_date"], errors="coerce")
for col in ["annotations_completed","rework_required","valid_count","time_spent_minutes"]:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
start_date = st.sidebar.date_input("분석 기간 시작", value=open_date)
end_date   = st.sidebar.date_input("분석 기간 종료", value=target_end_date)
df = df[(df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)]
project_ids = df["project_id"].unique()
sel_proj = st.sidebar.selectbox("프로젝트 선택", project_ids)
df = df[df["project_id"] == sel_proj]

# ===== DERIVED METRICS =====
remaining_qty    = total_qty - completed_qty
progress_pct     = completed_qty / total_qty if total_qty>0 else 0
remaining_days   = (target_end_date - date.today()).days
avg_per_day      = completed_qty / ( (date.today() - open_date).days ) if (date.today()-open_date).days>0 else 0
predicted_end_qty= avg_per_day * (remaining_days + (date.today()-open_date).days)
predicted_pct    = predicted_end_qty / total_qty if total_qty>0 else 0

# KPI CALC: per-hour, rework, annotators
df["week_number"]    = df["date"].dt.isocalendar().week
df["month"]          = df["date"].dt.month
df["week_of_month"]  = ((df["date"].dt.day - 1)//7)+1
df["week_label"]     = df["month"].astype(str)+"월 "+df["week_of_month"].astype(str)+"주차"
df["time_hours"]     = df["time_spent_minutes"]/60
# Worker stats
worker = st.sidebar.selectbox("작업자 선택", df["annotator_name"].unique())
wdf = df[df["annotator_name"]==worker]
total_time_h = wdf["time_hours"].sum()
hourly_rate = (daily_target*20)/8  # placeholder: 20 처리 기준
reject_rate= wdf["rework_required"].sum()/ wdf["annotations_completed"].sum() if wdf["annotations_completed"].sum()>0 else 0
activity_rate= total_time_h/((date.today()-open_date).days*8) if (date.today()-open_date).days>0 else 0

# ===== DASHBOARD =====
st.markdown("## 📈 프로젝트 주요 수치")
col1,col2,col3,col4 = st.columns(4)
col1.metric("잔여 수량", f"{remaining_qty}")
col2.metric("진행률", f"{progress_pct:.1%}")
col3.metric("잔여일", f"{remaining_days}")
col4.metric("예상 완료율", f"{predicted_pct:.1%}")

# Weekly progress: 작업 vs 검수
st.markdown("## 📅 주별 진행 현황")
weekly = df.groupby(["week_label"]).agg(
    work_actual=("annotations_completed","sum"),
    work_target=("annotations_completed", lambda x: daily_target*7),
    review_actual=("valid_count","sum"),
    review_target=("valid_count", lambda x: daily_target*7*0.8)
).reset_index()
weekly["work_pct"]   = weekly["work_actual"]/weekly["work_target"]
weekly["work_pred"]  = (weekly["work_actual"].cumsum()/weekly["work_target"].cumsum())
weekly["rev_pct"]    = weekly["review_actual"]/weekly["review_target"]
weekly["rev_pred"]   = (weekly["review_actual"].cumsum()/weekly["review_target"].cumsum())
fig = px.bar(weekly, x="week_label",
             y=["work_actual","work_target","review_actual","review_target"],
             barmode="group", title="주별 작업/검수: 실제 vs 목표")
st.plotly_chart(fig, use_container_width=True)

# Worker status
st.markdown("## 👥 작업자 현황")
col1, col2, col3 = st.columns(3)
col1.metric("총 참여시간(hr)", f"{total_time_h:.1f}")
col2.metric("시급(원)", f"{hourly_rate}")
col3.metric("반려율", f"{reject_rate:.1%}")
flag = "정상"
if reject_rate>=0.3 or activity_rate<=0.5:
    flag="이상 참여자"
st.write(f"**상태: {flag}**")
