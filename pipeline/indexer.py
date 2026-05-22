import chromadb
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from extractors.scorm import extract_scorm
from extractors.pdf import extract_pdf
from extractors.docx_extractor import extract_docx
from extractors.pptx_extractor import extract_pptx
from extractors.video import extract_video

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path="./vectorstore")
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

# In-memory cache to avoid re-checking ChromaDB on every request
_indexed_courses: set = set()


def is_indexed(course_id: str) -> bool:
    if course_id in _indexed_courses:
        return True
    try:
        col = chroma_client.get_collection(f"course_{course_id}")
        if col.count() > 0:
            _indexed_courses.add(course_id)
            return True
    except Exception:
        pass
    return False


def extract_text(module_type: str, url: str) -> str:
    mt = module_type.lower()
    try:
        if "zip" in mt or "scorm" in mt:
            return extract_scorm(url)
        elif "pdf" in mt:
            return extract_pdf(url)
        elif "powerpoint" in mt or "pptx" in mt or "ppt" in mt or "presentation" in mt:
            return extract_pptx(url)
        elif "word" in mt or "docx" in mt or "document" in mt or "msword" in mt:
            return extract_docx(url)
        elif "video" in mt or "mp4" in mt or "webm" in mt or "mkv" in mt:
            return extract_video(url)
        elif "image" in mt or "png" in mt or "jpg" in mt or "jpeg" in mt:
            print(f"[indexer] Skipping image module (no text): {mt}")
            return ""
        else:
            print(f"[indexer] Unsupported moduleType: {module_type}")
            return ""
    except Exception as e:
        print(f"[indexer] Failed to extract ({module_type}) {url}: {e}")
        return ""


def index_course(course_id: str, modules: list):
    if is_indexed(course_id):
        print(f"[indexer] course {course_id} already indexed, skipping.")
        return

    print(f"[indexer] Indexing course {course_id} with {len(modules)} module(s)...")

    all_chunks = []
    all_metadatas = []

    for module in modules:
        text = extract_text(module["moduleType"], module["moduleFile"])
        if not text.strip():
            continue
        chunks = splitter.split_text(text)
        all_chunks.extend(chunks)
        all_metadatas.extend([
            {"moduleId": module["moduleId"], "moduleName": module.get("moduleName", "")}
            for _ in chunks
        ])

    if not all_chunks:
        print(f"[indexer] No text extracted for course {course_id}.")
        return

    vectors = embeddings.embed_documents(all_chunks)

    collection = chroma_client.get_or_create_collection(f"course_{course_id}")
    collection.add(
        documents=all_chunks,
        embeddings=vectors,
        metadatas=all_metadatas,
        ids=[f"chunk_{i}" for i in range(len(all_chunks))]
    )

    _indexed_courses.add(course_id)
    print(f"[indexer] course {course_id} indexed with {len(all_chunks)} chunks.")
