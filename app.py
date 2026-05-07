import streamlit as st
import tempfile
import os
import re
import uuid
from src.graph import app as blog_workflow
from src.memory import get_all_topics, delete_topic, get_topic_tone, update_topic_tone, save_user_guideline
from src.utils import analyze_custom_tone

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="Insight-Driven Blog Agent",
    page_icon="✍️",
    layout="wide"
)

st.title("✍️ Insight-Driven 블로그 에이전트")
st.markdown("나만의 학습 인사이트와 캡처 이미지를 바탕으로 블로그 포스팅을 자동 생성합니다.")

# 2. 사이드바 설정 (Room 및 환경 설정)
with st.sidebar:
    st.header("📁 워크스페이스 (Topic Room)")
    
    existing_topics = get_all_topics()
    room_options = ["새로운 토픽(방) 만들기..."] + existing_topics
    
    if 'new_topic_to_select' in st.session_state:
        if st.session_state['new_topic_to_select'] not in room_options:
            room_options.append(st.session_state['new_topic_to_select'])
    
    def on_room_change():
        if 'thread_id' in st.session_state:
            del st.session_state['thread_id']
        if 'new_topic_to_select' in st.session_state:
            del st.session_state['new_topic_to_select']
    
    default_idx = 0
    if 'new_topic_to_select' in st.session_state and st.session_state['new_topic_to_select'] in room_options:
        default_idx = room_options.index(st.session_state['new_topic_to_select'])
    
    selected_room = st.selectbox(
        "현재 입장한 토픽 방", 
        options=room_options,
        index=default_idx,
        key="room_selector",
        on_change=on_room_change
    )
    
    if selected_room == "새로운 토픽(방) 만들기...":
        current_topic = st.text_input("새로운 토픽 이름을 입력하세요", placeholder="예: LangGraph 멀티 에이전트")
        is_first_post = True
    else:
        current_topic = selected_room
        is_first_post = False
        st.success(f"📚 '{current_topic}' 연재 방에 입장했습니다.")
        
        if st.button(f"🗑️ '{current_topic}' 방 삭제하기", use_container_width=True):
            if delete_topic(current_topic):
                st.toast(f"'{current_topic}' 방 삭제 완료!", icon="✅")
                st.rerun() 
        
    st.session_state['current_topic'] = current_topic
    st.session_state['is_first_post'] = is_first_post
        
    st.markdown("---")
    st.header("⚙️ 에이전트 환경 설정")
    
    saved_tone = ""
    if not is_first_post and current_topic:
        saved_tone = get_topic_tone(current_topic)
        
    if saved_tone:
        st.info("🔒 이 연재 방에 고정된 톤앤매너가 자동 적용됩니다.")
        st.markdown(f"> {saved_tone}")
        tone_and_manner = saved_tone
    else:
        tone_setting_method = st.radio("문체 설정 방식", ["프리셋 선택", "내 글투 분석 (사용자 정의)"])
        if tone_setting_method == "프리셋 선택":
            tone_and_manner = st.selectbox("문체 프리셋", ["친절하고 열정적인 1인칭", "전문적이고 객관적인", "유머러스하고 재치있는", "담담한 회고록 스타일"])
        else:
            sample_text = st.text_area("평소 쓰는 글을 복사해 넣어주세요.", height=150)
            if st.button("🔍 내 글투 분석하기", use_container_width=True):
                if sample_text.strip():
                    with st.spinner("글투 분석 중..."):
                        analyzed_tone = analyze_custom_tone(sample_text)
                        st.session_state['custom_tone'] = analyzed_tone
                    st.success("분석 완료!")
            tone_and_manner = st.session_state.get('custom_tone', "분석된 글투가 여기에 적용됩니다.")
            
    max_revisions = st.slider("Critic 최대 반려 횟수", min_value=1, max_value=3, value=2)
    st.markdown("---")

# 3. 메인 입력 화면
col1, col2 = st.columns([1, 1])
with col1:
    display_topic = st.session_state.get('current_topic')
    display_name = display_topic if display_topic else '새로운 토픽'
    st.subheader(f"💡 [{display_name}] 인사이트 입력")
    insight_input_type = st.radio("입력 방식", ["텍스트 직접 입력", "파일 업로드 (.md, .txt)"], horizontal=True)
    
    learning_insights = ""
    if insight_input_type == "텍스트 직접 입력":
        learning_insights = st.text_area("오늘의 핵심 깨달음 (Insight)", height=150)
    else:
        uploaded_file = st.file_uploader("인사이트 파일 업로드", type=['txt', 'md'])
        if uploaded_file:
            learning_insights = uploaded_file.getvalue().decode("utf-8")

with col2:
    st.subheader("🖼️ 첨부 이미지 (선택 사항)")
    uploaded_images = st.file_uploader("캡처 이미지나 다이어그램을 올려주세요.", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

# 4. 실행 버튼 및 워크플로우 구동
if st.button("🚀 블로그 포스팅 생성 시작!", use_container_width=True, type="primary"):
    topic_to_run = st.session_state.get('current_topic')
    if not topic_to_run or not learning_insights:
        st.error("토픽 이름과 인사이트를 모두 입력해주세요!")
        st.stop()
        
    temp_image_paths = []
    if uploaded_images:
        temp_dir = tempfile.mkdtemp()
        for img in uploaded_images:
            temp_path = os.path.join(temp_dir, img.name)
            with open(temp_path, "wb") as f:
                f.write(img.getbuffer())
            temp_image_paths.append(temp_path)

    # 새로운 실행을 위한 thread_id 생성
    st.session_state['thread_id'] = str(uuid.uuid4())
    config = {"configurable": {"thread_id": st.session_state['thread_id']}}

    initial_state = {
        "is_first_post": st.session_state.get('is_first_post', True),
        "current_topic": topic_to_run,
        "tone_and_manner": tone_and_manner,
        "learning_insights": learning_insights,
        "captured_images": temp_image_paths,
        "revision_count": 0,
        "max_revisions": max_revisions
    }

    st.markdown("---")
    st.subheader("🤖 에이전트 작업 현황")
    
    with st.status("워크플로우 실행 중...", expanded=True) as status:
        # Checkpointer를 사용하므로 config 전달
        for output in blog_workflow.stream(initial_state, config=config, stream_mode="updates"):
            for node_name, state_update in output.items():
                st.write(f"✅ **[{node_name}]** 에이전트 작업 완료")
        status.update(label="에이전트 작업 완료 (검토 대기 중) 🎉", state="complete", expanded=False)

# 5. 결과물 시각화 및 HITL(사람 개입) 제어
if 'thread_id' in st.session_state:
    config = {"configurable": {"thread_id": st.session_state['thread_id']}}
    
    # Checkpointer에서 현재 상태 가져오기
    current_snapshot = blog_workflow.get_state(config)
    full_state = current_snapshot.values
    
    # interrupt_before=["human_review"]에 의해 멈춰있는지 확인
    is_paused = len(current_snapshot.next) > 0 and current_snapshot.next[0] == "human_review"
    
    if is_paused:
        st.markdown("---")
        st.warning("✋ 에디터의 초안 작성이 끝났습니다. 최종본을 확인하고 직접 수정하거나 피드백을 남겨주세요.")
        
        # 1. 사람이 직접 글을 수정할 수 있는 에디터
        draft_text = full_state.get("polished_content", "")
        edited_text = st.text_area("✍️ 최종본 직접 수정 (Manual Override)", value=draft_text, height=450)
        
        # 2. 피드백 입력란
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            feedback_tone = st.text_input("🗣️ 말투 피드백 (다음 포스팅에 반영)", placeholder="예: 좀 더 진지한 말투로...")
        with f_col2:
            feedback_struct = st.text_input("🏗️ 구조 피드백 (다음 포스팅에 반영)", placeholder="예: 서론을 짧게...")
        
        if st.button("✅ 최종 승인 및 저장", type="primary", use_container_width=True):
            # 피드백 DB 반영
            if feedback_tone: update_topic_tone(full_state['current_topic'], feedback_tone)
            if feedback_struct: save_user_guideline(full_state['current_topic'], feedback_struct)
            
            # Checkpointer 상태 강제 업데이트 (사람의 수정본 주입)
            blog_workflow.update_state(
                config,
                {"human_review_complete": True, "final_content": edited_text}
            )
            
            with st.spinner("최종 저장 중..."):
                # None을 전달하여 멈춘 지점부터 다시 실행
                for _ in blog_workflow.stream(None, config=config):
                    pass 
            
            st.success("🎉 최종 발행 및 장기 기억 저장이 완료되었습니다!")
            st.rerun()
            
    else: 
        # 최종 완료 상태 출력
        st.markdown("### 📋 최종 결과물 확인")
        with st.expander("🔍 작업 내역 상세 보기"):
            if "outline" in full_state: st.markdown(f"**[기획자 아웃라인]**\n\n{full_state['outline']}")
            if "image_information" in full_state: st.success(f"**[시각 분석 내역]**\n\n{full_state['image_information']}")

        final_text = full_state.get("final_content") or full_state.get("polished_content")
        
        if final_text:
            st.success("✨ 사람의 최종 승인이 완료된 포스팅입니다.")
            preview_tab, code_tab = st.tabs(["✨ 블로그 미리보기", "📄 마크다운 소스코드"])
            with preview_tab:
                display_text = re.sub(r'', r'\n\n> 🖼️ **[여기에 \1 이미지가 배치됩니다]**\n\n', final_text)
                st.markdown(display_text)
            with code_tab:
                st.info("아래 코드를 복사해서 블로그 에디터에 붙여넣으세요!")
                st.code(final_text, language="markdown")