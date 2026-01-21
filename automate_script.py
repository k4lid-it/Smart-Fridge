import cv2
import os
import subprocess
import re
import firebase_admin
from firebase_admin import credentials, db, storage

# Function to capture photo from webcam and save it to a folder
def capture_photo():
    # Open webcam
    cap = cv2.VideoCapture(0)

    # Check if webcam opened successfully
    if not cap.isOpened():
        print("Error: Could not open webcam")
        return None

    # Read frame from webcam
    ret, frame = cap.read()

    # Release webcam
    cap.release()

    # Specify relative path for saving the image
    image_dir = "images_det"
    image_name = "photo.jpg"
    image_path = os.path.join(image_dir, image_name)

    # Create directory if it doesn't exist
    os.makedirs(image_dir, exist_ok=True)

    # Save frame as image file
    if ret:
        cv2.imwrite(image_path, frame)
        print("Photo captured and saved successfully:", image_path)
        return image_path
    else:
        print("Error: Failed to capture photo")
        return None
    
# Function to upload date to Firebase Realtime Database
def upload_date_to_database(image_name, date_str):
    ref = db.reference('dates')
    ref.push({
        'image_name': image_name,
        'date': date_str
    })
    print("Date uploaded to Firebase Realtime Database.")

# Function to upload image to Firebase Storage
def upload_image_to_storage(image_path):
    # Create a Cloud Storage client
    bucket = storage.bucket()

    # Define the destination path in Firebase Storage
    destination_blob_name = "images/" + os.path.basename(image_path)

    # Upload the image to Cloud Storage
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(image_path)

    # Get the public URL of the uploaded image
    image_url = blob.public_url
    
    # Print the URL for reference
    print("Image uploaded to Firebase Storage:", image_url)
    return image_url

# Initialize Firebase Admin SDK
cred = credentials.Certificate("smart-fridge-pro-firebase-adminsdk-pehwn-7dc13ff916.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'smart-fridge-pro.appspot.com',
    'databaseURL': 'https://smart-fridge-pro-default-rtdb.firebaseio.com/'
})

# Capture photo from webcam
image_path = capture_photo()

# Check if photo captured successfully
if image_path:
    # Run Detection
    detection_process = subprocess.run(["./run_detection.exe"])

    # Check if detection was successful
    if detection_process.returncode == 0:
        print("Detection process completed successfully.")
        
        # Run Recognition
        recognition_process = subprocess.run(["./run_recognition.exe"])

        # Check if recognition was successful
        if recognition_process.returncode == 0:
            print("Recognition process completed successfully.")

            # Parse Results
            results_file = "./results_rec/recognized dates.txt"
            dates_to_upload = []
            images_to_upload = []

            with open(results_file, "r") as file:
                for line in file:
                    date_match = re.search(r"\S+\.jpg: (\d{1,2} \d{1,2} \d{2,4})", line)
                    if date_match:
                        date_str = date_match.group(1)
                        dates_to_upload.append(date_str)

                    image_match = re.search(r"(\S+\.jpg)", line)
                    if image_match:
                        image_name = image_match.group(1)
                        images_to_upload.append(image_name)


            # Upload images mentioned in recognized dates.txt to Firebase Storage
            for image_name in images_to_upload:
                image_path = os.path.join("images_det", image_name)
                if os.path.exists(image_path):
                    upload_image_to_storage(image_path)
                else:
                    print(f"Error: Image file {image_name} not found.")

            # Upload dates mentioned in recognized dates.txt to Firebase Realtime Database
            for image_name, date_str in zip(images_to_upload, dates_to_upload):
                upload_date_to_database(image_name, date_str)

        else:
            print("Error: Recognition process failed.")
    else:
        print("Error: Detection process failed.")

