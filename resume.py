import pymupdf


def load_resume(file_path: str) -> str:
    """读取简历文件，返回纯文本"""
    if file_path.endswith(".pdf"):
        doc = pymupdf.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text.strip()

    if file_path.endswith((".txt", ".md")):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()

    raise ValueError(f"不支持的文件格式：{file_path}")