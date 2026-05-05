from src.state import BlogState
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

# 작성용: 창의성을 위해 T -> 0.7
writer_llm = ChatOpenAI(model = 'gpt-4.1-mini', temperature=0.7)
# 비평용: 엄격하고 일관성을 위해 T -> 0.1
critic_llm = ChatOpenAI(model='gpt-4.1-mini', temperature=0.1)

def intro_supervisor_agent(state: BlogState) -> dict:
    print("\n[Node: Intro Supervisor] 1편 작성 부서 내부 작업 지시 중...")

    if not state.get("learning_insights"): # 이게 블로그를 작성하는 핵심 소스라서 서브 그래프에서도 한번 더 판단
        print("  -> ⚠️ 경고: 인사이트 없이 작성 부서에 진입했습니다. 메인으로 복귀합니다.")
        return {"sub_next_step": "finish", "next_step": "supervisor"}
    
    # State에 값이 채워져 있는지 확인하여 다음 워커를 지정
    if not state.get("outline"):
        next_worker = "outline"
    elif not state.get("image_placement_guide"):
        next_worker = "image_analysis"
    elif not state.get("draft_content"):
        next_worker = "draft"
    elif not state.get("polished_content"):
        next_worker = "internal_editor"
    else:
        print("  -> 서브 그래프 작업 완료! 메인 Supervisor로 복귀합니다.")
        return{
            'sub_next_step':'finish',
            'next_step': 'critic'
        }
        
    return {"sub_next_step": next_worker}


def intro_outline_agent(state: BlogState) -> dict:
    print("[Node: Intro outline] 1편용 아웃라인 설계 중...")
    topic = state.get('current_topic')
    insights = state.get('learning_insights')
    
    # 첫 포스팅 전용 프롬프트: 새로운 주제 시작에 집중
    sys_msg = f"""당신은 1인칭 학습 블로그 전문 기획자입니다.
    [절대 규칙]
    1. 뻔한 백과사전식 개념 나열(개요-특징-장단점)을 절대 피하세요.
    2. 사용자가 제공한 '학습 인사이트(깨달음)'가 전체 글의 핵심 뼈대가 되어야 합니다.
    3. '내가 오늘 무엇을 배웠고, 어떤 부분에서 유레카를 외쳤는지'가 목차에 드러나도록 마크다운 아웃라인을 짜세요.
    """

    human_msg = f"주제: {topic}\n인사이트: {insights}"
    
    response = writer_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=human_msg)
    ])
    return {"outline": response.content}

def intro_draft_agent(state: BlogState) -> dict:
    print("[Node: Intro Draft] 1편 초안 작성 중...")
    outline = state.get('outline')
    tone = state.get('tone_and_manner')
    insights = state.get('learning_insights')
    
    # 1편 전용 프롬프트: 첫인상과 배경 설명에 집중
    sys_msg = f"""
    당신은 {tone} 톤으로 글을 쓰는 열정적인 IT 블로거입니다.
    
    [작성 지침]
    1. 당신은 기계나 전문가가 아니라, '오늘 이 주제를 치열하게 공부하고 깨달음을 얻은 학습자'입니다.
    2. 주어진 아웃라인을 따르되, 사용자의 '핵심 깨달음(Insight)'을 글 전체에 자연스럽게 녹여내세요.
    3. "제가 오늘 공부하면서 가장 놀랐던 점은~", "처음엔 헷갈렸는데 이렇게 이해했다" 같은 1인칭 표현을 적극 사용하세요.
    """
    human_msg = f"핵심 깨달음(Insight):\n{insights}\n\n아웃라인:\n{outline}"
    
    response = writer_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=human_msg)
    ])
    return {"draft_content": response.content, "review_verdict": None}

def internal_editor_agent(state: BlogState) -> dict:
    print("[Node: Internal Editor] 작성된 초안을 매끄럽게 디벨롭합니다...")
    draft = state.get("draft_content")
    tone = state.get("tone_and_manner")
    
    sys_msg = f"""
    당신은 전문 에디터입니다. 
    주어진 초안의 내용을 절대 바꾸지 말고, '{tone}' 톤이 잘 유지되도록 문맥과 흐름만 매끄럽게 다듬으세요(Polishing).
    """
    human_msg = f"디벨롭할 초안:\n{draft}"
    
    response = writer_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=human_msg)
    ])
    
    return {"polished_content": response.content, 'review_verdict': None}