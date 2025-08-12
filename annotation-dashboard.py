# Data Annotation Project Management Dashboard
# Author: AI Assistant
# Description: Streamlit dashboard for managing data annotation projects

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta, date
import warnings
warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(
    page_title="Data Annotation Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Airtable/Power BI style design
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .kpi-container {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid #e0e0e0;
    }
    .status-good { color: #28a745; font-weight: bold; }
    .status-warning { color: #ffc107; font-weight: bold; }
    .status-danger { color: #dc3545; font-weight: bold; }
    .sidebar-section {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown("""
<div class="main-header">
    <h1>📊 Data Annotation Project Dashboard</h1>
    <p>실시간 프로젝트 관리 및 품질 모니터링</p>
</div>
""", unsafe_allow_html=True)

def load_sample_data():
    """Generate sample data for demonstration"""
    np.random.seed(42)
    dates = pd.date_range(start='2025-07-01', end='2025-08-12', freq='D')
    
    annotators = ['김민수', '이영희', '박지원', '최유진', '정성호']
    task_types = ['이미지_분류', '텍스트_태깅', '객체_탐지', '의료_영상', '음성_전사']
    
    data = []
    for i, date_val in enumerate(dates):
        for annotator in annotators:
            if np.random.random() > 0.3:  # Not everyone works every day
                data.append({
                    'date': date_val,
                    'annotator_id': f'ANN{annotators.index(annotator)+1:03d}',
                    'annotator_name': annotator,
                    'task_id': f'TASK{np.random.randint(1, 1000):04d}',
                    'task_type': np.random.choice(task_types),
                    'annotations_completed': np.random.randint(5, 50),
                    'time_spent_minutes': np.random.randint(60, 480),
                    'accuracy_score': np.random.uniform(0.85, 0.99),
                    'quality_rating': np.random.uniform(3.5, 5.0),
                    'rework_required': np.random.poisson(0.5),
                    'project_phase': np.random.choice(['Phase1', 'Phase2', 'Phase3']),
                    'week_number': date_val.isocalendar()[1]
                })
    
    return pd.DataFrame(data)

def calculate_kpis(df):
    """Calculate key performance indicators"""
    if df.empty:
        return {}
    
    total_annotations = df['annotations_completed'].sum()
    total_time = df['time_spent_minutes'].sum()
    avg_accuracy = df['accuracy_score'].mean()
    avg_quality = df['quality_rating'].mean()
    total_rework = df['rework_required'].sum()
    unique_annotators = df['annotator_name'].nunique()
    
    return {
        'total_annotations': total_annotations,
        'avg_annotations_per_hour': total_annotations / (total_time / 60) if total_time > 0 else 0,
        'avg_time_per_annotation': total_time / total_annotations if total_annotations > 0 else 0,
        'overall_accuracy': avg_accuracy,
        'avg_quality_rating': avg_quality,
        'rework_rate': total_rework / total_annotations if total_annotations > 0 else 0,
        'active_annotators': unique_annotators,
        'productivity_index': (total_annotations * avg_accuracy) / (total_time / 60) if total_time > 0 else 0
    }

def get_status_color(value, thresholds):
    """Get status color based on value and thresholds"""
    if value >= thresholds['good']:
        return 'status-good'
    elif value >= thresholds['warning']:
        return 'status-warning'
    else:
        return 'status-danger'

# Sidebar for data upload and filters
with st.sidebar:
    st.markdown("""
    <div class="sidebar-section">
        <h3>📁 데이터 업로드</h3>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "CSV 파일을 업로드하세요",
        type=['csv'],
        help="프로젝트 데이터가 포함된 CSV 파일을 선택하세요"
    )
    
    use_sample = st.checkbox("샘플 데이터 사용", value=True)
    
    st.markdown("""
    <div class="sidebar-section">
        <h3>🔍 필터 옵션</h3>
    </div>
    """, unsafe_allow_html=True)

# Load data
if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        df['date'] = pd.to_datetime(df['date'])
        st.success("✅ 데이터가 성공적으로 로드되었습니다!")
    except Exception as e:
        st.error(f"❌ 파일 로드 중 오류가 발생했습니다: {str(e)}")
        df = pd.DataFrame()
elif use_sample:
    df = load_sample_data()
    st.info("📊 샘플 데이터를 사용 중입니다.")
else:
    df = pd.DataFrame()
    st.warning("⚠️ 데이터를 업로드하거나 샘플 데이터를 활성화하세요.")

if not df.empty:
    # Sidebar filters
    with st.sidebar:
        date_range = st.date_input(
            "📅 날짜 범위",
            value=(df['date'].min().date(), df['date'].max().date()),
            min_value=df['date'].min().date(),
            max_value=df['date'].max().date()
        )
        
        if len(date_range) == 2:
            start_date, end_date = date_range
            df = df[(df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)]
        
        selected_annotators = st.multiselect(
            "👥 작업자 선택",
            options=df['annotator_name'].unique().tolist(),
            default=df['annotator_name'].unique().tolist()
        )
        
        selected_task_types = st.multiselect(
            "📋 작업 유형",
            options=df['task_type'].unique().tolist(),
            default=df['task_type'].unique().tolist()
        )
        
        selected_phases = st.multiselect(
            "🎯 프로젝트 단계",
            options=df['project_phase'].unique().tolist(),
            default=df['project_phase'].unique().tolist()
        )
        
        # Apply filters
        df_filtered = df[
            (df['annotator_name'].isin(selected_annotators)) &
            (df['task_type'].isin(selected_task_types)) &
            (df['project_phase'].isin(selected_phases))
        ]
    
    # Calculate KPIs
    kpis = calculate_kpis(df_filtered)
    
    # Executive Summary Dashboard
    st.markdown("## 📈 Executive Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            "총 완료 작업",
            f"{kpis.get('total_annotations', 0):,}",
            delta=f"+{kpis.get('total_annotations', 0)*0.05:.0f} (주간)"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        accuracy = kpis.get('overall_accuracy', 0)
        accuracy_status = get_status_color(accuracy, {'good': 0.95, 'warning': 0.90})
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("전체 정확도", f"{accuracy:.1%}")
        st.markdown(f'<p class="{accuracy_status}">{"우수" if accuracy >= 0.95 else "보통" if accuracy >= 0.90 else "개선 필요"}</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        productivity = kpis.get('avg_annotations_per_hour', 0)
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("시간당 작업량", f"{productivity:.1f}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        rework_rate = kpis.get('rework_rate', 0)
        rework_status = get_status_color(1-rework_rate, {'good': 0.95, 'warning': 0.90})
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("재작업률", f"{rework_rate:.1%}")
        st.markdown(f'<p class="{rework_status}">{"우수" if rework_rate <= 0.05 else "보통" if rework_rate <= 0.10 else "개선 필요"}</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Quality Management Section
    st.markdown("## 🎯 Quality Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Accuracy trend over time
        daily_accuracy = df_filtered.groupby(df_filtered['date'].dt.date)['accuracy_score'].mean().reset_index()
        fig_accuracy = px.line(
            daily_accuracy, 
            x='date', 
            y='accuracy_score',
            title='📊 일별 정확도 추이',
            labels={'accuracy_score': '정확도', 'date': '날짜'}
        )
        fig_accuracy.update_traces(line_color='#667eea')
        fig_accuracy.add_hline(y=0.95, line_dash="dash", line_color="green", annotation_text="목표 (95%)")
        st.plotly_chart(fig_accuracy, use_container_width=True)
    
    with col2:
        # Quality rating by task type
        quality_by_type = df_filtered.groupby('task_type')['quality_rating'].mean().reset_index()
        fig_quality = px.bar(
            quality_by_type,
            x='task_type',
            y='quality_rating',
            title='📋 작업 유형별 품질 평점',
            labels={'quality_rating': '품질 평점', 'task_type': '작업 유형'},
            color='quality_rating',
            color_continuous_scale='RdYlGn'
        )
        st.plotly_chart(fig_quality, use_container_width=True)
    
    # Team Performance Section
    st.markdown("## 👥 Team Performance")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Annotator performance comparison
        annotator_perf = df_filtered.groupby('annotator_name').agg({
            'annotations_completed': 'sum',
            'accuracy_score': 'mean',
            'quality_rating': 'mean'
        }).reset_index()
        
        fig_perf = px.scatter(
            annotator_perf,
            x='annotations_completed',
            y='accuracy_score',
            size='quality_rating',
            hover_name='annotator_name',
            title='👤 작업자 성과 비교 (크기: 품질평점)',
            labels={'annotations_completed': '완료 작업수', 'accuracy_score': '정확도'},
            color='quality_rating',
            color_continuous_scale='RdYlGn'
        )
        st.plotly_chart(fig_perf, use_container_width=True)
    
    with col2:
        # Weekly productivity trend
        weekly_prod = df_filtered.groupby(['week_number', 'annotator_name'])['annotations_completed'].sum().reset_index()
        fig_weekly = px.line(
            weekly_prod,
            x='week_number',
            y='annotations_completed',
            color='annotator_name',
            title='📅 주별 생산성 추이',
            labels={'annotations_completed': '완료 작업수', 'week_number': '주차'}
        )
        st.plotly_chart(fig_weekly, use_container_width=True)
    
    # Time Analysis Section
    st.markdown("## ⏱️ Time Analysis")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Time efficiency by task type
        time_efficiency = df_filtered.groupby('task_type').apply(
            lambda x: x['annotations_completed'].sum() / (x['time_spent_minutes'].sum() / 60)
        ).reset_index()
        time_efficiency.columns = ['task_type', 'annotations_per_hour']
        
        fig_time = px.bar(
            time_efficiency,
            x='task_type',
            y='annotations_per_hour',
            title='⚡ 작업 유형별 시간 효율성',
            labels={'annotations_per_hour': '시간당 작업수', 'task_type': '작업 유형'},
            color='annotations_per_hour',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_time, use_container_width=True)
    
    with col2:
        # Average time per annotation by annotator
        avg_time = df_filtered.groupby('annotator_name').apply(
            lambda x: x['time_spent_minutes'].sum() / x['annotations_completed'].sum()
        ).reset_index()
        avg_time.columns = ['annotator_name', 'avg_minutes_per_annotation']
        
        fig_avg_time = px.bar(
            avg_time,
            x='annotator_name',
            y='avg_minutes_per_annotation',
            title='👤 작업자별 평균 소요시간',
            labels={'avg_minutes_per_annotation': '평균 소요시간 (분)', 'annotator_name': '작업자'},
            color='avg_minutes_per_annotation',
            color_continuous_scale='RdYlBu_r'
        )
        st.plotly_chart(fig_avg_time, use_container_width=True)
    
    with col3:
        # Project phase progress
        phase_progress = df_filtered.groupby('project_phase')['annotations_completed'].sum().reset_index()
        fig_phase = px.pie(
            phase_progress,
            values='annotations_completed',
            names='project_phase',
            title='🎯 프로젝트 단계별 진행률'
        )
        st.plotly_chart(fig_phase, use_container_width=True)
    
    # Detailed Data Table
    with st.expander("📋 상세 데이터 테이블", expanded=False):
        st.dataframe(
            df_filtered.sort_values('date', ascending=False),
            use_container_width=True,
            hide_index=True
        )
        
        # Export functionality
        csv_data = df_filtered.to_csv(index=False)
        st.download_button(
            label="📥 필터된 데이터 다운로드 (CSV)",
            data=csv_data,
            file_name=f"annotation_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

else:
    # Instructions for CSV format
    st.markdown("## 📋 CSV 데이터 형식")
    
    sample_format = pd.DataFrame({
        'date': ['2025-08-01', '2025-08-02'],
        'annotator_id': ['ANN001', 'ANN002'],
        'annotator_name': ['김민수', '이영희'],
        'task_id': ['TASK001', 'TASK002'],
        'task_type': ['이미지_분류', '텍스트_태깅'],
        'annotations_completed': [25, 18],
        'time_spent_minutes': [120, 95],
        'accuracy_score': [0.95, 0.92],
        'quality_rating': [4.5, 4.2],
        'rework_required': [0, 1],
        'project_phase': ['Phase1', 'Phase1'],
        'week_number': [31, 31]
    })
    
    st.markdown("### 필수 컬럼:")
    st.dataframe(sample_format, use_container_width=True, hide_index=True)
    
    # Sample CSV download
    sample_csv = sample_format.to_csv(index=False)
    st.download_button(
        label="📥 샘플 CSV 템플릿 다운로드",
        data=sample_csv,
        file_name="annotation_template.csv",
        mime="text/csv"
    )
    
    st.markdown("""
    ### 컬럼 설명:
    - **date**: 작업 날짜 (YYYY-MM-DD 형식)
    - **annotator_id**: 작업자 고유 ID
    - **annotator_name**: 작업자 이름
    - **task_id**: 작업 고유 ID
    - **task_type**: 작업 유형 (이미지_분류, 텍스트_태깅 등)
    - **annotations_completed**: 완료된 어노테이션 수
    - **time_spent_minutes**: 소요 시간 (분)
    - **accuracy_score**: 정확도 점수 (0-1)
    - **quality_rating**: 품질 평점 (1-5)
    - **rework_required**: 재작업 필요 건수
    - **project_phase**: 프로젝트 단계
    - **week_number**: 주차
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666;">
    <p>Data Annotation Project Dashboard v1.0 | Built with Streamlit & Plotly</p>
</div>
""", unsafe_allow_html=True)