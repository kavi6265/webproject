import streamlit as st
import pandas as pd
import time
from datetime import datetime

# Function to load and display the attendance data
def load_and_display():
    ts = time.time()
    date = datetime.fromtimestamp(ts).strftime("%d-%m-%Y")
    timestamp = datetime.fromtimestamp(ts).strftime("%H-%M-%S")

    # Read the attendance CSV file
    df = pd.read_csv(f"Attendance/Attendance_{date}.csv")

    # Display the dataframe and highlight the maximum value in each column
    st.dataframe(df.style.highlight_max(axis=0))

# Streamlit app
st.title("Attendance Dashboard")

# Create an empty container to hold the dataframe
container = st.empty()

# Set the refresh interval in seconds (e.g., 5 seconds)
refresh_interval = 5

# Loop to refresh the content periodically
while True:
    # Clear the previous dataframe and load the updated one
    with container:
        load_and_display()

    # Wait for the specified interval before refreshing the data
    time.sleep(refresh_interval)
