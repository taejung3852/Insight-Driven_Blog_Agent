from src.state import BlogState
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

# 작성용: 창의성을 위해 T -> 0.7
writer_llm = ChatOpenAI(model = 'gpt-5.4', temperature=0.7)
# 비평용: 엄격하고 일관성을 위해 T -> 0.1
critic_llm = ChatOpenAI(model='gpt-5.4-mini', temperature=0.1)

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
    sys_msg = f"""
    **Role:**
    당신은 1인칭 학습 블로그 전문 기획자(Planner)입니다.

    **Objective:**
    사용자의 '학습 인사이트'를 바탕으로 전체 글의 뼈대(개요)를 마크다운 목차로 설계하세요.

    **Rules:**
    - 항상 전체적인 이야기의 기승전결(숲)을 먼저 고려하세요.
    - 절대 뻔한 백과사전식 나열(개요-특징-장단점)을 목차로 짜지 마세요.
    - '내가 무엇을 고민했고, 어떻게 해결했는지'가 목차 제목에서 드러나게 하세요.
    - 본문 내용은 적지 말고 오직 목차(Heading)만 작성하세요.

    **Format:**
    # (메인 제목)
    ## 1. (소제목)
    - (이 단락에서 다룰 핵심 내용 1줄)
    ## 2. (소제목)
    - (이 단락에서 다룰 핵심 내용 1줄)
    """
    
    human_msg = f"""
    **Context:**
    - 주제: {topic}
    - 핵심 인사이트: {insights}
    - 이전 맥락(연재글인 경우): {accumulated_context}
    """
    
    response = writer_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=human_msg)
    ])
    return {"outline": response.content}

def continuation_draft_agent(state: BlogState) -> dict:
    print("[Node: Continuation Draft] 연재글 초안 작성 중...")
    outline = state.get('outline')
    topic = state.get('current_topic')
    tone = state.get('tone_and_manner')
    accumulated_context = state.get('accumulated_context')
    insights = state.get('learning_insights')
    revision_count = state.get("revision_count", 0)
    messages = state.get("messages", []) # 크리틱의 피드백이 담긴 곳
    
    critic_feedback = state.get('critic_feedback')
    # 수정 횟수가 1 이상이고, 메시지가 존재한다면 (즉, 반려당해서 다시 온 거라면)
    if revision_count > 0 and messages:
        # 가장 마지막에 담긴 Critic의 피드백을 꺼내옵니다.
        critic_feedback = messages[-1].content
        
    # 연재글 전용 프롬프트: 이전 문체 유지 및 서사 연결
    sys_msg = f"""
    **Role:**
    당신은 톤앤매너에 맞춰 글을 쓰는 열정적인 IT 블로그 본문 전문 작가입니다.

    **Objective:**
    주어진 아웃라인과 인사이트를 바탕으로, 기계적인 냄새가 나지 않는 '사람의 본문 초안'을 작성하세요.

    **Rules:**
    - '이전 연재글 요약'을 참고하여, 앞에서 이미 자세히 설명한 기본 개념을 또다시 길게 설명하지 마세요.
    - 이전 편의 흐름을 이어받아 서사가 자연스럽게 연결되도록 서론을 부드럽게 시작하세요. (예: "전에 ~에 대해 공부했다. 이번에는...")
    - 항상 1인칭 시점에서 본인이 직접 경험한 것처럼 서술하세요.
    - 절대 아웃라인의 구조를 마음대로 바꾸거나 누락하지 마세요.
    - 아웃라인의 bullet point 내용에 살을 붙여서 구체적이고 매끄러운 문장으로 확장하세요.
    - 기술적 설명은 독자가 이해하기 쉽게 풀어서 설명하세요.

    **Format:**
    - 마크다운 문법을 사용한 완성된 블로그 본문 전체
    """
    
    if critic_feedback:
        sys_msg += f"""
        \n\n=========================================
        [🚨 편집장의 이전 반려 사유 및 피드백 반영 지시]
        이전 작성본이 아래와 같은 사유로 반려되었습니다. 
        이번 작성 시에는 아래 피드백을 **적절히 반영**해 주세요.
        
        {critic_feedback}
        =========================================
        """
        
    human_msg = f"""
    **Context:**
    - 적용할 톤앤매너: {tone}
    - 주제: {topic}
    - 아웃라인: {outline}
    - 핵심 인사이트: {insights}
    - 이전 연재글 요약(맥락): {accumulated_context}
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
    **Role:**
    당신은 10년 차 IT 테크 블로그 수석 윤문 에디터(Editor)입니다.

    **Objective:**
    작성된 초안을 검토하고, 톤앤매너에 맞춰 문맥과 흐름을 매끄럽게 수정하세요(Polishing).

    **Rules:**
    - 항상 기존 초안의 '기술적 팩트'와 '핵심 인사이트'는 100% 보존하세요.
    - 절대 글의 구조(목차)를 변경하거나 새로운 내용을 창작해서 추가하지 마세요.
    - 문장이 너무 길거나 어색한 번역투 문장을 자연스러운 한국어 구어체로 교정하세요.
    - 단락 간의 연결 고리(접속사 등)를 자연스럽게 수정하세요.

    **Format:**
    - 윤문이 완료된 마크다운 텍스트 원문 (수정 코멘트는 절대 포함하지 말 것)
    """
    
    human_msg = f"""
    **Context:**
    - 적용할 톤앤매너: {tone}
    - 원본 초안: {draft}
    """
    
    response = writer_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=human_msg)
    ])
    
    return {"polished_content": response.content, 'review_verdict': None}
