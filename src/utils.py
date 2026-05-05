import os
import base64

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