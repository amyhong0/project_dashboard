# annotation-dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime, date

st.set_page_config(page_title="Project Dashboard", layout="wide")

# 헤더 스타일
st.markdown("""
<style>
.main-header {
    background: #0176d3;
    padding: 1rem;
    border-radius: 0.5rem;
    color: white;
    text-align: center;
    margin-bottom: 0.5rem;
}
.sub-header {
    text-align: center;
    margin-bottom: 1.5rem;
    font-size: 1rem;
    color: #333;
}
</style>
""", unsafe_allow_html=True)
st.markdown('<div class="main-header"><h1>Project Dashboard</h1></div>', unsafe_allow_html=True)

# 프로젝트 정보 표시
# 데이터 로드 전이므로 placeholder 사용
project_info = st.empty()

# 원천 CSV 컬럼 매핑
STANDARD_COLUMNS = {
    "프로젝트ID":              "project_id",
    "데이터 ID":               "task_id",
    "작업 상태":               "status",
    "작업불가여부":             "blocked",
    "최종 오브젝트 수":         "annotations_completed",
    "수정 여부":               "rework_required",
    "유효 오브젝트 수":         "valid_count",
    "Worker ID":               "annotator_id",
    "작업자 닉네임":             "annotator_name",
    "Checker ID":              "checker_id",
    "검수자 닉네임":             "checker_name",
    "작업 종료일":             "date",
    "검수 종료일":             "review_date",
    "작업 수정 시간":           "time_spent_minutes",
    "CO 모니터링 URL":          "monitor_url"
}

def load_and_clean(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.rename(columns=STANDARD_COLUMNS)[list(STANDARD_COLUMNS.values())].copy()
    for col in ["date", "review_date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    for col in ["annotations_completed", "rework_required", "valid_count", "time_spent_minutes"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    df["week_number"] = df["date"].dt.isocalendar().week
    start = df["date"].min()
    end   = df["date"].max()
    df["project_start"], df["project_end"] = start, end
    df["days_since_start"] = (df["date"] - start).dt.days
    total_days = (end - start).days + 1
    bins = [-1, total_days/3, total_days*2/3, total_days+1]
    df["project_phase"] = pd.cut(df["days_since_start"], bins=bins, labels=["Phase1","Phase2","Phase3"])
    return df

def calculate_kpis(df: pd.DataFrame) -> dict:
    total = df["annotations_completed"].sum()
    hours = df["time_spent_minutes"].sum() / 60
    start = df["project_start"].iloc[0]
    end   = df["project_end"].iloc[0]
    today = pd.to_datetime(date.today())
    last_day = min(today, end)
    elapsed_days = (last_day - start).days + 1
    total_days = (end - start).days + 1
    avg_per_day = total / elapsed_days if elapsed_days>0 else 0
    predicted_total = avg_per_day * total_days
    return {
        "total_annotations": total,
        "avg_per_hour": total/hours if hours>0 else 0,
        "rework_rate": df["rework_required"].sum()/total if total>0 else 0,
        "active_annotators": df["annotator_name"].nunique(),
        "elapsed_pct": elapsed_days/total_days if total_days>0 else 0,
        "predicted_pct": total/predicted_total if predicted_total>0 else 0
    }

# 사이드바
st.sidebar.header("📁 데이터 업로드 및 설정")
uploaded = st.sidebar.file_uploader("Raw CSV 선택", type="csv")
if st.sidebar.checkbox("샘플 데이터 사용"):
    sample = pd.DataFrame([{
        "프로젝트ID":"P001","데이터 ID":"T001","작업 상태":"완료","작업불가여부":"N",
        "최종 오브젝트 수":20,"수정 여부":2,"유효 오브젝트 수":18,
        "Worker ID":"W001","작업자 닉네임":"김민수","Checker ID":"C001","검수자 닉네임":"이영희",
        "작업 종료일":"2025-08-01","검수 종료일":"2025-08-02","작업 수정 시간":120,
        "CO 모니터링 URL":"http://example.com"
    } for _ in range(50)])
    raw = sample
elif uploaded:
    raw = pd.read_csv(uploaded, dtype=str)
else:
    st.info("Raw CSV를 업로드하거나 샘플 데이터를 선택하세요.")
    st.stop()

df = load_and_clean(raw)

# 프로젝트 정보 업데이트
proj_ids = df["project_id"].unique()
info_text = f"**프로젝트:** {', '.join(proj_ids)}  |  시작일: {df['project_start'].iloc[0].date()}  |  종료일: {df['project_end'].iloc[0].date()}"
project_info.markdown(f'<div class="sub-header">{info_text}</div>', unsafe_allow_html=True)

# 자유 기간 설정
st.sidebar.markdown("### 📅 기간 설정")
start_date, end_date = st.sidebar.date_input(
    "분석 기간 선택",
    value=(df["date"].min().date(), df["date"].max().date())
)
mask = (df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)
filtered = df.loc[mask]

# 작업자 필터
workers = st.sidebar.multiselect(
    "작업자 선택",
    options=filtered["annotator_name"].unique(),
    default=filtered["annotator_name"].unique()
)
filtered = filtered[filtered["annotator_name"].isin(workers)]

# KPI 계산
kpis = calculate_kpis(filtered)
st.markdown("## 📈 Executive Summary")
cols = st.columns(6)
cols[0].metric("총 완료 작업", f"{kpis['total_annotations']:,}")
cols[1].metric("시간당 작업량", f"{kpis['avg_per_hour']:.1f}")
cols[2].metric("재작업률", f"{kpis['rework_rate']:.1%}")
cols[3].metric("활성 작업자", f"{kpis['active_annotators']}")
cols[4].metric("경과 기간 비율", f"{kpis['elapsed_pct']:.1%}")
cols[5].metric("예측 완료율", f"{kpis['predicted_pct']:.1%}")

# 일별 차트
st.markdown("## 🗓️ 일별 완료 작업수")
daily = filtered.groupby(filtered["date"].dt.date)["annotations_completed"].sum().reset_index()
fig_daily = px.line(daily, x="date", y="annotations_completed", title="Daily Annotations")
st.plotly_chart(fig_daily, use_container_width=True)
with st.expander("일별 상세 데이터", expanded=False):
    sel = st.selectbox("날짜 선택", daily["date"].astype(str))
    st.dataframe(filtered[filtered["date"].dt.date == pd.to_datetime(sel).date()])

# 주별 차트 (월+주차 레이블)
st.markdown("## 📅 주별 완료 작업수")
weekly = filtered.groupby("week_number").agg({
    "annotations_completed": "sum",
    "date": "min"
}).reset_index()
weekly["label"] = weekly["date"].dt.strftime("%m월") + " " + (weekly["date"].dt.isocalendar().week % 4 + 1).astype(str) + "주차"
fig_weekly = px.bar(weekly, x="label", y="annotations_completed", title="Weekly Annotations")
st.plotly_chart(fig_weekly, use_container_width=True)
with st.expander("주별 상세 데이터", expanded=False):
    sel = st.selectbox("주 선택", weekly["label"])
    week_num = weekly.loc[weekly["label"] == sel, "week_number"].iloc[0]
    st.dataframe(filtered[filtered["week_number"] == week_num])

# 작업자별 차트
st.markdown("## 👥 작업자별 완료 작업수")
by_w = filtered.groupby("annotator_name")["annotations_completed"].sum().reset_index()
fig_worker = px.bar(by_w, x="annotator_name", y="annotations_completed", title="By Annotator")
st.plotly_chart(fig_worker, use_container_width=True)
with st.expander("작업자별 상세 데이터", expanded=False):
    sel = st.selectbox("작업자 선택", by_w["annotator_name"])
    st.dataframe(filtered[filtered["annotator_name"] == sel])

# Phase별 차트
st.markdown("## 🎯 Phase별 완료 작업 비율")
phase = filtered.groupby("project_phase")["annotations_completed"].sum().reset_index()
fig_phase = px.pie(phase, names="project_phase", values="annotations_completed", title="By Phase")
st.plotly_chart(fig_phase, use_container_width=True)
with st.expander("Phase별 상세 데이터", expanded=False):
    sel = st.selectbox("Phase 선택", phase["project_phase"])
    st.dataframe(filtered[filtered["project_phase"] == sel])

# 전체 데이터 보기/다운로드
with st.expander("📋 전체 데이터 보기/다운로드", expanded=False):
    st.dataframe(filtered)
    csv = filtered.to_csv(index=False)
    st.download_button("CSV 다운로드", csv, "data.csv", "text/csv")
