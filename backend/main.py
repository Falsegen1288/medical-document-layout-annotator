import os
import json
import uuid
import asyncio
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import shutil

from backend.pipeline import run_pipeline, sessions_progress

app = FastAPI(title="Layout Annotator API")

# Configure CORS so Vite frontend on port 3000/5173 can query the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In development, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

class SaveRequest(BaseModel):
    pages_data: dict # Maps string page numbers to PageData models

@app.post("/api/session/start")
async def start_session(
    background_tasks: BackgroundTasks,
    pdf: UploadFile = File(...),
    pages: str = Form(...) # comma-separated and/or ranges (e.g. "1-5,7,15-20")
):
    # 1. Generate unique session ID
    session_id = str(uuid.uuid4())
    session_dir = os.path.join(UPLOAD_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    # 2. Save uploaded files
    pdf_path = os.path.join(session_dir, pdf.filename)
    
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(pdf.file, buffer)
        
    # 4. Parse page numbers
    parsed_pages = parse_page_numbers(pages)
    if not parsed_pages:
        raise HTTPException(status_code=400, detail="Invalid page numbers input format.")
        
    # 5. Launch pipeline background task
    background_tasks.add_task(
        run_pipeline,
        session_id=session_id,
        pdf_path=pdf_path,
        pages=parsed_pages,
        output_dir=session_dir
    )
    
    return {
        "session_id": session_id,
        "models_found": ["DocLayoutYOLO", "Nemotron-Parse-v1.1", "ADE-DPT2"],
        "pages": parsed_pages,
        "landing_ai_key_detected": os.environ.get("LANDING_AI_API_KEY") is not None
    }

@app.get("/api/session/{session_id}/status")
async def get_status_stream(session_id: str):
    """
    SSE stream endpoint pushing pipeline progress in real-time to the frontend.
    """
    if session_id not in sessions_progress:
        sessions_progress[session_id] = []
        
    async def event_generator():
        last_idx = 0
        while True:
            # Yield any new progress logs
            if last_idx < len(sessions_progress[session_id]):
                for i in range(last_idx, len(sessions_progress[session_id])):
                    data = sessions_progress[session_id][i]
                    yield f"data: {json.dumps(data)}\n\n"
                    
                    if data.get("step") in ["complete", "error"]:
                        return
                last_idx = len(sessions_progress[session_id])
                
            await asyncio.sleep(0.5)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/session/{session_id}/data")
async def get_session_data(session_id: str):
    session_file = os.path.join(UPLOAD_DIR, session_id, "annotation_input.json")
    if not os.path.exists(session_file):
        raise HTTPException(status_code=404, detail="Session layout data not found or still processing.")
        
    with open(session_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

@app.post("/api/session/{session_id}/save")
async def save_session_data(session_id: str, request: SaveRequest):
    session_file = os.path.join(UPLOAD_DIR, session_id, "annotation_input.json")
    if not os.path.exists(session_file):
        raise HTTPException(status_code=404, detail="Session does not exist.")
        
    try:
        # We merge/update the ground_truth edits into the stored file on disk
        with open(session_file, "r", encoding="utf-8") as f:
            stored_data = json.load(f)
            
        for page_str, page_val in request.pages_data.items():
            if page_str in stored_data:
                # Update ground_truth field
                stored_data[page_str]["ground_truth"] = page_val.get("ground_truth")
                
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(stored_data, f, indent=2)
            
        return {"status": "success", "message": "Ground truth saved successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save ground truth: {e}")

@app.get("/api/images/{session_id}/{filename}")
async def serve_image(session_id: str, filename: str):
    image_path = os.path.join(UPLOAD_DIR, session_id, filename)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found.")
    return FileResponse(image_path)

@app.get("/api/session/{session_id}/export")
async def export_ground_truth(session_id: str):
    session_file = os.path.join(UPLOAD_DIR, session_id, "annotation_input.json")
    if not os.path.exists(session_file):
        raise HTTPException(status_code=404, detail="Session does not exist.")
        
    with open(session_file, "r", encoding="utf-8") as f:
        stored_data = json.load(f)
        
    output = {}
    for page_str, page_val in stored_data.items():
        output[page_str] = page_val.get("ground_truth")
        
    return output

@app.delete("/api/session/{session_id}")
async def reset_session(session_id: str):
    """
    Top-bar 'New Session' triggers session clearing: deletes the session temp folder
    and removes progress tracking.
    """
    session_dir = os.path.join(UPLOAD_DIR, session_id)
    if os.path.exists(session_dir):
        shutil.rmtree(session_dir)
    if session_id in sessions_progress:
        del sessions_progress[session_id]
    return {"status": "success", "message": f"Session {session_id} deleted."}

def parse_page_numbers(pages_input: str) -> List[int]:
    """
    Parse a comma-separated list of page numbers and/or ranges.
    Example: '1-3, 5, 7-10' -> [1, 2, 3, 5, 7, 8, 9, 10]
    """
    pages = set()
    cleaned = pages_input.replace(" ", "")
    parts = cleaned.split(",")
    
    for part in parts:
        if not part:
            continue
        if "-" in part:
            try:
                start, end = map(int, part.split("-"))
                if start <= end:
                    pages.update(range(start, end + 1))
            except ValueError:
                pass
        else:
            try:
                pages.add(int(part))
            except ValueError:
                pass
                
    return sorted(list(pages))
