from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_text_splitters import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
import streamlit as st

load_dotenv()
# 1. 임베딩 모델 설정
# text-embedding-3-small은 OpenAI의 최신 임베딩 모델로 성능이 좋고 비용이 매우 저렴하다
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

text_splitter = CharacterTextSplitter(
    chunk_size = 500,
    chunk_overlap=100,
    separator='\n'
)

# 2. 로컬 DB 저장소 경로
DB_DIR = "./chroma_db"
COLLECTION_NAME = "blog_memory"
@st.cache_resource
def get_vector_db():
    """ChromaDB 인스턴스를 초기화하고 반환합니다."""
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=DB_DIR
    )

def save_blog_context(topic: str, context_text: str):
    """
    완성된 블로그 글의 핵심 맥락을 VectorDB에 저장합니다.
    """
    db = get_vector_db()
    
    # Document 객체로 포장해서 저장 (메타데이터로 주제를 달아줍니다)
    raw_doc = Document(
        page_content=context_text,
        metadata={"topic": topic}
    )
    docs = text_splitter.split_documents([raw_doc])
    db.add_documents(docs)
    print(f"  -> 💾 VectorDB 저장 완료: [{topic}]의 맥락이 기록되었습니다.")

def retrieve_past_context(current_topic: str, k: int = 1) -> str:
    """
    새로운 포스팅 주제와 가장 유사한 과거 맥락을 VectorDB에서 검색합니다.
    k는 가져올 문서의 개수입니다.
    """
    db = get_vector_db()
    
    # DB에 데이터가 있는지 먼저 확인
    if not db.get()['documents']:
         return "아직 저장된 이전 포스팅 맥락이 없습니다."

    # 현재 주제(current_topic)를 쿼리로 날려서 가장 비슷한 과거 글을 찾기 
    query = f"""
    **Role:**
    당신은 VectorDB 검색 쿼리 최적화 전문가입니다.

    **Objective:**
    주어진 '현재 블로그 주제'를 바탕으로, 과거 데이터베이스에서 가장 연관성 높은 문서를 찾기 위한 '검색 키워드 묶음'을 생성하세요.

    **Context:**
    - 현재 주제: {current_topic}

    **Rules:**
    - 문장형태로 작성하지 마세요. (예: "~에 대해 알려줘" 금지)
    - 현재 주제와 관련된 IT 기술 용어, 개념어, 동의어만 3~5개 추출하세요.
    - 쉼표로 구분된 단어들만 출력하세요.

    **Format:**
    키워드1, 키워드2, 키워드3
    """
    
    results = db.similarity_search(query, k=k) 
    
    if not results:
        return "관련된 이전 포스팅 맥락을 찾지 못했습니다."
        
    # 검색된 문서들을 하나의 문자열로 취합
    context_list = []
    for i, doc in enumerate(results):
        topic = doc.metadata.get('topic', '알 수 없는 주제')
        context_list.append(f"[과거 포스팅 {i+1} - {topic}]\n{doc.page_content}")
        
    return "\n\n".join(context_list)