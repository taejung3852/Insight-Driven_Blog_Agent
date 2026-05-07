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

def save_blog_context(topic: str, context_text: str, tone: str = ''):
    """
    완성된 블로그 글의 핵심 맥락을 VectorDB에 저장합니다.
    """
    db = get_vector_db()
    
    # Document 객체로 포장해서 저장 (메타데이터로 주제를 달아줍니다)
    raw_doc = Document(
        page_content=context_text,
        metadata={"topic": topic, 'tone': tone}
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


def get_all_topics() -> list[str]:
    """VectorDB에 저장된 모든 고유 토픽(방 이름) 목록 불러오기"""
    db = get_vector_db() # 캐싱된 DB 호출
    try:
        # ChromaDB에서 모든 데이터의 메타데이터 불러오기
        collection = db._collection
        result = collection.get(include=["metadatas"])
        
        if not result or not result.get("metadatas"):
            return []
            
        # 메타데이터에서 'topic' 키의 값만 추출하여 중복 제거
        topics = set()
        for metadata in result["metadatas"]:
            if metadata and "topic" in metadata:
                topics.add(metadata["topic"])
                
        return list(topics)
    except Exception as e:
        print(f"토픽 목록 로드 중 에러 발생: {e}")
        return []

def delete_topic(topic: str) -> bool:
    """VectorDB에서 특정 토픽(방)의 모든 데이터를 삭제합니다."""
    db = get_vector_db()
    try:
        collection = db._collection
        # metadata의 'topic' 필드가 입력받은 topic과 일치하는 데이터 모두 삭제
        collection.delete(where={"topic": topic})
        print(f"🗑️ [System] '{topic}' 관련 데이터가 ChromaDB에서 삭제되었습니다.")
        return True
    except Exception as e:
        print(f"토픽 삭제 중 에러 발생: {e}")
        return False

def get_topic_tone(topic: str) -> str:
    """특정 방에 저장된 톤앤매너를 가져옵니다."""
    db = get_vector_db()
    result = db._collection.get(where={"topic": topic}, include=["metadatas"])
    if result and result.get("metadatas"):
        for meta in result["metadatas"]:
            if meta and "tone" in meta and meta["tone"]:
                return meta["tone"]
    return ""

def update_topic_tone(topic: str, new_tone: str):
    """사용자 피드백을 반영하여 특정 방의 톤앤매너를 영구 업데이트합니다."""
    db = get_vector_db()
    collection = db._collection
    
    # 기존 데이터의 메타데이터를 확인
    result = collection.get(where={"topic": topic})
    if result and result.get("ids"):
        # 기존 메타데이터 가져와서 tone만 수정
        metadatas = result["metadatas"]
        for meta in metadatas:
            meta["tone"] = new_tone
        
        # 수정된 메타데이터로 덮어쓰기
        collection.update(
            ids=result["ids"],
            metadatas=metadatas
        )
        print(f"🔄 [System] '{topic}' 방의 톤앤매너가 사용자 피드백으로 업데이트되었습니다.")

def save_user_guideline(topic: str, guideline: str):
    """사용자가 지적한 '글의 구조/내용' 피드백을 다음 작성을 위해 가이드라인으로 저장합니다."""
    # Context Injection 단계에서 과거 요약본과 함께 검색될 수 있도록 메타데이터와 함께 저장
    save_blog_context(
        topic=topic, 
        context_text=f"[사용자 피드백/가이드라인 절대 준수]\n{guideline}", 
        tone=""
    )