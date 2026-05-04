from src.state import BlogState
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

# 작성용: 창의성을 위해 T -> 0.7
writer_llm = ChatOpenAI(model = 'gpt-5.5', temperature=0.7)
# 비평용: 엄격하고 일관성을 위해 T -> 0.1
critic_llm = ChatOpenAI(model='gpt-5.5', temperature=0.1)

def continuation_supervisor_agent(state: BlogState) -> dict:
    print("\n[Node: Continuation Supervisor] 연재글 작성 부서 내부 작업 지시 중...")
    
    if not state.get("content_structure"):
        next_worker = "content_structure"
    elif not state.get("image_placement_guide"):
        next_worker = "image_analysis"
    elif not state.get("draft_content"):
        next_worker = "humanized_draft"
    elif not state.get("polished_content"):
        next_worker = "internal_editor"
    else:
        print("  -> 연재글 서브 그래프 작업 완료! 메인 Supervisor로 복귀합니다.")
        return{
            'sub_next_step':'finish',
            'next_step': 'critic'
        }
        
    return {"sub_next_step": next_worker}

def continuation_content_structure_agent(state: BlogState) -> dict:
    print("[Node: Continuation Structure] 연재글용 아웃라인 설계 중...")
    topic = state.get('current_topic')
    insights = state.get('learning_insights')
    accumulated_context = state.get('accumulated_context') # 핵심: 이전 맥락 주입!
    
    # 연재글 전용 프롬프트: 이전 맥락과의 연결성에 집중
    system_prompt = "당신은 IT 블로그 기획자입니다. '이전 포스팅의 맥락'을 반드시 이어받아, 이번 주제의 아웃라인을 작성하세요."
    
    response = writer_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"이전 맥락: {accumulated_context}\n이번 주제: {topic}\n인사이트: {insights}")
    ])
    return {"content_structure": response.content}

def continuation_humanized_draft_agent(state: BlogState) -> dict:
    print("[Node: Continuation Draft] 연재글 초안 작성 중...")
    structure = state.get('content_structure')
    tone = state.get('tone_and_manner')
    accumulated_context = state.get('accumulated_context')
    
    # 연재글 전용 프롬프트: 이전 문체 유지 및 서사 연결
    system_prompt = f"당신은 {tone} 톤으로 글을 쓰는 블로거입니다. 이전 글의 내용({accumulated_context})과 자연스럽게 이어지도록 '연재 포스팅' 초안을 작성하세요."
    
    response = writer_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"아웃라인:\n{structure}")
    ])
    return {"draft_content": response.content, "review_verdict": None}

def continuation_internal_editor_agent(state: BlogState) -> dict:
    print("[Node: Continuation Internal Editor] 연재글 초안을 매끄럽게 디벨롭합니다...")
    draft = state.get("draft_content")
    tone = state.get("tone_and_manner")
    context = state.get("accumulated_context")
    
    # 1편 에디터와 다르게 '이전 맥락'과의 연결성을 강조합니다.
    system_prompt = f"""당신은 전문 에디터입니다. 
    주어진 초안의 내용을 절대 바꾸지 말고, '{tone}' 톤이 잘 유지되도록 다듬으세요.
    특히 이전 글의 맥락({context})과 자연스럽게 이어지도록 문맥과 흐름을 중점적으로 교정하세요(Polishing)."""
    
    response = writer_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"디벨롭할 초안:\n{draft}")
    ])
    
    return {"polished_content": response.content, 'review_verdict': None}
