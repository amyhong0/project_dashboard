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

df["work_date"]       = pd.to_datetime(df["work_date"], errors="coerce")
df["review_date"]     = pd.to_datetime(df["review_date"], errors="coerce")
df["annotations_completed"] = pd.to_numeric(df["annotations_completed"], errors="coerce").fillna(0).astype(int)
df["valid_count"]           = pd.to_numeric(df["valid_count"], errors="coerce").fillna(0).astype(int)
df["rework_required"]       = pd.to_numeric(df["rework_required"], errors="coerce").fillna(0).astype(int)
df["work_time_minutes"]     = pd.to_numeric(df["work_time_minutes"], errors="coerce").fillna(0).astype(int)

df = df[(df["work_date"].dt.date >= open_date) & (df["work_date"].dt.date <= target_end_date)]
active_days = (target_end_date - open_date).days + 1
dates = pd.date_range(open_date, target_end_date)

# PROJECT OVERVIEW CALCULATIONS
completed_qty = df["data_id"].nunique()
remaining_qty = total_data_qty - completed_qty
progress_pct = completed_qty / total_data_qty
remaining_days = (target_end_date - date.today()).days
elapsed_days = (date.today() - open_date).days + 1
daily_avg = completed_qty / elapsed_days if elapsed_days > 0 else 0
predicted_total = daily_avg * active_days
predicted_pct = predicted_total / total_data_qty if total_data_qty > 0 else 0

# PROJECT OVERVIEW DISPLAY
st.markdown("## 📊 전체 프로젝트 현황")
c1, c2, c3, c4 = st.columns(4)
c1.metric("데이터 총 수량", f"{total_data_qty:,}")
c2.metric("완료 수량", f"{completed_qty:,}")
c3.metric("잔여 수량", f"{remaining_qty:,}")
c4.metric("진행률", f"{progress_pct:.1%}")
c5, c6, c7, c8 = st.columns(4)
c5.metric("잔여일", f"{remaining_days}")
c6.metric("1일 처리 목표", f"{daily_target:,}")
c7.metric("1일 처리 평균", f"{daily_avg:.1f}")
c8.metric("예상 완료율", f"{predicted_pct:.1%}")

# PROJECT PROGRESSION CHART
daily_done = df.groupby(df["work_date"].dt.date)["data_id"].nunique().reindex(dates.date, fill_value=0).cumsum().reset_index()
daily_done.columns = ["date","cumulative"]
target_line = pd.DataFrame({
    "date": dates.date,
    "cumulative": np.linspace(0, total_data_qty, len(dates))
})
fig_proj = px.line(daily_done, x="date", y="cumulative", title="프로젝트 진행 추이")
fig_proj.add_scatter(x=target_line["date"], y=target_line["cumulative"], mode="lines", name="목표 진행선")
st.plotly_chart(fig_proj, use_container_width=True)

# WORKER METRICS
wd = df.groupby(["worker_id","worker_name"]).agg(
    completed=("annotations_completed","sum"),
    rework=("rework_required","sum"),
    work_time=("work_time_minutes","sum")
).reset_index()
wd["hours"]        = wd["work_time"]/60
wd["daily_avg"]    = wd["completed"]/active_days
wd["hourly_rate"]  = (wd["completed"]/wd["hours"].replace(0,np.nan))*unit_price
wd["reject_rate"]  = wd["rework"]/wd["completed"].replace(0,np.nan)
wd["activity_rate"]= wd["hours"]/(active_days*8)
wd["reject_rate"]  = wd["reject_rate"].clip(lower=0)
wd["reject_rate_pct"]   = wd["reject_rate"]*100
wd["activity_rate_pct"]= wd["activity_rate"]*100

st.markdown("## 👥 작업자 현황")
fig_w = px.bar(wd, x="worker_name", y="completed", title="작업량 by 작업자")
st.plotly_chart(fig_w, use_container_width=True)
st.dataframe(wd[[
    "worker_id","worker_name","activity_rate_pct","hourly_rate",
    "reject_rate_pct","completed","hours","daily_avg"
]].rename(columns={
    "worker_id":"ID","worker_name":"닉네임","activity_rate_pct":"활성률(%)",
    "hourly_rate":"시급(원)","reject_rate_pct":"반려율(%)","completed":"작업수량",
    "hours":"참여시간(시간)","daily_avg":"일평균"
}), use_container_width=True)

# CHECKER METRICS
cd = df.groupby(["checker_id","checker_name"]).agg(
    reviews=("data_id","count"),
    valid=("valid_count","sum")
).reset_index()
cd["hours"]         = cd["reviews"]  # proxy
cd["daily_avg"]     = cd["reviews"]/active_days
cd["hourly_rate"]   = (cd["reviews"]/cd["hours"].replace(0,np.nan))*review_price
cd["error_rate"]    = (cd["reviews"]-cd["valid"])/cd["reviews"].replace(0,np.nan)
cd["activity_rate"] = cd["hours"]/(active_days*8)
cd["error_rate"]    = cd["error_rate"].clip(lower=0)
cd["error_rate_pct"]= cd["error_rate"]*100
cd["activity_rate_pct"]= cd["activity_rate"]*100

st.markdown("## 👥 검수자 현황")
fig_c = px.bar(cd, x="checker_name", y="reviews", title="검수량 by 검수자")
st.plotly_chart(fig_c, use_container_width=True)
st.dataframe(cd[[
    "checker_id","checker_name","activity_rate_pct","hourly_rate",
    "error_rate_pct","reviews","hours","daily_avg"
]].rename(columns={
    "checker_id":"ID","checker_name":"닉네임","activity_rate_pct":"활성률(%)",
    "hourly_rate":"시급(원)","error_rate_pct":"오류율(%)","reviews":"검수수량",
    "hours":"참여시간(시간)","daily_avg":"일평균"
}), use_container_width=True)



# … (기존 코드 유지) …

# ===== 주별 진척률 =====
st.markdown("## 📊 주별 진척률")
# 실제 작업량
weekly_work = df.groupby(df["work_date"].dt.to_period("W")).agg(
    work_actual=("annotations_completed", "sum")
).reset_index()
weekly_work["week_start"] = weekly_work["work_date"].dt.start_time.dt.date
weekly_work["week_label"] = weekly_work["week_start"].apply(lambda d: f"{d.month}월 {((d.day-1)//7)+1}주차")
# 예상 작업량 (주 단위 목표)
weekly_work["work_target"] = daily_target * 7
weekly_work["work_pct"] = weekly_work["work_actual"] / weekly_work["work_target"]

# 실제 검수량
weekly_review = df.groupby(df["work_date"].dt.to_period("W")).agg(
    review_actual=("valid_count", "sum")
).reset_index()
weekly_review["week_start"] = weekly_review["work_date"].dt.start_time.dt.date
weekly_review["week_label"] = weekly_review["week_start"].apply(lambda d: f"{d.month}월 {((d.day-1)//7)+1}주차")
weekly_review["review_target"] = daily_target * 7 * 0.8
weekly_review["review_pct"] = weekly_review["review_actual"] / weekly_review["review_target"]

# 검수 대기건수
# 작업 완료됐으나 review_date가 NaT인 건수
wait = df[df["annotations_completed"]>0 & df["review_date"].isna()]
weekly_wait = wait.groupby(wait["work_date"].dt.to_period("W")).agg(
    review_wait=("data_id", "count")
).reset_index()
weekly_wait["week_start"] = weekly_wait["work_date"].dt.start_time.dt.date
weekly_wait["week_label"] = weekly_wait["week_start"].apply(lambda d: f"{d.month}월 {((d.day-1)//7)+1}주차")

# 병합
weekly = pd.merge(weekly_work, weekly_review[["week_label","review_actual","review_target","review_pct"]], on="week_label")
weekly = pd.merge(weekly, weekly_wait[["week_label","review_wait"]], on="week_label", how="left").fillna(0)

fig = px.bar(
    weekly,
    x="week_label",
    y=["work_actual","work_target","review_actual","review_target","review_wait"],
    barmode="group",
    title="주별 진척률: 작업 vs 검수"
)
fig.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig, use_container_width=True)

# ===== 작업자 현황 요약 =====
st.markdown("## 📝 작업자 현황 요약")
# 전체 작업자 기준
total_summary = {
    "활성률": f"{wd['activity_rate_pct'].mean():.1f}%",
    "시급": f"{wd['hourly_rate'].mean():.0f}원",
    "반려율": f"{wd['reject_rate_pct'].mean():.1f}%",
    "작업수량": f"{wd['completed'].mean():.0f}"
}
# 활성 작업자 기준
active = wd[~wd["abnormal"]]
active_summary = {
    "활성률": f"{active['activity_rate_pct'].mean():.1f}%",
    "시급": f"{active['hourly_rate'].mean():.0f}원",
    "반려율": f"{active['reject_rate_pct'].mean():.1f}%",
    "작업수량": f"{active['completed'].mean():.0f}"
}
st.write("**전체 작업자 평균:**", total_summary)
st.write("**활성 작업자 평균:**", active_summary)

# ===== 검수자 현황 요약 =====
st.markdown("## 📝 검수자 현황 요약")
# 전체 검수자 기준
total_summary_c = {
    "활성률": f"{cd['activity_rate_pct'].mean():.1f}%",
    "시급": f"{cd['hourly_rate'].mean():.0f}원",
    "오류율": f"{cd['error_rate_pct'].mean():.1f}%",
    "검수수량": f"{cd['reviews'].mean():.0f}"
}
# 활성 검수자 기준
active_c = cd[~cd["abnormal"]]
active_summary_c = {
    "활성률": f"{active_c['activity_rate_pct'].mean():.1f}%",
    "시급": f"{active_c['hourly_rate'].mean():.0f}원",
    "오류율": f"{active_c['error_rate_pct'].mean():.1f}%",
    "검수수량": f"{active_c['reviews'].mean():.0f}"
}
st.write("**전체 검수자 평균:**", total_summary_c)
st.write("**활성 검수자 평균:**", active_summary_c)

