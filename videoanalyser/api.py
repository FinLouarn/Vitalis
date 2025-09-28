from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse
import shutil, os, json
from main import SquatAnalyser  # <-- ton code actuel

app = FastAPI()

UPLOAD_DIR = "uploads"
RESULTS_DIR = "results"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

@app.post("/analyze-squat/")
async def analyze_squat(file: UploadFile = File(...)):
    # Sauvegarde vidéo uploadée
    video_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Analyse
    analyser = SquatAnalyser(mode=1, file_path=video_path)
    output_video_path = os.path.join(RESULTS_DIR, f"processed_{file.filename}")
    analyser.process_frame(save_path=output_video_path)

    # Charger JSON enrichi
    json_path = "squat_analysis_results_enriched_issues.json"
    with open(json_path, "r") as f:
        analysis_data = json.load(f)

    return {
        "analysis": analysis_data,
        "processed_video": f"/download/{os.path.basename(output_video_path)}"
    }

@app.get("/download/{filename}")
async def download_video(filename: str):
    file_path = os.path.join(RESULTS_DIR, filename)
    return FileResponse(file_path, media_type="video/mp4", filename=filename)