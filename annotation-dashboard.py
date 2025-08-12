# Data Annotation Project Management Dashboard (v1.3)
# Author: AI Assistant
# Date: 2025-08-12
# Description: Streamlit dashboard with updated header title and Power BI-style color

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime
from dateutil.parser import parse
import warnings
warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────────────────
# 📄 PAGE CONFIGURATION
# ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Project Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────
# 🎨 CUSTOM CSS (Power BI simple color)
# ──────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
        .main-header {
            background-color: #0078D4;
            padding: 1rem;
            border-radius: 10px;
            color: white;
            text-align: center;
            margin-bottom: 2rem;
        }
        .metric-card {
            background: white;
            padding: 1.3rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border: 1px solid #e0e0e0;
        }
        .status-good { color:#28a745; font-weight:bold; }
        .status-warning { color:#ffc107; font-weight:bold; }
        .status-danger { color:#dc3545; font-weight:bold; }
        .sidebar-section {
            background:#f8f9fa;
            padding:1rem;
            border-radius:8px;
            margin:1rem 0;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────
# 📊 SAMPLE DATA (fallback)
# ──────────────────────────────────────────────────────────────
def load_sample_data() -> pd.DataFrame:
    np.random.seed(42)
    dates = pd.date_range("2025-07-01", "2025-08-12", freq="D")
    annotators = ["김민수", "이영희", "박지원", "최유진", "정성호"]
    task_types = ["이미지_분류", "텍스트_태깅", "객체_탐지", "의료_영상", "음성_전사"]
    rows = []
    for d in dates:
        for name in annotators:
            if np.random.rand() > 0.3:
                rows.append({
                    "date": d.strftime("%Y-%m-%d"),
                    "annotator_id": f"ANN{annotators.index(name)+1:03d}",
                    "annotator_name": name,
                    "task_id": f"TASK{np.random.randint(1,9999):04d}",
                    "task_type": np.random.choice(task_types),
                    "annotations_completed": str(np.random.randint(5,50)),
                    "time_spent_minutes": str(np.random.randint(60,480)),
                    "accuracy_score": f"{np.random.uniform(0.85,0.99):.4f}",
                    "quality_rating": f"{np.random.uniform(3.5,5.0):.2f}",
                    "rework_required": str(np.random.poisson(0.5)),
                    "project_phase": np.random.choice(["Phase1","Phase2","Phase3"]),
                })
    return pd.DataFrame(rows)

# ──────────────────────────────────────────────────────────────
# 🧹 DATA UTILITIES
# ──────────────────────────────────────────────────────────────
COLUMN_MAP = {
    "date": ["date","날짜","timestamp","created_at"],
    "annotator_id": ["annotator_id","worker_id"],
    "annotator_name": ["annotator_name","worker_name","name"],
    "task_id": ["task_id","job_id"],
    "task_type": ["task_type","job_type","category"],
    "annotations_completed": ["annotations_completed","completed","count"],
    "time_spent_minutes": ["time_spent_minutes","duration","minutes"],
    "accuracy_score": ["accuracy_score","accuracy","score"],
    "quality_rating": ["quality_rating","rating"],
    "rework_required": ["rework_required","rework","revision"],
    "project_phase": ["project_phase","phase"],
}
DATE_FORMATS = [
    "%Y-%m-%d","%Y/%m/%d","%m/%d/%Y","%d/%m/%Y",
    "%Y-%m-%d %H:%M:%S","%Y/%m/%d %H:%M:%S"
]

@st.cache_data(show_spinner=False)
def load_csv(file, encoding="utf-8") -> pd.DataFrame:
    file.seek(0)
    return pd.read_csv(file, dtype=str, encoding=encoding, keep_default_na=False)

def map_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename = {}
    for std, aliases in COLUMN_MAP.items():
        for a in aliases:
            if a in df.columns:
                rename[a] = std; break
    return df.rename(columns=rename)

def parse_date(val: str):
    if not val: return pd.NaT
    for f in DATE_FORMATS:
        try: return pd.to_datetime(val, format=f)
        except: pass
    try: return parse(val, fuzzy=True)
    except: return pd.NaT

def clean_data(raw: pd.DataFrame) -> pd.DataFrame:
    df = map_columns(raw.copy())
    df["date"] = df["date"].apply(parse_date)
    numeric_cols = [
        "annotations_completed","time_spent_minutes",
        "accuracy_score","quality_rating","rework_required"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

# ──────────────────────────────────────────────────────────────
# 📌 KPI HELPERS
# ──────────────────────────────────────────────────────────────
def kpi_stats(d: pd.DataFrame):
    if d.empty: return {}
    total = d.annotations_completed.sum()
    time = d.time_spent_minutes.sum()
    return {
        "ann": total,
        "acc": d.accuracy_score.mean(),
        "aph": total/(time/60) if time else 0,
        "rr": d.rework_required.sum()/total if total else 0,
    }

# ──────────────────────────────────────────────────────────────
# 🖥️ HEADER
# ──────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="main-header">
        <h1>Project Dashboard</h1>
        <p>주별 프로젝트 분석</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────
# 📁 SIDEBAR – UPLOAD & FILTERS
# ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<div class='sidebar-section'><h3>📁 CSV 업로드</h3></div>", unsafe_allow_html=True)
    upl = st.file_uploader("CSV 파일", type=["csv"])
    enc = st.selectbox("인코딩", ["utf-8","cp949"], 0)
    sample = st.checkbox("샘플 데이터 사용", True)

if upl:
    raw = load_csv(upl, enc)
    df = clean_data(raw)
    st.success("데이터 로드 완료!")
elif sample:
    df = clean_data(load_sample_data())
    st.info("샘플 데이터 사용 중")
else:
    st.warning("CSV 파일을 업로드하거나 샘플 데이터를 선택하세요.")
    st.stop()

with st.sidebar:
    st.markdown("<div class='sidebar-section'><h3>🗓️ 프로젝트 기간</h3></div>", unsafe_allow_html=True)
    min_d, max_d = df.date.min().date(), df.date.max().date()
    proj_start = st.date_input("시작일", value=min_d, min_value=min_d, max_value=max_d)
    proj_end   = st.date_input("종료일", value=max_d, min_value=min_d, max_value=max_d)
    if proj_start>proj_end:
        st.error("시작일은 종료일보다 이전이어야 합니다.")
        st.stop()
    mask = (df.date.dt.date>=proj_start)&(df.date.dt.date<=proj_end)
    df = df[mask]

with st.sidebar:
    st.markdown("<div class='sidebar-section'><h3>🔍 세부 필터</h3></div>", unsafe_allow_html=True)
    annos = st.multiselect("작업자", df.annotator_name.unique(), df.annotator_name.unique())
    types = st.multiselect("작업 유형", df.task_type.unique(), df.task_type.unique())
    df = df[df.annotator_name.isin(annos)&df.task_type.isin(types)]
    if df.empty:
        st.warning("조건에 맞는 데이터가 없습니다.")
        st.stop()

# ──────────────────────────────────────────────────────────────
# 📈 EXEC SUMMARY
# ──────────────────────────────────────────────────────────────
stat = kpi_stats(df)
cols = st.columns(4)
labels = ["총 작업","정확도","시간당 작업","재작업률"]
values = [stat['ann'], f"{stat['acc']:.1%}", f"{stat['aph']:.1f}", f"{stat['rr']:.1%}"]
for c,lab,val in zip(cols,labels,values):
    c.markdown(f"<div class='metric-card'><h6>{lab}</h6><h3>{val}</h3></div>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# 📆 WEEKLY ANALYSIS
# ──────────────────────────────────────────────────────────────
st.markdown("## 📅 Weekly Overview")
weekly = (
    df.set_index("date")
      .resample("W-MON", label="left", closed="left")
      .agg(total_annotations=("annotations_completed","sum"), avg_accuracy=("accuracy_score","mean"))
      .reset_index()
)
cols = st.columns(2)
fig1 = px.line(weekly, x="date", y="total_annotations", title="주별 완료 작업수", markers=True)
fig2 = px.line(weekly, x="date", y="avg_accuracy", title="주별 평균 정확도", markers=True, range_y=[0,1])
fig2.add_hline(y=0.95, line_dash="dash", line_color="green")
cols[0].plotly_chart(fig1, use_container_width=True)
cols[1].plotly_chart(fig2, use_container_width=True)

# ──────────────────────────────────────────────────────────────
# 👥 Team Performance & Data Table
# ──────────────────────────────────────────────────────────────
st.markdown("## 👥 Team Performance")
team = df.groupby("annotator_name").agg(ann=("annotations_completed","sum"), acc=("accuracy_score","mean")).reset_index()
fig_team = px.bar(team, x="annotator_name", y="ann", color="acc", title="작업자별 총 작업수 & 정확도", color_continuous_scale="RdYlGn")
st.plotly_chart(fig_team, use_container_width=True)

with st.expander("데이터 미리보기"):
    st.dataframe(df, use_container_width=True)
    st.download_button("CSV 다운로드", data=df.to_csv(index=False).encode("utf-8-sig"), file_name="filtered.csv", mime="text/csv")

st.markdown("<hr style='margin:2rem 0'>", unsafe_allow_html=True)
st.markdown("<div style='text-align:center;color:#666'>Project Dashboard v1.3 © 2025</div>", unsafe_allow_html=True)
