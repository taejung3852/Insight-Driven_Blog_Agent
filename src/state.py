# from pydantic import BaseModel
from typing import Annotated, Optional, Literal, TypedDict
from langgraph.graph import add_messages

class BlogState(TypedDict):
    messages: Annotated[list, add_messages] # LLM 답변 저장할 키

    # 필수 초기 설정값
    is_first_post: bool                     # 분기용, 첫 포스팅인지 여부
    current_topic: str                      # 작성할 내용의 주제
    tone_and_manner: str                    # 블로그 말투
    learning_insights: Optional[str]        # 사용자의 깨달음 (입력 데이터)

    # 상태 업데이투 과정에서 채워지는 필드들 (반드시 None으로 기본값 지정)
    accumulated_context: str                # 이전 포스팅들의 요약본(맥락)
    next_step: Optional[Literal[            # supervisor가 판단한 경로 선택 목록
        'intro_graph', 
        'continuation_graph', 
        'final', 
        'critic'
        ]]
    sub_next_step: Optional[Literal[        # 하위 그래프들의 경로 선택 목록
        'outline',
        'image_analysis',
        'draft',
        'internal_editor',
        'finish'
        ]]    
    draft_content: Optional[str]            # 초안
    final_content: Optional[str]            # 최종안
    review_verdict: Optional[str]           # OK(통과) or REVISE(불통) 여부
    critic_feedback: Optional[str]

    revision_count: int                     # Critic 거절 횟수 (무한 루프 방지 -> 필수다)
    max_revisions: int                      # 최대 거절 횟수

    
    captured_images: Optional[list[str]]    # 이미지 데이터 (없으면 빈 리스트)
    
    outline: Optional[str]                  # Structure 워커의 결과물
    image_information: Optional[str]        # Image Analysis 워커의 결과물
    polished_content: Optional[str]         # Editor 워커의 결과물

    human_review_complete: Optional[bool]   # 사용자 검토 완료 여부
    human_feedback_tone: Optional[str]      # 사용자가 지적한 말투 피드백
    human_feedback_structure: Optional[str] # 사용자가 지적한 글 구조/내용 피드백