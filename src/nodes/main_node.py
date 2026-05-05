import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import END
from src.state import BlogState
from src.memory import retrieve_past_context, save_blog_context
from src.utils import load_learning_insights, encode_image_to_base64

load_dotenv()

# 작성용: 창의성을 위해 T -> 0.7
writer_llm = ChatOpenAI(model = 'gpt-4.1-mini', temperature=0.7)
# 비평용: 엄격하고 일관성을 위해 T -> 0.1
critic_llm = ChatOpenAI(model='gpt-4.1-mini', temperature=0.1)

def supervisor_agent(state: BlogState) -> dict:
    print("\n[Node: supervisor] 라우팅 판단 중...")

    raw_insights = state.get("learning_insights")
    if not raw_insights:
        print("  -> ❌ 에러: learning_insights가 없습니다. 글 작성을 중단합니다.")
        return {"next_step": END} # 인사이트 없으면 종료

    # 경로일 경우 내용을 읽어서 다시 저장 (한 번만 실행되도록 조건부 처리)
    if isinstance(raw_insights, str) and (raw_insights.endswith('.txt') or raw_insights.endswith('.md')):
         processed_insights = load_learning_insights(raw_insights)
         # state 업데이트를 위해 return에 포함
    else:
         processed_insights = raw_insights
         
    is_first = state.get('is_first_post', True)
    accumulated = state.get("accumulated_context")
    draft = state.get("draft_content")
    verdict = state.get("review_verdict")
    rev_count = state.get("revision_count", 0)
    max_rev = state.get("max_revisions", 2)
    
    if not is_first and not accumulated:
        next_step = "context_injection"
        
    elif not draft:
        next_step = "intro_graph" if is_first else "continuation_graph" # 각 서브 그래프로 옮겨가게 된다.
        
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
    return {"next_step": next_step, "learning_insights": processed_insights}

def context_injection_agent(state: BlogState) -> dict:
    print("[Node: Context Injection] VectorDB에서 이전 글의 메타데이터를 가져옵니다.")
    topic = state.get('current_topic')

    if state.get('is_first_post'):
        return {"accumulated_context": "첫 포스팅이므로 이전 맥락이 없습니다."}

    past_context = retrieve_past_context(current_topic = topic, k = 2)
    print(f"  -> 🔍 검색된 맥락 데이터:\n{past_context[:100]}...\n")
    
    return {'accumulated_context': past_context}


def image_analysis_agent(state: BlogState) -> dict:
    print("\n[Node: Image Analysis] 첨부된 이미지의 시각적 요소를 분석합니다...")
    
    image_paths = state.get('captured_images', [])
    if not image_paths:
        return {"image_information": "첨부된 이미지 없음"}

    base64_images = []
    file_names = []
    for path in image_paths:
        encoded = encode_image_to_base64(path)
        if encoded:
            base64_images.append(encoded)
            file_names.append(os.path.basename(path))

    file_names_str = "\n\n".join(file_names) # 리스트 문자열로 변경
    
    if not base64_images:
        return {"image_information": "유효한 이미지 파일이 없습니다."}

    print(f"  -> {len(base64_images)}개의 이미지를 분석 중...")

    # 프롬프트: 철저하게 캡셔닝(Captioning)만 지시
    sys_msg = f"""
    **Role:**
    당신은 IT 블로그의 시각 데이터 분석가(Visual Data Analyst)입니다.

    **Objective:**
    제공된 이미지들을 관찰하고, 각 이미지의 핵심 정보와 의도를 상세히 텍스트로 요약하세요.

    **Rules:**
    - 항상 이미지가 무엇을 설명하려는지(다이어그램, 코드 스니펫, UI 등) 정확히 파악하세요.
    - 절대 없는 내용을 지어내지 마세요.
    - 각 파일명과 그에 대한 분석을 반드시 매핑해서 작성하세요.

    **Format:**
    - [파일명1]: (이미지의 핵심 내용 및 역할 요약 1~2문장)
    - [파일명2]: (이미지의 핵심 내용 및 역할 요약 1~2문장)
    """

    content_parts = [{"type": "text", "text": f"첨부된 이미지 파일명: {file_names_str}"}] # 휴먼 메시지로 들어갈 내용이다.
    
    for b64_img in base64_images:
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
        })

    response = critic_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=content_parts)
    ])

    print("  -> ✅ 이미지 분석(Captioning) 완료.")
    return {"image_information": response.content}

def image_placement_agent(state: BlogState) -> dict:
    print("\n[Node: Image Placement] 분석된 이미지를 최종안의 적절한 위치에 삽입합니다...")
    
    guide = state.get("image_information")
    draft = state.get("polished_content")

    # 이미지가 없거나 분석되지 않았다면 패스
    if not guide or guide == "첨부된 이미지 없음":
        return {}

    sys_msg = f"""
    **Role:**
    당신은 세밀한 레이아웃을 담당하는 편집 디자이너입니다.

    **Objective:**
    '이미지 분석 내역'을 바탕으로 '원본 블로그 글'의 가장 어울리는 문단 사이사이에 이미지 삽입 마커를 배치하세요.

    **Rules:**
    - 절대 원본 블로그 글의 문장, 단어, 띄어쓰기를 단 한 글자도 수정하거나 훼손하지 마세요.
    - 항상 이미지의 설명이 등장하기 직전, 혹은 직후의 문단 사이에 마커를 삽입하세요.
    - 마커는 반드시 별도의 줄(개행)에 독립적으로 존재해야 합니다.

    **Format:**
    (원본 텍스트)
    <!-- [이미지 삽입: 파일명] -->
    (원본 텍스트)
    """

    human_msg = f"""
    **Context:**
    - 이미지 분석 내역: {guide}
    - 원본 블로그 글: {draft}
    """
    
    response = critic_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=human_msg)
    ])

    print("  -> ✅ 이미지 마커 삽입 완료.")
    # 마커가 추가된 글로 덮어씌움
    return {"polished_content": response.content}

def critic_agent(state: BlogState) -> dict:
    print("[Node: Critic] LLM 비평가가 초안을 검토합니다...")
    polished = state.get('polished_content')
    tone = state.get('tone_and_manner')
    current_count = state.get('revision_count', 0)
    max_rev = state.get('max_revisions', 2) # 최대 수정 횟수 가져오기

    sys_msg = f"""
    **Role:**
    당신은 품질을 타협하지 않는 엄격한 콘텐츠 편집장(Editor-in-Chief)입니다.

    **Objective:**
    최종 블로그 초안이 주어진 톤앤매너를 지켰는지, 논리적 흐름이 완벽한지 평가하고 통과 여부를 결정하세요.

    **Rules:**
    - 항상 독자의 관점에서 글이 읽기 편한지, 전문성은 담겨있는지 냉정하게 평가하세요.
    - 절대 글을 직접 수정하거나 다시 쓰지 마세요.
    - 피드백은 3문장 이내로 핵심만 간결하게 작성하세요.
    - 평가 결과의 맨 마지막 줄에는 반드시 아래의 '출력 형식' 중 하나를 단독으로 출력하세요.

    **Format:**
    (3문장 이내의 평가 피드백)

    VERDICT: OK (통과 시) 
    또는 
    VERDICT: REVISE (수정 필요 시)
    """

    human_msg = f"""
    **Context:**
    - 검토할 글: {polished}
    - 요구된 톤앤매너: {tone}
    """
    
    response = critic_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=human_msg)
    ])
    
    feedback = response.content
    print(f"  -> 피드백 요약: {feedback[:100]}...\n")

    if "VERDICT: OK" in feedback.upper():
        print("  -> ✅ 최종안 승인")
        return {
            "final_content": polished, 
            "review_verdict": "OK",
            "messages": [response]
        }
    else:
        print(f"  -> ❌ 반려 (재작성 요구) - 현재 수정 횟수: {current_count + 1}/{max_rev}")
        if current_count + 1 >= max_rev:
            print("  -> ⚠️ 최대 수정 횟수 도달. 현재 버전을 최종안으로 확정합니다.")
            return {
                "final_content": polished, # 날리지 않고 최종안으로 승격!
                "revision_count": current_count + 1,
                "review_verdict": "REVISE", 
                "messages": [response]
            }
        else:
            # 아직 수정 기회가 남았다면 기존처럼 에디터가 다시 쓰도록 지워줌
            return {
                "revision_count": current_count + 1, 
                "review_verdict": "REVISE",
                "polished_content": None, 
                "messages": [response]
            }


def final_agent(state: BlogState) -> dict:
    print("\n[Node: Final Agent] 최종 결과물 완성. 장기 기억(VectorDB)에 저장합니다...")    
    final_content = state.get("final_content")
    topic = state.get("current_topic")  

    print(f"""
    ==================== [최종본] ====================

    {final_content}

    =================================================
    """)
    
    # 그냥 통째로 넣으면 토큰이 낭비되므로, LLM을 이용해 '핵심 3요소'만 추출하여 요약
    system_prompt = f"""
    **Role**
    당신은 블로그 데이터베이스를 관리하는 수석 데이터 아키텍트 입니다.

    **Obejective**
    완성된 블로그 글에서 장기 기억(VectorDB)에 저장할 핵심 메타데이터만 정확하게 추출하세요.

    **Rules:**
    - 절대 원본 글을 그대로 요약하지 마세요.
    - 불필요한 서술어는 모두 제거하고 명사/개념 위주로 작성하세요.
    - 반드시 아래의 'Format'을 100% 지켜서 작성하세요.

    **Format**
    [이전 글 핵심 요약]
    - (핵심 개념 1)
    - (핵심 개념 2)
    [이전 글 결론]
    - (글의 최종 결론 1줄)
    [문체 및 톤앤매너]
    - (사용된 1인칭 표현이나 말투 특징 요약)
    """

    human_msg = f"""
    **Context:**
    - 다음 연재글 작성 시, 이전 글의 '주요 개념'과 '결론'을 참고하기 위해 사용됩니다.
    - 원본 글: {final_content}
    """
    
    # (주의: writer_llm 객체가 이 파일에 정의되어 있어야 합니다)
    summary_response = writer_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_msg)
    ])
    
    summary_text = summary_response.content
    print("  -> 📝 메타데이터(용어, 결론, 문체) 추출 완료. DB에 기록합니다.")
    
    # 요약된 핵심 내용을 memory.py를 통해 ChromaDB에 영구 저장
    save_blog_context(topic, summary_text)
    
    print("\n====================================")
    print("## 블로그 작성 워크플로우가 모두 성공적으로 종료되었습니다! ##")
    print("====================================")
    
    return {}