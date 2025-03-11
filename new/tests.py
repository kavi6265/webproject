import cv2
import pickle
import numpy as np
import os
from sklearn.neighbors import KNeighborsClassifier
import csv
import time
from datetime import datetime
from win32com.client import Dispatch

def speak(str1):
    speak = Dispatch(("SAPI.SpVoice"))
    speak.Speak(str1)
# Check if the files exist in the root directory
names_file = 'names.pkl'
faces_file = 'faces_data.pkl'


COL_NAMES=['NAMES','TIME']

# Check if the files exist
if not os.path.exists(names_file):
    print(f"File {names_file} not found. Please make sure the file exists in the root directory.")
    exit()

if not os.path.exists(faces_file):
    print(f"File {faces_file} not found. Please make sure the file exists in the root directory.")
    exit()

# Load the names and faces data
with open(names_file, 'rb') as f:
    LABELS = pickle.load(f)

with open(faces_file, 'rb') as f:
    FACES = pickle.load(f)

# Initialize webcam and face detector
video = cv2.VideoCapture(0)
facedetect = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

# Initialize KNN classifier
knn = KNeighborsClassifier(n_neighbors=5)
knn.fit(FACES, LABELS)

# Load background image
imgbackground = cv2.imread('background.png')

# Check if the background image is loaded correctly
if imgbackground is None:
    print("Error: 'scanning.jpg' could not be loaded. Please make sure the file exists and is valid.")
    exit()

while True:
    ret, frame = video.read()
    if not ret:
        print("Error: Failed to capture frame from webcam.")
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = facedetect.detectMultiScale(gray, 1.3, 5)

    if len(faces) == 0:
        print("No faces detected in this frame.")
    
    for (x, y, w, h) in faces:
        crop_img = frame[y:y + h, x:x + w, :]
        resized_img = cv2.resize(crop_img, (50, 50)).flatten().reshape(1, -1)
        output = knn.predict(resized_img)
        ts=time.time()
        date=datetime.fromtimestamp(ts).strftime("%d-%m-%Y")
        timestamp=datetime.fromtimestamp(ts).strftime("%H-%M-%S")
        exist=os.path.isfile("Attendance/Attendance_" + date + ".csv")
        # Display the name on the frame
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 1)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (50, 50, 255), 2)
        cv2.rectangle(frame, (x, y - 40), (x + w, y), (50, 50, 255), -1)
        cv2.putText(frame, str(output[0]), (x, y - 15), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 1)
        attendance=[str(output[0]),str(timestamp)]
    # Resize the background to match the frame size
    imgbackground[162:162+480,55:55+640]=frame   # Show the final output
    cv2.imshow("Frame", imgbackground)
    
    # Press 'q' to stop the process
    k = cv2.waitKey(1)
    if k==ord('o'):
        speak("Attendance Taken..")
        time.sleep(5)
        if exist:
            with open("Attendance/Attendance_" + date + ".csv" ,"+a") as csvfile:
                writer=csv.writer(csvfile)
                writer.writerow(attendance)
            csvfile.close()
        else:
            with open("Attendance/Attendance_" + date + ".csv" ,"+a") as csvfile:
                writer=csv.writer(csvfile)
                writer.writerow(COL_NAMES)
                writer.writerow(attendance)
            csvfile.close()
    if k == ord('q'):
        break

video.release()
cv2.destroyAllWindows()
