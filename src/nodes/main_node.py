import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_google_genai import GoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import END
from src.state import TechDocState

# TODO: memory.py와 utils.py의 함수명도 기술 문서 도메인에 맞게 수성 해야함
from src.memory import retrieve_past_context, save_doc_context
from src.utils import load_learning_insights

load_dotenv()

# 작성용: 구조적이고 명확한 작성을 위해 T -> 0.4 / 너무 높으면 창의성이 높아져서 일관성이 떨어지고 기술문서에 맞지 않다
writer_llm = GoogleGenerativeAI(model = 'gemini-3-flash-preview', temperature=0.4)

# 비평 및 검증용: 최대한 엄격하고 일관성을 위해 T -> 0.0
critic_llm = GoogleGenerativeAI(model = 'gemini-3-flash-preview', temperature=0)


# ==============================================
# Supervisor 에이전트
def supervisor_agent(state: TechDocState) -> dict:
    print("\n[Node: supervisor] 라우팅 판단 중...")

    is_update = state.get('is_update_request', False)
    past_context = state.get("previous_doc_context")
    reviewed_content = state.get("tech_reviewed_content")  
    verdict = state.get("review_verdict")
    rev_count = state.get("revision_count", 0)
    max_rev = state.get("max_revisions", 2)
    raw_source = state.get("technical_source")
    
    if not raw_source:
        print("  -> ❌ 에러: technical source(기술 자료)가 없습니다. 파이프라인을 중단합니다.")
        return {"next_step": 'end'} # 인사이트 없으면 종료

    # 경로일 경우 내용을 읽어서 다시 저장 (한 번만 실행되도록 조건부 처리)
    # md 파일, txt 파일만 되도록 해주고 있다. (V1: ㅅ텍스트 및 마크다운 우선으로)
    if isinstance(raw_source, str) and (raw_source.endswith('.txt') or raw_source.endswith('.md')):
         processed_source = load_learning_insights(raw_source)
         # state 업데이트를 위해 return에 포함
    else:
         processed_source = raw_source
         
    # 1. 업데이트 요청인데 이전 컨텍스트가 없는 경우 -> 이전 데이터를 불러오는 컨텍스트 주입 노드
    if is_update and not past_context:
        next_step = "context_injection"

    # 2. 에디터가 작성한 기술 초안이 없는 경우 혹은 리뷰 완료본이 없는 경우 -> 작성 그래프로
    elif not reviewed_content:
        next_step = "update_doc_graph" if is_update else "new_doc_graph" # 각 서브 그래프로 옮겨가게 된다.

    # 3. 작성은 되어있지만 QA를 받지 않은 경우
    elif not verdict:
        next_step = "qa_critic"

    # 4. QA 검증 결과에 따른 라우팅
    else:
        if verdict == "PASS":
            if not state.get('human_review_complete'):
                next_step = 'human_approval'
            else:
                next_step = "final_publish"
                
        elif verdict == "REVISE" and rev_count < max_rev:
            print(f"  -> QA 에이전트에서 반료됨. 재작성 요청 (현재 수정 횟수: {rev_count}/{max_rev})")
            next_step = "update_doc_graph" if is_update else "new_doc_graph"
        else:
            # 반려되었으나 최대 수정횟수에 도달한 경우 강제로 휴먼 리뷰
            next_step = 'human_approval'
            

    print(f"  -> 다음 단계: {next_step}")
    return {"next_step": next_step, "technical_source": processed_source}


# ==============================================
# 이전 맥락 주입 에이전트
def context_injection_agent(state: TechDocState) -> dict:
    print("[Node: Context Injection] VectorDB에서 시스템의 아키텍처 맥락을 가져옵니다.")
    system_name = state.get('system_name') # 문서화할 이름

    # TODO: memory.py 수정후 retrieve_past_context인자 변경 필요하다. 현재 프젝에 맞지 않는 이름 (current_topic -> current_system_name)
    past_context = retrieve_past_context(current_topic = system_name, k = 2)
    print(f"  -> 검색된 맥락 데이터 로드 완료.\n")
    
    return {'previous_doc_context': past_context}


# ==============================================
# QA 에이전트
def qa_critic_agent(state: TechDocState) -> dict:
    print("[Node: QA Critic] 품질 보증 시스템이 문서의 규격과 정합성을 검증합니다...")
    reviewed_content = state.get('tech_reviewed_content')
    style_guide = state.get('doc_style_guide')
    current_count = state.get('revision_count', 0)

    sys_msg = f"""
    # Role
    당신은 사내 기술 표준 및 규격 준수 여부를 엄격하게 판단하는 수석 QA(Quality Assurance) 엔지니어입니다.

    # Instructions
    작성된 기술 문서 초안이 사내 가이드라인을 완벽히 준수하고 있는지 검증하십시오.

    # Steps
    1. 입력된 문서 초안의 구조와 가이드라인의 필수 항목을 대조하십시오.
    2. 기술적 용어의 통일성 및 비정형 데이터와의 정합성을 확인하십시오.
    3. 규격 위반 사항이나 논리적 비약이 발견되면 <Violation> 태그 내에 구체적으로 리스트업 하십시오.

    # Expectations
    최종 목표는 주니어 개발자도 오해 없이 읽고 즉각적으로 시스템을 이해할 수 있는 무결점의 기술 문서를 확보하는 것입니다.

    # Narrowing
    - 항상 객관적인 지표와 가이드라인에 근거하여 평가하십시오.
    - 절대 문서 본문을 직접 수정하여 출력하지 마십시오. 오직 문제점(피드백)만 지적하십시오.
    - 감성적인 표현이나 모호한 부사가 포함되어 있다면 반드시 수정을 요구하십시오.
    - 평가 결과의 가장 마지막 줄에는 반드시 아래 판정 결과 중 하나를 단독으로 기재하십시오.
        - 통과 시: VERDICT: PASS
        - 수정 필요 시: VERDICT: REVISE
    """

    human_msg = f"""
    [사내 가이드라인]
    {style_guide}
    
    [검증할 기술 문서 초안]
    검토할 글: {reviewed_content}
    """
    
    response = critic_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=human_msg)
    ])
    
    feedback = response.content
    print(f"  -> QA 리포트 생성 완료 (판정 결과 대기 중)\n")

    if "VERDICT: PASS" in feedback.upper():
        print("  -> ✅ 규격 통과 (PASS)")
        return {
            "final_doc": reviewed_content, 
            "review_verdict": "PASS",
            'qa_feedback': None,
            "messages": [response]
        }
    else:
        print(f"  -> ❌ 규격 미달 (REVISE)")
        
        return{
            "revision_count": current_count + 1, 
            "review_verdict": "REVISE",
            "doc_draft": None,
            "tech_reviewed_content": None, # 기존 작성본 파기
            "qa_feedback": feedback,
            "messages": [response]
        }

# ==============================================
# HITL 에이전트
def human_approval_agent(state: TechDocState) -> dict:
    print("\n[Node: Human Approval] 에이전트 작업 완료. 사용자의 최종 기술 검토(HITL)를 대기합니다...")
    return {}

# ==============================================
# 최종 마무리 에이전트
def final_publish_agent(state: TechDocState) -> dict:
    print("\n[Node: Final Publish] 최종 문서 승인 완료. 시스템 형상 관리(VectorDB)에 기록합니다...")
    final_doc = state.get("final_doc")
    system_name = state.get('system_name')

    
    # 문서 전체가 아닌 아키텍처/기술 요약 메타데이터만 추출해서 DB에 저장
    sys_msg = f"""
    # Role
    당신은 시스템 아키텍처 데이터베이스를 관리하는 수석 데이터 아키텍트입니다.

    # Instructions
    완성된 기술 문서에서 장기 기억(VectorDB)에 저장할 핵심 아키텍처 메타데이터만 정확하게 추출하십시오.

    # Steps
    1. 문서 내에서 시스템의 핵심 목적, 주요 컴포넌트, 그리고 데이터 흐름을 식별하십시오.
    2. 변경된 아키텍처나 API 명세의 핵심 키워드를 추출하십시오.
    3. 불필요한 서술어를 모두 제거하고 명사/개념 위주의 요약본을 작성하십시오.

    # Expectations
    이 요약본은 향후 다른 에이전트가 시스템 업데이트 문서를 작성할 때 '과거 아키텍처 맥락'으로 활용될 핵심 설계 지식입니다.

    # Narrowing
    - 절대 원본 글을 그대로 복사하거나 감성적인 문장을 포함하지 마십시오.
    - 반드시 아래의 Format을 반드시 지켜서 작성하십시오.
    
    [Format]
    [시스템 핵심 목적]
    - (1줄 요약)
    [주요 아키텍처 및 컴포넌트]
    - (컴포넌트 1: 역할)
    - (컴포넌트 2: 역할)
    """

    human_msg = f"""
    [승인된 기술 문서 원본]
    {final_doc}
    """
    
    # (주의: writer_llm 객체가 이 파일에 정의되어 있어야 합니다)
    summary_response = writer_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=human_msg)
    ])
    
    summary_text = summary_response.content
    print("  -> 📝 아키텍처 메타데이터 추출 완료. DB 갱신을 진행합니다.")
    
    # TODO: memory.py 수정 후 save_doc_context 로 변경하고 tone도 빼기
    save_doc_context(system_name, summary_text, tone='')
    
    print("\n====================================")
    print(f"✅ [{system_name}] 기술 문서 파이프라인이 성공적으로 종료되었습니다.")
    print("====================================")
    
    return {}