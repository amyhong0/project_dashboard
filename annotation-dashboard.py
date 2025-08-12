# annotation-dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Project Dashboard", layout="wide")

# --- Custom CSS for header ---
st.markdown("""
<style>
.main-header {
    background-color: #2C3E50;  /* Power BI style navy */
    padding: 1rem;
    border-radius: 8px;
    color: white;
    text-align: center;
    margin-bottom: 1.5rem;
}
</style>
""", unsafe_allow_html=True)

# --- 유틸리티 함수 ---
def parse_date(x):
    try:
        return pd.to_datetime(x, errors="coerce")
    except:
        return pd.NaT

# 컬럼명 매핑 (raw → 내부)
COL_MAPPING = {
    "프로젝트ID":          "project_id",
    "데이터 ID":           "task_id",
    "작업 상태":           "task_status",
    "작업불가여부":         "unusable_flag",
    "최종 오브젝트 수":     "annotations_completed",
    "수정 여부":           "rework_required",
    "유효 오브젝트 수":     "valid_objects",
    "Worker ID":          "annotator_id",
    "작업자 닉네임":         "annotator_name",
    "Checker ID":         "checker_id",
    "검수자 닉네임":         "checker_name",
    "작업 종료일":          "date",
    "검수 종료일":          "review_date",
    "작업 수정 시간":        "time_spent_minutes",
    "CO 모니터링 URL":      "monitoring_url"
}

EXPECTED_COLS = [
    "date","review_date","project_id","task_id","task_status","unusable_flag",
    "annotations_completed","valid_objects","rework_required","time_spent_minutes",
    "annotator_id","annotator_name","checker_id","checker_name","monitoring_url"
]

# --- 사이드바: 파일 업로드 & 기간 선택 ---
st.sidebar.title("설정")
uploaded = st.sidebar.file_uploader("CSV 파일 업로드", type=["csv"])
use_sample = st.sidebar.checkbox("샘플 데이터로 테스트", value=False)

start_date = st.sidebar.date_input("분석 시작일", value=datetime.today().date())
end_date   = st.sidebar.date_input("분석 종료일", value=datetime.today().date())

# --- Main Header ---
st.markdown('<div class="main-header"><h1>Project Dashboard</h1></div>', unsafe_allow_html=True)

# 샘플 데이터 로더 (테스트용)
def load_sample_data():
    np.random.seed(1)
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    annotators = ["A", "B", "C"]
    data = []
    for d in dates:
        for w in annotators:
            if np.random.rand()>0.3:
                data.append({
                    "date": d, "review_date": d + pd.Timedelta(days=1),
                    "project_id":"PRJ", "task_id":f"T{np.random.randint(1,1000)}",
                    "task_status":"완료","unusable_flag":"N",
                    "annotations_completed":np.random.randint(5,50),
                    "valid_objects":np.random.randint(3,45),
                    "rework_required":np.random.randint(0,3),
                    "time_spent_minutes":np.random.randint(30,240),
                    "annotator_id":w, "annotator_name":w,
                    "checker_id":"CK", "checker_name":"CK",
                    "monitoring_url":""
                })
    return pd.DataFrame(data)

# 데이터 로드 & 전처리
if uploaded is not None or use_sample:
    if uploaded:
        df_raw = pd.read_csv(uploaded, dtype=str).fillna("")
    else:
        df_raw = load_sample_data().astype(str)
    # 컬럼 매핑
    df_raw = df_raw.rename(columns=COL_MAPPING)
    # 예상 컬럼 확보
    for col in EXPECTED_COLS:
        if col not in df_raw:
            df_raw[col] = ""
    df = df_raw[EXPECTED_COLS].copy()
    # 타입 변환
    df["date"]  = df["date"].apply(parse_date)
    df["review_date"] = df["review_date"].apply(parse_date)
    df["annotations_completed"] = pd.to_numeric(df["annotations_completed"], errors="coerce").fillna(0).astype(int)
    df["valid_objects"]         = pd.to_numeric(df["valid_objects"], errors="coerce").fillna(0).astype(int)
    df["rework_required"]       = pd.to_numeric(df["rework_required"], errors="coerce").fillna(0).astype(int)
    df["time_spent_minutes"]    = pd.to_numeric(df["time_spent_minutes"], errors="coerce").fillna(0).astype(int)
    # 전체 기간 필터
    mask = (df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)
    df = df.loc[mask].copy()
    st.success(f"데이터 로드 완료: {len(df)}건")
else:
    st.info("왼쪽 사이드바에서 CSV 파일 업로드 또는 샘플 데이터 선택 후 기간을 설정하세요.")
    st.stop()

# --- KPI 계산 ---
total = df["annotations_completed"].sum()
avg_time = (df["time_spent_minutes"] / df["annotations_completed"].replace(0,np.nan)).mean()
valid_rate = (df["valid_objects"] / df["annotations_completed"].replace(0,np.nan)).mean()

col1, col2, col3 = st.columns(3)
col1.metric("총 어노테이션", f"{total:,}")
col2.metric("평균 소요시간(분)", f"{avg_time:.2f}")
col3.metric("유효 오브젝트 비율", f"{valid_rate:.1%}")

# --- 전체 기간 분석 차트 ---
st.subheader("1. 전체 기간 분석")
daily = df.dropna(subset=["date"]).groupby(df["date"].dt.date)["annotations_completed"].sum().reset_index()
fig_daily = px.bar(daily, x="date", y="annotations_completed", title="일별 완료 건수")
st.plotly_chart(fig_daily, use_container_width=True)

# --- 주 단위 분석 ---
st.subheader("2. 주 단위 분석")
df["week"] = df["date"].dt.isocalendar().week
weekly = df.groupby("week")["annotations_completed"].sum().reset_index()
fig_weekly = px.line(weekly, x="week", y="annotations_completed", markers=True,
                     title="주별 완료 건수")
st.plotly_chart(fig_weekly, use_container_width=True)

# --- 작업자별 주간 생산성 ---
st.subheader("3. 작업자별 주간 생산성")
weekly_worker = df.groupby(["week","annotator_name"])["annotations_completed"].sum().reset_index()
fig_wk_worker = px.line(weekly_worker, x="week", y="annotations_completed", color="annotator_name",
                        title="작업자별 주간 작업수")
st.plotly_chart(fig_wk_worker, use_container_width=True)

# --- 상세 데이터 테이블 & 다운로드 ---
with st.expander("🔍 상세 데이터 보기"):
    st.dataframe(df.sort_values("date", ascending=False), use_container_width=True)
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("CSV 다운로드", csv, "filtered_data.csv", "text/csv")
