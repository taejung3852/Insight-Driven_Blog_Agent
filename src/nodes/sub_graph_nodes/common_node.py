from src.utils import encode_image_to_base64
from src.state import BlogState
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import os

# 작성용: 창의성을 위해 T -> 0.7
writer_llm = ChatOpenAI(model = 'gpt-5.4', temperature=0.7)
# 비평용: 엄격하고 일관성을 위해 T -> 0.1
critic_llm = ChatOpenAI(model='gpt-5.4-mini', temperature=0.1)

load_dotenv()

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