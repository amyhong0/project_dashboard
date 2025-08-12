# annotation-dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Data Annotation Dashboard", layout="wide")

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
    # 컬럼명 변환
    df = raw.rename(columns=STANDARD_COLUMNS)
    # 표준 컬럼만 선택
    df = df[list(STANDARD_COLUMNS.values())].copy()
    # 날짜 파싱
    for col in ["date", "review_date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    # 숫자 변환
    for col in ["annotations_completed", "rework_required", "valid_count", "time_spent_minutes"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    # 주차 계산
    df["week_number"] = df["date"].dt.isocalendar().week
    # 전체 기간 자동 파악
    df["min_date"] = df["date"].min()
    df["max_date"] = df["date"].max()
    # 프로젝트 단계(Phase) 분할: 1/3 지점 단위
    total_days = (df["max_date"].iloc[0] - df["min_date"].iloc[0]).days + 1
    cut_points = [
        -1,
        total_days * 1/3,
        total_days * 2/3,
        total_days + 1
    ]
    df["days_since_start"] = (df["date"] - df["min_date"]).dt.days
    df["project_phase"] = pd.cut(
        df["days_since_start"],
        bins=cut_points,
        labels=["Phase1", "Phase2", "Phase3"]
    )
    # 필요 컬럼만 반환
    return df.drop(columns=["min_date", "max_date", "days_since_start"])

def calculate_kpis(df: pd.DataFrame) -> dict:
    total = df["annotations_completed"].sum()
    hours = df["time_spent_minutes"].sum() / 60
    return {
        "total_annotations": total,
        "avg_per_hour": total / hours if hours else 0,
        "rework_rate": df["rework_required"].sum() / total if total else 0,
        "active_annotators": df["annotator_name"].nunique()
    }

# 사이드바: CSV 업로드 & 기간 설정
st.sidebar.header("📁 데이터 업로드 및 설정")
uploaded = st.sidebar.file_uploader("Raw CSV 파일 선택", type="csv")
use_sample = st.sidebar.checkbox("샘플 데이터 사용", value=False)

if uploaded:
    raw_df = pd.read_csv(uploaded, dtype=str)
    df = load_and_clean(raw_df)
elif use_sample:
    # 이전 export.csv 형식의 샘플 로드 (파일명: export.csv)
    raw_df = pd.read_csv("export.csv", dtype=str)
    df = load_and_clean(raw_df)
else:
    st.info("Raw CSV를 업로드하거나 샘플 데이터를 선택하세요.")
    st.stop()

# 전체 기간 입력 또는 자동
st.sidebar.markdown("### 📅 전체 기간 설정")
auto_period = st.sidebar.checkbox("기간 자동 설정", value=True)
if auto_period:
    start_date = df["date"].min().date()
    end_date = df["date"].max().date()
else:
    start_date, end_date = st.sidebar.date_input(
        "기간 선택",
        value=(df["date"].min().date(), df["date"].max().date()),
        min_value=df["date"].min().date(),
        max_value=df["date"].max().date()
    )

# 필터: 기간, 작업자
mask = (df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)
filtered = df.loc[mask]
annotators = st.sidebar.multiselect(
    "작업자 선택",
    options=filtered["annotator_name"].unique(),
    default=filtered["annotator_name"].unique()
)
filtered = filtered[filtered["annotator_name"].isin(annotators)]

# KPI 계산
kpis = calculate_kpis(filtered)

# Executive Summary
st.markdown("## 📈 Executive Summary")
col1, col2, col3, col4 = st.columns(4)
col1.metric("총 완료 작업", f"{kpis['total_annotations']:,}")
col2.metric("시간당 작업량", f"{kpis['avg_per_hour']:.1f}")
col3.metric("재작업률", f"{kpis['rework_rate']:.1%}")
col4.metric("활성 작업자", f"{kpis['active_annotators']}")

# 전체 기간별 분석
st.markdown("## 🗓️ 전체 기간별 분석")
daily = filtered.groupby(filtered["date"].dt.date)["annotations_completed"].sum().reset_index()
fig_daily = px.line(daily, x="date", y="annotations_completed", title="일별 완료 작업수")
st.plotly_chart(fig_daily, use_container_width=True)

# 주 단위 분석 (주차 자동 반영)
st.markdown("## 📅 주 단위 분석")
weekly = filtered.groupby("week_number")["annotations_completed"].sum().reset_index()
fig_weekly = px.bar(weekly, x="week_number", y="annotations_completed", title="주별 완료 작업수")
st.plotly_chart(fig_weekly, use_container_width=True)

# 작업자별 분석
st.markdown("## 👥 작업자별 분석")
by_worker = filtered.groupby("annotator_name").agg({
    "annotations_completed": "sum",
    "time_spent_minutes": "sum",
    "rework_required": "sum"
}).reset_index()
by_worker["avg_time_per_item"] = by_worker["time_spent_minutes"] / by_worker["annotations_completed"]
fig_worker = px.bar(
    by_worker,
    x="annotator_name",
    y="annotations_completed",
    title="작업자별 완료 작업수",
    color="avg_time_per_item",
    labels={"avg_time_per_item": "평균 소요시간(분)"}
)
st.plotly_chart(fig_worker, use_container_width=True)

# 프로젝트 단계별 분석
st.markdown("## 🎯 프로젝트 단계별 분석")
phase = filtered.groupby("project_phase")["annotations_completed"].sum().reset_index()
fig_phase = px.pie(phase, names="project_phase", values="annotations_completed", title="Phase별 완료 작업 비율")
st.plotly_chart(fig_phase, use_container_width=True)

# 상세 테이블 및 다운로드
with st.expander("📋 상세 데이터"):
    st.dataframe(filtered.sort_values("date", ascending=False))
    csv = filtered.to_csv(index=False)
    st.download_button("CSV 다운로드", data=csv, file_name="filtered_data.csv", mime="text/csv")
