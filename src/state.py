from pydantic import BaseModel
from typing import Annotated, Optional, Literal
from langgraph.graph import add_messages

class BlogState(BaseModel):
    messages: Annotated[list, add_messages] # LLM 답변 저장할 키
    is_first_post: bool                     # 분기용, 첫 포스팅인지 여부
    current_topic: str                      # 작성할 내용의 주제
    accumulated_context: str                # 이전 포스팅들의 요약본(맥락)
    tone_and_manner: str                    # 블로그 말투
    next_step: Optional[Literal[            # supervisor가 판단한 경로 선택 목록
        'intro_graph', 
        'continuation_graph', 
        'final', 
        'critic'
        ]]

    sub_next_step: Optional[Literal[        # 하위 그래프들의 경로 선택 목록
        'reviewer',
        'gen_draft_content',
        'gen_final_content'
        ]]
    

    draft_content: Optional[str]            # 초안
    final_content: Optional[str]            # 최종안

    revision_count: int                     # Critic 거절 횟수 (무한 루프 방지 -> 필수다)

    