from src.state import BlogState
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

# 작성용: 창의성을 위해 T -> 0.7
writer_llm = ChatOpenAI(model = 'gpt-4.1-mini', temperature=0.7)
# 비평용: 엄격하고 일관성을 위해 T -> 0.1
critic_llm = ChatOpenAI(model='gpt-4.1-mini', temperature=0.1)

def intro_supervisor_agent(state: BlogState) -> dict:
    print("\n[Node: Intro Supervisor] 1편 작성 부서 내부 작업 지시 중...")
    
    # State에 값이 채워져 있는지 확인하여 다음 워커를 지정
    if not state.get("content_structure"):
        next_worker = "content_structure"
    elif not state.get("image_placement_guide"):
        next_worker = "image_analysis"
    elif not state.get("draft_content"):
        next_worker = "humanized_draft"
    elif not state.get("polished_content"):
        next_worker = "internal_editor"
    else:
        print("  -> 서브 그래프 작업 완료! 메인 Supervisor로 복귀합니다.")
        return{
            'sub_next_step':'finish',
            'next_step': 'critic'
        }
        
    return {"sub_next_step": next_worker}


def intro_content_structure_agent(state: BlogState) -> dict:
    print("[Node: Intro Structure] 1편용 아웃라인 설계 중...")
    topic = state.get('current_topic')
    insights = state.get('learning_insights')
    
    # 첫 포스팅 전용 프롬프트: 새로운 주제 시작에 집중
    system_prompt = "당신은 IT 블로그 기획자입니다. 주어진 인사이트를 바탕으로 '새로운 시리즈를 시작하는 1편'의 아웃라인을 마크다운으로 작성하세요."
    
    response = writer_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"주제: {topic}\n인사이트: {insights}")
    ])
    return {"content_structure": response.content}

def intro_humanized_draft_agent(state: BlogState) -> dict:
    print("[Node: Intro Draft] 1편 초안 작성 중...")
    structure = state.get('content_structure')
    tone = state.get('tone_and_manner')
    
    # 1편 전용 프롬프트: 첫인상과 배경 설명에 집중
    system_prompt = f"당신은 {tone} 톤으로 글을 쓰는 블로거입니다. 구조를 바탕으로 '이 주제를 처음 다루는' 사람 냄새 나는 첫 포스팅을 작성하세요."
    
    response = writer_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"아웃라인:\n{structure}")
    ])
    return {"draft_content": response.content, "review_verdict": None}

def internal_editor_agent(state: BlogState) -> dict:
    print("[Node: Internal Editor] 작성된 초안을 매끄럽게 디벨롭합니다...")
    draft = state.get("draft_content")
    tone = state.get("tone_and_manner")
    
    system_prompt = f"""당신은 전문 에디터입니다. 
    주어진 초안의 내용을 절대 바꾸지 말고, '{tone}' 톤이 잘 유지되도록 문맥과 흐름만 매끄럽게 다듬으세요(Polishing)."""
    
    response = writer_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"디벨롭할 초안:\n{draft}")
    ])
    
    return {"polished_content": response.content, 'review_verdict': None}