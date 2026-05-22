# LMS AI Summary Service — API Documentation

**Base URL:** `https://web-production-835b2.up.railway.app`

---

## Overview

This service accepts a video URL, extracts the audio, transcribes it using Groq Whisper, and returns an AI-generated summary of the lecture content.

Because video processing can take several minutes, the API uses an **async job pattern**:
1. Start a job → get a `jobId`
2. Poll with that `jobId` until the summary is ready

---

## Endpoints

### 1. Health Check

Check if the service is running.

**`GET /health`**

**Response**
```json
{
  "status": "ok"
}
```

---

### 2. Start Summary Job

Submit a video for transcription and summarization. Returns immediately with a `jobId`.

**`POST /summary/start`**

**Request Headers**
```
Content-Type: application/json
```

**Request Body**
| Field | Type | Required | Description |
|---|---|---|---|
| `moduleId` | string | Yes | Unique identifier for the module (used for caching) |
| `moduleFile` | string | Yes | Full URL to the video file (e.g. S3 URL) |

**Example Request**
```json
{
  "moduleId": "module_123",
  "moduleFile": "https://your-bucket.s3.amazonaws.com/videos/lecture1.mp4"
}
```

**Example Response** `200 OK`
```json
{
  "jobId": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "processing"
}
```

---

### 3. Poll Job Status

Check the status of a summary job. Keep polling until `status` is `"done"` or `"error"`.

**`GET /summary/status/{jobId}`**

**Path Parameter**
| Parameter | Type | Description |
|---|---|---|
| `jobId` | string | The `jobId` returned from `/summary/start` |

**Response Fields**
| Field | Type | Description |
|---|---|---|
| `status` | string | `"processing"` / `"done"` / `"error"` |
| `summary` | string or null | The generated summary (present when `status` is `"done"`) |
| `error` | string or null | Error message (present when `status` is `"error"`) |

**Example — Still Processing**
```json
{
  "status": "processing",
  "summary": null,
  "error": null
}
```

**Example — Done**
```json
{
  "status": "done",
  "summary": "This lecture covers the fundamentals of machine learning...",
  "error": null
}
```

**Example — Error**
```json
{
  "status": "error",
  "summary": null,
  "error": "ffmpeg error: unable to open input stream"
}
```

**`404 Not Found`** — returned if the `jobId` does not exist
```json
{
  "detail": "Job not found"
}
```

---

## Complete Flow Example

### JavaScript / React Native

```javascript
const BASE_URL = "https://web-production-835b2.up.railway.app";

async function getVideoSummary(moduleId, moduleFileUrl) {
  // Step 1: Start the job
  const startRes = await fetch(`${BASE_URL}/summary/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ moduleId, moduleFile: moduleFileUrl }),
  });

  const { jobId } = await startRes.json();

  // Step 2: Poll every 4 seconds until done
  while (true) {
    await new Promise((r) => setTimeout(r, 4000));

    const pollRes = await fetch(`${BASE_URL}/summary/status/${jobId}`);
    const job = await pollRes.json();

    if (job.status === "done") return job.summary;
    if (job.status === "error") throw new Error(job.error);
  }
}
```

### Python

```python
import time
import requests

BASE_URL = "https://web-production-835b2.up.railway.app"

def get_video_summary(module_id: str, module_file_url: str) -> str:
    # Step 1: Start the job
    res = requests.post(f"{BASE_URL}/summary/start", json={
        "moduleId": module_id,
        "moduleFile": module_file_url,
    })
    job_id = res.json()["jobId"]

    # Step 2: Poll every 4 seconds until done
    while True:
        time.sleep(4)
        poll = requests.get(f"{BASE_URL}/summary/status/{job_id}").json()

        if poll["status"] == "done":
            return poll["summary"]
        if poll["status"] == "error":
            raise Exception(poll["error"])
```

### cURL

```bash
# Step 1: Start job
curl -X POST https://web-production-835b2.up.railway.app/summary/start \
  -H "Content-Type: application/json" \
  -d '{"moduleId": "module_123", "moduleFile": "https://your-bucket.s3.amazonaws.com/video.mp4"}'

# Step 2: Poll status (replace JOB_ID with value from step 1)
curl https://web-production-835b2.up.railway.app/summary/status/JOB_ID
```

---

## Notes

- **Supported video formats:** Any format supported by ffmpeg (mp4, mkv, avi, mov, webm, etc.)
- **Recommended max video length:** 45 minutes (longer videos may exceed the 25MB Whisper API limit)
- **Caching:** Summaries are cached by `moduleId`. Sending the same `moduleId` again returns the cached result instantly without reprocessing the video.
- **Polling interval:** Recommend polling every 4 seconds. A 45-minute video typically takes 2–5 minutes to process.
- **Timeout:** Stop polling after 10 minutes if no result — the job likely failed silently.
