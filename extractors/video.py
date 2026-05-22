import os
import shutil
import subprocess
import tempfile
import requests
from groq import Groq

client = Groq()


def extract_video(url: str) -> str:
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    print(f"[video] ffmpeg path: {ffmpeg_bin}")

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
        # Extract compressed mono audio (~10MB for 45 min)
        print(f"[video] Extracting audio...")
        result = subprocess.run(
            [ffmpeg_bin, "-i", video_path, "-vn", "-ar", "16000",
             "-ac", "1", "-b:a", "32k", audio_path, "-y"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg error: {result.stderr[-300:]}")

        # Transcribe with Groq Whisper API
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
