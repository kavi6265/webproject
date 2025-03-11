from flask import Flask, render_template, request, redirect, url_for, flash, Response
import cv2
import numpy as np
import mysql.connector
from datetime import datetime, timedelta
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
app.secret_key = 'your_secret_key'

def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='face_recognition'
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/index', methods=['GET', 'POST'])
def register_face():
    if request.method == 'POST':
        name = request.form['name']
        video_capture = cv2.VideoCapture(0)
        ret, frame = video_capture.read()
        video_capture.release()

        if not ret:
            flash('Failed to capture face, try again.', 'error')
            return redirect(url_for('register_face'))

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        facedetect = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = facedetect.detectMultiScale(gray, 1.3, 5)

        if len(faces) == 0:
            flash('No face detected, try again.', 'error')
            return redirect(url_for('register_face'))

        (x, y, w, h) = faces[0]
        crop_img = frame[y:y + h, x:x + w, :]
        resized_img = cv2.resize(crop_img, (50, 50))
        face_data = resized_img.flatten().tobytes()

        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("INSERT INTO faces (name, face_data, attendance_status, attendance_time) VALUES (%s, %s, %s, %s)", (name, face_data, 'Absent', None))
        connection.commit()
        cursor.close()
        connection.close()
        flash(f'Face registered for {name}', 'success')
        return redirect(url_for('mark_attendance'))

    return render_template('mark.html')

@app.route('/mark', methods=['GET', 'POST'])
def mark_attendance():
    if request.method == 'POST':
        video_capture = cv2.VideoCapture(0)
        ret, frame = video_capture.read()
        video_capture.release()

        if not ret:
            flash('Failed to capture face, try again.', 'error')
            return redirect(url_for('mark_attendance'))

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        facedetect = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = facedetect.detectMultiScale(gray, 1.3, 5)

        if len(faces) == 0:
            flash('No face detected, try again.', 'error')
            return redirect(url_for('mark_attendance'))

        (x, y, w, h) = faces[0]
        crop_img = frame[y:y + h, x:x + w, :]
        resized_img = cv2.resize(crop_img, (50, 50))
        face_data = resized_img.flatten().tobytes()

        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT id, name, face_data, attendance_time FROM faces")
        stored_faces = cursor.fetchall()

        recognized_name = None
        min_distance = float('inf')  # To track the minimum distance for face match

        for face_id, name, stored_face_data, attendance_time in stored_faces:
            stored_face_array = np.frombuffer(stored_face_data, dtype=np.uint8).reshape((50, 50, 3))
            # Calculate the cosine similarity between the captured face and stored face
            similarity = cosine_similarity([resized_img.flatten()], [stored_face_array.flatten()])[0][0]

            # Adjust threshold based on your accuracy requirement
            if similarity > 0.9:  # Consider this as a match if similarity > 0.9
                recognized_name = name
                break

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if recognized_name:
            # Check if attendance time is older than 24 hours
            if attendance_time:
                if isinstance(attendance_time, str):
                    attendance_time = datetime.strptime(attendance_time, "%Y-%m-%d %H:%M:%S")  # Convert string to datetime
            if isinstance(attendance_time, datetime) and (datetime.now() - attendance_time) > timedelta(hours=24):
                status = 'Absent'  # Mark as Absent if 24 hours have passed
            else:
                status = 'Present'
            cursor.execute("UPDATE faces SET attendance_status = %s, attendance_time = %s WHERE name = %s", (status, current_time, recognized_name))
            flash(f'Attendance marked for {recognized_name}', 'success')
        else:
            cursor.execute("INSERT INTO faces (name, face_data, attendance_status, attendance_time) VALUES (%s, %s, %s, %s)", ("Unknown", face_data, 'Absent', current_time))
            flash('Face not recognized. Marked as Absent.', 'error')

        connection.commit()
        cursor.close()
        connection.close()

    return render_template('mark.html')

@app.route('/attendance')
def view_attendance():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT name, attendance_status, attendance_time FROM faces")
    records = cursor.fetchall()
    cursor.close()
    connection.close()

    # Update attendance status if more than 24 hours have passed
    current_time = datetime.now()
    updated_records = []
    for record in records:
        name, status, attendance_time = record
        
        # Check if attendance_time is a string or datetime
        if attendance_time:
            if isinstance(attendance_time, str):
                attendance_time = datetime.strptime(attendance_time, "%Y-%m-%d %H:%M:%S")  # Convert string to datetime
            # If attendance_time is already a datetime, no conversion needed
            if isinstance(attendance_time, datetime) and (current_time - attendance_time) > timedelta(hours=24):
                status = 'Absent'
        
        updated_records.append((name, status, attendance_time))

    return render_template('attendance.html', records=updated_records)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def generate_frames():
    camera = cv2.VideoCapture(0)
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    camera.release()

if __name__ == '__main__':
    app.run(debug=True)
