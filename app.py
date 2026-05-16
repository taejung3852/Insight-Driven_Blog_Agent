import streamlit as st
import tempfile
import os
import re
import uuid
from src.graph import app as doc_workflow
from src.memory import get_all_systems, delete_system, save_user_guideline
from src.utils import extract_tech_doc_style, synthesize_tech_feedback

# 페이지 인프라 정의
st.set_page_config(
    page_title="AutoDoc-MAS: Enterprise Technical Documentation System",
    layout="wide"
)

st.title("AutoDoc-MAS: Enterprise Tech-Doc Control Center")
st.markdown("파편화된 원시 기술 데이터를 수집하여 사내 기술 표준 가이드라인에 부합하는 엔터프라이즈급 기술 문서를 생성하고 형상을 관리합니다.")

# 사이드바 인프라 제어 (시스템 형상 관리 및 규격 설정)
with st.sidebar:
    st.header("System Configuration")
    
    existing_systems = get_all_systems()
    system_options = ["Create New System Namespace..."] + existing_systems
    
    if 'new_system_to_select' in st.session_state:
        if st.session_state['new_system_to_select'] not in system_options:
            system_options.append(st.session_state['new_system_to_select'])
            
    def on_system_change():
        if 'thread_id' in st.session_state:
            del st.session_state['thread_id']
        if 'new_system_to_select' in st.session_state:
            del st.session_state['new_system_to_select']
            
    selected_system = st.selectbox(
        "Target System Namespace",
        options=system_options,
        index=0,
        key="system_selector",
        on_change=on_system_change
    )
    
    if selected_system == "Create New System Namespace...":
        system_name = st.text_input("System Identifier", placeholder="e.g., Auth-Service-v2")
        is_update_request = False
    else:
        system_name = selected_system
        is_update_request = True
        st.info(f"Active System Namespace: {system_name}")
        
        if st.button("Delete System Data", use_container_width=True):
            if delete_system(system_name):
                st.toast(f"Namespace '{system_name}' Deleted Successfully.")
                st.rerun()
                
    st.session_state['system_name'] = system_name
    st.session_state['is_update_request'] = is_update_request
    
    st.markdown("---")
    st.header("Artifact Specifications")
    
    doc_type = st.selectbox(
        "Document Type",
        options=["feature_spec", "release_note", "api_doc"],
        index=0
    )
    
    st.markdown("---")
    st.header("Compliance & Quality Assurance")
    
    doc_style_guide_input = st.text_area(
        "Corporate Style Guide / Compliance Guidelines",
        height=150,
        placeholder="e.g., Use 3rd-person objective tone. Maintain markdown hierarchy."
    )
    
    style_extraction_method = st.checkbox("Extract Style from Existing Document Sample")
    if style_extraction_method:
        sample_doc_text = st.text_area("Paste Corporate Document Sample", height=150)
        if st.button("Analyze & Extract Guidelines", use_container_width=True):
            if sample_doc_text.strip():
                with st.spinner("Analyzing text patterns..."):
                    extracted_guide = extract_tech_doc_style(sample_doc_text)
                    st.session_state['extracted_guide'] = extracted_guide
                st.success("Extraction Completed.")
        doc_style_guide = st.session_state.get('extracted_guide', doc_style_guide_input)
    else:
        doc_style_guide = doc_style_guide_input
        
    max_revisions = st.slider("Max QA Critic Revisions", min_value=1, max_value=3, value=2)
    st.markdown("---")

# 메인 작업 공간 (데이터 수집 및 적재)
col1, col2 = st.columns([1, 1])
with col1:
    active_name = st.session_state.get('system_name') if st.session_state.get('system_name') else 'Unassigned'
    st.subheader(f"Raw Technical Data Input [{active_name}]")
    source_input_type = st.radio("Source Format", ["Direct Text / Logs / Commits", "File Upload (.md, .txt)"], horizontal=True)
    
    technical_source = ""
    if source_input_type == "Direct Text / Logs / Commits":
        technical_source = st.text_area("Input Fragmented Technical Source Data", height=200)
    else:
        uploaded_file = st.file_uploader("Upload Technical Source File", type=['txt', 'md'])
        if uploaded_file:
            technical_source = uploaded_file.getvalue().decode("utf-8")

with col2:
    st.subheader("Architecture Diagrams / Visual Specs")
    uploaded_diagrams = st.file_uploader("Upload Architecture Diagrams or ERD Images", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

# 파이프라인 트리거
if st.button("Execute AutoDoc-MAS Pipeline", use_container_width=True, type="primary"):
    system_to_run = st.session_state.get('system_name')
    if not system_to_run or not technical_source:
        st.error("Execution Failed: System Identifier and Technical Source Data are strictly required.")
        st.stop()
        
    temp_diagram_paths = []
    if uploaded_diagrams:
        temp_dir = tempfile.mkdtemp()
        for img in uploaded_diagrams:
            temp_path = os.path.join(temp_dir, img.name)
            with open(temp_path, "wb") as f:
                f.write(img.getbuffer())
            temp_diagram_paths.append(temp_path)

    st.session_state['thread_id'] = str(uuid.uuid4())
    config = {"configurable": {"thread_id": st.session_state['thread_id']}}

    initial_state = {
        "doc_type": doc_type,
        "system_name": system_to_run,
        "doc_style_guide": doc_style_guide,
        "technical_source": technical_source,
        "is_update_request": st.session_state.get('is_update_request', False),
        "revision_count": 0,
        "max_revisions": max_revisions,
        "captured_diagrams": temp_diagram_paths
    }

    st.markdown("---")
    st.subheader("Agent Telemetry & Execution Logs")
    
    with st.status("Initializing StateGraph Infrastructure...", expanded=True) as status:
        for output in doc_workflow.stream(initial_state, config=config, stream_mode="updates"):
            for node_name, state_update in output.items():
                st.write(f"Node Executed Successfully: [{node_name}]")
        status.update(label="Pipeline Suspended: Awaiting Human Verification", state="complete", expanded=False)

# HITL 및 수동 재정의 (Manual Override) 엔지니어링 파트
if 'thread_id' in st.session_state:
    config = {"configurable": {"thread_id": st.session_state['thread_id']}}
    current_snapshot = doc_workflow.get_state(config)
    full_state = current_snapshot.values
    
    is_paused = len(current_snapshot.next) > 0 and current_snapshot.next[0] == "human_approval"
    
    if is_paused:
        st.markdown("---")
        st.warning("Verification Needed: Compliance and drafting stages completed. Review the artifact below.")
        
        draft_text = full_state.get("tech_reviewed_content", "")
        edited_text = st.text_area("Technical Document Editor (Manual Override)", value=draft_text, height=500)
        
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            feedback_tech = st.text_input("Technical Fact Correction Feedback", placeholder="e.g., Modify the API endpoint response block to include error schemas.")
        with f_col2:
            feedback_compliance = st.text_input("Compliance & Format Feedback", placeholder="e.g., Re-format the code snippet to follow standard conventions.")
            
        if st.button("Approve & Publish Document", type="primary", use_container_width=True):
            with st.spinner("Processing structural adjustments and optimization..."):
                if feedback_tech or feedback_compliance or (draft_text != edited_text):
                    synthesized = synthesize_tech_feedback(edited_text, feedback_tech, feedback_compliance)
                    
                    if synthesized.get("technical_rule"):
                        # 백엔드 피드백 보관소 활용 명시
                        save_user_guideline(full_state['system_name'], synthesized["technical_rule"])
                        
            # StateGraph 제어권 반환 데이터 구성
            doc_workflow.update_state(
                config,
                {
                    "human_review_complete": True, 
                    "final_doc": edited_text,
                    "human_feedback_technical": feedback_tech,
                    "human_feedback_compliance": feedback_compliance
                }
            )
            
            with st.spinner("Executing final synchronization and persistence..."):
                for _ in doc_workflow.stream(None, config=config):
                    pass
                    
            st.success("Artifact Saved and Vector Database Synchronized Successfully.")
            st.rerun()
            
    else:
        st.markdown("### Production Technical Artifact View")
        with st.expander("System Telemetry Details"):
            if "doc_outline" in full_state: 
                st.markdown(f"**[Generated Document Outline]**\n\n{full_state['doc_outline']}")
            if "diagram_analysis_result" in full_state: 
                st.info(f"**[Vision Model Diagram Analysis Result]**\n\n{full_state['diagram_analysis_result']}")

        final_artifact = full_state.get("final_doc") or full_state.get("tech_reviewed_content")
        
        if final_artifact:
            st.success("Verified Artifact Status: Certified and Synced.")
            preview_tab, code_tab = st.tabs(["Rendered Specification View", "Markdown Source Code"])
            with preview_tab:
                # 콤포넌트 수준 다이어그램 삽입 마커 파싱 및 뷰어 치환 정규식 처리
                display_text = re.sub(
                    r'<!--\s*\[Diagram:\s*(.*?)\]\s*-->',
                    r'\n\n> 🖼️ **[Diagram Resource Embedded: \1]**\n\n',
                    final_artifact,
                    flags=re.IGNORECASE
                )
                st.markdown(display_text)
            with code_tab:
                st.code(final_artifact, language="markdown")