
from flask import Flask, render_template, request, redirect, url_for, flash, session, render_template_string, send_file, Response
import mysql.connector
import re
import cv2
import numpy as np
from datetime import datetime, timedelta
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
##from sklearn.metrics.pairwise import cosine_similarity
import bcrypt  
import uuid;
##import base64
##from PIL import Image
##import io
##import tempfile
##import imghdr
import face_recognition  # Add this to the top

import os

app = Flask(__name__)
app.secret_key = 'xyzsdfg' 

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'akavi6265@gmail.com'
app.config['MAIL_PASSWORD'] = 'gxgs sloy wlpb yiwz'  # Store in environment variable

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)

TOTAL_DAYS = 150  

def get_db_connection(db_name):
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database=db_name
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        flash('Database connection error. Please try again later.', 'error')
        return None

def close_db_connection(connection): 
    if connection:
        connection.close()

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']

        connection = get_db_connection('users_db')
        if connection is None:
            return redirect(url_for('login'))

        cursor = connection.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        cursor.close()
        close_db_connection(connection)

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):  
            session['loggedin'] = True
            session['id'] = user['id']
            session['email'] = user['email']
            message = 'Logged in successfully!'
            return render_template('welcome.html', message=message)
        else:
            message = 'Please enter correct email/password!'
    return render_template('login.html', message=message)


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'loggedin' in session:
        user_id = session['id']

        connection = get_db_connection('users_db')
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
            close_db_connection(connection)
            return render_template('profile.html', user=user, message=message)

        cursor.close()
        close_db_connection(connection)
        return render_template('profile.html', user=user)

    return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('email', None)
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ''

    if request.method == 'POST' and all(key in request.form for key in ['username', 'email', 'password']):
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']  

        connection = get_db_connection('users_db')
        if connection is None:
            message = 'Database connection failed!'
            return render_template('register.html', message=message)

        cursor = connection.cursor(dictionary=True)

        # Check if username or email already exists
        cursor.execute('SELECT * FROM users WHERE username = %s OR email = %s LIMIT 1', (username, email))
        account = cursor.fetchone()

        if account:
            if account['username'] == username:
                message = 'Username already taken!'
            elif account['email'] == email:
                message = 'Email already taken!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            message = 'Invalid email address!'
        elif not username or not password or not email:
            message = 'Please fill out the form!'
        else:
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute(
                'INSERT INTO users (username, email, password) VALUES (%s, %s, %s)',
                (username, email, hashed_password)  
            )
            connection.commit()
            message = 'You have successfully registered!'

        cursor.close()
        close_db_connection(connection)

    return render_template('register.html', message=message)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    message = ''
    if request.method == 'POST':
        email = request.form['email']
        connection = get_db_connection('users_db')
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        close_db_connection(connection)

        if user:
            token = serializer.dumps(email, salt='password-reset-salt')
            reset_url = url_for('reset_with_token', token=token, _external=True)
            print("Reset Url:", reset_url)
            try:
                msg = Message('Password Reset Request', sender='akavi6265@gmail.com', recipients=[email])
                msg.body = f"To reset your password, click the link: {reset_url}"
                mail.send(msg)
                flash('Password reset link sent to your email!', 'info')
            except Exception as e:
                print("Email error:", e)
                flash('Failed to send email. Please try again.', 'error')
        else:
            message = 'Email not found!'

    return render_template('forgot_password.html', message=message)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_with_token(token):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)
        email = email.strip().lower()
        print("Decoded email:", email)
    except Exception:
        flash('The reset link is invalid or has expired.', 'error')
        return redirect(url_for('forgot_password'))

    message = ''

    if request.method == 'POST':
        new_password = request.form['password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            message = 'Passwords do not match!'
        else:
            connection = get_db_connection('users_db')
            if connection is None:
                flash("Database connection failed!", 'error')
                return redirect(url_for('login'))

            cursor = connection.cursor()
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute("UPDATE users SET password = %s WHERE email = %s", (hashed_password, email))
            print("Rows affected:", cursor.rowcount)  
            connection.commit()
            cursor.close()
            close_db_connection(connection)

            if cursor.rowcount == 0:
                message = 'Password update failed. Email not found.'
            else:
                flash('Password has been reset successfully. Please log in.', 'success')
                return redirect(url_for('login'))

    return render_template('reset_password.html', message=message)

@app.route('/welcome') 
def welcome():
   
    connection = get_db_connection('face_recognition')
    cursor = connection.cursor(dictionary=True)

    # Safely fetch attendance data
    cursor.execute("""
        SELECT date,
               COALESCE(SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END), 0) AS present_count,
               COALESCE(SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END), 0) AS absent_count
        FROM attendance_records
        GROUP BY date
        ORDER BY date
    """)    
    rows = cursor.fetchall()
    cursor.close()
    close_db_connection(connection)

    dates = [row['date'].strftime("%Y-%m-%d") if row['date'] else "" for row in rows]
    present_counts = [row['present_count'] or 0 for row in rows]
    absent_counts = [row['absent_count'] or 0 for row in rows]

    return render_template('welcome.html',
                           dates=dates,
                           present_counts=present_counts,
                           absent_counts=absent_counts)


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

        rgb_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_img)
        face_encodings = face_recognition.face_encodings(rgb_img, face_locations)

        if len(face_encodings) == 0:
            flash('No face detected, try again.', 'error')
            return redirect(url_for('register_face'))

        face_encoding = face_encodings[0]

        connection = get_db_connection('face_recognition')
        if connection is None:
            flash('Database connection failed.', 'error')
            return redirect(url_for('register_face'))

        cursor = connection.cursor()
        cursor.execute("SELECT face_data, name FROM faces")
        existing_faces = cursor.fetchall()

        for row in existing_faces:
            existing_encoding = np.frombuffer(row[0], dtype=np.float64)
            matches = face_recognition.compare_faces([existing_encoding], face_encoding, tolerance=0.5)
            if matches[0]:
                flash(f"Face already registered as '{row[1]}'.", 'warning')
                cursor.close()
                close_db_connection(connection)
                return redirect(url_for('register_face'))

        # No match, continue to save new face
        encoding_bytes = face_encoding.tobytes()
        unique_id = str(uuid.uuid4())
        filename = f"{unique_id}.jpg"
        image_folder = 'static/faces'
        os.makedirs(image_folder, exist_ok=True)
        image_path = os.path.join(image_folder, filename)
        db_image_path = f"static/faces/{filename}"
        cv2.imwrite(image_path, frame)

        cursor.execute("""
            INSERT INTO faces (unique_id, name, face_data, image_path, attendance_status, attendance_time, total_days, present_days)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (unique_id, name, encoding_bytes, db_image_path, 'Absent', None, TOTAL_DAYS, 0))
        connection.commit()
        cursor.close()
        close_db_connection(connection)

        flash(f'Face registered for {name}', 'success')
        return redirect(url_for('mark_attendance'))

    return render_template('index.html')



@app.route('/mark_attendance', methods=['GET', 'POST'])
def mark_attendance():
    if request.method == 'POST':
        video_capture = cv2.VideoCapture(0)
        ret, frame = video_capture.read()
        video_capture.release()

        if not ret:
            flash('Failed to capture face, try again.', 'error')
            return redirect(url_for('mark_attendance'))

        rgb_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_img)
        face_encodings = face_recognition.face_encodings(rgb_img, face_locations)

        if len(face_encodings) == 0:
            flash('No face detected, try again.', 'error')
            return redirect(url_for('mark_attendance'))

        input_encoding = face_encodings[0]
        connection = get_db_connection('face_recognition')
        if connection is None:
            flash("Database connection failed", "error")
            return redirect(url_for('mark_attendance'))

        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT unique_id, name, face_data, attendance_time, present_days FROM faces")
        stored_faces = cursor.fetchall()

        recognized_name = None
        recognized_unique_id = None
        current_time = datetime.now()

        for face in stored_faces:
            stored_encoding = np.frombuffer(face['face_data'], dtype=np.float64)
            match = face_recognition.compare_faces([stored_encoding], input_encoding)[0]
            distance = face_recognition.face_distance([stored_encoding], input_encoding)[0]

            if match and distance < 0.6:
                recognized_name = face['name']
                recognized_unique_id = face['unique_id']
                attendance_time = face['attendance_time']
                present_days = face['present_days']
                break

        if recognized_name and recognized_unique_id:
            cursor.execute("""
                SELECT status FROM leave_requests 
                WHERE name = %s AND leave_date = %s
            """, (recognized_unique_id, current_time.date()))
            leave_today = cursor.fetchone()

            if leave_today and leave_today['status'] == 'Approved':
                flash(f"{recognized_name}, you already marked attendance through approved leave request.", 'info')
            else:
                already_marked_today = False
                if attendance_time:
                    if isinstance(attendance_time, str):
                        attendance_time = datetime.strptime(attendance_time, "%Y-%m-%d %H:%M:%S")
                    if (current_time - attendance_time) < timedelta(hours=24):
                        already_marked_today = True

                if not already_marked_today:
                    present_days += 1
                    if present_days > TOTAL_DAYS:
                        present_days = 0
                    cursor.execute("""
                        UPDATE faces
                        SET attendance_status = %s, attendance_time = %s, present_days = %s
                        WHERE unique_id = %s
                    """, ('Present', current_time, present_days, recognized_unique_id))

                    cursor.execute("""
                        INSERT INTO attendance_records (face_unique_id, date, time, status)
                        VALUES (%s, %s, %s, %s)
                    """, (recognized_unique_id, current_time.date(), current_time.time(), 'Present'))

                    flash(f'Attendance marked for {recognized_name}', 'success')
                else:
                    flash(f'Attendance already marked within the last 24 hours for {recognized_name}', 'info')
        else:
            unknown_id = str(uuid.uuid4())
            unique_unknown_name = f"Unknown_{unknown_id[:8]}"
            cursor.execute("""
                INSERT INTO faces (unique_id, name, face_data, attendance_status, attendance_time, total_days, present_days)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (unknown_id, unique_unknown_name, input_encoding.tobytes(), 'Absent', current_time, TOTAL_DAYS, 0))
            cursor.execute("""
                INSERT INTO attendance_records (face_unique_id, date, time, status)
                VALUES (%s, %s, %s, %s)
            """, (unknown_id, current_time.date(), current_time.time(), 'Absent'))

            flash('Face not recognized. Marked as Absent.', 'error')

        connection.commit()
        cursor.close()
        close_db_connection(connection)

    return render_template('mark.html')


@app.route('/attendance',methods=['GET', 'POST'])
def view_attendance():
    try:
        connection = get_db_connection('face_recognition')
        if connection is None:
            return redirect(url_for('attendance'))

        cursor = connection.cursor()
        cursor.execute("""
            SELECT name, attendance_status, attendance_time, total_days, present_days, image_path
            FROM faces
        """)
        records = cursor.fetchall()
        cursor.close()
        close_db_connection(connection)

        current_time = datetime.now()
        updated_records = []

        for record in records:
            name, status, attendance_time, total_days_value, present_days, image_path = record

            if attendance_time:
                if isinstance(attendance_time, str):
                    attendance_time = datetime.strptime(attendance_time, "%Y-%m-%d %H:%M:%S")
                if isinstance(attendance_time, datetime) and (current_time - attendance_time) > timedelta(hours=24):
                    status = 'Absent'
            else:
                status = 'Absent'

            percentage = (present_days / total_days_value * 100) if total_days_value > 0 else 0

            relative_image_path = None
            if image_path and os.path.exists(image_path):
                relative_image_path = '/static/' + os.path.relpath(image_path, 'static').replace('\\', '/')

            updated_records.append((
                name, status, attendance_time, f"{percentage:.2f}%", relative_image_path
            ))

        return render_template('attendance.html', records=updated_records)

    except Exception as e:
        print(f"Error while fetching attendance: {e}")
        flash('There was an error fetching attendance data.', 'error')
        return render_template('attendance.html', records=[])



@app.route('/attendance_history', methods=['GET', 'POST'])
def attendance_history():
    connection = get_db_connection('face_recognition')
    if connection is None:
        flash("Failed to connect to database.", "error")
        return render_template("attendance_history.html", records=[])

    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT ar.id, f.name, ar.date, ar.time, ar.status
        FROM attendance_records ar
        JOIN faces f ON ar.face_unique_id = f.unique_id
        ORDER BY ar.date DESC, ar.time DESC
    """)
    records = cursor.fetchall()

    cursor.close()
    close_db_connection(connection)
    return render_template('attendance_history.html', records=records)



@app.route('/request_leave', methods=['GET', 'POST'])
def request_leave():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    message = ''
    if request.method == 'POST':
        name = request.form['name']
        leave_date = request.form['leave_date']
        reason = request.form['reason']
        student_email = request.form['email']
        student_id = session['id']

        connection = get_db_connection('face_recognition')
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM faces WHERE name = %s", (name,))
        face_record = cursor.fetchone()

        if not face_record:
            message = "Name not found in Database. Please contact admin."
            cursor.close()
            close_db_connection(connection)
            return render_template('request_leave.html', message=message)

        cursor.execute("""
            INSERT INTO leave_requests (user_id, name, leave_date, reason, email)
            VALUES (%s, %s, %s, %s, %s)
        """, (student_id, name, leave_date, reason, student_email))
        leave_id = cursor.lastrowid
        connection.commit()

        approve_url = url_for('handle_leave_response', leave_id=leave_id, action='approve', _external=True)
        reject_url = url_for('handle_leave_response', leave_id=leave_id, action='reject', _external=True)

        try:
            msg = Message('Leave Request',
                          sender=app.config['MAIL_USERNAME'],
                          recipients=['akavi6266@gmail.com']) 

            msg.body = f"""
            Leave Request from: {name} ({student_email})
            Date: {leave_date}
            Reason: {reason}

            Approve: {approve_url}
            Reject: {reject_url}
            """
            mail.send(msg)
            message = 'Leave request sent to class teacher!'
        except Exception as e:
            print("Email error:", e)
            message = 'Failed to send email.'

        cursor.close()
        close_db_connection(connection)

    return render_template('request_leave.html', message=message)





@app.route('/handle_leave_response/<int:leave_id>/<action>')
def handle_leave_response(leave_id, action):
    action = action.lower()
    if action not in ['approve', 'reject']:
        return "Invalid action."

    connection = get_db_connection('face_recognition')
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM leave_requests WHERE id = %s", (leave_id,))
    leave = cursor.fetchone()

    if not leave:
        cursor.close()
        close_db_connection(connection)
        return "Leave request not found."

    if leave['status'] != 'Pending':
        cursor.close()
        close_db_connection(connection)
        return f"Leave already {leave['status']}."

    status = 'Approved' if action == 'approve' else 'Rejected'
    cursor.execute("UPDATE leave_requests SET status = %s WHERE id = %s", (status, leave_id))

    student_email = leave['email']
    try:
        msg = Message(f"Your Leave Request is {status}",
                      sender=app.config['MAIL_USERNAME'],
                      recipients=[student_email])
        msg.body = f"""
        Dear Student,

        Your leave request for the date {leave['leave_date']} has been {status}.

        Reason: {leave['reason']}

        Regards,
        Your School Admin
        """
        mail.send(msg)
    except Exception as e:
        print("Email error:", e)

    attendance_status = "Unknown"
    leave_date = leave['leave_date']
    leave_name = leave['name']

    cursor.execute("SELECT unique_id FROM faces WHERE name = %s", (leave_name,))
    face = cursor.fetchone()

    if face:
        unique_id = face['unique_id']
        attendance_status = 'Present' if action == 'approve' else 'Absent'

        cursor.execute("""
            INSERT INTO attendance_records (face_unique_id, date, time, status)
            VALUES (%s, %s, %s, %s)
        """, (unique_id, leave_date, datetime.now().time(), attendance_status))

        if attendance_status == 'Present':
            cursor.execute("""
                UPDATE faces SET present_days = present_days + 1 WHERE unique_id = %s
            """, (unique_id,))
    else:
        print(f"Face not found for name '{leave_name}'")

    connection.commit()
    cursor.close()
    close_db_connection(connection)

    return f"Leave {status.lower()} successfully. Attendance marked as {attendance_status}."








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
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r')

if __name__ == "__main__":
    app.run(debug=True)
