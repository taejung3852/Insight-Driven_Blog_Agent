from src.state import BlogState
from src.graph import app

def run_test(is_first: bool, topic: str):
    """
    그래프 실행 및 동작 검증을 위한 테스트 함수
    """
    print(f"\n{'='*20}")
    print(f"🚀 {'신규' if is_first else '연재'} 포스팅 테스트 시작")
    print(f"{'='*20}")

    # 1. 초기 상태 설정 (BlogState 스키마 준수)
    initial_state = {
        "is_first_post": is_first,
        "current_topic": topic,
        "tone_and_manner": "전문적이면서 친근한",
        "learning_insights": "./test_insights.md",  # 파일 경로 전달
        "revision_count": 0,
        "max_revisions": 2, # 최대 수정 횟수 제한
        "messages": []
    }

    # 2. 그래프 스트리밍 실행
    # stream()을 사용하면 각 노드가 완료될 때마다 상태 변화를 추적할 수 있습니다.
    try:
        for event in app.stream(initial_state): # 스트림을 사용하면 노드가 하나씩 실행되는 것을 딕셔너리 형식으로 출력할 수 있다. 
            for node_name, state_update in event.items(): # event에는 이렇게 저장되어있다. "노드이름": { "상태키": "업데이트된값" }
                print(f"\n📍 [실행 완료]: {node_name}")
                # 업데이트된 필드가 있다면 출력
                if state_update:
                    print(f"   ㄴ 업데이트 항목: {list(state_update.keys())}")
    except Exception as e:
        print(f"\n❌ 실행 중 오류 발생: {e}")

    print(f"\n{'='*20}")
    print("✅ 테스트 종료")
    print(f"{'='*20}\n")

if __name__ == "__main__":
    # 테스트 1: 신규 포스팅 (Supervisor -> Intro -> Supervisor -> Critic -> ... -> Final)
    run_test(is_first=False, topic="LLM 에이전트의 미래")

    # 테스트 2: 연재 포스팅 (Supervisor -> Injection -> Supervisor -> Continuation -> ... -> Final)
    # run_test(is_first=False, topic="LLM 에이전트의 미래 - 2편")