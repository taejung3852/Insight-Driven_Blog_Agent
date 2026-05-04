import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.graph import BlogState

load_dotenv()

# 작성용: 창의성을 위해 T -> 0.7
writer_llm = ChatOpenAI(model = 'gpt-5.5', temperature=0.7)
# 비평용: 엄격하고 일관성을 위해 T -> 0.1
critic_llm = ChatOpenAI(model='gpt-5.5', temperature=0.1)

def supervisor_agent(state: BlogState) -> dict:
    print("\n[Node: supervisor] 라우팅 판단 중...")
    is_first = state.get('is_first_post', True)
    accumulated = state.get("accumulated_context")
    draft = state.get("draft_content")
    verdict = state.get("review_verdict")
    rev_count = state.get("revision_count", 0)
    max_rev = state.get("max_revisions", 2)
    
    if not is_first and not accumulated:
        next_step = "context_injection"
        
    elif not draft:
        next_step = "intro_graph" if is_first else "continuation_graph"
        
    elif not verdict:
        next_step = "critic"
        
    else:
        if "OK" in verdict:
            next_step = "final"
        elif "REVISE" in verdict and rev_count < max_rev:
            next_step = "intro_graph" if is_first else "continuation_graph"
        else:
            next_step = "final"

    print(f"  -> 다음 단계: {next_step}")
    return {"next_step": next_step}

def context_injection_agent(state: BlogState) -> dict:
    print("[Node: Context Injection] VectorDB에서 이전 글의 메타데이터를 가져옵니다.")
    # RAG/VectorDB 연동은 Phase4에서 진행하므로 우선 현상태 유지
    return {'accumulated_context': '이전 포스트들의 3요소(용어, 결론, 문체) 데이터'}

def intro_graph_agent(state: BlogState) -> dict:
    print("[Node: Intro Graph] 1편 작성을 시작합니다.")
    topic = state.get('current_topic')
    tone = state.get('tone_and_manner')

    sys_msg = f"""
    **Role:**
    당신은 10년차 IT 전문 블로그 편집장입니다.

    **Objective:**
    작성된 블로그 포스트 초안이 주어진 톤앤매너를 유지해서 작성해주세요, 논리적 비약이나 기술적 오류 없게 잘 작성해주세요.

    **Context:**
    - 요구되는 톤앤매너: {tone}
    """
    human_msg = f"주제: {topic}"

    response = writer_llm.invoke([SystemMessage(content=sys_msg), HumanMessage(content=human_msg)])

    return {
        'draft_content': response.content,
        'review_verdict': None,
        'messages': [response]
    }

def continuation_graph_agent(state: BlogState) -> dict:
    print("[Node: Continuation Graph] LLM이 이전 맥락을 바탕으로 연재글을 작성합니다...")
    topic = state.get('current_topic')
    tone = state.get('tone_and_manner')
    context = state.get('accumulated_context')
    
    system_prompt = f"""당신은 전문 블로그 작성자입니다. {tone} 톤으로 연재 포스팅을 작성하세요.
    반드시 다음의 이전 맥락을 자연스럽게 이어받아야 합니다: {context}"""
    human_prompt = f"이번 포스팅 주제: {topic}"
    
    response = writer_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ])
    
    return {
        "draft_content": response.content,
        "review_verdict": None,
        "messages": [response]
    }

def critic_agent(state: BlogState) -> dict:
    print("[Node: Critic] LLM 비평가가 초안을 검토합니다...")
    draft = state.get('draft_content')
    tone = state.get('tone_and_manner')
    current_count = state.get('revision_count', 0)

    system_prompt = f"""당신은 엄격한 콘텐츠 편집장입니다. 
    작성된 초안이 '{tone}' 톤을 잘 유지하고 있는지, 내용의 논리적 비약은 없는지 평가하세요.
    
    평가 결과의 맨 마지막 줄에는 반드시 다음 둘 중 하나를 출력해야 합니다:
    - 통과할 경우: VERDICT: OK
    - 수정이 필요한 경우: VERDICT: REVISE
    """
    
    response = critic_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"검토할 초안:\n{draft}")
    ])
    
    feedback = response.content
    print(f"  -> 피드백 요약: {feedback[:100]}...\n")

    if "VERDICT: OK" in feedback.upper():
        print("  -> ✅ 최종안 승인")
        return {
            "final_content": draft, 
            "review_verdict": "OK",
            "messages": [response]
        }
    else:
        print("  -> ❌ 반려 (재작성 요구)")
        return {
            "revision_count": current_count + 1, 
            "review_verdict": "REVISE",
            "messages": [response]
        }


def final_agent(state: BlogState) -> dict:
    print("\n[Node: final_agent] 워크플로우 종료. 최종 결과물이 완성되었습니다.")
    # 실제로는 여기서 VectorDB나 파일로 저장하는 로직이 추가됩니다.
    return {}