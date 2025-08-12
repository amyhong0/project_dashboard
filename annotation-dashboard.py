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
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)
st.markdown('<div class="main-header"><h1>Project Dashboard</h1></div>', unsafe_allow_html=True)

# RAW→표준 컬럼 매핑
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
    # 날짜/숫자 변환
    for col in ["date", "review_date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    for col in ["annotations_completed","rework_required","valid_count","time_spent_minutes"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    # 주차 및 라벨
    df["week_number"] = df["date"].dt.isocalendar().week
    df["week_year"] = df["date"].dt.isocalendar().year
    df["week_label"] = df.apply(
        lambda r: f"{r['week_year']}년 {int(r['week_number'])}주차", axis=1
    )
    # 프로젝트 기간 및 Phase
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
    hrs = df["time_spent_minutes"].sum()/60
    start = df["project_start"].iloc[0]
    end   = df["project_end"].iloc[0]
    today = pd.to_datetime(date.today())
    last  = min(today, end)
    elapsed = (last - start).days + 1
    period  = (end - start).days + 1
    avg_per_day = total/elapsed if elapsed>0 else 0
    predicted_total = avg_per_day*period
    return {
        "total_annotations": total,
        "avg_per_hour": total/hrs if hrs>0 else 0,
        "rework_rate": df["rework_required"].sum()/total if total>0 else 0,
        "active_annotators": df["annotator_name"].nunique(),
        "elapsed_pct": elapsed/period if period>0 else 0,
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
    st.info("CSV 업로드 또는 샘플 데이터 선택 필요")
    st.stop()

df = load_and_clean(raw)

# 프로젝트 ID 선택
project_ids = df["project_id"].unique()
sel_proj = st.sidebar.selectbox("프로젝트 선택", project_ids)
df = df[df["project_id"]==sel_proj]

# 기간 설정
st.sidebar.markdown("### 📅 기간 설정")
start_date, end_date = st.sidebar.date_input(
    "분석 기간", (df["date"].min().date(), df["date"].max().date())
)
mask = (df["date"].dt.date>=start_date)&(df["date"].dt.date<=end_date)
filtered = df[mask]

# 작업자 필터
workers = st.sidebar.multiselect(
    "작업자 선택", filtered["annotator_name"].unique(), filtered["annotator_name"].unique()
)
filtered = filtered[filtered["annotator_name"].isin(workers)]

# KPI
kpis = calculate_kpis(filtered)
st.markdown("## 📈 Executive Summary")
c1,c2,c3,c4,c5,c6 = st.columns(6)
c1.metric("총 완료 작업", f"{kpis['total_annotations']:,}")
c2.metric("시간당 작업량", f"{kpis['avg_per_hour']:.1f}")
c3.metric("재작업률", f"{kpis['rework_rate']:.1%}")
c4.metric("활성 작업자", f"{kpis['active_annotators']}")
c5.metric("경과 기간", f"{kpis['elapsed_pct']:.1%}")
c6.metric("예측 완료율", f"{kpis['predicted_pct']:.1%}")

# 일별 차트
st.markdown("## 🗓️ 일별 완료 작업수")
daily = filtered.groupby(filtered["date"].dt.date)["annotations_completed"].sum().reset_index()
fig_daily = px.line(daily, x="date", y="annotations_completed", title="Daily Annotations")
st.plotly_chart(fig_daily, use_container_width=True)
with st.expander("일별 상세 데이터", expanded=False):
    sel = st.selectbox("날짜 선택", daily["date"].astype(str))
    st.dataframe(filtered[filtered["date"].dt.date==pd.to_datetime(sel).date()])

# 주별 차트
st.markdown("## 📅 주별 완료 작업수")
weekly = filtered.groupby("week_label")["annotations_completed"].sum().reset_index()
fig_weekly = px.bar(weekly, x="week_label", y="annotations_completed", title="Weekly Annotations")
fig_weekly.update_xaxes(tickangle= -45)
st.plotly_chart(fig_weekly, use_container_width=True)
with st.expander("주별 상세 데이터", expanded=False):
    sel = st.selectbox("주차 선택", weekly["week_label"])
    st.dataframe(filtered[filtered["week_label"]==sel])

# 작업자별 차트
st.markdown("## 👥 작업자별 완료 작업수")
by_w = filtered.groupby("annotator_name")["annotations_completed"].sum().reset_index()
fig_worker = px.bar(by_w, x="annotator_name", y="annotations_completed", title="By Annotator")
st.plotly_chart(fig_worker, use_container_width=True)
with st.expander("작업자별 상세 데이터", expanded=False):
    sel = st.selectbox("작업자 선택", by_w["annotator_name"])
    st.dataframe(filtered[filtered["annotator_name"]==sel])

# Phase 차트
st.markdown("## 🎯 Phase별 완료 작업 비율")
phase = filtered.groupby("project_phase")["annotations_completed"].sum().reset_index()
fig_phase = px.pie(phase, names="project_phase", values="annotations_completed", title="By Phase")
st.plotly_chart(fig_phase, use_container_width=True)
with st.expander("Phase별 상세 데이터", expanded=False):
    sel = st.selectbox("Phase 선택", phase["project_phase"])
    st.dataframe(filtered[filtered["project_phase"]==sel])

# 전체 데이터
with st.expander("📋 전체 데이터 보기/다운로드", expanded=False):
    st.dataframe(filtered)
    csv = filtered.to_csv(index=False)
    st.download_button("CSV 다운로드", csv, "data.csv", "text/csv")
