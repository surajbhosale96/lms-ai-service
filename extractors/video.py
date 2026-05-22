import os
import shutil
import subprocess
import tempfile
from groq import Groq

_client = None

def get_client():
    global _client
    if _client is None:
        _client = Groq()
    return _client


def extract_video(url: str) -> str:
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    print(f"[video] ffmpeg: {ffmpeg_bin}")
    print(f"[video] Streaming audio extraction from URL...")

    audio_path = tempfile.mktemp(suffix=".mp3")

    try:
        # Pass URL directly to ffmpeg — no need to download the full video file
        # ffmpeg streams it internally, saving memory on the server
        result = subprocess.run(
            [
                ffmpeg_bin,
                "-i", url,
                "-vn",          # no video
                "-ar", "16000", # 16kHz sample rate
                "-ac", "1",     # mono
                "-b:a", "32k",  # 32kbps — keeps audio under 25MB for 45-min video
                audio_path,
                "-y",
            ],
            capture_output=True,
            text=True,
            timeout=600,        # 10 min max
        )

        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg error: {result.stderr[-500:]}")

        audio_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        print(f"[video] Audio extracted: {audio_size_mb:.1f} MB")

        # Transcribe with Groq Whisper API
        print(f"[video] Transcribing with Groq Whisper...")
        with open(audio_path, "rb") as af:
            transcription = get_client().audio.transcriptions.create(
                file=(os.path.basename(audio_path), af),
                model="whisper-large-v3",
                response_format="text",
            )

        print(f"[video] Transcription complete.")
        return transcription if isinstance(transcription, str) else transcription.text

    finally:
        if os.path.exists(audio_path):
            os.unlink(audio_path)
