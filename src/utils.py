import os
import base64
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

def load_learning_insights(path_or_text: str) -> str:
    """경로면 파일을 읽고, 아니면 텍스트 그대로 반환"""
    if os.path.exists(path_or_text): # 경로가 입력이 되면 읽어내고 아니면 바로 읽기.
        with open(path_or_text, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    return path_or_text # 경로가 아니면 입력값 그대로 반환


def encode_image_to_base64(image_path: str):
    """이미지 파일 경로를 받아 Base64 문자열로 변환합니다."""
    if os.path.exists(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    else:
        print(f"⚠️ 경고: 이미지를 찾을 수 없습니다 -> {image_path}")
        return None


def analyze_custom_tone(sample_text: str) -> str:
    """사용자의 예시 글을 분석하여 톤앤매너 프롬프트를 생성합니다."""
    # 분석은 빠르고 가벼운 모델을 사용하여 비용과 시간을 절약합니다.
    analyzer_llm = ChatOpenAI(model='gpt-5.4-mini', temperature=0)
    
    sys_msg = """
    **Role:**
    당신은 작가의 문체와 표현 방식을 예리하게 파악하는 수석 텍스트 스타일 분석가입니다.

    **Objective:**
    주어진 예시 글을 분석하여, 다른 AI 작가가 해당 문체를 완벽하게 모방할 수 있도록 '프롬프트 형식의 톤앤매너 지시서'를 작성하세요.

    **Context:**
    - 이 분석 결과는 이후 블로그 본문을 작성하는 에이전트의 시스템 프롬프트(행동 지침)로 직접 주입됩니다.

    **Rules:**
    - 항상 예시 글의 어미(~습니다, ~해요, ~다 등), 어조(전문적, 감성적, 논리적 등), 특징적인 표현 방식(비유, 이모지 사용 등)을 구체적으로 추출하세요.
    - 절대 예시 글의 '내용(Content)'이나 '주제'를 요약하지 마세요. 오직 '말투와 스타일(Tone & Manner)'만 분석해야 합니다.
    - 다른 AI가 지시사항으로 바로 읽고 따를 수 있는 명확한 행동 지침 형태로 작성하세요.
    - 반드시 3문장 이내로 핵심만 간결하게 작성하세요.

    **Format:**
    - (AI 작가에게 전달할 행동 지침 3문장 이내)

    """

    human_msg = f"분석할 예시 글:\n{sample_text}"
    
    response = analyzer_llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=human_msg)
    ])
    
    return response.content