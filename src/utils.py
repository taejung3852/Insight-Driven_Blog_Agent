import os

def load_learning_insights(path_or_text: str) -> str:
    """경로면 파일을 읽고, 아니면 텍스트 그대로 반환"""
    if os.path.exists(path_or_text): # 경로가 입력이 되면 읽어내고 아니면 바로 읽기.
        with open(path_or_text, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    return path_or_text # 경로가 아니면 입력값 그대로 반환