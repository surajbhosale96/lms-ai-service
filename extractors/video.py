import os
import tempfile
import requests
from groq import Groq

client = Groq()


def extract_video(url: str) -> str:
    # Download video to a temp file
    print(f"[video] Downloading video from {url[:60]}...")
    response = requests.get(url, stream=True, timeout=300)
    response.raise_for_status()

    suffix = ".mp4"
    for ext in [".webm", ".mkv", ".mov", ".avi"]:
        if ext in url.lower():
            suffix = ext
            break

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as vf:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            vf.write(chunk)
        video_path = vf.name

    audio_path = video_path.replace(suffix, ".mp3")

    try:
        # Extract compressed mono audio with ffmpeg (~10MB for 45 min)
        print(f"[video] Extracting audio...")
        ret = os.system(
            f'ffmpeg -i "{video_path}" -vn -ar 16000 -ac 1 -b:a 32k "{audio_path}" -y -loglevel error'
        )
        if ret != 0:
            raise RuntimeError("ffmpeg audio extraction failed")

        # Transcribe with Groq Whisper API (handles 45 min in ~10 seconds)
        print(f"[video] Transcribing with Groq Whisper...")
        with open(audio_path, "rb") as af:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(audio_path), af),
                model="whisper-large-v3",
                response_format="text",
            )

        print(f"[video] Transcription complete.")
        return transcription if isinstance(transcription, str) else transcription.text

    finally:
        if os.path.exists(video_path):
            os.unlink(video_path)
        if os.path.exists(audio_path):
            os.unlink(audio_path)
