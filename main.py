import uuid
import threading
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")

from pipeline.summarizer import get_video_summary

app = FastAPI(title="LMS AI Summary Service")

@app.on_event("startup")
async def startup():
    import shutil, os
    ffmpeg = shutil.which("ffmpeg")
    groq_key = os.environ.get("GROQ_API_KEY", "NOT SET")
    print(f"[startup] ffmpeg: {ffmpeg}")
    print(f"[startup] GROQ_API_KEY set: {'yes' if groq_key != 'NOT SET' else 'NO - MISSING'}")
    print("[startup] App ready.")

# In-memory job store: jobId -> {status, summary, error}
_jobs: dict = {}


@app.get("/")
def root():
    return {"status": "LMS AI Service is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


class SummaryRequest(BaseModel):
    moduleId: str
    moduleFile: str


@app.post("/summary/start")
def summary_start(request: SummaryRequest):
    """Start async summary job. Returns jobId immediately."""
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "processing", "summary": None, "error": None}

    def run():
        try:
            text = get_video_summary(request.moduleId, request.moduleFile)
            _jobs[job_id]["summary"] = text
            _jobs[job_id]["status"] = "done"
        except Exception as e:
            _jobs[job_id]["error"] = str(e)
            _jobs[job_id]["status"] = "error"

    threading.Thread(target=run, daemon=True).start()
    return {"jobId": job_id, "status": "processing"}


@app.get("/summary/status/{job_id}")
def summary_status(job_id: str):
    """Poll this endpoint until status is 'done' or 'error'."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
