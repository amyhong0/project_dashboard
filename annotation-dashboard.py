# annotation-dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Project Dashboard", layout="wide")

# Custom CSS: Power BI–style simple header color
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

# 원천 CSV 컬럼 → 표준 컬럼 매핑
STANDARD_COLUMNS = {
    "프로젝트ID":              "project_id",
    "데이터 ID":               "task_id",
    "작업 상태":               "status",
    "작업불가여부":             "blocked",
    "최종 오브젝트 수":         "annotations_completed",
    "수정 여부":               "rework_required",
    "유효 오브젝트 수":         "valid_count",
    "Worker ID":              "annotator_id",
    "작업자 닉네임":             "annotator_name",
    "Checker ID":             "checker_id",
    "검수자 닉네임":             "checker_name",
    "작업 종료일":             "date",
    "검수 종료일":             "review_date",
    "작업 수정 시간":          "time_spent_minutes",
    "CO 모니터링 URL":         "monitor_url"
}

def load_and_clean(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.rename(columns=STANDARD_COLUMNS)[list(STANDARD_COLUMNS.values())].copy()
    for col in ["date", "review_date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    for col in ["annotations_completed", "rework_required", "valid_count", "time_spent_minutes"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    df["week_number"] = df["date"].dt.isocalendar().week
    min_d, max_d = df["date"].min(), df["date"].max()
    total_days = (max_d - min_d).days + 1
    df["days_since_start"] = (df["date"] - min_d).dt.days
    bins = [-1, total_days/3, total_days*2/3, total_days+1]
    df["project_phase"] = pd.cut(df["days_since_start"], bins=bins, labels=["Phase1","Phase2","Phase3"])
    return df.drop(columns=["days_since_start"])

def calculate_kpis(df):
    total = df["annotations_completed"].sum()
    hrs = df["time_spent_minutes"].sum() / 60
    return {
        "total_annotations": total,
        "avg_per_hour": total/hrs if hrs else 0,
        "rework_rate": df["rework_required"].sum()/total if total else 0,
        "active_annotators": df["annotator_name"].nunique()
    }

# Sidebar: data upload & period
st.sidebar.header("📁 데이터 업로드 & 설정")
uploaded = st.sidebar.file_uploader("Raw CSV 선택", type="csv")
use_sample = st.sidebar.checkbox("샘플 데이터 사용", value=False)

if uploaded:
    raw = pd.read_csv(uploaded, dtype=str)
    df = load_and_clean(raw)
elif use_sample:
    raw = pd.read_csv("export.csv", dtype=str)
    df = load_and_clean(raw)
else:
    st.info("CSV 업로드 또는 샘플 선택 필요")
    st.stop()

# 전체 기간 설정
st.sidebar.markdown("### 📅 기간 설정")
auto = st.sidebar.checkbox("자동 설정", True)
if auto:
    start, end = df["date"].min().date(), df["date"].max().date()
else:
    start, end = st.sidebar.date_input(
        "기간 선택",
        value=(df["date"].min().date(), df["date"].max().date()),
        min_value=df["date"].min().date(),
        max_value=df["date"].max().date()
    )

mask = (df["date"].dt.date>=start)&(df["date"].dt.date<=end)
filtered = df[mask]
workers = st.sidebar.multiselect("작업자 선택", filtered["annotator_name"].unique(), filtered["annotator_name"].unique())
filtered = filtered[filtered["annotator_name"].isin(workers)]

# KPIs
kpis = calculate_kpis(filtered)
st.markdown("## 📈 Executive Summary")
c1,c2,c3,c4 = st.columns(4)
c1.metric("총 완료 작업", f"{kpis['total_annotations']:,}")
c2.metric("시간당 작업량", f"{kpis['avg_per_hour']:.1f}")
c3.metric("재작업률", f"{kpis['rework_rate']:.1%}")
c4.metric("활성 작업자", f"{kpis['active_annotators']}")

# 전체 기간별 (일별) 차트 + 상세 선택
st.markdown("## 🗓️ 일별 완료 작업수")
daily = filtered.groupby(filtered["date"].dt.date)["annotations_completed"].sum().reset_index()
fig_daily = px.line(daily, x="date", y="annotations_completed", title="Daily Annotations")
st.plotly_chart(fig_daily, use_container_width=True)
sel_date = st.selectbox("날짜별 상세 보기", daily["date"].astype(str))
df_day = filtered[filtered["date"].dt.date==pd.to_datetime(sel_date).date()]
st.dataframe(df_day)

# 주 단위 차트 + 상세 선택
st.markdown("## 📅 주별 완료 작업수")
weekly = filtered.groupby("week_number")["annotations_completed"].sum().reset_index()
fig_weekly = px.bar(weekly, x="week_number", y="annotations_completed", title="Weekly Annotations")
st.plotly_chart(fig_weekly, use_container_width=True)
sel_week = st.selectbox("주차별 상세 보기", weekly["week_number"])
df_week = filtered[filtered["week_number"]==sel_week]
st.dataframe(df_week)

# 작업자별 차트 + 상세 선택
st.markdown("## 👥 작업자별 완료 작업수")
by_w = filtered.groupby("annotator_name")["annotations_completed"].sum().reset_index()
fig_worker = px.bar(by_w, x="annotator_name", y="annotations_completed", title="By Annotator")
st.plotly_chart(fig_worker, use_container_width=True)
sel_worker = st.selectbox("작업자별 상세 보기", by_w["annotator_name"])
df_worker = filtered[filtered["annotator_name"]==sel_worker]
st.dataframe(df_worker)

# Phase별 차트 + 상세 선택
st.markdown("## 🎯 Phase별 완료 작업 비율")
phase = filtered.groupby("project_phase")["annotations_completed"].sum().reset_index()
fig_phase = px.pie(phase, names="project_phase", values="annotations_completed", title="By Phase")
st.plotly_chart(fig_phase, use_container_width=True)
sel_phase = st.selectbox("Phase별 상세 보기", phase["project_phase"])
df_phase = filtered[filtered["project_phase"]==sel_phase]
st.dataframe(df_phase)

# 전체 데이터 다운로드
with st.expander("📋 전체 데이터 보기/다운로드"):
    st.dataframe(filtered)
    csv = filtered.to_csv(index=False)
    st.download_button("CSV 다운로드", csv, "data.csv", "text/csv")
