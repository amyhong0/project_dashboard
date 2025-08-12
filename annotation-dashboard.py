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
total_data_qty  = st.sidebar.number_input("데이터 총 수량", value=1000, min_value=1)
open_date       = st.sidebar.date_input("오픈일", value=date.today())
target_end_date = st.sidebar.date_input("목표 종료일", value=date.today())
daily_target    = st.sidebar.number_input("1일 처리 목표 건수", value=20, min_value=1)
unit_price      = st.sidebar.number_input("작업 건당 단가(원)", value=100, min_value=0)
review_price    = st.sidebar.number_input("검수 건당 단가(원)", value=50, min_value=0)

# DATA CLEANING
df = raw.rename(columns={
    "프로젝트ID":"project_id","데이터 ID":"data_id","작업 상태":"status",
    "작업불가여부":"blocked","최종 오브젝트 수":"annotations_completed",
    "수정 여부":"rework_required","유효 오브젝트 수":"valid_count",
    "Worker ID":"worker_id","작업자 닉네임":"worker_name","Checker ID":"checker_id",
    "검수자 닉네임":"checker_name","작업 종료일":"work_date","검수 종료일":"review_date",
    "작업 수정 시간":"work_time_minutes"
})[[
    "data_id","status","annotations_completed","valid_count","rework_required",
    "worker_id","worker_name","checker_id","checker_name",
    "work_date","review_date","work_time_minutes"
]].copy()

df["work_date"]       = pd.to_datetime(df["work_date"], errors="coerce")
df["review_date"]     = pd.to_datetime(df["review_date"], errors="coerce")
for col in ["annotations_completed","valid_count","rework_required","work_time_minutes"]:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

df = df[(df["work_date"].dt.date >= open_date) & (df["work_date"].dt.date <= target_end_date)]
active_days = (target_end_date - open_date).days + 1

# PROJECT OVERVIEW CALCULATIONS
completed_qty   = df["data_id"].nunique()
remaining_qty   = total_data_qty - completed_qty
progress_pct    = completed_qty/total_data_qty if total_data_qty>0 else 0
remaining_days  = (target_end_date - date.today()).days
elapsed_days    = (date.today() - open_date).days + 1
daily_avg       = completed_qty/elapsed_days if elapsed_days>0 else 0
predicted_total = daily_avg*active_days
predicted_pct   = predicted_total/total_data_qty if total_data_qty>0 else 0

# PROJECT OVERVIEW DISPLAY (reverted design)
st.markdown("## 📊 전체 프로젝트 현황")
col1, col2, col3, col4 = st.columns(4)
col1.metric("데이터 총 수량", f"{total_data_qty:,}")
col2.metric("완료 수량", f"{completed_qty:,}")
col3.metric("잔여 수량", f"{remaining_qty:,}")
col4.metric("진행률", f"{progress_pct:.1%}")
col5, col6, col7, col8 = st.columns(4)
col5.metric("잔여일", f"{remaining_days}")
col6.metric("1일 처리 목표", f"{daily_target:,}")
col7.metric("1일 처리 평균", f"{daily_avg:.1f}")
col8.metric("예상 완료율", f"{predicted_pct:.1%}")

# PROGRESSION CHART
dates = pd.date_range(open_date, target_end_date)
daily_done = df.groupby(df["work_date"].dt.date)["data_id"].nunique().reindex(dates.date, fill_value=0).cumsum().reset_index()
daily_done.columns = ["date","cumulative"]
target_line = pd.DataFrame({"date":dates.date,"cumulative":np.linspace(0,total_data_qty,len(dates))})
fig_proj = px.line(daily_done,x="date",y="cumulative",title="프로젝트 진행 추이")
fig_proj.add_scatter(x=target_line["date"],y=target_line["cumulative"],mode="lines",name="목표 진행선")
st.plotly_chart(fig_proj,use_container_width=True)

# WEEKLY PROGRESS
df["month"]=df["work_date"].dt.month
df["wom"]=((df["work_date"].dt.day-1)//7)+1
df["week_label"]=df["month"].astype(str)+"월 "+df["wom"].astype(str)+"주차"
weekly = df.groupby("week_label").agg(
    work_actual=("annotations_completed","sum"),
    review_actual=("valid_count","sum")
).reset_index()
weekly["work_target"]   = daily_target*7
weekly["review_target"] = daily_target*7*0.8
weekly["work_pct"]      = weekly["work_actual"]/weekly["work_target"]
weekly["review_pct"]    = weekly["review_actual"]/weekly["review_target"]
weekly["review_wait"]   = df[(df["annotations_completed"]>0)&df["review_date"].isna()]\
    .groupby("week_label")["data_id"].count().reindex(weekly["week_label"],fill_value=0).values

st.markdown("## 📊 주별 진척률")
# separate charts
fig_w1 = px.bar(weekly, x="week_label", y=["work_actual","work_target"], barmode="group", title="주별 작업: 실제 vs 목표")
fig_w1.update_xaxes(tickangle=-45)
st.plotly_chart(fig_w1,use_container_width=True)
fig_w2 = px.bar(weekly, x="week_label", y=["review_actual","review_target"], barmode="group", title="주별 검수: 실제 vs 목표")
fig_w2.update_xaxes(tickangle=-45)
st.plotly_chart(fig_w2,use_container_width=True)
# numeric table
st.table(weekly.assign(
    work_pct=weekly["work_pct"].map("{:.1%}".format),
    review_pct=weekly["review_pct"].map("{:.1%}".format)
)[[
    "week_label","work_actual","work_target","work_pct",
    "review_actual","review_target","review_pct","review_wait"
]].rename(columns={
    "week_label":"주차","work_actual":"작업실제","work_target":"작업목표","work_pct":"작업달성",
    "review_actual":"검수실제","review_target":"검수목표","review_pct":"검수달성","review_wait":"검수대기"
}))

# WORKER SUMMARY & DETAIL
wd=df.groupby(["worker_id","worker_name"]).agg(
    completed=("annotations_completed","sum"),
    rework=("rework_required","sum"),
    work_time=("work_time_minutes","sum")
).reset_index()
wd["hours"]=wd["work_time"]/60
wd["hourly_rate"]=(wd["completed"]/wd["hours"].replace(0,np.nan))*unit_price
wd["reject_rate"]=wd["rework"]/wd["completed"].replace(0,np.nan)
wd["activity_rate"]=wd["hours"]/(active_days*8)
wd["reject_rate"].clip(lower=0, inplace=True)
wd["reject_pct"]=wd["reject_rate"].map("{:.1%}".format)
wd["activity_pct"]=wd["activity_rate"].map("{:.1%}".format)
wd.sort_values("completed",ascending=False, inplace=True)

st.markdown("## 👥 작업자 현황")
fig_wd=px.bar(wd, x="worker_name", y="completed", title="작업량 by 작업자")
st.plotly_chart(fig_wd,use_container_width=True)
st.dataframe(wd[[
    "worker_id","worker_name","activity_pct","hourly_rate","reject_pct","completed"
]].rename(columns={
    "worker_id":"ID","worker_name":"닉네임","activity_pct":"활성률","hourly_rate":"시급(원)",
    "reject_pct":"반려율","completed":"작업수량"
}),use_container_width=True)

# CHECKER SUMMARY & DETAIL
cd=df.groupby(["checker_id","checker_name"]).agg(
    reviews=("data_id","count"),
    valid=("valid_count","sum")
).reset_index()
cd["hours"]=cd["reviews"]
cd["hourly_rate"]=(cd["reviews"]/cd["hours"].replace(0,np.nan))*review_price
cd["error_rate"]=((cd["reviews"]-cd["valid"])/cd["reviews"].replace(0,np.nan)).clip(lower=0)
cd["activity_rate"]=cd["hours"]/(active_days*8)
cd["error_pct"]=cd["error_rate"].map("{:.1%}".format)
cd["activity_pct"]=cd["activity_rate"].map("{:.1%}".format)
cd.sort_values("reviews",ascending=False, inplace=True)

st.markdown("## 👥 검수자 현황")
fig_cd=px.bar(cd, x="checker_name", y="reviews", title="검수량 by 검수자")
st.plotly_chart(fig_cd,use_container_width=True)
st.dataframe(cd[[
    "checker_id","checker_name","activity_pct","hourly_rate","error_pct","reviews"
]].rename(columns={
    "checker_id":"ID","checker_name":"닉네임","activity_pct":"활성률","hourly_rate":"시급(원)",
    "error_pct":"오류율","reviews":"검수수량"
}),use_container_width=True)

