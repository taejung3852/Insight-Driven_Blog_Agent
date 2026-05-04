from src.state import BlogState

def supervisor_agent(state: BlogState) ->  dict:
    print("\n[Node: supervisor] State 데이터를 기반으로 다음 단계 판단 중...")

    # TypedDict는 .get()으로 가져와야한다.
    is_first = state.get('is_first_post', True)
    accumulated = state.get("accumulated_context")
    draft = state.get("draft_content")
    verdict = state.get("review_verdict")
    rev_count = state.get("revision_count", 0)
    max_rev = state.get("max_revisions", 2)
    
    # 1. 첫 포스팅이 아니면서, 맥락이 없으면 인젝션
    if not is_first and not accumulated:
        next_step = "context_injection"

    # 2. 초안이 없으면 작성 단계로
    elif not draft:
        if is_first:
            next_step = "intro_graph"
        else:
            next_step = "continuation_graph"
            
    # 3. 평가 결과(Verdict)가 없으면 평가 단계로
    elif not verdict:
        next_step = "critic"

    # 4. 평가 결과에 따른 분기 (디렉터님의 정석 패턴 적용). 평가 결과가 있다.
    else:
        if "OK" in verdict:
            next_step = "final"
        elif "REVISE" in verdict and rev_count < max_rev:
            # 반려되었으므로 다시 작성하도록 라우팅 (초안 삭제 대신 덮어쓰기 유도)
            if is_first:
                next_step = "intro_graph"
            else:
                next_step = "continuation_graph"
        else:
            next_step = "final" # 최대 수정 횟수 초과 시 강제 종료

    print(f"  -> 다음 단계: {next_step}")
    return {"next_step": next_step}

def context_injection_agent(state: BlogState) -> dict:
    print("[Node: Context Injection] VectorDB에서 이전 글의 메타데이터를 가져옵니다.")
    return {'accumulated_context': '이전 포스트들의 3요소(용어, 결론, 문체) 데이터'}

def intro_graph_agent(state: BlogState) -> dict:
    print("[Node: Intro Graph] 1편 작성을 시작합니다.")
    return {
        "draft_content": f"주제 '{state.get('current_topic')}'에 대한 첫 번째 초안입니다.",
        "review_verdict": None # 재작성 시 이전 평가 결과 초기화
        }
    
def continuation_graph_agent(state: BlogState) -> dict:
    print("[Node: Continuation Graph] 이전 맥락을 바탕으로 2편 작성을 시작합니다.")
    return {
        "draft_content": f"이전 맥락({state.get('accumulated_context')})을 이어서 초안을 썼습니다.",
        "review_verdict": None
        }

def final_agent(state: BlogState) -> dict:
    print("[Node: final_agent] 모든 워크플로우가 성공적으로 마쳤습니다. 현재 블로그 내용을 VectorDB에 업데이트를 하고 마치겠습니다.")
    return {}



def critic_agent(state: BlogState) -> dict:
    print("[Node: Critic] 초안의 일관성을 검토합니다...")
    current_count = state.get('revision_count')

    if current_count < 1:
        print(f"  -> ❌ 반려: 품질 미달")
        return {
            "revision_count": current_count + 1, 
            "review_verdict": "REVISE"
        }
    else:
        print(f"  -> ✅ 통과: 최종안으로 승인합니다.")
        return {
            "final_content": state.get('draft_content'), 
            "review_verdict": "OK"
        }