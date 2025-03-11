import cv2
import numpy as np
import mysql.connector
import time
from datetime import datetime
from win32com.client import Dispatch
from flask import Flask, render_template, Response, jsonify

app = Flask(__name__)

# Initialize speech synthesis
def speak(str1):
    speak = Dispatch(("SAPI.SpVoice"))
    speak.Speak(str1)

# Database connection setup
def get_db_connection():
    conn = mysql.connector.connect(
        host='localhost',
        user='root',  # Replace with your MySQL username
        password='',  # Replace with your MySQL password
        database='face_recognition'  # Replace with your database name
    )
    return conn

# Function to get stored faces from the database
def get_faces_from_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, face_data FROM faces")  # Select name and face data from the database
    faces = cursor.fetchall()
    cursor.close()
    conn.close()
    return faces

# Function to store a new face in the database
def store_face_in_db(name, face_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO faces (name, face_data) VALUES (%s, %s)", (name, face_data))
    conn.commit()
    cursor.close()
    conn.close()

# Function to store attendance in the database
def log_attendance(name, presence):
    current_date = datetime.now().date()
    current_time = datetime.now().time()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO attendance (name, date, time, presence) VALUES (%s, %s, %s, %s)",
        (name, current_date, current_time, presence)
    )
    conn.commit()
    cursor.close()
    conn.close()

# Function to compare a detected face with stored faces in the database
def compare_faces(detected_face, stored_face_data):
    # Convert the binary face data from the database to a numpy array
    stored_face = np.frombuffer(stored_face_data, dtype=np.uint8).reshape(50, 50, 3)  # Adjust shape if needed
    # Compare faces (this can be improved using real face recognition libraries)
    return np.array_equal(detected_face.flatten(), stored_face.flatten())

# Initialize webcam and face detector
video = cv2.VideoCapture(0)
facedetect = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

@app.route('/')
def index():
    return render_template('attend.html')  # Render your HTML page

# Function to take attendance and display name based on face recognition
@app.route('/take_attendance', methods=['POST','GET'])
def take_attendance():
    # Capture image from webcam
    ret, frame = video.read()
    if not ret:
        return jsonify({"status": "error", "message": "Error capturing frame"})

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = facedetect.detectMultiScale(gray, 1.3, 5)

    if len(faces) == 0:
        return jsonify({"status": "error", "message": "No face detected"})

    # Get stored faces from the database
    stored_faces = get_faces_from_db()

    if len(stored_faces) == 0:
        return jsonify({"status": "error", "message": "No faces stored in the database"})

    # Process the first detected face
    recognized_name = "Unknown"  # Default name if no match found
    for (x, y, w, h) in faces:
        crop_img = frame[y:y + h, x:x + w, :]
        resized_img = cv2.resize(crop_img, (50, 50)).flatten().reshape(1, -1)

        # Compare the detected face with the stored faces in the database
        for stored_face in stored_faces:
            face_data = stored_face[2]  # The face data (binary) from the database
            if compare_faces(resized_img, face_data):
                recognized_name = stored_face[1]  # The name from the database
                break  # Stop if a match is found

        # Draw rectangle around the face and display the name
        if recognized_name != "Unknown":
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)  # Green rectangle

            # Add name text with background for visibility
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 1
            color = (0, 255, 0)  # Green color for the text
            thickness = 2
            text = recognized_name

            # Get the size of the text
            (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)

            # Set the background rectangle
            text_x = x
            text_y = y - 10
            cv2.rectangle(frame, (text_x, text_y - text_height), (text_x + text_width, text_y + baseline), (0, 0, 0), -1)

            # Put the text on top of the rectangle
            cv2.putText(frame, text, (text_x, text_y), font, font_scale, color, thickness, lineType=cv2.LINE_AA)

            # Log attendance with presence as 'Present'
            log_attendance(recognized_name, 'Present')

            # Provide feedback to the user
            speak(f"Attendance taken for {recognized_name}")
            return jsonify({"status": "success", "name": recognized_name, "presence": "Present"})

    # If no face matched, log absence
    log_attendance("Unknown", 'Absent')
    return jsonify({"status": "error", "message": "Face not recognized"})

# Route to stream video feed
def generate_frames():
    while True:
        ret, frame = video.read()
        if not ret:
            break
        # Convert the frame to grayscale for face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = facedetect.detectMultiScale(gray, 1.3, 5)

        # Get stored faces from the database (moved here to ensure it's always fresh)
        stored_faces = get_faces_from_db()

        # Draw rectangles and names on the detected faces
        recognized_name = "Unknown"
        for (x, y, w, h) in faces:
            crop_img = frame[y:y + h, x:x + w, :]
            resized_img = cv2.resize(crop_img, (50, 50)).flatten().reshape(1, -1)

            # Compare the detected face with the stored faces in the database
            for stored_face in stored_faces:
                face_data = stored_face[2]  # The face data (binary) from the database
                if compare_faces(resized_img, face_data):
                    recognized_name = stored_face[1]  # The name from the database
                    break  # Stop if a match is found

            # Draw rectangle around the face
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)  # Green rectangle

            # Add name text with background for visibility
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 1
            color = (0, 255, 0)  # Green color for the text
            thickness = 2
            text = recognized_name

            # Get the size of the text
            (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)

            # Set the background rectangle
            text_x = x
            text_y = y - 10
            cv2.rectangle(frame, (text_x, text_y - text_height), (text_x + text_width, text_y + baseline), (0, 0, 0), -1)

            # Put the text on top of the rectangle
            cv2.putText(frame, text, (text_x, text_y), font, font_scale, color, thickness, lineType=cv2.LINE_AA)

        # Encode the frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(debug=True)
