import streamlit as st
import tempfile
import os
import re
from src.graph import app as blog_workflow

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="Insight-Driven Blog Agent",
    page_icon="✍️",
    layout="wide"
)

st.title("✍️ Insight-Driven 블로그 에이전트")
st.markdown("나만의 학습 인사이트와 캡처 이미지를 바탕으로 블로그 포스팅을 자동 생성합니다.")

# 2. 사이드바 설정 (환경 설정)
with st.sidebar:
    st.header("⚙️ 환경 설정")
    post_type = st.radio("포스팅 유형", ["새로운 시리즈 시작 (1편)", "기존 시리즈 연재"])
    is_first_post = True if post_type == "새로운 시리즈 시작 (1편)" else False
    
    tone_and_manner = st.selectbox(
        "문체 (Tone & Manner)",
        ["친절하고 열정적인 1인칭", "전문적이고 객관적인", "유머러스하고 재치있는", "담담한 회고록 스타일"]
    )
    max_revisions = st.slider("Critic 최대 반려 횟수", min_value=1, max_value=3, value=2)
    st.markdown("---")

# 3. 메인 입력 화면
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("💡 학습 주제 및 인사이트")
    current_topic = st.text_input("이번 포스팅의 핵심 주제는?", placeholder="예: LangGraph 멀티 에이전트")
    
    insight_input_type = st.radio("인사이트 입력 방식", ["텍스트 직접 입력", "파일 업로드 (.md, .txt)"], horizontal=True)
    
    learning_insights = ""
    if insight_input_type == "텍스트 직접 입력":
        learning_insights = st.text_area("오늘의 핵심 깨달음 (Insight)", height=150)
    else:
        uploaded_file = st.file_uploader("인사이트 파일 업로드", type=['txt', 'md'])
        if uploaded_file:
            learning_insights = uploaded_file.getvalue().decode("utf-8")
            st.success("인사이트 파일 로드 완료!")

with col2:
    st.subheader("🖼️ 첨부 이미지 (선택 사항)")
    # 여러 장의 이미지를 업로드 받을 수 있도록 설정
    uploaded_images = st.file_uploader(
        "글에 포함할 캡처 이미지나 다이어그램을 올려주세요.", 
        type=['png', 'jpg', 'jpeg'], 
        accept_multiple_files=True
    )

# 4. 실행 버튼 및 워크플로우 구동
if st.button("🚀 블로그 포스팅 생성 시작!", use_container_width=True, type="primary"):
    
    if not current_topic or not learning_insights:
        st.error("주제와 인사이트를 모두 입력해주세요!")
        st.stop()
        
    # [핵심] 업로드된 이미지를 임시 파일로 저장하여 backend(경로 기반)로 넘길 준비
    temp_image_paths = []
    if uploaded_images:
        temp_dir = tempfile.mkdtemp()
        for img in uploaded_images:
            temp_path = os.path.join(temp_dir, img.name)
            with open(temp_path, "wb") as f:
                f.write(img.getbuffer())
            temp_image_paths.append(temp_path)

    initial_state = {
        "is_first_post": is_first_post,
        "current_topic": current_topic,
        "tone_and_manner": tone_and_manner,
        "learning_insights": learning_insights,
        "captured_images": temp_image_paths, # 임시 경로 리스트 전달
        "revision_count": 0,
        "max_revisions": max_revisions
    }

    st.markdown("---")
    st.subheader("🤖 에이전트 작업 현황")
    
    with st.status("워크플로우 실행 중...", expanded=True) as status:
        full_state = initial_state.copy() 
        
        # 워크플로우 실행 및 실시간 렌더링
        for output in blog_workflow.stream(initial_state, {"recursion_limit": 50}):
            for node_name, state_update in output.items():
                st.write(f"✅ **[{node_name}]** 에이전트 작업 완료")
                # 🚨 NoneType 에러 해결: state_update가 존재할 때만 업데이트
                if state_update: 
                    full_state.update(state_update) 
                
        status.update(label="블로그 포스팅 생성 완료! 🎉", state="complete", expanded=False)

    # 5. 결과물 시각화
    if full_state:
        st.markdown("### 📋 최종 결과물 확인")
        
        # 메타데이터 및 과정 확인 영역
        with st.expander("🔍 작업 내역 상세 보기 (VectorDB, 아웃라인, 시각 분석, Critic 피드백)"):
            if not is_first_post and "accumulated_context" in full_state:
                st.info(f"**[VectorDB 이전 맥락]**\n\n{full_state['accumulated_context']}")
            if "outline" in full_state:
                st.markdown(f"**[기획자 아웃라인]**\n\n{full_state['outline']}")
            if "image_information" in full_state:
                st.success(f"**[시각 분석 내역]**\n\n{full_state['image_information']}")
            if "messages" in full_state and full_state["messages"]:
                st.warning(f"**[Critic 피드백]**\n\n{full_state['messages'][-1].content}")

        # 최종 글 렌더링
        final_text = full_state.get("final_content") or full_state.get("polished_content") or full_state.get("draft_content")
        
        if final_text:
            if full_state.get("final_content"):
                st.success("✨ 최종 발행 준비가 완료된 포스팅입니다.")
            else:
                st.warning("⚠️ 최종 승인은 나지 않았지만, 최신 수정본을 보여줍니다.")
            
            st.markdown("---")
            
            # [시각화 꿀팁] HTML 주석으로 숨겨진 마커를 화면에 예쁘게 보이도록 정규식 치환
            display_text = re.sub(
                r'<!-- \[이미지 삽입: (.*?)\] -->', 
                r'\n\n> 🖼️ **[여기에 \1 이미지가 배치됩니다]**\n\n', 
                final_text
            )
            st.markdown(display_text)