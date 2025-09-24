# firebase_setup_template.py
# Copy this file to firebase_setup.py and fill in your Firebase credentials

import pyrebase

# Firebase configuration - Replace with your actual Firebase project credentials
# Get these from Firebase Console > Project Settings > General > Your apps > Config
config = {
    "apiKey": "your-api-key-here",
    "authDomain": "your-project-id.firebaseapp.com",
    "projectId": "your-project-id",
    "storageBucket": "your-project-id.appspot.com",
    "messagingSenderId": "your-messaging-sender-id",
    "appId": "your-app-id-here",
    "databaseURL": "https://your-project-id-default-rtdb.firebaseio.com/"  # Optional for Realtime Database
}

# Initialize Firebase
firebase = pyrebase.initialize_app(config)
auth = firebase.auth()
db = firebase.database()  # Optional for Realtime Database

# Instructions:
# 1. Go to Firebase Console (https://console.firebase.google.com/)
# 2. Create a new project or select existing project
# 3. Go to Authentication > Sign-in method > Email/Password > Enable
# 4. Go to Project Settings > General > Your apps
# 5. Add web app if you haven't already
# 6. Copy the configuration values and replace the placeholders above
# 7. Save this file as firebase_setup.py (remove _template from filename)
