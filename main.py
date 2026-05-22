from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")

from pipeline.summarizer import get_video_summary

app = FastAPI(title="LMS AI Summary Service")


@app.get("/")
def root():
    return {"status": "LMS AI Service is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


class SummaryRequest(BaseModel):
    moduleId: str
    moduleFile: str


class SummaryResponse(BaseModel):
    moduleId: str
    summary: str


@app.post("/summary", response_model=SummaryResponse)
def summary(request: SummaryRequest):
    try:
        text = get_video_summary(request.moduleId, request.moduleFile)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary failed: {str(e)}")
    return SummaryResponse(moduleId=request.moduleId, summary=text)
