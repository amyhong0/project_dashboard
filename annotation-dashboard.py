# annotation-dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import date

st.set_page_config(page_title="Project Dashboard", layout="wide")

# HEADER
st.markdown('<h1 style="text-align:center; color:#333;">Project Dashboard</h1>', unsafe_allow_html=True)

# SIDEBAR INPUTS
st.sidebar.header("📁 데이터 및 파라미터")
uploaded = st.sidebar.file_uploader("export.csv 업로드", type="csv")
if not uploaded:
    st.info("export.csv 파일을 업로드하세요.")
    st.stop()
raw = pd.read_csv(uploaded, dtype=str)

st.sidebar.header("⚙️ 프로젝트 파라미터")
total_data_qty      = st.sidebar.number_input("데이터 총 수량", min_value=1, value=1000)
open_date           = st.sidebar.date_input("오픈일", value=date.today())
target_end_date     = st.sidebar.date_input("목표 종료일", value=date.today())
daily_work_target   = st.sidebar.number_input("1일 작업 목표", min_value=1, value=20)
daily_review_target = st.sidebar.number_input("1일 검수 목표", min_value=1, value=16)
unit_price          = st.sidebar.number_input("작업 단가(원)", min_value=0, value=100)
review_price        = st.sidebar.number_input("검수 단가(원)", min_value=0, value=50)

# DATA CLEANING
df = raw.rename(columns={
    "데이터 ID":"data_id", "최종 오브젝트 수":"annotations_completed", "유효 오브젝트 수":"valid_count",
    "수정 여부":"rework_required", "Worker ID":"worker_id", "작업자 닉네임":"worker_name",
    "Checker ID":"checker_id", "검수자 닉네임":"checker_name", "작업 종료일":"work_date",
    "검수 종료일":"review_date", "작업 수정 시간":"work_time_minutes"
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
progress_pct    = completed_qty/total_data_qty if total_data_qty>0 else 0
remaining_days  = (target_end_date-date.today()).days
elapsed_days    = (date.today()-open_date).days+1
daily_avg       = completed_qty/elapsed_days if elapsed_days>0 else 0
predicted_total = daily_avg*active_days
predicted_pct   = predicted_total/total_data_qty if total_data_qty>0 else 0

st.subheader("📊 전체 프로젝트 현황")
col1, col2, col3, col4 = st.columns(4)
col1.metric("총 수량", f"{total_data_qty:,}")
col2.metric("완료 수량", f"{completed_qty:,}")
col3.metric("잔여 수량", f"{remaining_qty:,}")
col4.metric("진행률", f"{progress_pct:.1%}")
col5, col6, col7, col8 = st.columns(4)
col5.metric("잔여일", f"{remaining_days}")
col6.metric("1일 작업 목표", f"{daily_work_target:,}")
col7.metric("1일 검수 목표", f"{daily_review_target:,}")
col8.metric("예상 완료율", f"{predicted_pct:.1%}")

# PROGRESSION CHART
dates = pd.date_range(open_date, target_end_date)
daily_done = df.groupby(df["work_date"].dt.date)["data_id"].nunique().reindex(dates.date, fill_value=0).cumsum().reset_index()
daily_done.columns = ["date","cumulative"]
target_line = pd.DataFrame({"date":dates.date,"cumulative":np.linspace(0,total_data_qty,len(dates))})
fig = px.line(daily_done, x="date", y="cumulative", title="프로젝트 진행 추이", template="plotly_white")
fig.add_scatter(x=target_line["date"], y=target_line["cumulative"], mode="lines", name="목표선")
st.plotly_chart(fig, use_container_width=True)

# WEEKLY PROGRESS
df["month"] = df["work_date"].dt.month
df["wom"] = ((df["work_date"].dt.day-1)//7)+1
df["week_label"] = df["month"].astype(str)+"월 "+df["wom"].astype(str)+"주차"

# 주별 집계
weekly = df.groupby("week_label").agg(
    work_actual=("annotations_completed","sum"),
    review_actual=("valid_count","sum")
).reset_index()
weekly["work_target"] = daily_work_target*7
weekly["review_target"] = daily_review_target*7
weekly["work_pct"] = weekly["work_actual"]/weekly["work_target"]
weekly["review_pct"] = weekly["review_actual"]/weekly["review_target"]
weekly["review_wait"] = df[(df["annotations_completed"]>0)&df["review_date"].isna()]\
    .groupby("week_label")["data_id"].count().reindex(weekly["week_label"],fill_value=0).values

# 일별 집계
daily = df.groupby([df["work_date"].dt.date, "week_label"]).agg(
    work_actual=("annotations_completed","sum"),
    review_actual=("valid_count","sum")
).reset_index()
daily["work_date"] = daily["work_date"].astype(str)
daily["review_wait"] = df[(df["annotations_completed"]>0)&df["review_date"].isna()]\
    .groupby([df["work_date"].dt.date, "week_label"])["data_id"].count().reindex(daily.set_index(["work_date","week_label"]).index, fill_value=0).values

st.subheader("📊 주별 진척률 - 작업")
fig1 = px.bar(weekly, x="week_label", y=["work_actual","work_target"], barmode="group", template="plotly_white")
fig1.update_xaxes(tickangle=-45)
st.plotly_chart(fig1, use_container_width=True)

# 작업 상세 테이블 (주별 + 일별)
work_display = []
for _, week_row in weekly.iterrows():
    week_data = {
        "구분": week_row["week_label"],
        "실제 건수": f"{week_row['work_actual']:,}",
        "목표 건수": f"{week_row['work_target']:,}",
        "달성율": f"{week_row['work_pct']:.1%}"
    }
    work_display.append(week_data)
    
    # 해당 주의 일별 데이터
    week_daily = daily[daily["week_label"] == week_row["week_label"]]
    for _, day_row in week_daily.iterrows():
        day_data = {
            "구분": f"  └ {day_row['work_date']}",
            "실제 건수": f"{day_row['work_actual']:,}",
            "목표 건수": f"{daily_work_target:,}",
            "달성율": f"{day_row['work_actual']/daily_work_target:.1%}" if daily_work_target > 0 else "0.0%"
        }
        work_display.append(day_data)

# 총합 추가
total_work = {
    "구분": "총합",
    "실제 건수": f"{weekly['work_actual'].sum():,}",
    "목표 건수": f"{weekly['work_target'].sum():,}",
    "달성율": f"{weekly['work_actual'].sum()/weekly['work_target'].sum():.1%}" if weekly['work_target'].sum() > 0 else "0.0%"
}
work_display.append(total_work)
st.table(pd.DataFrame(work_display))

st.subheader("📊 주별 진척률 - 검수")
fig2 = px.bar(weekly, x="week_label", y=["review_actual","review_target"], barmode="group", template="plotly_white")
fig2.update_xaxes(tickangle=-45)
st.plotly_chart(fig2, use_container_width=True)

# 검수 상세 테이블 (주별 + 일별)
review_display = []
for _, week_row in weekly.iterrows():
    week_data = {
        "구분": week_row["week_label"],
        "실제 건수": f"{week_row['review_actual']:,}",
        "목표 건수": f"{week_row['review_target']:,}",
        "달성율": f"{week_row['review_pct']:.1%}",
        "검수 대기 건수": f"{week_row['review_wait']:,}"
    }
    review_display.append(week_data)
    
    # 해당 주의 일별 데이터
    week_daily = daily[daily["week_label"] == week_row["week_label"]]
    for _, day_row in week_daily.iterrows():
        day_data = {
            "구분": f"  └ {day_row['work_date']}",
            "실제 건수": f"{day_row['review_actual']:,}",
            "목표 건수": f"{daily_review_target:,}",
            "달성율": f"{day_row['review_actual']/daily_review_target:.1%}" if daily_review_target > 0 else "0.0%",
            "검수 대기 건수": f"{day_row['review_wait']:,}"
        }
        review_display.append(day_data)

# 총합 추가
total_review = {
    "구분": "총합",
    "실제 건수": f"{weekly['review_actual'].sum():,}",
    "목표 건수": f"{weekly['review_target'].sum():,}",
    "달성율": f"{weekly['review_actual'].sum()/weekly['review_target'].sum():.1%}" if weekly['review_target'].sum() > 0 else "0.0%",
    "검수 대기 건수": f"{weekly['review_wait'].sum():,}"
}
review_display.append(total_review)
st.table(pd.DataFrame(review_display))

# WORKER METRICS
wd = df.groupby(["worker_id","worker_name"]).agg(
    completed=("annotations_completed","sum"),
    rework=("rework_required","sum"),
    work_time=("work_time_minutes","sum"),
    last_date=("work_date","max")
).reset_index()
wd["hours"] = wd["work_time"]/60
wd["per_hr"] = wd["completed"]/wd["hours"].replace(0,np.nan)
wd["hourly_rate"] = (wd["per_hr"].fillna(0) * unit_price).astype(int)
wd["avg_min_per_task"] = ((wd["hours"]/wd["completed"].replace(0,np.nan))*60).astype(int)
wd["daily_min"] = ((wd["hours"]/active_days)*60).astype(int)
wd["reject_rate"] = (wd["rework"]/wd["completed"].replace(0,np.nan)).clip(lower=0)
wd["activity_rate"] = wd["hours"]/(active_days*8)
wd["reject_pct"] = wd["reject_rate"].map("{:.1%}".format)
wd["activity_pct"] = wd["activity_rate"].map("{:.1%}".format)
wd["abnormal_flag"] = np.where((wd["reject_rate"]>=0.3)|(wd["activity_rate"]<=0.5),"Y","N")

st.subheader("👥 작업자 현황")
summary_w = pd.DataFrame({
    "구분":["전체 평균","활성 평균"],
    "활성률(%)":[wd["activity_rate"].mean(),wd[wd["abnormal_flag"]=="N"]["activity_rate"].mean()],
    "시급(원)":[wd["hourly_rate"].mean(),wd[wd["abnormal_flag"]=="N"]["hourly_rate"].mean()],
    "반려율(%)":[wd["reject_rate"].mean(),wd[wd["abnormal_flag"]=="N"]["reject_rate"].mean()],
    "작업수량":[wd["completed"].mean(),wd[wd["abnormal_flag"]=="N"]["completed"].mean()]
})
summary_w[["활성률(%)","반려율(%)"]] = summary_w[["활성률(%)","반려율(%)"]].applymap(lambda x:f"{x:.1%}")
summary_w["시급(원)"] = summary_w["시급(원)"].map(lambda x: f"{x:,.0f}")
summary_w["작업수량"] = summary_w["작업수량"].map(lambda x: f"{x:,.0f}")

# 총합 행 추가
summary_total = pd.DataFrame({
    "구분":["총합"],
    "활성률(%)": [f"{wd['activity_rate'].mean():.1%}"],
    "시급(원)": [f"{wd['hourly_rate'].sum():,}"],
    "반려율(%)": [f"{wd['reject_rate'].sum():.1%}"],
    "작업수량": [f"{wd['completed'].sum():,}"]
})
summary_w = pd.concat([summary_w, summary_total], ignore_index=True)
st.table(summary_w)

fig_wd = px.bar(wd.sort_values("completed",ascending=False), x="worker_name", y="completed", title="작업량 by 작업자", template="plotly_white")
st.plotly_chart(fig_wd, use_container_width=True)

# Worker dataframe with styling and total
worker_display = wd.sort_values("completed",ascending=False)[[
    "worker_id","worker_name","activity_pct","hourly_rate","reject_pct","completed",
    "avg_min_per_task","daily_min","last_date","abnormal_flag"
]].copy()

worker_display["hourly_rate"] = worker_display["hourly_rate"].map(lambda x: f"{x:,}")
worker_display["completed"] = worker_display["completed"].map(lambda x: f"{x:,}")
worker_display["avg_min_per_task"] = worker_display["avg_min_per_task"].map(lambda x: f"{x:,}")
worker_display["daily_min"] = worker_display["daily_min"].map(lambda x: f"{x:,}")

# 총합 행 추가
worker_total = pd.DataFrame({
    "worker_id": ["총합"],
    "worker_name": [""],
    "activity_pct": [f"{wd['activity_rate'].mean():.1%}"],
    "hourly_rate": [f"{wd['hourly_rate'].sum():,}"],
    "reject_pct": [f"{wd['reject_rate'].mean():.1%}"],
    "completed": [f"{wd['completed'].sum():,}"],
    "avg_min_per_task": [f"{wd['avg_min_per_task'].mean():,}"],
    "daily_min": [f"{wd['daily_min'].sum():,}"],
    "last_date": [""],
    "abnormal_flag": [""]
})
worker_display = pd.concat([worker_display, worker_total], ignore_index=True)
worker_display = worker_display.rename(columns={
    "worker_id":"ID","worker_name":"닉네임","activity_pct":"활성률(%)","hourly_rate":"시급(원)",
    "reject_pct":"반료율(%)","completed":"작업수량","avg_min_per_task":"건당평균(분)",
    "daily_min":"일평균(분)","last_date":"마지막작업일","abnormal_flag":"이상참여자"
})

st.dataframe(worker_display.style.applymap(lambda v:'color:red;' if v=='Y' else '', subset=["이상참여자"]), use_container_width=True)

# CHECKER METRICS (수정된 로직)
cd = df.groupby(["checker_id","checker_name"]).agg(
    reviews=("valid_count","sum"),  # 수정: 실제 검수한 오브젝트 수
    valid=("valid_count","sum"),
    last_date=("review_date","max")
).reset_index()
cd["hours"] = cd["reviews"]
cd["per_hr"] = cd["reviews"]/cd["hours"].replace(0,np.nan)
cd["hourly_rate"] = (cd["per_hr"].fillna(0) * review_price).astype(int)
cd["avg_min_per_task"] = ((cd["hours"]/cd["reviews"].replace(0,np.nan))*60).astype(int)
cd["daily_min"] = ((cd["hours"]/active_days)*60).astype(int)
cd["error_rate"] = ((cd["reviews"]-cd["valid"])/cd["reviews"].replace(0,np.nan)).clip(lower=0)
cd["error_pct"] = cd["error_rate"].map("{:.1%}".format)
cd["activity_rate"] = cd["hours"]/(active_days*8)
cd["activity_pct"] = cd["activity_rate"].map("{:.1%}".format)
cd["abnormal_flag"] = np.where((cd["error_rate"]>=0.3)|(cd["activity_rate"]<=0.5),"Y","N")

st.subheader("👥 검수자 현황")
summary_c = pd.DataFrame({
    "구분":["전체 평균","활성 평균"],
    "활성률(%)":[cd["activity_rate"].mean(),cd[cd["abnormal_flag"]=="N"]["activity_rate"].mean()],
    "시급(원)":[cd["hourly_rate"].mean(),cd[cd["abnormal_flag"]=="N"]["hourly_rate"].mean()],
    "오류율(%)":[cd["error_rate"].mean(),cd[cd["abnormal_flag"]=="N"]["error_rate"].mean()],
    "검수수량":[cd["reviews"].mean(),cd[cd["abnormal_flag"]=="N"]["reviews"].mean()]
})
summary_c[["활성률(%)","오류율(%)"]] = summary_c[["활성률(%)","오류율(%)"]].applymap(lambda x:f"{x:.1%}")
summary_c["시급(원)"] = summary_c["시급(원)"].map(lambda x: f"{x:,.0f}")
summary_c["검수수량"] = summary_c["검수수량"].map(lambda x: f"{x:,.0f}")

# 총합 행 추가
summary_c_total = pd.DataFrame({
    "구분":["총합"],
    "활성률(%)": [f"{cd['activity_rate'].mean():.1%}"],
    "시급(원)": [f"{cd['hourly_rate'].sum():,}"],
    "오류율(%)": [f"{cd['error_rate'].sum():.1%}"],
    "검수수량": [f"{cd['reviews'].sum():,}"]
})
summary_c = pd.concat([summary_c, summary_c_total], ignore_index=True)
st.table(summary_c)

fig_cd = px.bar(cd.sort_values("reviews",ascending=False), x="checker_name", y="reviews", title="검수량 by 검수자", template="plotly_white")
st.plotly_chart(fig_cd, use_container_width=True)

# Checker dataframe with styling and total
checker_display = cd.sort_values("reviews",ascending=False)[[
    "checker_id","checker_name","activity_pct","hourly_rate","error_pct","reviews",
    "avg_min_per_task","daily_min","last_date","abnormal_flag"
]].copy()

checker_display["hourly_rate"] = checker_display["hourly_rate"].map(lambda x: f"{x:,}")
checker_display["reviews"] = checker_display["reviews"].map(lambda x: f"{x:,}")
checker_display["avg_min_per_task"] = checker_display["avg_min_per_task"].map(lambda x: f"{x:,}")
checker_display["daily_min"] = checker_display["daily_min"].map(lambda x: f"{x:,}")

# 총합 행 추가
checker_total = pd.DataFrame({
    "checker_id": ["총합"],
    "checker_name": [""],
    "activity_pct": [f"{cd['activity_rate'].mean():.1%}"],
    "hourly_rate": [f"{cd['hourly_rate'].sum():,}"],
    "error_pct": [f"{cd['error_rate'].mean():.1%}"],
    "reviews": [f"{cd['reviews'].sum():,}"],
    "avg_min_per_task": [f"{cd['avg_min_per_task'].mean():,}"],
    "daily_min": [f"{cd['daily_min'].sum():,}"],
    "last_date": [""],
    "abnormal_flag": [""]
})
checker_display = pd.concat([checker_display, checker_total], ignore_index=True)
checker_display = checker_display.rename(columns={
    "checker_id":"ID","checker_name":"닉네임","activity_pct":"활성률(%)","hourly_rate":"시급(원)",
    "error_pct":"오류율(%)","reviews":"검수수량","avg_min_per_task":"건당평균(분)",
    "daily_min":"일평균(분)","last_date":"마지막검수일","abnormal_flag":"이상참여자"
})

st.dataframe(checker_display.style.applymap(lambda v:'color:red;' if v=='Y' else '', subset=["이상참여자"]), use_container_width=True)

# 주별 작업자 현황
st.subheader("👤 주별 작업자 현황")
weekly_worker_display = []
for week in weekly["week_label"].unique():
    week_df = df[df["week_label"]==week]
    wwd = week_df.groupby(["worker_id","worker_name"]).agg(
        작업수량=("annotations_completed","sum"),
        참여시간분=("work_time_minutes","sum")
    ).reset_index()
    
    # 주차별 데이터
    for _, row in wwd.iterrows():
        weekly_worker_display.append({
            "주차": week,
            "ID": row["worker_id"],
            "닉네임": row["worker_name"],
            "작업수량": f"{row['작업수량']:,}",
            "참여시간(분)": f"{row['참여시간분']:,}"
        })
    
    # 주차별 소계
    weekly_worker_display.append({
        "주차": f"{week} 소계",
        "ID": "",
        "닉네임": "",
        "작업수량": f"{wwd['작업수량'].sum():,}",
        "참여시간(분)": f"{wwd['참여시간분'].sum():,}"
    })

# 전체 총합
total_worker = df.groupby(["worker_id","worker_name"]).agg(
    작업수량=("annotations_completed","sum"),
    참여시간분=("work_time_minutes","sum")
).reset_index()
weekly_worker_display.append({
    "주차": "전체 총합",
    "ID": "",
    "닉네임": "",
    "작업수량": f"{total_worker['작업수량'].sum():,}",
    "참여시간(분)": f"{total_worker['참여시간분'].sum():,}"
})
st.table(pd.DataFrame(weekly_worker_display))

# 주별 검수자 현황
st.subheader("👮 주별 검수자 현황")
weekly_checker_display = []
for week in weekly["week_label"].unique():
    week_df = df[df["week_label"]==week]
    wcd = week_df.groupby(["checker_id","checker_name"]).agg(
        검수수량=("valid_count","sum"),
        참여시간분=("work_time_minutes","sum")
    ).reset_index()
    
    # 주차별 데이터
    for _, row in wcd.iterrows():
        weekly_checker_display.append({
            "주차": week,
            "ID": row["checker_id"],
            "닉네임": row["checker_name"],
            "검수수량": f"{row['검수수량']:,}",
            "참여시간(분)": f"{row['참여시간분']:,}"
        })
    
    # 주차별 소계
    weekly_checker_display.append({
        "주차": f"{week} 소계",
        "ID": "",
        "닉네임": "",
        "검수수량": f"{wcd['검수수량'].sum():,}",
        "참여시간(분)": f"{wcd['참여시간분'].sum():,}"
    })

# 전체 총합
total_checker = df.groupby(["checker_id","checker_name"]).agg(
    검수수량=("valid_count","sum"),
    참여시간분=("work_time_minutes","sum")
).reset_index()
weekly_checker_display.append({
    "주차": "전체 총합",
    "ID": "",
    "닉네임": "",
    "검수수량": f"{total_checker['검수수량'].sum():,}",
    "참여시간(분)": f"{total_checker['참여시간분'].sum():,}"
})
st.table(pd.DataFrame(weekly_checker_display))
