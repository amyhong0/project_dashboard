# annotation-dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import date

st.set_page_config(page_title="Project Dashboard", layout="wide")

# HEADER
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

# SIDEBAR INPUTS
st.sidebar.header("📁 데이터 및 파라미터")
uploaded = st.sidebar.file_uploader("export.csv 업로드", type="csv")
if not uploaded:
    st.info("export.csv 파일을 업로드하세요.")
    st.stop()
raw = pd.read_csv(uploaded, dtype=str)

st.sidebar.header("⚙️ 프로젝트 설정")
open_date       = st.sidebar.date_input("오픈일", value=date.today())
target_end_date = st.sidebar.date_input("목표 종료일", value=date.today())
daily_target    = st.sidebar.number_input("1일 처리 목표 건수", value=20, min_value=1)
unit_price      = st.sidebar.number_input("작업 건당 단가(원)", value=100, min_value=0)
review_price    = st.sidebar.number_input("검수 건당 단가(원)", value=50, min_value=0)

# DATA CLEANING
# Rename and select relevant columns
df = raw.rename(columns={
    "프로젝트ID":"project_id",
    "데이터 ID":"data_id",
    "작업 상태":"status",
    "작업불가여부":"blocked",
    "최종 오브젝트 수":"annotations_completed",
    "수정 여부":"rework_required",
    "유효 오브젝트 수":"valid_count",
    "Worker ID":"worker_id",
    "작업자 닉네임":"worker_name",
    "Checker ID":"checker_id",
    "검수자 닉네임":"checker_name",
    "작업 종료일":"work_date",
    "검수 종료일":"review_date",
    "작업 수정 시간":"work_time_minutes"
})[[
    "data_id","status","annotations_completed","valid_count","rework_required",
    "worker_id","worker_name","checker_id","checker_name",
    "work_date","review_date","work_time_minutes"
]].copy()

# Type conversion
df["work_date"]       = pd.to_datetime(df["work_date"], errors="coerce")
df["review_date"]     = pd.to_datetime(df["review_date"], errors="coerce")
df["annotations_completed"] = pd.to_numeric(df["annotations_completed"], errors="coerce").fillna(0).astype(int)
df["valid_count"]           = pd.to_numeric(df["valid_count"], errors="coerce").fillna(0).astype(int)
df["rework_required"]       = pd.to_numeric(df["rework_required"], errors="coerce").fillna(0).astype(int)
df["work_time_minutes"]     = pd.to_numeric(df["work_time_minutes"], errors="coerce").fillna(0).astype(int)

# Filter by date
df = df[(df["work_date"].dt.date >= open_date) & (df["work_date"].dt.date <= target_end_date)]

# WORKER METRICS
wd = df.groupby(["worker_id","worker_name"]).agg(
    tasks=("data_id","count"),
    completed=("annotations_completed","sum"),
    rework=("rework_required","sum"),
    work_time=("work_time_minutes","sum")
).reset_index()
wd["hours"]        = wd["work_time"]/60
active_days        = (target_end_date - open_date).days + 1
wd["daily_avg"]    = wd["completed"]/active_days
wd["avg_per_task"]= wd["hours"]/wd["tasks"].replace(0, np.nan)
wd["hourly_rate"] = wd["daily_avg"] * unit_price
wd["reject_rate"] = wd["rework"]/wd["completed"].replace(0, np.nan)
wd["activity_rate"]= wd["hours"]/(active_days*8)
wd["abnormal"]    = (wd["reject_rate"]>=0.3)|(wd["activity_rate"]<=0.5)

# CHECKER METRICS
cd = df.groupby(["checker_id","checker_name"]).agg(
    reviews=("data_id","count"),
    valid=("valid_count","sum"),
    review_time=("review_date","count")  # count as proxy
).reset_index()
cd["reviews"]       = cd["reviews"]
cd["hours"]         = cd["review_time"]  # proxy for time
cd["daily_avg"]     = cd["reviews"]/active_days
cd["hourly_rate"]   = cd["daily_avg"] * review_price
cd["error_rate"]    = 1 - (cd["valid"]/cd["reviews"].replace(0, np.nan))
cd["activity_rate"]= cd["hours"]/(active_days*8)
cd["abnormal"]     = (cd["error_rate"]>=0.3)|(cd["activity_rate"]<=0.5)

# DASHBOARD DISPLAY
st.markdown("## 👥 작업자 현황")
st.dataframe(wd[[
    "worker_id","worker_name","activity_rate","hourly_rate",
    "reject_rate","completed","hours","avg_per_task","daily_avg","abnormal"
]])
st.markdown("평균(전체) — 활성률: {:.1%}, 시급: {:.0f}, 반려율: {:.1%}, 작업수: {:.0f}".format(
    wd["activity_rate"].mean(), wd["hourly_rate"].mean(),
    wd["reject_rate"].mean(), wd["completed"].mean()
))
st.markdown("평균(활성) — 활성률: {:.1%}, 시급: {:.0f}, 반려율: {:.1%}, 작업수: {:.0f}".format(
    wd.loc[~wd["abnormal"],"activity_rate"].mean(),
    wd.loc[~wd["abnormal"],"hourly_rate"].mean(),
    wd.loc[~wd["abnormal"],"reject_rate"].mean(),
    wd.loc[~wd["abnormal"],"completed"].mean()
))

st.markdown("## 👥 검수자 현황")
st.dataframe(cd[[
    "checker_id","checker_name","activity_rate","hourly_rate",
    "error_rate","reviews","hours","daily_avg","abnormal"
]])
st.markdown("평균(전체) — 활성률: {:.1%}, 시급: {:.0f}, 오류율: {:.1%}, 검수수: {:.0f}".format(
    cd["activity_rate"].mean(), cd["hourly_rate"].mean(),
    cd["error_rate"].mean(), cd["reviews"].mean()
))
st.markdown("평균(활성) — 활성률: {:.1%}, 시급: {:.0f}, 오류율: {:.1%}, 검수수: {:.0f}".format(
    cd.loc[~cd["abnormal"],"activity_rate"].mean(),
    cd.loc[~cd["abnormal"],"hourly_rate"].mean(),
    cd.loc[~cd["abnormal"],"error_rate"].mean(),
    cd.loc[~cd["abnormal"],"reviews"].mean()
))

# Visualize counts
fig = px.bar(x=["작업자","검수자"], y=[wd.shape[0], cd.shape[0]],
             labels={"x":"역할","y":"인원 수"}, title="작업자 vs 검수자 수")
st.plotly_chart(fig, use_container_width=True)
