import cv2
import pickle
import os
import numpy as np

# Initialize the webcam and face detector
video = cv2.VideoCapture(0)
facedetect = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

# List to store face data and labels (names)
faces_data = []
labels = []

i = 0
name = input("Enter Your Name: ")

while True:
    ret, frame = video.read()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = facedetect.detectMultiScale(gray, 1.3, 5)
    
    for (x, y, w, h) in faces:
        crop_img = frame[y:y + h, x:x + w, :]
        resized_img = cv2.resize(crop_img, (50, 50))
        faces_data.append(resized_img.flatten())  # Flatten to 1D array
        labels.append(name)  # Store the name label

        # Show the face with a rectangle
        cv2.rectangle(frame, (x, y), (x + w, y + h), (50, 50, 255), 1)
    
    cv2.imshow("Frame", frame)
    
    i += 1
    if i > 100:  # Collect 100 faces
        break

    # Press 'q' to stop the process
    k = cv2.waitKey(1)
    if k == ord('q'):
        break

# Convert faces_data and labels to numpy arrays
faces_data = np.array(faces_data)
labels = np.array(labels)

# Save faces_data and labels to pickle files
with open('faces_data.pkl', 'wb') as f:
    pickle.dump(faces_data, f)

with open('names.pkl', 'wb') as f:
    pickle.dump(labels, f)

video.release()
cv2.destroyAllWindows()

print("Data saved successfully.")
