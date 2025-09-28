# 🏋️ Vitalis, your AI physio Coach (MVP)

## 🎯 Goal  

We aimed to build an **AI-powered osteopath assistant** that:  

- Lets you **upload a short video** of a squat or walk  
- Detects **movement/posture issues** using pose estimation  
- Provides **personalized recommendations**  
- Talks back to you via a **voice agent** (like ChatGPT’s voice mode)  
- Shows results through a **Beyond Presence avatar** for a human-like experience  

👉 The vision: **accessible, visual, and conversational coaching**, like having a physiotherapist guiding you in real time.  

---

## ✅ Current Status  

For now, only the **squat analysis** part works.  

It can already:  

- Extract **pose landmarks** from video (MediaPipe)  
- Detect issues:  
  - Heels off ground  
  - Excessive spine flexion  
  - Knees behind toes  
  - Squat depth  
- **Count reps** and flag “good depth” squats  
- Output:  
  - Processed video with overlays  
  - JSON report with detected issues  
  - Enriched JSON with recommendations from **Weaviate**  

🚧 The **avatar** still need to be connected to the voice agent  

---

## ⚙️ How It Works  

1. **Pose Estimation** → Landmarks with MediaPipe  
2. **Rule Checks** → Angles & distances detect issues  
3. **Rep Counter** → Down–up cycles logged  
4. **Video Output** → Skeleton + issue labels  
5. **JSON Report** → Issues with optional recommendations  

---

## 🚀 Quick Start  

### 1. Install dependencies  

```bash
#python -m venv .venv python=3.11.13
#source .venv/bin/activate   # Windows: .venv\Scripts\activate
conda create --name vitalis_env python=3.11.13
conda activate vitalis_env
pip install --upgrade pip
pip install -r requirements.txt
```
Install ffmpeg (needed for MP4 output):
	•	macOS: brew install ffmpeg
	•	Ubuntu/Debian: sudo apt-get install ffmpeg

⸻

2 Run the typescript from replit server
https://replit.com/@streguer/AnatomyServer

example of a proper squat
https://14b07126-a1dc-418b-901e-8b010fdb1dfb-00-2v701fzfy35au.kirk.replit.dev/


3 Run analysis on a video

Put a side-profile squat video in your folder (e.g., my_squat.mp4), then run:
```bash
python -c "from squat_analyser_v2_weaviate import SquatAnalyser; \
SquatAnalyser(mode=1, file_path='my_squat.mp4').process_frame(save_path='processed_video.mp4')"
```
This generates:
	•	processed_video.mp4 → video with skeleton overlay + issues
	•	squat_analysis_results.json → raw analysis
	•	squat_analysis_results_enriched_issues.json → (if Weaviate configured)

⸻

4. Select webcam on the tk GUI
- upload the video of your squat
- get the analysis

⸻

📂 Example Output

JSON Report
```
{
  "exercise": "squat",
  "total_squat": 3,
  "total_perfect_depth_squat": 1,
  "detected_issues": [
    {
      "issue_type": "heels_off_ground",
      "explanation_hint": "Heel rising relative to foot",
      "metric": {
        "baseline_heel_angle": 3.0,
        "current_heel_angle": 22.4
      }
    }
  ]
}
```

⸻

🛠️ Roadmap
	•	Squat analysis working
	•	Walking analysis
	•	Voice agent → speaks results after analysis
	•	Beyond Presence avatar → shows & speaks recommendations
	•	Export to PDF reports

⸻

⚠️ Disclaimer

This project is for educational and fitness support only.
It is not medical advice.

⸻

✨ Future versions will include the voice agent and avatar so the assistant can talk you through your squat results instead of just showing text.
