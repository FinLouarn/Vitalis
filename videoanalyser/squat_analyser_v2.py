import tkinter as tk
from tkinter import filedialog
import threading
import mediapipe as mp
from mediapipe import solutions
import numpy as np
import cv2
from cv2 import VideoCapture, waitKey, imshow, CAP_PROP_FRAME_WIDTH, CAP_PROP_FRAME_HEIGHT, destroyAllWindows, COLOR_BGR2RGB, cvtColor
import json

mp_drawing = solutions.drawing_utils
mp_pose = solutions.pose

class SquatAnalyser():
    def __init__(self, *, mode: int, file_path: str = None):
        '''
            mode 0 -> Inbuilt Webcam
            mode 1 -> Video File
        '''
        if mode == 0:
            self.cap = VideoCapture(0)
        else:
            self.cap = VideoCapture(file_path)

        # Read the first frame to get original dimensions
        ret, frame = self.cap.read()
        if not ret:
            raise ValueError("Failed to read the first frame")

        original_height, original_width = frame.shape[:2]
        aspect_ratio = original_width / original_height
        new_width = int(900 * aspect_ratio)

        self.frame_width = new_width
        self.frame_height = 900
        self.frame_size = [self.frame_width, self.frame_height]
        
        self.joints = {} # Store relevant joint coordinates
        self.reps = 0 # Variable for counting repetitions
        self.initial_back_length = 0
        self.initial_heel_angle = 0
        self.stage = "up" # Initial position of SQUAT. Will be set to "down" when user goes parallel or below parallel to ground
        
        self.analysis_results = {
            "exercise": "squat",
            "total_squat": 0,
            "total_perfect_depth_squat": 0,
            "detected_issues": []
        }

        self.max_issues = {}

        self.good_reps = 0

        self.deep_squat_flag = False

    def initialise_bounds(self, shoulder, hip, heel, foot_index):
        left_upper_back_pixel = np.multiply(shoulder, self.frame_size)
        left_lower_back_pixel = np.multiply(hip, self.frame_size)
        self.initial_back_length = np.linalg.norm(left_upper_back_pixel-left_lower_back_pixel) # back length is not calculated from normalized coordinates 
        self.initial_heel_angle =  np.abs(180*np.arctan2(heel[1]-foot_index[1],heel[0]-foot_index[0])/np.pi)      
          
    def calculate_joint_angle(self, *, j1, j2, j3):
        '''
            Calculates angle between j1 j2 and j3
        '''
        v1 = np.array(j1-j2)
        v2 = np.array(j3-j2)
        cos_angle = np.dot(v1,v2)/(np.linalg.norm(v1)*np.linalg.norm(v2))
        radians = np.arccos(np.clip(cos_angle, -1, 1))
        angle = np.abs(radians*180.0/np.pi)
        if angle > 180:
            angle = 360 - angle
        return angle
    
    def back_slacking(self, image):
        upper_back = np.multiply(self.joints['shoulder'],self.frame_size)
        lower_back = np.multiply(self.joints['hip'],self.frame_size)
        distance = np.linalg.norm(upper_back - lower_back)
        mid_back = ((upper_back + lower_back)/2).astype(int)
        if distance+7< self.initial_back_length:
            cv2.circle(image, mid_back, 3, (22, 35, 219), -1)
            cv2.line(image, mid_back, [mid_back[0]+10, mid_back[1]-10], (255, 255, 255), 1, cv2.LINE_AA)
            cv2.line(image, [mid_back[0]+10, mid_back[1]-10], [mid_back[0]+60, mid_back[1]-10], (255, 255, 255), 1, cv2.LINE_AA)
            text = "Excessive Spine Flexion"
            position = (int(mid_back[0] + 60), int(mid_back[1] - 10))
            (text_width, text_height), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            rect_start = (position[0] - 5, position[1] - text_height - 5)
            rect_end = (position[0] + text_width + 5, position[1] + baseline + 5)
            cv2.rectangle(image, rect_start, rect_end, (0, 0, 0), cv2.FILLED)
            cv2.putText(image, text, position, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

            # Log issue
            self.log_issue(
                issue_type="excessive_spine_flexion",
                explanation_hint="Back rounding compared to upright posture",
                metric={
                    "baseline_back_length": float(self.initial_back_length),
                    "current_back_length": float(distance+7)
                }
            )

            return False
        return True
       
    def heels_off_ground(self, image):
        heel = self.joints['heel']
        foot_index = self.joints['foot index']
        radians = np.arctan2(heel[1]-foot_index[1], heel[0]-foot_index[0])
        angle = np.abs(radians*180/np.pi)
        if angle > self.initial_heel_angle + 3:
            mid = np.multiply(heel, self.frame_size).astype(int)
            cv2.circle(image, mid, 3, (22, 35, 219), -1)
            cv2.line(image, mid, [mid[0]+10, mid[1]-10], (255, 255, 255), 1, cv2.LINE_AA)
            cv2.line(image, [mid[0]+10, mid[1]-10], [mid[0]+60, mid[1]-10], (255, 255, 255), 1, cv2.LINE_AA)
            text = "Heels Off Ground"
            position = (int(mid[0] + 60), int(mid[1] - 10))
            (text_width, text_height), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            rect_start = (position[0] - 5, position[1] - text_height - 5)
            rect_end = (position[0] + text_width + 5, position[1] + baseline + 5)
            cv2.rectangle(image, rect_start, rect_end, (0, 0, 0), cv2.FILLED)
            cv2.putText(image, text, position, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

            # Log issue
            self.log_issue(
                issue_type="heels_off_ground",
                explanation_hint="Heel rising relative to foot",
                metric={
                    "baseline_heel_angle": float(self.initial_heel_angle+3),
                    "current_heel_angle": float(angle)
                }
            )
        
    def knee_over_toes(self, image):
        lower_back = self.joints['hip']
        knee = self.joints['knee']
        foot_index = self.joints['foot index']
        radians = np.arctan2(lower_back[1]-knee[1], lower_back[0]-knee[0])
        angle = np.abs(radians*180.0/np.pi)
        if angle < 44 and knee[0] > foot_index[0]:
            mid = np.multiply(knee, self.frame_size).astype(int)
            cv2.circle(image, mid, 3, (22, 35, 219), -1)
            cv2.line(image, mid, [mid[0]+10, mid[1]-10], (255, 255, 255), 1, cv2.LINE_AA)
            cv2.line(image, [mid[0]+10, mid[1]-10], [mid[0]+60, mid[1]-10], (255, 255, 255), 1, cv2.LINE_AA)
            text = "Knees Behind Toes"
            position = (int(mid[0] + 60), int(mid[1] - 10))
            (text_width, text_height), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            rect_start = (position[0] - 5, position[1] - text_height - 5)
            rect_end = (position[0] + text_width + 5, position[1] + baseline + 5)
            cv2.rectangle(image, rect_start, rect_end, (0, 0, 0), cv2.FILLED)
            cv2.putText(image, text, position, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

            # Log issue
            self.log_issue(
                issue_type="knees_behind_toes",
                explanation_hint="Knee positioned posterior to the toes",
                metric={
                    "baseline_knee_angle": 44.0,
                    "current_knee_angle": float(angle)
                }
            )

            return False
        else:
            return True
        
    def ensure_proper_depth(self, image):
        lower_back = self.joints['hip']
        knee = self.joints['knee']
        radians = np.arctan2(lower_back[1]-knee[1], lower_back[0]-knee[0])
        angle = np.abs(radians*180.0/np.pi)
        if angle < 20:
            text = "Awesome Depth"
            position = (10, 70)
            (text_width, text_height), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1, 1)
            rect_start = (position[0] - 5, position[1] - text_height - 5)
            rect_end = (position[0] + text_width + 5, position[1] + baseline + 5)
            cv2.rectangle(image, rect_start, rect_end, (0, 0, 0), cv2.FILLED)
            cv2.putText(image, text, position, cv2.FONT_HERSHEY_SIMPLEX, 1, (23, 185, 43), 1, cv2.LINE_AA)
            self.deep_squat_flag = True
            return True
        return False
      
    def show_reps_on_screen(self,image,knee_hip_angle):
        if(knee_hip_angle<25 and self.stage=="up"):
            self.stage = "down"
            self.deep_squat_flag = False
        elif(knee_hip_angle>30 and self.stage=="down"):
            self.reps+=1
            if getattr(self, "deep_squat_flag", False):
                self.good_reps += 1
            self.stage= "up"
        cv2.putText(image,"Reps: "+str(self.reps),(10,30),
                    cv2.FONT_HERSHEY_SIMPLEX,1,(255,255,255),2,cv2.LINE_AA)
          
    def draw_landmarks(self,image):
        #draw Circles on joints
        for joint in self.joints.values():
            cv2.circle(image,np.multiply(joint,self.frame_size).astype(int),3,(135, 53, 3),-1)
            cv2.circle(image,np.multiply(joint,self.frame_size).astype(int),6,(194, 99, 41),1)
        # draw lines between joints
        pairs = [['shoulder','hip'],['hip','knee'],['knee','ankle'],['heel','foot index'],['ankle','heel']]
        COLOR = (237, 185, 102)
        for pair in pairs:
            cv2.line(image,np.multiply(self.joints[pair[0]],self.frame_size).astype(int),
                     np.multiply(self.joints[pair[1]],self.frame_size).astype(int),COLOR,1,cv2.LINE_AA)
            
    def log_issue(self, issue_type, explanation_hint, metric):
        # Si le type d'erreur n'existe pas encore, on l'ajoute directement
        if issue_type not in self.max_issues:
            self.max_issues[issue_type] = {
                "issue_type": issue_type,
                "explanation_hint": explanation_hint,
                "metric": metric
            }
        else:
            # Sinon, on compare le metric principal et on garde le maximum
            # On prend comme "clé principale" le premier item de metric
            key = list(metric.keys())[1]  # ex: 'current_heel_angle'
            if metric[key] > self.max_issues[issue_type]["metric"][key]:
                self.max_issues[issue_type]["metric"] = metric
    
    def process_frame(self, save_path: str = None):
        if not self.cap.isOpened():
            print("Error opening video stream or file")
            return

        # Initialize MediaPipe Pose
        with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
            # Initialize VideoWriter if save_path is provided
            out = None
            if save_path:
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(save_path, fourcc, 30, (self.frame_width, self.frame_height))

            while self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret:
                    break

                # Resize frame
                original_height, original_width = frame.shape[:2]
                aspect_ratio = original_width / original_height
                new_width = int(900 * aspect_ratio)
                frame = cv2.resize(frame, (new_width, 900))
                image = cvtColor(frame, COLOR_BGR2RGB)
                results = pose.process(image)
                image = cvtColor(image, COLOR_BGR2RGB)

                if results.pose_landmarks:
                    landmarks = results.pose_landmarks.landmark
                    self.joints['shoulder'] = np.array([landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                                                        landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y])
                    self.joints['hip'] = np.array([landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x,
                                                landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y])
                    self.joints['knee'] = np.array([landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x,
                                                    landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y])
                    self.joints['ankle'] = np.array([landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x,
                                                    landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y])
                    self.joints['heel'] = np.array([landmarks[mp_pose.PoseLandmark.LEFT_HEEL.value].x,
                                                    landmarks[mp_pose.PoseLandmark.LEFT_HEEL.value].y])
                    self.joints['foot index'] = np.array([landmarks[mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value].x,
                                                        landmarks[mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value].y])

                    self.draw_landmarks(image)

                    if 167 < self.calculate_joint_angle(j1=self.joints['hip'], j2=self.joints['knee'], j3=self.joints['ankle']) < 180:
                        self.initialise_bounds(self.joints['shoulder'], self.joints['hip'], self.joints['heel'], self.joints['foot index'])

                    # Check form
                    self.back_slacking(image)
                    self.knee_over_toes(image)
                    self.heels_off_ground(image)
                    self.ensure_proper_depth(image)

                    # Rep counter
                    knee_hip_angle = np.abs(180*np.arctan2(self.joints['hip'][1]-self.joints['knee'][1],
                                                        self.joints['hip'][0]-self.joints['knee'][0])/np.pi)
                    self.show_reps_on_screen(image, knee_hip_angle)

                # Show frame
                imshow('Squat Analysis', image)

                # Write frame to output video
                if out:
                    out.write(image)

                if waitKey(10) & 0xFF == ord('q'):
                    break

            self.cap.release()
            if out:
                out.release()
            destroyAllWindows()

            # At the very end of process_frame, after releasing video
            self.analysis_results["detected_issues"] = list(self.max_issues.values())
            self.analysis_results["total_squat"] = self.reps
            self.analysis_results["total_perfect_depth_squat"] = self.good_reps
            with open("squat_analysis_results.json", "w") as f:
                json.dump(self.analysis_results, f, indent=2)


class SquatAnalyserApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Squat Analysis")
        self.root.geometry("300x150")
        
        self.label = tk.Label(root, text="Choose Input Method:")
        self.label.pack(pady=10)

        self.webcam_button = tk.Button(root, text="Webcam", command=self.start_webcam_analysis)
        self.webcam_button.pack(pady=5)

        self.video_button = tk.Button(root, text="Video File", command=self.choose_video_file)
        self.video_button.pack(pady=5)

    def start_webcam_analysis(self):
        analyser = SquatAnalyser(mode=0)
        threading.Thread(target=analyser.process_frame).start()

    def choose_video_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            save_path = filedialog.asksaveasfilename(defaultextension=".mp4",
                                                    filetypes=[("MP4 files", "*.mp4")])
            if save_path:
                analyser = SquatAnalyser(mode=1, file_path=file_path)
                threading.Thread(target=lambda: analyser.process_frame(save_path=save_path)).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = SquatAnalyserApp(root)
    root.mainloop()

"""def __init__(self, file_path: str):
        self.cap = cv2.VideoCapture(file_path)

        if not self.cap.isOpened():
            raise ValueError("Error opening video stream or file")"""
"""if __name__ == "__main__":
    video_path = "IMG_2250.MOV"
    analyser = SquatAnalyser(file_path=video_path)
    analyser.process_frame(save_path="processed_video.mp4")"""
