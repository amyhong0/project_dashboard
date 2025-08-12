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
.main-header {background: #0176d3; padding: 1rem; border-radius: 0.5rem;
             color: white; text-align: center; margin-bottom: 1rem;}
</style>
""", unsafe_allow_html=True)
st.markdown('<div class="main-header"><h1>Project Dashboard</h1></div>', unsafe_allow_html=True)

# ===== SIDEBAR INPUTS =====
st.sidebar.header("📁 데이터 & 파라미터")
uploaded = st.sidebar.file_uploader("Raw CSV 선택", type="csv")
use_sample = st.sidebar.checkbox("샘플 데이터 사용")
if use_sample:
    raw = pd.DataFrame([{
        "프로젝트ID":"P001","데이터 ID":"T001","작업 상태":"완료","작업불가여부":"N",
        "최종 오브젝트 수":20,"수정 여부":2,"유효 오브젝트 수":18,
        "Worker ID":"W001","작업자 닉네임":"김민수","Checker ID":"C001","검수자 닉네임":"이영희",
        "작업 종료일":(date.today()-timedelta(days=np.random.randint(1,30))).isoformat(),
        "검수 종료일":(date.today()-timedelta(days=np.random.randint(0,29))).isoformat(),
        "작업 수정 시간":120,"CO 모니터링 URL":"http://"}
        for _ in range(200)])
elif uploaded:
    raw = pd.read_csv(uploaded, dtype=str)
else:
    st.info("CSV를 업로드하거나 샘플 데이터를 선택하세요.")
    st.stop()

# 프로젝트 파라미터
st.sidebar.header("⚙️ 프로젝트 설정")
total_qty       = st.sidebar.number_input("작업 총 수량", value=1000, step=1, min_value=0)
completed_qty   = st.sidebar.number_input("완료 수량", value=400, step=1, min_value=0, max_value=total_qty)
open_date       = st.sidebar.date_input("오픈일", value=date.today()-timedelta(days=30))
target_end_date = st.sidebar.date_input("목표 종료일", value=date.today()+timedelta(days=30))
daily_target    = st.sidebar.number_input("1일 처리 목표 건수", value=20, step=1, min_value=1)
unit_price      = st.sidebar.number_input("건당 단가(원)", value=100, step=100, min_value=0)

# ===== DATA CLEAN & DERIVE =====
cols_map = {
  "프로젝트ID":"project_id","데이터 ID":"task_id","작업 상태":"status","작업불가여부":"blocked",
  "최종 오브젝트 수":"annotations_completed","수정 여부":"rework_required","유효 오브젝트 수":"valid_count",
  "Worker ID":"annotator_id","작업자 닉네임":"annotator_name","Checker ID":"checker_id","검수자 닉네임":"checker_name",
  "작업 종료일":"date","검수 종료일":"review_date","작업 수정 시간":"time_spent_minutes","CO 모니터링 URL":"monitor_url"
}
df = raw.rename(columns=cols_map)[list(cols_map.values())].copy()
df["date"]        = pd.to_datetime(df["date"], errors="coerce")
df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce")
for c in ["annotations_completed","rework_required","valid_count","time_spent_minutes"]:
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

# filter project
project_ids = df["project_id"].unique()
sel_proj = st.sidebar.selectbox("프로젝트 선택", project_ids)
df = df[df["project_id"]==sel_proj]

# period = open to target_end
df = df[(df["date"].dt.date>=open_date)&(df["date"].dt.date<=target_end_date)]
period_days = (target_end_date - open_date).days + 1

# week label mm월 n주차
df["month"]         = df["date"].dt.month
df["week_of_month"] = ((df["date"].dt.day-1)//7)+1
df["week_label"]    = df["month"].astype(str)+"월 "+df["week_of_month"].astype(str)+"주차"

# ===== PROJECT KPI CALC =====
remaining_qty  = total_qty - completed_qty
progress_pct   = completed_qty/total_qty if total_qty>0 else 0
remaining_days = (target_end_date - date.today()).days
# predicted end qty based on avg per day
elapsed_days   = (date.today()-open_date).days+1
avg_per_day    = completed_qty/elapsed_days if elapsed_days>0 else 0
predicted_qty  = avg_per_day*period_days
predicted_pct  = predicted_qty/total_qty if total_qty>0 else 0

# ===== DISPLAY: PROJECT KPIs =====
st.markdown("## 📈 프로젝트 주요 지표")
c1,c2,c3,c4 = st.columns(4)
c1.metric("잔여 수량", f"{remaining_qty}")
c2.metric("진행률", f"{progress_pct:.1%}")
c3.metric("잔여일", f"{remaining_days}")
c4.metric("예상 완료율", f"{predicted_pct:.1%}")

# ===== WEEKLY PROGRESS =====
weekly = df.groupby("week_label").agg(
    work_actual=("annotations_completed","sum"),
    work_target=lambda x: daily_target*7,
    review_actual=("valid_count","sum"),
    review_target=lambda x: daily_target*7*0.8
).reset_index()
weekly["work_pct"]  = weekly["work_actual"]/weekly["work_target"]
weekly["review_pct"]= weekly["review_actual"]/weekly["review_target"]
weekly["review_wait"] = df[df["review_date"].isna()].groupby("week_label")["task_id"].count().reindex(weekly["week_label"], fill_value=0).values

st.markdown("## 📅 주별 진행 현황")
fig_w = px.bar(weekly, x="week_label",
               y=["work_actual","work_target","review_actual","review_target"],
               barmode="group", title="주별 작업/검수 실적 vs 목표")
st.plotly_chart(fig_w, use_container_width=True)
with st.expander("주별 세부 지표", expanded=False):
    st.dataframe(weekly[[
        "week_label","work_actual","work_target","work_pct",
        "review_actual","review_target","review_pct","review_wait"
    ]])

# ===== WORKER OVERVIEW =====
st.markdown("## 👥 작업자 전체 현황")
wd = df.groupby("annotator_name").agg(
    work_sum=("annotations_completed","sum"),
    review_sum=("valid_count","sum"),
    rework_sum=("rework_required","sum"),
    time_sum=("time_spent_minutes","sum"),
    last_date=("date","max")
).reset_index()
wd["time_hr"]      = wd["time_sum"]/60
wd["avg_per_hr"]   = wd["work_sum"]/wd["time_hr"].replace(0,np.nan)
wd["hourly_rate"]  = wd["avg_per_hr"]*unit_price
wd["reject_rate"]  = wd["rework_sum"]/wd["work_sum"].replace(0,np.nan)
wd["days_active"]  = (date.today()-open_date).days+1
wd["activity_rate"]= wd["time_sum"]/60/(wd["days_active"]*8)
avg_activity       = wd["activity_rate"].mean()
avg_reject         = wd["reject_rate"].mean()

def flag(r):
    return (r["reject_rate"]>=0.3)|(r["activity_rate"]<=0.5)
wd["abnormal"] = wd.apply(flag,axis=1)

with st.expander("작업자 상세 현황", expanded=False):
    st.dataframe(wd[[
        "annotator_name","work_sum","review_sum","time_hr","avg_per_hr",
        "hourly_rate","reject_rate","activity_rate","last_date","abnormal"
    ]])
st.write(f"*평균 활성률: {avg_activity:.1%}, 평균 반려율: {avg_reject:.1%}*")
