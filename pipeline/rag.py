import chromadb
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path="./vectorstore")

_llm = None

def get_llm():
    global _llm
    if _llm is None:
        _llm = ChatGroq(model="llama-3.1-8b-instant")
    return _llm

SYSTEM_PROMPT = """You are a helpful course assistant for an LMS app.
Answer the user's question using only the course content provided.
If the answer is not found in the content, say: "I don't have information about that in this course."
Keep answers clear and concise."""


def get_answer(course_id: str, question: str) -> str:
    collection = chroma_client.get_collection(f"course_{course_id}")

    query_vector = embeddings.embed_query(question)
    results = collection.query(query_embeddings=[query_vector], n_results=5)

    if not results["documents"] or not results["documents"][0]:
        return "No course content found to answer your question."

    context = "\n\n".join(results["documents"][0])

    prompt = f"""{SYSTEM_PROMPT}

Course Content:
{context}

Question: {question}

Answer:"""

    response = get_llm().invoke(prompt)
    return response.content
