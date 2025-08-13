# annotation-dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import date

st.set_page_config(page_title="Project Dashboard", layout="wide")

# HEADER
st.markdown('<h1 style="text-align:center; color:#333;">Project Dashboard</h1>', unsafe_allow_html=True)

# SIDEBAR
st.sidebar.header("📁 데이터 및 파라미터")
uploaded = st.sidebar.file_uploader("export.csv 업로드", type="csv")
if not uploaded:
    st.info("export.csv 파일을 업로드하세요.")
    st.stop()
raw = pd.read_csv(uploaded, dtype=str)

st.sidebar.header("⚙️ 프로젝트 파라미터")
total_data_qty      = st.sidebar.number_input("데이터 총 수량", 1, 100000, 1000)
open_date           = st.sidebar.date_input("오픈일", date.today())
target_end_date     = st.sidebar.date_input("목표 종료일", date.today())
daily_work_target   = st.sidebar.number_input("1일 작업 목표", 1, 10000, 20)
daily_review_target = st.sidebar.number_input("1일 검수 목표", 1, 10000, 16)
unit_price          = st.sidebar.number_input("작업 단가(원)", 0, 100000, 100)
review_price        = st.sidebar.number_input("검수 단가(원)", 0, 100000, 50)

# DATA CLEANING
df = raw.rename(columns={
    "데이터 ID":"data_id","최종 오브젝트 수":"annotations_completed","유효 오브젝트 수":"valid_count",
    "수정 여부":"rework_required","Worker ID":"worker_id","작업자 닉네임":"worker_name",
    "Checker ID":"checker_id","검수자 닉네임":"checker_name","작업 종료일":"work_date",
    "검수 종료일":"review_date","작업 수정 시간":"work_time_minutes"
})
df["work_date"]   = pd.to_datetime(df["work_date"], errors="coerce")
df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce")
for c in ["annotations_completed","valid_count","rework_required","work_time_minutes"]:
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
df = df[(df["work_date"].dt.date>=open_date)&(df["work_date"].dt.date<=target_end_date)]
active_days = (target_end_date-open_date).days+1

# PROJECT OVERVIEW
completed_qty   = df["data_id"].nunique()
remaining_qty   = total_data_qty-completed_qty
progress_pct    = completed_qty/total_data_qty if total_data_qty else 0
remaining_days  = (target_end_date-date.today()).days
elapsed_days    = (date.today()-open_date).days+1
daily_avg       = completed_qty/elapsed_days if elapsed_days else 0
predicted_total = daily_avg*active_days
predicted_pct   = predicted_total/total_data_qty if total_data_qty else 0

st.subheader("📊 전체 프로젝트 현황")
c1,c2,c3,c4 = st.columns(4)
c1.metric("총 수량", f"{total_data_qty:,}")
c2.metric("완료 수량", f"{completed_qty:,}")
c3.metric("잔여 수량", f"{remaining_qty:,}")
c4.metric("진행률", f"{progress_pct:.1%}")
c5,c6,c7,c8 = st.columns(4)
c5.metric("잔여일", f"{remaining_days}")
c6.metric("1일 작업 목표", f"{daily_work_target:,}")
c7.metric("1일 검수 목표", f"{daily_review_target:,}")
c8.metric("예상 완료율", f"{predicted_pct:.1%}")

# WEEKLY PROGRESS
df["month"] = df["work_date"].dt.month
df["wom"] = ((df["work_date"].dt.day-1)//7)+1
df["week_label"] = df["month"].astype(str)+"월 "+df["wom"].astype(str)+"주차"

weekly = df.groupby("week_label").agg(
    work_actual=("annotations_completed","sum"),
    review_actual=("valid_count","sum")
).reset_index()
weekly["days"] = df.groupby("week_label")["work_date"].nunique().values
weekly["work_target"] = weekly["days"]*daily_work_target
weekly["review_target"] = weekly["days"]*daily_review_target
weekly["work_pct"] = weekly["work_actual"]/weekly["work_target"]
weekly["review_pct"] = weekly["review_actual"]/weekly["review_target"]
weekly["review_wait"] = df[(df["annotations_completed"]>0)&df["review_date"].isna()] \
    .groupby("week_label")["data_id"].count() \
    .reindex(weekly["week_label"], fill_value=0).values

total = pd.DataFrame([{
    "week_label":"총합",
    "work_actual":weekly["work_actual"].sum(),
    "review_actual":weekly["review_actual"].sum(),
    "days":weekly["days"].sum(),
    "work_target":weekly["work_target"].sum(),
    "review_target":weekly["review_target"].sum(),
    "work_pct":weekly["work_actual"].sum()/weekly["work_target"].sum(),
    "review_pct":weekly["review_actual"].sum()/weekly["review_target"].sum(),
    "review_wait":weekly["review_wait"].sum()
}])
weekly = pd.concat([weekly, total], ignore_index=True)

st.subheader("📊 주별 진척률")
fig1 = px.bar(weekly.iloc[:-1], x="week_label", y=["work_actual","work_target"], barmode="group", template="plotly_white")
fig1.update_xaxes(tickangle=-45)
st.plotly_chart(fig1, use_container_width=True)
st.dataframe(
    weekly.rename(columns={
        "week_label":"주차","work_actual":"실제 건수","work_target":"목표 건수","work_pct":"달성율",
        "review_actual":"실제 검수 수","review_target":"목표 검수 수","review_pct":"검수 달성율","review_wait":"검수 대기 건수"
    }).style.apply(
        lambda df: ["background:#f0f0f0" if i==0 or i==len(weekly)-1 else "" for i in range(len(df))],
        axis=1
    ).format({
        "실제 건수":"{:,}","목표 건수":"{:,}","실제 검수 수":"{:,}",
        "목표 검수 수":"{:,}","검수 대기 건수":"{:,}",
        "달성율":"{:.1%}","검수 달성율":"{:.1%}"
    })
)

# WORKER OVERVIEW
wd = df.groupby(["worker_id","worker_name"]).agg(
    completed=("annotations_completed","sum"),
    rework=("rework_required","sum"),
    work_time=("work_time_minutes","sum"),
    last_date=("work_date","max")
).reset_index()
wd["hours"] = wd["work_time"]/60
wd["hourly_rate"] = (wd["completed"]/wd["hours"].replace(0,np.nan)*unit_price).round().astype(int)
wd["avg_min_per_task"] = ((wd["work_time"]/wd["completed"].replace(0,np.nan))).round().astype(int)
wd["daily_min"] = ((wd["work_time"]/active_days)).round().astype(int)
wd["reject_rate"] = (wd["rework"]/wd["completed"].replace(0,np.nan)).clip(lower=0)
wd["activity_rate"] = wd["hours"]/(active_days*8)
wd["reject_pct"] = wd["reject_rate"].map("{:.1%}".format)
wd["activity_pct"] = wd["activity_rate"].map("{:.1%}".format)
wd["abnormal_flag"] = np.where((wd["reject_rate"]>=0.3)|(wd["activity_rate"]<=0.5),"Y","N")

st.subheader("👥 작업자 현황")
summary_w = pd.DataFrame({
    "구분":["전체 평균","활성 평균","총합"],
    "활성률(%)":[wd["activity_rate"].mean(),wd[wd["abnormal_flag"]=="N"]["activity_rate"].mean(),wd["activity_rate"].sum()/len(wd)],
    "시급(원)":[wd["hourly_rate"].mean(),wd[wd["abnormal_flag"]=="N"]["hourly_rate"].mean(),wd["hourly_rate"].sum()],
    "반려율(%)":[wd["reject_rate"].mean(),wd[wd["abnormal_flag"]=="N"]["reject_rate"].mean(),wd["reject_rate"].sum()/len(wd)],
    "작업수량":[wd["completed"].mean(),wd[wd["abnormal_flag"]=="N"]["completed"].mean(),wd["completed"].sum()]
})
summary_w[["활성률(%)","반려율(%)"]] = summary_w[["활성률(%)","반려율(%)"]].applymap(lambda x:f"{x:.1%}")
summary_w["시급(원)"] = summary_w["시급(원)"].map("{:,}".format)
summary_w["작업수량"] = summary_w["작업수량"].map("{:,}".format)
st.table(summary_w)

fig_wd = px.bar(wd.sort_values("completed",ascending=False), x="worker_name", y="completed", title="작업량 by 작업자", template="plotly_white")
st.plotly_chart(fig_wd, use_container_width=True)

# WEEKLY WORKER
st.subheader("👤 주별 작업자 현황")
for week in weekly["주차"][:-1]:
    st.markdown(f"### {week}")
    tw = df[df["week_label"]==week]
    wwd = tw.groupby(["worker_id","worker_name"]).agg(
        completed=("annotations_completed","sum"),
        work_time=("work_time_minutes","sum")
    ).reset_index()
    wwd["hourly_rate"] = (wwd["completed"]/(wwd["work_time"]/60).replace(0,np.nan)*unit_price).round().astype(int)
    wwd["avg_min_per_task"] = ((wwd["work_time"]/wwd["completed"].replace(0,np.nan))).round().astype(int)
    wwd["daily_min"] = ((wwd["work_time"]/active_days)).round().astype(int)
    subtotal = pd.DataFrame([{
        "worker_id":"합계","worker_name":"",
        "completed":wwd["completed"].sum(),"work_time":wwd["work_time"].sum(),
        "hourly_rate":wwd["hourly_rate"].sum(),
        "avg_min_per_task":int(wwd["avg_min_per_task"].mean()),"daily_min":wwd["daily_min"].sum()
    }])
    tbl = pd.concat([wwd, subtotal], ignore_index=True)
    st.table(tbl.rename(columns={
        "worker_id":"ID","worker_name":"닉네임","completed":"작업수량",
        "work_time":"참여시간(분)","hourly_rate":"시급(원)",
        "avg_min_per_task":"건당평균(분)","daily_min":"일평균(분)"
    }).style.applymap(lambda v:'background-color:#f0f0f0', subset=pd.IndexSlice[[len(tbl)-1],:])))

# CHECKER OVERVIEW
cd = df.groupby(["checker_id","checker_name"]).agg(
    review_count=("valid_count","sum"),
    work_time=("work_time_minutes","sum"),
    last_date=("review_date","max")
).reset_index()
cd["hourly_rate"] = (cd["review_count"]/(cd["work_time"]/60).replace(0,np.nan)*review_price).round().astype(int)
cd["avg_min_per_task"] = ((cd["work_time"]/cd["review_count"].replace(0,np.nan))).round().astype(int)
cd["daily_min"] = ((cd["work_time"]/active_days)).round().astype(int)
cd["error_rate"] = ((cd["review_count"]-cd["review_count"])/cd["review_count"].replace(0,np.nan)).clip(lower=0)
cd["error_pct"] = cd["error_rate"].map("{:.1%}".format)
cd["activity_rate"] = cd["work_time"]/60/(active_days*8)
cd["activity_pct"] = cd["activity_rate"].map("{:.1%}".format)
cd["abnormal_flag"] = np.where((cd["error_rate"]>=0.3)|(cd["activity_rate"]<=0.5),"Y","N")

st.subheader("👥 검수자 현황")
summary_c = pd.DataFrame({
    "구분":["전체 평균","활성 평균","총합"],
    "활성률(%)":[cd["activity_rate"].mean(),cd[cd["abnormal_flag"]=="N"]["activity_rate"].mean(),cd["activity_rate"].sum()/len(cd)],
    "시급(원)":[cd["hourly_rate"].mean(),cd[cd["abnormal_flag"]=="N"]["hourly_rate"].mean(),cd["hourly_rate"].sum()],
    "오류율(%)":[cd["error_rate"].mean(),cd[cd["abnormal_flag"]=="N"]["error_rate"].mean(),cd["error_rate"].sum()/len(cd)],
    "검수수량":[cd["review_count"].mean(),cd[cd["abnormal_flag"]=="N"]["review_count"].mean(),cd["review_count"].sum()]
})
summary_c[["활성률(%)","오류율(%)"]] = summary_c[["활성률(%)","오류율(%)"]].applymap(lambda x:f"{x:.1%}")
summary_c["시급(원)"] = summary_c["시급(원)"].map("{:,}".format)
summary_c["검수수량"] = summary_c["검수수량"].map("{:,}".format)
st.table(summary_c)

fig_cd = px.bar(cd.sort_values("review_count",ascending=False), x="checker_name", y="review_count", title="검수량 by 검수자", template="plotly_white")
st.plotly_chart(fig_cd, use_container_width=True)

# WEEKLY CHECKER
st.subheader("👮 주별 검수자 현황")
for week in weekly["주차"][:-1]:
    st.markdown(f"### {week}")
    tr = df[df["week_label"]==week]
    wcd = tr.groupby(["checker_id","checker_name"]).agg(
        review_count=("valid_count","sum"),
        work_time=("work_time_minutes","sum")
    ).reset_index()
    wcd["hourly_rate"] = (wcd["review_count"]/(wcd["work_time"]/60).replace(0,np.nan)*review_price).round().astype(int)
    wcd["avg_min_per_task"] = ((wcd["work_time"]/wcd["review_count"].replace(0,np.nan))).round().astype(int)
    wcd["daily_min"] = ((wcd["work_time"]/active_days)).round().astype(int)
    subtotal = pd.DataFrame([{
        "checker_id":"합계","checker_name":"",
        "review_count":wcd["review_count"].sum(),"work_time":wcd["work_time"].sum(),
        "hourly_rate":wcd["hourly_rate"].sum(),
        "avg_min_per_task":int(wcd["avg_min_per_task"].mean()),"daily_min":wcd["daily_min"].sum()
    }])
    tbl = pd.concat([wcd, subtotal], ignore_index=True)
    st.table(tbl.rename(columns={
        "checker_id":"ID","checker_name":"닉네임","review_count":"검수수량",
        "work_time":"참여시간(분)","hourly_rate":"시급(원)",
        "avg_min_per_task":"건당평균(분)","daily_min":"일평균(분)"
    }).style.applymap(lambda v:'background-color:#f0f0f0', subset=pd.IndexSlice[[len(tbl)-1],:]))

