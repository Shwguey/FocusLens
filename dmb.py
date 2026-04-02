import cv2
import mediapipe as mp
import time
import joblib
import numpy as np
from datetime import datetime
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

app = Flask(__name__)
# MySQL Connection Setup 
# format: mysql+mysqlconnector://username:password@localhost/db_name
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:password@localhost/focus_lens_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

#  Database Model for User Reports 
class UserReport(db.Model):
    __tablename__ = 'user_reports'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False) # Connected to React User ID
    status = db.Column(db.String(50))
    label = db.Column(db.Integer)
    avg_ear = db.Column(db.Float)
    distraction_ratio = db.Column(db.Float)
    session_duration = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.now)

# Create the table if it doesn't exist
with app.app_context():
    db.create_all()

# Load ML Model 
clf = joblib.load('focus_rf_model.pkl')
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True)

def get_dist(p1, p2):
    return np.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

@socketio.on('start_tracking')
def handle_tracking(data):
    user_id = data.get('user_id') # Receive User ID from React
    
    # Session Variables
    active_time = 0
    last_time = time.time()
    buffer = []
    dist_frames = 0
    total_frames = 0
    absent_frames = 0
    
    cap = cv2.VideoCapture(0)
    
    while cap.isOpened():
        delta = time.time() - last_time
        last_time = time.time()
        
        ret, frame = cap.read()
        if not ret: break
        
        results = face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        
        if results.multi_face_landmarks:
            active_time += delta
            total_frames += 1
            absent_frames = 0
            lm = results.multi_face_landmarks[0].landmark
            
            # Feature Extraction
            ear = (get_dist(lm[159], lm[145]) + get_dist(lm[386], lm[374])) / 2
            head_yaw = abs(get_dist(lm[1], lm[234]) - get_dist(lm[1], lm[454]))
            head_pitch = get_dist(lm[10], lm[152])
            
            is_distracted = (ear < 0.012 or head_yaw > 0.09 or head_pitch < 0.18)
            if is_distracted: dist_frames += 1
            
            buffer.append([ear, head_yaw, head_pitch, 0, 0])
            
            #Send update to React
            socketio.emit('status_update', {
                'status': 'DISTRACTED' if is_distracted else 'FOCUSED',
                'remaining': int(300 - active_time),
                'active_s': int(active_time)
            })
        else:
            absent_frames += 1
            if absent_frames > 35:
                socketio.emit('status_update', {'status': 'USER ABSENT', 'remaining': int(300 - active_time)})

        # Save to MySQL every 5 Minutes, make post request to backend
        if active_time >= 300:
            avg_feat = np.mean(buffer, axis=0)
            ratio = dist_frames / total_frames
            pred = 1 if ratio > 0.4 else int(clf.predict([avg_feat])[0])
            
            # save to MySQL
            new_report = UserReport(
                user_id=user_id,
                status="Distracted" if pred == 1 else "Focused",
                label=pred,
                avg_ear=round(avg_feat[0], 4),
                distraction_ratio=round(ratio, 4),
                session_duration="5m 0s"
            )
            
            with app.app_context():
                db.session.add(new_report)
                db.session.commit()
            
            # Reset
            active_time, buffer, dist_frames, total_frames = 0, [], 0, 0

    cap.release()

if __name__ == '__main__':
    socketio.run(app, port=5000, debug=True)