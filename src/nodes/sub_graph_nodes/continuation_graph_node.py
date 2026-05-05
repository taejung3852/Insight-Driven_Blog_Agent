from src.state import BlogState
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

# 작성용: 창의성을 위해 T -> 0.7
writer_llm = ChatOpenAI(model = 'gpt-4.1-mini', temperature=0.7)
# 비평용: 엄격하고 일관성을 위해 T -> 0.1
critic_llm = ChatOpenAI(model='gpt-4.1-mini', temperature=0.1)

def continuation_supervisor_agent(state: BlogState) -> dict:
    print("\n[Node: Continuation Supervisor] 연재글 작성 부서 내부 작업 지시 중...")

    if not state.get("learning_insights"): # 이게 블로그를 작성하는 핵심 소스라서 서브 그래프에서도 한번 더 판단
        print("  -> ⚠️ 경고: 인사이트 없이 작성 부서에 진입했습니다. 메인으로 복귀합니다.")
        return {"sub_next_step": "finish", "next_step": "supervisor"}
    
    if not state.get("outline"):
        next_worker = "outline"
    elif not state.get("draft_content"):
        next_worker = "draft"
    elif not state.get("polished_content"):
        next_worker = "internal_editor"
    elif state.get('captured_images') and not state.get('image_information'):
        next_worker = 'image_analysis'
    else:
        print("  -> 연재글 서브 그래프 작업 완료! 메인 Supervisor로 복귀합니다.")
        return{
            'sub_next_step':'finish',
            'next_step': 'critic'
        }
        
    return {"sub_next_step": next_worker}

def continuation_outline_agent(state: BlogState) -> dict:
    print("[Node: Continuation outline] 연재글용 아웃라인 설계 중...")
    topic = state.get('current_topic')
    insights = state.get('learning_insights')
    accumulated_context = state.get('accumulated_context') # 핵심: 이전 맥락 주입!
    
    # 연재글 전용 프롬프트: 이전 맥락과의 연결성에 집중
    sys_msg = f"""당신은 1인칭 학습 블로그 전문 기획자입니다.
    [절대 규칙]
    1. 뻔한 백과사전식 개념 나열(개요-특징-장단점)을 절대 피하세요.
    2. 사용자가 제공한 '학습 인사이트(깨달음)'가 전체 글의 핵심 뼈대가 되어야 합니다.
    3. '내가 오늘 무엇을 배웠고, 어떤 부분에서 유레카를 외쳤는지'가 목차에 드러나도록 마크다운 아웃라인을 짜세요.
    """
    human_msg = f"이전 맥락: {accumulated_context}\n이번 주제: {topic}\n인사이트: {insights}"
    
    response = writer_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=human_msg)
    ])
    return {"outline": response.content}

def continuation_draft_agent(state: BlogState) -> dict:
    print("[Node: Continuation Draft] 연재글 초안 작성 중...")
    outline = state.get('outline')
    tone = state.get('tone_and_manner')
    accumulated_context = state.get('accumulated_context')
    insights = state.get('learning_insights')
    
    # 연재글 전용 프롬프트: 이전 문체 유지 및 서사 연결
    sys_msg = f"""
    당신은 {tone} 톤으로 글을 쓰는 IT 블로거이며, 현재 하나의 주제를 연재 중입니다.

    [역할 정의]
    - 당신은 전문가가 아니라, 오늘 직접 공부하며 깨달음을 얻은 학습자입니다.
    - 이전 글들과 하나의 흐름으로 이어지는 '연재 글'을 작성해야 합니다.

    [작성 지침]
    1. 반드시 이전 글의 흐름을 이어받아 자연스럽게 시작하세요. (맥락 단절 금지)
    2. 이전 글에서 이미 설명한 내용은 반복하지 말고, 이어서 확장하세요.
    3. 사용자의 핵심 깨달음(Insight)을 글 전체에 자연스럽게 녹여내세요.
    4. "내가 오늘 공부하면서 느낀 점은", "처음엔 헷갈렸는데 이렇게 이해했다" 같은 1인칭 학습자 시점을 유지하세요.
    5. 단순 요약이 아니라, 이전 글 위에 새로운 이해를 쌓는 방식으로 작성하세요.
    """
    human_msg = f"""
    [이전 연재 글 맥락]
    {accumulated_context}

    [핵심 깨달음 (Insight)]
    {insights}

    [이번 글 아웃라인]
    {outline}

    [작성 요청]
    - 위 '이전 연재 글 맥락'을 기반으로 자연스럽게 이어지는 다음 글을 작성하세요.
    - 글 초반에 이전 내용과 자연스럽게 연결되는 흐름을 반드시 포함하세요.
    """
    
    response = writer_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=human_msg)
    ])
    return {"draft_content": response.content, "review_verdict": None}

def continuation_internal_editor_agent(state: BlogState) -> dict:
    print("[Node: Continuation Internal Editor] 연재글 초안을 매끄럽게 디벨롭합니다...")
    draft = state.get("draft_content")
    tone = state.get("tone_and_manner")
    context = state.get("accumulated_context")
    
    # 1편 에디터와 다르게 '이전 맥락'과의 연결성을 강조합니다.
    sys_msg = f"""
    당신은 전문 에디터입니다. 
    주어진 초안의 내용을 절대 바꾸지 말고, '{tone}' 톤이 잘 유지되도록 다듬으세요.
    특히 이전 글의 맥락({context})과 자연스럽게 이어지도록 문맥과 흐름을 중점적으로 교정하세요(Polishing).
    """
    human_msg = f"디벨롭할 초안:\n{draft}"
    
    response = writer_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=human_msg)
    ])
    
    return {"polished_content": response.content, 'review_verdict': None}
