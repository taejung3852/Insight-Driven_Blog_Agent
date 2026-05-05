import streamlit as st
import tempfile
import os
import re
from src.graph import app as blog_workflow
from src.memory import get_all_topics, delete_topic, get_topic_tone
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
    
    # DB에서 기존 토픽 목록 불러오기
    existing_topics = get_all_topics()
    room_options = ["새로운 토픽(방) 만들기..."] + existing_topics
    
    # 새로 만들어질 방을 목록에 강제 추가하여 즉시 반영되도록 처리
    if 'new_topic_to_select' in st.session_state:
        if st.session_state['new_topic_to_select'] not in room_options:
            room_options.append(st.session_state['new_topic_to_select'])
    
    # 방이 바뀌면 기존에 띄워둔 결과물 세션을 초기화하는 콜백
    def on_room_change():
        if 'full_state' in st.session_state:
            del st.session_state['full_state']
        if 'new_topic_to_select' in st.session_state:
            del st.session_state['new_topic_to_select']
    
    # [에러 방지] 인덱스를 동적으로 계산하여 셀렉트박스 값 강제 제어
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
        if current_topic:
            st.info("✨ 새로운 시리즈의 1편으로 시작됩니다.")
    else:
        current_topic = selected_room
        is_first_post = False
        st.success(f"📚 '{current_topic}' 연재 방에 입장했습니다.")
        
        # 기존 방 삭제 기능
        if st.button(f"🗑️ '{current_topic}' 방 삭제하기", use_container_width=True):
            success = delete_topic(current_topic)
            if success:
                st.toast(f"'{current_topic}' 방이 성공적으로 삭제되었습니다!", icon="✅")
                st.session_state['current_topic'] = ""
                st.session_state['is_first_post'] = True
                if 'full_state' in st.session_state:
                    del st.session_state['full_state']
                if 'new_topic_to_select' in st.session_state:
                    del st.session_state['new_topic_to_select']
                st.rerun() 
            else:
                st.error("삭제 중 오류가 발생했습니다.")
        
    st.session_state['current_topic'] = current_topic
    st.session_state['is_first_post'] = is_first_post
        
    st.markdown("---")
    st.header("⚙️ 에이전트 환경 설정")
    
    # 방별 톤앤매너 고정 로직
    saved_tone = ""
    if not is_first_post and current_topic:
        saved_tone = get_topic_tone(current_topic)
        
    if saved_tone:
        st.info("🔒 이 연재 방에 고정된 톤앤매너가 자동 적용됩니다.")
        st.markdown(f"> {saved_tone}")
        tone_and_manner = saved_tone
    else:
        tone_setting_method = st.radio("문체(Tone & Manner) 설정 방식", ["프리셋 선택", "내 글투 분석 (사용자 정의)"])
        
        if tone_setting_method == "프리셋 선택":
            tone_and_manner = st.selectbox(
                "문체 프리셋",
                ["친절하고 열정적인 1인칭", "전문적이고 객관적인", "유머러스하고 재치있는", "담담한 회고록 스타일"]
            )
        else:
            sample_text = st.text_area("평소 쓰는 블로그 글이나 원하는 스타일의 글을 복사해 넣어주세요.", height=150)
            
            if st.button("🔍 내 글투 분석하기", use_container_width=True):
                if sample_text.strip():
                    with st.spinner("글투를 분석 중입니다 (빠르고 저렴한 모델 사용)..."):
                        analyzed_tone = analyze_custom_tone(sample_text)
                        st.session_state['custom_tone'] = analyzed_tone
                    st.success("글투 분석 완료!")
                else:
                    st.warning("예시 글을 먼저 입력해주세요.")
                    
            tone_and_manner = st.session_state.get('custom_tone', "분석된 글투가 여기에 적용됩니다.")
            
            if 'custom_tone' in st.session_state:
                st.info(f"**[적용될 톤앤매너 지시서]**\n{tone_and_manner}")
            
    max_revisions = st.slider("Critic 최대 반려 횟수", min_value=1, max_value=3, value=2)
    st.markdown("---")

# 3. 메인 입력 화면
col1, col2 = st.columns([1, 1])

with col1:
    display_topic = st.session_state.get('current_topic')
    display_name = display_topic if display_topic else '새로운 토픽'
    
    st.subheader(f"💡 [{display_name}] 인사이트 입력")
    
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
    uploaded_images = st.file_uploader(
        "글에 포함할 캡처 이미지나 다이어그램을 올려주세요.", 
        type=['png', 'jpg', 'jpeg'], 
        accept_multiple_files=True
    )

# 4. 실행 버튼 및 워크플로우 구동
if st.button("🚀 블로그 포스팅 생성 시작!", use_container_width=True, type="primary"):
    topic_to_run = st.session_state.get('current_topic')
    
    if not topic_to_run or not learning_insights:
        st.error("토픽(방) 이름과 인사이트를 모두 입력해주세요!")
        st.stop()
        
    temp_image_paths = []
    if uploaded_images:
        temp_dir = tempfile.mkdtemp()
        for img in uploaded_images:
            temp_path = os.path.join(temp_dir, img.name)
            with open(temp_path, "wb") as f:
                f.write(img.getbuffer())
            temp_image_paths.append(temp_path)

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
        full_state = initial_state.copy() 
        
        for output in blog_workflow.stream(initial_state, {"recursion_limit": 50}):
            for node_name, state_update in output.items():
                st.write(f"✅ **[{node_name}]** 에이전트 작업 완료")
                if state_update: 
                    full_state.update(state_update) 
                
        status.update(label="블로그 포스팅 생성 완료! 🎉", state="complete", expanded=False)
    
    st.session_state['full_state'] = full_state
    
    # 새 방 생성 시 자동 전환 처리
    if st.session_state.get('is_first_post'):
        st.session_state['new_topic_to_select'] = topic_to_run
        st.rerun()

# 5. 결과물 시각화
if 'full_state' in st.session_state:
    full_state = st.session_state['full_state']
    st.markdown("### 📋 최종 결과물 확인")
    
    with st.expander("🔍 작업 내역 상세 보기 (VectorDB, 아웃라인, 시각 분석, Critic 피드백)"):
        if not full_state.get('is_first_post') and "accumulated_context" in full_state:
            st.info(f"**[VectorDB 이전 맥락]**\n\n{full_state['accumulated_context']}")
        if "outline" in full_state:
            st.markdown(f"**[기획자 아웃라인]**\n\n{full_state['outline']}")
        if "image_information" in full_state:
            st.success(f"**[시각 분석 내역]**\n\n{full_state['image_information']}")
        if "messages" in full_state and full_state["messages"]:
            st.warning(f"**[Critic 피드백]**\n\n{full_state['messages'][-1].content}")

    # 최종 텍스트 결정 (우선순위: final -> polished -> draft)
    final_text = full_state.get("final_content") or full_state.get("polished_content") or full_state.get("draft_content")
    
    if final_text:
        if full_state.get("final_content"):
            st.success("✨ 최종 발행 준비가 완료된 포스팅입니다.")
        else:
            st.warning("⚠️ 최종 승인은 나지 않았지만, 최신 수정본을 보여줍니다.")
        
        st.markdown("---")
        
        # 🚨 [신규 기능] 미리보기와 코드박스 탭 분리
        preview_tab, code_tab = st.tabs(["✨ 블로그 미리보기", "📄 마크다운 소스코드"])

        with preview_tab:
            # 미리보기용 이미지 마커 시각화
            display_text = re.sub(
                r'<!-- \[이미지 삽입: (.*?)\] -->', 
                r'\n\n> 🖼️ **[여기에 \1 이미지가 배치됩니다]**\n\n', 
                final_text
            )
            st.markdown(display_text)

        with code_tab:
            st.info("아래 코드를 복사해서 블로그 에디터(Velog, Tistory 등)에 붙여넣으세요!")
            # 복사하기 버튼이 포함된 마크다운 코드박스
            st.code(final_text, language="markdown")