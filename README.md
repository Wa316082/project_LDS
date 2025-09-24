# Legal Document Analyzer

A Streamlit-based web application that uses AI/ML to analyze legal documents, extract key information, classify clauses, and provide intelligent summaries. The application includes user authentication with Firebase and persistent sessions using cookies.

## Features

- 📄 **Document Upload**: Support for PDF and text files
- 🤖 **AI-Powered Analysis**: Automatic clause classification and summarization
- 🔍 **Information Extraction**: Extract important points, obligations, and dates
- 👤 **User Authentication**: Firebase-based login/registration system
- 💾 **Save Analyses**: Store and retrieve your document analyses
- 🍪 **Persistent Sessions**: Stay logged in across browser sessions
- 📱 **Responsive UI**: Clean, modern interface built with Streamlit

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Firebase project (for authentication)
- Git (for cloning the repository)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Wa316082/project_LDS.git
cd project_LDS
```

### 2. Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Required Packages

```bash
pip install -r requirements.txt
```

If you don't have a `requirements.txt` file, install the packages manually:

```bash
pip install streamlit
pip install streamlit-cookies-manager
pip install torch torchvision torchaudio
pip install transformers
pip install spacy
pip install pypdf2
pip install pyrebase4
pip install python-dateutil
pip install nltk
pip install scikit-learn
pip install pandas
pip install numpy
```

### 4. Install spaCy Language Model

```bash
python -m spacy download en_core_web_sm
```

### 5. Firebase Setup

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or use an existing one
3. Enable Authentication and choose "Email/Password" as a sign-in method
4. Go to Project Settings > General > Your apps
5. Add a web app and copy the Firebase configuration
6. Create/update `firebase_setup.py` with your Firebase credentials:

```python
import pyrebase

# Firebase configuration
config = {
    "apiKey": "your-api-key",
    "authDomain": "your-auth-domain",
    "projectId": "your-project-id",
    "storageBucket": "your-storage-bucket",
    "messagingSenderId": "your-messaging-sender-id",
    "appId": "your-app-id",
    "databaseURL": "your-database-url"  # Optional for Realtime Database
}

# Initialize Firebase
firebase = pyrebase.initialize_app(config)
auth = firebase.auth()
db = firebase.database()  # Optional for Realtime Database
```

### 6. Security Configuration

Update the cookie password in `cookie_manager.py`:

```python
# In cookie_manager.py, line ~12
password="your_secret_password_here_change_this_in_production"
```

Replace with a strong, unique password for production use.

## Running the Application

### Local Development

1. Make sure your virtual environment is activated
2. Navigate to the project directory
3. Run the Streamlit app:

```bash
streamlit run main.py
```

The application will open in your default web browser at `http://localhost:8501`

### Alternative Run Methods

```bash
# Run on a specific port
streamlit run main.py --server.port 8502

# Run and make accessible on network
streamlit run main.py --server.address 0.0.0.0

# Run with specific configuration
streamlit run main.py --server.maxUploadSize 200
```

## Project Structure

```
project-LDS/
│
├── main.py                 # Main Streamlit application
├── auth.py                 # Authentication logic
├── cookie_manager.py       # Cookie management for persistent sessions
├── firebase_setup.py       # Firebase configuration
├── models.py               # AI/ML model loading and management
├── nlp_utils.py           # NLP processing utilities
├── pdf_utils.py           # PDF processing utilities
├── save_analysis.py       # Save/load analysis functionality
├── document.txt           # Sample document
├── legal_doc.txt          # Sample legal document
├── tempCodeRunnerFile.py  # Temporary file
└── __pycache__/           # Python cache files
```

## Usage Instructions

### 1. First Time Setup
1. Start the application using `streamlit run main.py`
2. Navigate to "Login/Register" in the sidebar
3. Create a new account or login with existing credentials

### 2. Analyzing Documents
1. Go to "Analyze Document" page
2. Upload a PDF or text file containing legal content
3. Wait for the AI analysis to complete
4. Review the extracted information:
   - Document overview and metadata
   - Clause classification and summaries
   - Important points and obligations
   - Key dates and deadlines

### 3. Saving Analyses
1. After analyzing a document, click "Save Analysis to My Account"
2. Access saved analyses from "See Saved Files" in the sidebar
3. View, review, and manage your previous analyses

### 4. Session Management
- Your login session will persist across browser restarts
- Sessions automatically expire after 7 days
- Use the "Logout" button to manually end your session

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure all required packages are installed
   ```bash
   pip install -r requirements.txt
   ```

2. **Firebase Authentication Errors**: Check your Firebase configuration in `firebase_setup.py`

3. **Model Loading Issues**: Ensure spaCy model is installed:
   ```bash
   python -m spacy download en_core_web_sm
   ```

4. **Cookie Warnings**: Make sure you've removed any caching decorators from cookie manager functions

5. **PDF Upload Issues**: Verify PyPDF2 is installed and PDF files are not corrupted

### Performance Tips

- First run may take longer as AI models are downloaded and cached
- Larger documents will take more time to process
- Consider upgrading to a GPU-enabled environment for faster processing

## Development

### Adding New Features

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Environment Variables (Optional)

Create a `.env` file for sensitive configuration:

```env
FIREBASE_API_KEY=your_api_key
FIREBASE_AUTH_DOMAIN=your_auth_domain
COOKIE_PASSWORD=your_cookie_password
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review existing GitHub issues
3. Create a new issue with detailed information about your problem

## Contributing

Contributions are welcome! Please read the contributing guidelines and submit pull requests for any improvements.

---

**Note**: This application processes sensitive legal documents. Ensure you comply with your organization's data privacy and security policies when using this tool.
