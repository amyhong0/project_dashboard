# annotation-dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import date

st.set_page_config(page_title="Project Dashboard", layout="wide")

# STYLES
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
.project-metric {
    text-align: center;
    margin: 0.5rem;
}
.project-metric h4 {
    margin: 0;
    font-size: 1rem;
    color: #555;
}
.project-metric p {
    margin: 0;
    font-size: 2rem;
    font-weight: bold;
    color: #222;
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

st.sidebar.header("⚙️ 프로젝트 파라미터")
total_data_qty    = st.sidebar.number_input("데이터 총 수량", min_value=1, value=1000)
open_date         = st.sidebar.date_input("오픈일", value=date.today())
target_end_date   = st.sidebar.date_input("목표 종료일", value=date.today())
daily_work_target = st.sidebar.number_input("1일 작업 목표", min_value=1, value=20)
daily_review_target = st.sidebar.number_input("1일 검수 목표", min_value=1, value=16)
unit_price        = st.sidebar.number_input("작업 단가(원)", min_value=0, value=100)
review_price      = st.sidebar.number_input("검수 단가(원)", min_value=0, value=50)

# DATA CLEANING
df = raw.rename(columns={
    "데이터 ID":"data_id","최종 오브젝트 수":"annotations_completed","유효 오브젝트 수":"valid_count",
    "수정 여부":"rework_required","Worker ID":"worker_id","작업자 닉네임":"worker_name",
    "Checker ID":"checker_id","검수자 닉네임":"checker_name","작업 종료일":"work_date",
    "검수 종료일":"review_date","작업 수정 시간":"work_time_minutes"
})[[
    "data_id","annotations_completed","valid_count","rework_required",
    "worker_id","worker_name","checker_id","checker_name",
    "work_date","review_date","work_time_minutes"
]]
df["work_date"]   = pd.to_datetime(df["work_date"], errors="coerce")
df["review_date"]= pd.to_datetime(df["review_date"], errors="coerce")
for c in ["annotations_completed","valid_count","rework_required","work_time_minutes"]:
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
df = df[(df["work_date"].dt.date>=open_date)&(df["work_date"].dt.date<=target_end_date)]
active_days = (target_end_date-open_date).days+1

# PROJECT OVERVIEW
completed_qty   = df["data_id"].nunique()
remaining_qty   = total_data_qty-completed_qty
progress_pct    = completed_qty/total_data_qty
remaining_days  = (target_end_date-date.today()).days
elapsed_days    = (date.today()-open_date).days+1
daily_avg       = completed_qty/elapsed_days if elapsed_days>0 else 0
predicted_total = daily_avg*active_days
predicted_pct   = predicted_total/total_data_qty

st.markdown("## 📊 전체 프로젝트 현황")
c1,c2,c3,c4 = st.columns(4)
c1.markdown(f'<div class="metric-card"><h4>총 수량</h4><p>{total_data_qty:,}</p></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="metric-card"><h4>완료 수량</h4><p>{completed_qty:,}</p></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="metric-card"><h4>잔여 수량</h4><p>{remaining_qty:,}</p></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="metric-card"><h4>진행률</h4><p>{progress_pct:.1%}</p></div>', unsafe_allow_html=True)
c5,c6,c7,c8 = st.columns(4)
c5.markdown(f'<div class="metric-card"><h4>잔여일</h4><p>{remaining_days}</p></div>', unsafe_allow_html=True)
c6.markdown(f'<div class="metric-card"><h4>1일 작업 목표</h4><p>{daily_work_target:,}</p></div>', unsafe_allow_html=True)
c7.markdown(f'<div class="metric-card"><h4>1일 검수 목표</h4><p>{daily_review_target:,}</p></div>', unsafe_allow_html=True)
c8.markdown(f'<div class="metric-card"><h4>예상 완료율</h4><p>{predicted_pct:.1%}</p></div>', unsafe_allow_html=True)

# PROGRESSION CHART
dates = pd.date_range(open_date, target_end_date)
daily_done = df.groupby(df["work_date"].dt.date)["data_id"].nunique().reindex(dates.date, fill_value=0).cumsum().reset_index()
daily_done.columns = ["date","cumulative"]
target_line = pd.DataFrame({"date":dates.date,"cumulative":np.linspace(0,total_data_qty,len(dates))})
fig=px.line(daily_done, x="date", y="cumulative", title="프로젝트 진행 추이")
fig.add_scatter(x=target_line["date"], y=target_line["cumulative"], mode="lines", name="목표선")
st.plotly_chart(fig, use_container_width=True)

# WEEKLY PROGRESS
df["month"]=df["work_date"].dt.month
df["wom"]=((df["work_date"].dt.day-1)//7)+1
df["week_label"]=df["month"].astype(str)+"월 "+df["wom"].astype(str)+"주차"
weekly=df.groupby("week_label").agg(
    work_actual=("annotations_completed","sum"),
    review_actual=("valid_count","sum")
).reset_index()
weekly["work_target"]=daily_work_target*7
weekly["review_target"]=daily_review_target*7
weekly["work_pct"]=weekly["work_actual"]/weekly["work_target"]
weekly["review_pct"]=weekly["review_actual"]/weekly["review_target"]
weekly["review_wait"]=df[(df["annotations_completed"]>0)&df["review_date"].isna()]\
    .groupby("week_label")["data_id"].count().reindex(weekly["week_label"],fill_value=0).values

st.markdown("## 📊 주별 진척률")
fig1=px.bar(weekly, x="week_label", y=["work_actual","work_target"], barmode="group", title="주별 작업")
fig1.update_xaxes(tickangle=-45); st.plotly_chart(fig1,use_container_width=True)
st.table(weekly[["week_label","work_actual","work_target","work_pct"]]
         .assign(work_pct=lambda df: df["work_pct"].map("{:.1%}".format))
         .rename(columns={"week_label":"주차","work_actual":"실제","work_target":"목표","work_pct":"달성율"}))

fig2=px.bar(weekly, x="week_label", y=["review_actual","review_target"], barmode="group", title="주별 검수")
fig2.update_xaxes(tickangle=-45); st.plotly_chart(fig2,use_container_width=True)
st.table(weekly[["week_label","review_actual","review_target","review_pct","review_wait"]]
         .assign(review_pct=lambda df: df["review_pct"].map("{:.1%}".format))
         .rename(columns={"week_label":"주차","review_actual":"실제","review_target":"목표",
                          "review_pct":"달성율","review_wait":"대기수"}))

# WORKER METRICS
wd=df.groupby(["worker_id","worker_name"]).agg(
    completed=("annotations_completed","sum"),
    rework=("rework_required","sum"),
    work_time=("work_time_minutes","sum"),
    last_date=("work_date","max")
).reset_index()
wd["hours"]=wd["work_time"]/60
wd["per_hr"]=wd["completed"]/wd["hours"].replace(0,np.nan)
wd["hourly_rate"]= (wd["per_hr"].fillna(0) * unit_price).round(0).astype(int)
wd["avg_min_per_task"]=((wd["hours"]/wd["completed"].replace(0,np.nan))*60).round(0).astype(int)
wd["daily_min"]=((wd["hours"]/active_days)*60).round(0).astype(int)
wd["reject_rate"]= (wd["rework"]/wd["completed"].replace(0,np.nan)).clip(lower=0)
wd["activity_rate"]=wd["hours"]/(active_days*8)
wd["reject_pct"]=wd["reject_rate"].map("{:.1%}".format)
wd["activity_pct"]=wd["activity_rate"].map("{:.1%}".format)
wd["abnormal_flag"]=np.where((wd["reject_rate"]>=0.3)|(wd["activity_rate"]<=0.5),"Y","N")

st.markdown("## 👥 작업자 현황")
summary_w=pd.DataFrame({
    "구분":["전체 평균","활성 평균"],
    "활성률(%)":[wd["activity_rate"].mean(),wd[wd["abnormal_flag"]=="N"]["activity_rate"].mean()],
    "시급(원)":[wd["hourly_rate"].mean(),wd[wd["abnormal_flag"]=="N"]["hourly_rate"].mean()],
    "반려율(%)":[wd["reject_rate"].mean(),wd[wd["abnormal_flag"]=="N"]["reject_rate"].mean()],
    "작업수량":[wd["completed"].mean(),wd[wd["abnormal_flag"]=="N"]["completed"].mean()]
})
summary_w[["활성률(%)","반려율(%)"]]=summary_w[["활성률(%)","반려율(%)"]].applymap(lambda x:f"{x:.1%}")
summary_w["시급(원)"]=summary_w["시급(원)"].map("{:.0f}".format)
summary_w["작업수량"]=summary_w["작업수량"].map("{:.0f}".format)
st.table(summary_w)

fig_wd=px.bar(wd.sort_values("completed",ascending=False),x="worker_name",y="completed",title="작업량 by 작업자")
st.plotly_chart(fig_wd,use_container_width=True)
st.dataframe(wd.sort_values("completed",ascending=False)[[
    "worker_id","worker_name","activity_pct","hourly_rate","reject_pct","completed",
    "avg_min_per_task","daily_min","last_date","abnormal_flag"
]].rename(columns={
    "worker_id":"ID","worker_name":"닉네임","activity_pct":"활성률(%)","hourly_rate":"시급(원)",
    "reject_pct":"반려율(%)","completed":"작업수량","avg_min_per_task":"건당평균(분)",
    "daily_min":"일평균(분)","last_date":"마지막작업일","abnormal_flag":"이상참여자"
}).style.applymap(lambda v:'color:red;' if v=='Y' else '', subset=["이상참여자"]),use_container_width=True)

# CHECKER METRICS
cd=df.groupby(["checker_id","checker_name"]).agg(
    reviews=("data_id","count"),
    valid=("valid_count","sum"),
    last_date=("review_date","max")
).reset_index()
cd["hours"]=cd["reviews"]
cd["per_hr"]=cd["reviews"]/cd["hours"].replace(0,np.nan)
cd["hourly_rate"]= (cd["per_hr"].fillna(0) * review_price).round(0).astype(int)
cd["avg_min_per_task"]=((cd["hours"]/cd["reviews"].replace(0,np.nan))*60).round(0).astype(int)
cd["daily_min"]=((cd["hours"]/active_days)*60).round(0).astype(int)
cd["error_rate"]=((cd["reviews"]-cd["valid"])/cd["reviews"].replace(0,np.nan)).clip(lower=0)
cd["error_pct"]=cd["error_rate"].map("{:.1%}".format)
cd["activity_rate"]=cd["hours"]/(active_days*8)
cd["activity_pct"]=cd["activity_rate"].map("{:.1%}".format)
cd["abnormal_flag"]=np.where((cd["error_rate"]>=0.3)|(cd["activity_rate"]<=0.5),"Y","N")

st.markdown("## 👥 검수자 현황")
summary_c=pd.DataFrame({
    "구분":["전체 평균","활성 평균"],
    "활성률(%)":[cd["activity_rate"].mean(),cd[cd["abnormal_flag"]=="N"]["activity_rate"].mean()],
    "시급(원)":[cd["hourly_rate"].mean(),cd[cd["abnormal_flag"]=="N"]["hourly_rate"].mean()],
    "오류율(%)":[cd["error_rate"].mean(),cd[cd["abnormal_flag"]=="N"]["error_rate"].mean()],
    "검수수량":[cd["reviews"].mean(),cd[cd["abnormal_flag"]=="N"]["reviews"].mean()]
})
summary_c[["활성률(%)","오류율(%)"]]=summary_c[["활성률(%)","오류율(%)"]].applymap(lambda x:f"{x:.1%}")
summary_c["시급(원)"]=summary_c["시급(원)"].map("{:.0f}".format)
summary_c["검수수량"]=summary_c["검수수량"].map("{:.0f}".format)
st.table(summary_c)

fig_cd=px.bar(cd.sort_values("reviews",ascending=False),x="checker_name",y="reviews",title="검수량 by 검수자")
st.plotly_chart(fig_cd,use_container_width=True)
st.dataframe(cd.sort_values("reviews",ascending=False)[[
    "checker_id","checker_name","activity_pct","hourly_rate","error_pct","reviews",
    "avg_min_per_task","daily_min","last_date","abnormal_flag"
]].rename(columns={
    "checker_id":"ID","checker_name":"닉네임","activity_pct":"활성률(%)","hourly_rate":"시급(원)",
    "error_pct":"오류율(%)","reviews":"검수수량","avg_min_per_task":"건당평균(분)",
    "daily_min":"일평균(분)","last_date":"마지막검수일","abnormal_flag":"이상참여자"
}).style.applymap(lambda v:'color:red;' if v=='Y' else '', subset=["이상참여자"]),use_container_width=True)

