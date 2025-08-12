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

# ===== PROJECT SETTINGS =====
st.sidebar.header("⚙️ 프로젝트 설정")
total_qty       = st.sidebar.number_input("작업 총 수량", min_value=0, value=1000)
completed_qty   = st.sidebar.number_input("완료 수량", min_value=0, value=400)
open_date       = st.sidebar.date_input("오픈일", value=date.today()-timedelta(days=30))
target_end_date = st.sidebar.date_input("목표 종료일", value=date.today()+timedelta(days=30))
daily_target    = st.sidebar.number_input("1일 처리 목표 건수", min_value=1, value=20)

# ===== DATA CLEANING =====
# Column mapping
COLUMNS = {
    "프로젝트ID":"project_id","데이터 ID":"task_id","작업 상태":"status","작업불가여부":"blocked",
    "최종 오브젝트 수":"annotations_completed","수정 여부":"rework_required","유효 오브젝트 수":"valid_count",
    "Worker ID":"annotator_id","작업자 닉네임":"annotator_name","Checker ID":"checker_id",
    "검수자 닉네임":"checker_name","작업 종료일":"date","검수 종료일":"review_date",
    "작업 수정 시간":"time_spent_minutes","CO 모니터링 URL":"monitor_url"
}
df = raw.rename(columns=COLUMNS)[list(COLUMNS.values())].copy()
df["date"]        = pd.to_datetime(df["date"], errors="coerce")
df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce")
for col in ["annotations_completed","rework_required","valid_count","time_spent_minutes"]:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

# Filter by project and period
df = df[df["date"].dt.date.between(open_date, target_end_date)]
proj = st.sidebar.selectbox("프로젝트 선택", df["project_id"].unique())
df = df[df["project_id"]==proj]

# ===== DERIVED METRICS =====
remaining_qty    = total_qty - completed_qty
progress_pct     = completed_qty/total_qty if total_qty else 0
remaining_days   = (target_end_date - date.today()).days
elapsed_days     = (date.today()-open_date).days or 1
avg_per_day      = completed_qty/elapsed_days
predicted_total  = avg_per_day*((target_end_date-open_date).days or 1)
predicted_pct    = predicted_total/total_qty if total_qty else 0
# Weekly labels
df["week_of_month"] = ((df["date"].dt.day-1)//7)+1
df["week_label"]    = df["date"].dt.month.astype(str)+"월 "+df["week_of_month"].astype(str)+"주차"

# Weekly summaries
weekly = df.groupby("week_label").agg(
    work_actual=("annotations_completed","sum"),
    review_actual=("valid_count","sum"),
).reset_index()
weekly["work_target"]   = daily_target*7
weekly["review_target"] = daily_target*7*0.8
weekly["work_pct"]      = weekly["work_actual"]/weekly["work_target"]
weekly["review_pct"]    = weekly["review_actual"]/weekly["review_target"]
# Review waiting = tasks completed but no review_date
weekly["review_wait"] = df[df["review_date"].isna()].groupby(df["date"].dt.to_period("W").astype(str))["task_id"].count().reindex(weekly["week_label"], fill_value=0).values

# Worker overview
workers = df["annotator_name"].unique()
worker_stats = []
for w in workers:
    wdf = df[df["annotator_name"]==w]
    time_h = wdf["time_spent_minutes"].sum()/60
    qty = wdf["annotations_completed"].sum()
    rev = wdf["valid_count"].sum()
    reject_rate = wdf["rework_required"].sum()/qty if qty else 0
    days_active = wdf["date"].dt.date.nunique()
    active_rate = days_active/elapsed_days
    avg_time_per = time_h/qty if qty else 0
    avg_per_day_w = qty/days_active if days_active else 0
    worker_stats.append({
        "worker":w,"time_h":time_h,"qty":qty,"rev":rev,
        "reject_rate":reject_rate,"active_rate":active_rate,
        "avg_time_per":avg_time_per,"avg_per_day":avg_per_day_w
    })
wdf_stats = pd.DataFrame(worker_stats)
avg_stats = wdf_stats.mean(numeric_only=True)

# ===== DASHBOARD =====
st.markdown("## 📈 프로젝트 주요 수치")
c1,c2,c3,c4 = st.columns(4)
c1.metric("잔여 수량", remaining_qty)
c2.metric("진행률", f"{progress_pct:.1%}")
c3.metric("잔여일", remaining_days)
c4.metric("예상 완료율", f"{predicted_pct:.1%}")

# Weekly progress chart
st.markdown("## 📅 주별 진행 현황")
fig = px.bar(weekly, x="week_label",
             y=["work_actual","work_target","review_actual","review_target"],
             barmode="group",
             labels={"value":"건수","week_label":"주차"},
             title="Weekly: 작업 vs 검수 (실제 vs 목표)")
st.plotly_chart(fig, use_container_width=True)
with st.expander("주별 세부 테이블", expanded=False):
    st.dataframe(weekly[["week_label","work_actual","work_target","work_pct",
                         "review_actual","review_target","review_pct","review_wait"]])

# Worker overview table
st.markdown("## 👥 작업자 전체 현황")
cols = st.columns(4)
cols[0].metric("평균 활성률", f"{avg_stats['active_rate']:.1%}")
cols[1].metric("평균 시급", f"{(daily_target*20)/8:.0f}원")
cols[2].metric("평균 반려율", f"{avg_stats['reject_rate']:.1%}")
cols[3].metric("평균 작업/검수 건수", f"{avg_stats['qty']+avg_stats['rev']:.1f}")

st.dataframe(wdf_stats.style.apply(
    lambda row: ["background:red" if (row.reject_rate>=0.3 or row.active_rate<=0.5) else "" for _ in row],
    axis=1
))

# End of dashboard
