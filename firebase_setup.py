import os
from dotenv import load_dotenv
import pyrebase

# Load environment variables from .env file
load_dotenv()

firebaseConfig = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID"),
    "databaseURL": os.getenv("FIREBASE_DATABASE_URL"),
}

# Check if all required values are set
missing_configs = [key for key, value in firebaseConfig.items() if not value]
if missing_configs:
    print(f"WARNING: Missing Firebase configurations: {missing_configs}")

print("Initializing Firebase...")
print("Database URL:", os.getenv("FIREBASE_DATABASE_URL"))

firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()
db = firebase.database()