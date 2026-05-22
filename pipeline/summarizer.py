from groq import Groq
from extractors.video import extract_video

_client = None

def get_client():
    global _client
    if _client is None:
        _client = Groq()
    return _client

# Cache: moduleId -> summary string
_summary_cache: dict = {}

SUMMARY_PROMPT = """You are an educational assistant. Below is a transcript of a video lecture.
Write a clear, well-structured summary covering all key points, concepts, and takeaways.
Format it with short paragraphs. Keep it concise but complete.

Transcript:
{transcript}

Summary:"""


def get_video_summary(module_id: str, module_file: str) -> str:
    if module_id in _summary_cache:
        return _summary_cache[module_id]

    print(f"[summarizer] Transcribing video for module {module_id}...")
    transcript = extract_video(module_file)

    if not transcript.strip():
        return "Could not extract audio from this video."

    print(f"[summarizer] Generating summary for module {module_id}...")
    prompt = SUMMARY_PROMPT.format(transcript=transcript[:6000])

    response = get_client().chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
    )
    summary = response.choices[0].message.content

    _summary_cache[module_id] = summary
    print(f"[summarizer] Summary ready for module {module_id}.")
    return summary
