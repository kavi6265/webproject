from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
import mysql.connector
import re
import cv2
import numpy as np
from datetime import datetime, timedelta
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)

app.secret_key = 'xyzsdfg'

# MySQL connection for both users_db and face_recognition_db using mysql.connector
def get_db_connection(db_name):
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database=db_name  # Specify the database name dynamically
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        flash('Database connection error. Please try again later.', 'error')
        return None

# Route to the login page
@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        
        # Connect to the 'users_db' to authenticate
        connection = get_db_connection('users_db')  # Connect to users_db
        if connection is None:
            return redirect(url_for('login'))

        cursor = connection.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE email = %s AND password = %s', (email, password))
        user = cursor.fetchone()
        cursor.close()
        connection.close()

        if user:
            session['loggedin'] = True
            session['id'] = user['id']
            session['email'] = user['email']
            session['password'] = user['password']
            message = 'Logged in successfully!'
            return render_template('welcome.html', message=message)
        else:
            message = 'Please enter correct email/password!'
    return render_template('login.html', message=message)

# Route for user profile management
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'loggedin' in session:
        user_id = session['id']
        
        # Connect to the 'users_db' to fetch user data
        connection = get_db_connection('users_db')  # Connect to users_db
        if connection is None:
            return redirect(url_for('login'))

        cursor = connection.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()

        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            cursor.execute('UPDATE users SET username = %s, email = %s WHERE id = %s', (name, email, user_id))
            connection.commit()

            session['name'] = name
            session['email'] = email

            message = "Profile updated successfully!"
            cursor.close()
            connection.close()
            return render_template('profile.html', user=user, message=message)
        
        cursor.close()
        connection.close()
        return render_template('profile.html', user=user)

    return redirect(url_for('login'))

@app.route('/welcome')
def welcome():
    return render_template('welcome.html')

# Route to logout
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('email', None)
    return redirect(url_for('login'))

# Route to register a new user
@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ''
    if request.method == 'POST' and 'name' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['name']
        password = request.form['password']
        email = request.form['email']
        
        # Connect to 'users_db' to check if the email already exists
        connection = get_db_connection('users_db')  # Connect to users_db
        if connection is None:
            return redirect(url_for('register'))

        cursor = connection.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        account = cursor.fetchone()
        
        if account:
            message = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            message = 'Invalid email address!'
        elif not username or not password or not email:
            message = 'Please fill out the form!'
        else:
            cursor.execute('INSERT INTO users VALUES (NULL, %s, %s, %s)', (username, email, password))
            connection.commit()
            message = 'You have successfully registered!'
        cursor.close()
        connection.close()
        return render_template('welcome.html', message=message)
    
    return render_template('register.html', message=message)

# Route to register a face for face recognition
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

        # Connect to 'face_recognition_db' to save the face data
        connection = get_db_connection('face_recognition')  # Connect to face_recognition_db
        if connection is None:
            return redirect(url_for('register_face'))

        cursor = connection.cursor()
        cursor.execute("INSERT INTO faces (name, face_data, attendance_status, attendance_time) VALUES (%s, %s, %s, %s)",
                       (name, face_data, 'Absent', None))
        connection.commit()
        cursor.close()
        flash(f'Face registered for {name}', 'success')
        return redirect(url_for('mark_attendance'))

    return render_template('index.html')

# Route to mark attendance using face recognition
@app.route('/mark_attendance', methods=['GET', 'POST'])
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

        # Connect to 'face_recognition_db' to check for face recognition and attendance
        connection = get_db_connection('face_recognition')  # Connect to face_recognition_db
        if connection is None:
            return redirect(url_for('mark_attendance'))

        cursor = connection.cursor()
        cursor.execute("SELECT id, name, face_data, attendance_time FROM faces")
        stored_faces = cursor.fetchall()

        recognized_name = None
        min_distance = float('inf')

        for face_id, name, stored_face_data, attendance_time in stored_faces:
            stored_face_array = np.frombuffer(stored_face_data, dtype=np.uint8).reshape((50, 50, 3))
            similarity = cosine_similarity([resized_img.flatten()], [stored_face_array.flatten()])[0][0]

            if similarity > 0.9:
                recognized_name = name
                break

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if recognized_name:
            if attendance_time:
                if isinstance(attendance_time, str):
                    attendance_time = datetime.strptime(attendance_time, "%Y-%m-%d %H:%M:%S")
            if isinstance(attendance_time, datetime) and (datetime.now() - attendance_time) > timedelta(hours=24):
                status = 'Absent'
            else:
                status = 'Present'
            cursor.execute("UPDATE faces SET attendance_status = %s, attendance_time = %s WHERE name = %s",
                           (status, current_time, recognized_name))
            flash(f'Attendance marked for {recognized_name}', 'success')
        else:
            cursor.execute("INSERT INTO faces (name, face_data, attendance_status, attendance_time) VALUES (%s, %s, %s, %s)",
                           ("Unknown", face_data, 'Absent', current_time))
            flash('Face not recognized. Marked as Absent.', 'error')

        connection.commit()
        cursor.close()

    return render_template('mark.html')

# Route to view attendance
@app.route('/attendance')
def view_attendance():
    try:
        connection = get_db_connection('face_recognition')  # Connect to face_recognition_db
        if connection is None:
            return redirect(url_for('attendance'))

        cursor = connection.cursor()
        cursor.execute("SELECT name, attendance_status, attendance_time FROM faces")
        records = cursor.fetchall()
        cursor.close()

        current_time = datetime.now()
        updated_records = []

        for record in records:
            name, status, attendance_time = record

            if attendance_time:
                if isinstance(attendance_time, str):
                    attendance_time = datetime.strptime(attendance_time, "%Y-%m-%d %H:%M:%S")
                if isinstance(attendance_time, datetime) and (current_time - attendance_time) > timedelta(hours=24):
                    status = 'Absent'
            else:
                status = 'Absent'  # Default to Absent if no attendance time is found

            updated_records.append((name, status, attendance_time))

        return render_template('attendance.html', records=updated_records)

    except Exception as e:
        # Log the error and show an error message
        print(f"Error while fetching attendance: {e}")
        flash('There was an error fetching attendance data.', 'error')
        return render_template('attendance.html', records=[])

# Route to stream video feed (used in face recognition)
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Function to generate frames for video feed
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
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r')

if __name__ == "__main__":
    app.run(debug=True)
