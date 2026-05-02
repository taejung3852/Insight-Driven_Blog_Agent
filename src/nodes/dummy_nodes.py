from src.state import BlogState

def supervisor_agent(state: BlogState) ->  dict:
    print(f"[Node: supervisor] 어떤 노드로 가야할지 판단합니다.")
    if state.is_first_post:
        return {"next_step": "intro_graph"}
    else:
        return {"next_step": "context_injection"}

def context_injection_agent(state: BlogState) -> dict:
    print("[Node: Context Injection] VectorDB에서 이전 글의 메타데이터를 가져옵니다.")
    return {'accumulated_context': '이전 포스트들의 3요소(용어, 결론, 문체) 데이터'}

def final_agent(state: BlogState) -> dict:
    print("[Node: final_agent] 모든 워크플로우가 성공적으로 마쳤습니다. 현재 블로그 내용을 VectorDB에 업데이트를 하고 마치겠습니다.")
    return {}

def continuation_graph_agent(state: BlogState) -> dict:
    print("[Node: Continuation Graph] 이전 맥락을 바탕으로 2편 작성을 시작합니다.")
    return {"draft_content": f"이전 맥락({state['accumulated_context']})을 이어서 초안을 썼습니다."}

def intro_graph_agent(state: BlogState) -> dict:
    print("[Node: Intro Graph] 1편 작성을 시작합니다.")
    return {"draft_content": f"주제 '{state['current_topic']}'에 대한 첫 번째 초안입니다."}

def critic_agent(state: BlogState) -> dict:
    print("[Node: Critic] 초안의 일관성을 검토합니다...")
    # 더미 테스트: 첫 번째 검토는 무조건 반려, 두 번째는 통과하도록 세팅
    current_count = state.get("revision_count", 0)

    if current_count < 1:
        print("  -> ❌ 반려: 문체가 가이드와 맞지 않습니다.")
        return {"revision_count": current_count + 1}
    else:
        print("  -> ✅ 통과: 훌륭한 글입니다.")
        return {"final_content": state["draft_content"]} # 초안을 최종본으로 승격