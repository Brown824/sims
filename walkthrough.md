# SIMS Phase 1: Architecture & Code Walkthrough

Welcome to the SIMS project! This guide explains exactly what we built in Phase 1, how the files are organized, and how they talk to each other. 

The project is split into two main parts:
1. **The Backend (`/backend`)**: The "brain" in the cloud that runs the AI model and talks to VirusTotal.
2. **The Mobile App (`/mobile-app`)**: The Android interface that the user sees and interacts with.

---

## 1. The Big Picture: How it works together

When an SMS arrives on the phone, the flow looks like this:

1. **Interception**: `mobile-app/src/services/smsInterceptor.js` detects the new SMS in the background.
2. **Network Check**: `mobile-app/src/utils/networkCheck.js` checks if the phone has internet.
3. **Inference (Online Mode)**: 
   - The app sends the SMS to the cloud via `mobile-app/src/services/api.js`.
   - The FastAPI server receives it at `backend/app/api/predict.py`.
   - The text goes to `backend/app/ml/preprocessor.py` to be cleaned and tokenized.
   - Any URLs are sent to `backend/app/services/virustotal.py` to check for malware.
   - The clean text is fed to the AI model in `backend/app/ml/model.py`.
   - The final verdict (SPAM/HAM) is returned to the phone.
4. **Alert**: If it's spam, the app triggers a push notification.

---

## 2. The Backend Files (`/backend`)

The backend is built with **FastAPI** (a modern, fast Python framework) and uses **Docker** for easy deployment.

### Core Application setup
*   **`requirements.txt`**: This lists every Python library the project needs (like `tensorflow`, `fastapi`, `pandas`). Running `pip install -r requirements.txt` downloads them all.
*   **`app/main.py`**: The entry point of the API. When the server starts, it runs the code here. It connects the routes (`/predict`, `/health`) to the web server and sets up CORS (security rules allowing the mobile app to talk to the backend).
*   **`app/config.py`**: The settings manager. It reads secret keys (like your VirusTotal API key) from the `.env` file so they aren't hardcoded in the source code.

### API Endpoints (The "Doors" to the server)
*   **`app/api/health.py`**: A simple endpoint that the mobile app pings to ask, *"Are you online?"*. If it replies "ok", the app knows it can use cloud ML; otherwise, it switches to the offline TFLite model.
*   **`app/api/predict.py`**: The most important file. It receives the SMS text, extracts URLs using Regex, runs the AI model, merges the AI score with the URL threat score, and makes the final decision (`SPAM`, `SUSPICIOUS`, or `HAM`).
*   **`app/api/feedback.py`**: Receives reports from users when the AI makes a mistake (e.g., flagging a real message as spam). It will save this to the database to retrain the model later.

### Machine Learning & Data (`app/ml/`)
*   **`app/ml/preprocessor.py`**: AI models can't read text; they only read numbers. This file takes Swahili/English text, cleans it, replaces slang (like "m-pesa" -> "mpesa"), and converts the words into an array of numbers (tokens) using BERT or a custom dictionary.
*   **`app/ml/model.py`**: This manages your CNN-GRU neural network. It has logic to load the `.h5` file from your hard drive, feed the number array into the neural network, and output a spam score between `0.0` and `1.0`.

### Services & Database
*   **`app/services/virustotal.py`**: Talks to the external VirusTotal API. It sends any URLs found in an SMS and waits to see if antivirus engines flag it as malicious.
*   **`app/db/database.py`**: A connection manager for MongoDB (for the final cloud version) or SQLite (for local testing).

### DevOps & Scripts
*   **`Dockerfile` & `docker-compose.yml`**: These files define an isolated "virtual computer" (container) that has exactly the right version of Linux, Python, and libraries to run your backend perfectly, no matter what PC you use it on.
*   **`scripts/validate_env.py`**: A handy script you can run on your terminal to check if you installed Python correctly and if all your folders are set up right.

---

## 3. The Mobile App Files (`/mobile-app`)

The mobile app uses **React Native** and **Expo**, meaning we write Javascript, and it turns into a real Android `.apk`.

### Configuration
*   **`package.json`**: Similar to `requirements.txt`, this lists the Javascript libraries needed (React, Expo, TensorFlow JS, navigation).
*   **`app.json`**: Expo configuration. This is where we tell Android that our app needs special permissions: `READ_SMS` and `RECEIVE_SMS`.

### UI Screens (`src/screens/`)
*   **`App.js`**: The main navigation file. It tells the app how to move between different screens.
*   **`HomeScreen.js`**: The dashboard showing recent scans and how much spam was blocked today.
*   **`DetailScreen.js`**: A detailed view of a single SMS, showing the raw text, the spam score, and the URL threat level.
*   **`ReportScreen.js`**: A form where the user can tell the system "This wasn't spam!" (which sends data to `backend/app/api/feedback.py`).
*   **`SettingsScreen.js`**: Toggles for push notifications and offline mode.

### App Logic (`src/services/` & `src/utils/`)
*   **`services/smsInterceptor.js`**: The background listener. Even if the app is closed, this file listens for incoming texts from the Android OS.
*   **`services/api.js`**: The network messenger. It uses `axios` to send HTTP requests to your FastAPI backend.
*   **`services/offlineModel.js`**: Your backup plan. If there is no internet, this file loads the `.tflite` model directly onto the phone's memory and calculates the spam score locally.
*   **`utils/networkCheck.js`**: A small utility that checks if Wi-Fi or mobile data is turned on.

---

## 4. Root Project Files

*   **`README.md`**: The front page of your project. It contains your technical blueprint, the architecture, and instructions on how to run the code.
*   **`.env.example`**: A template for your secret keys. You copy this to a file called `.env` (which stays hidden and is never uploaded to GitHub) and paste your actual database passwords and API keys inside.
*   **`.gitignore`**: Tells Git (version control) which files to ignore. For example, we tell it to ignore the `node_modules/` folder and `data/raw/` so we don't accidentally upload 500MB of raw datasets to GitHub.

---

> [!TIP]
> **Next Steps:**
> Now that the skeleton is built, our next job in Phase 2 is to write the actual Python code inside `backend/scripts/download_datasets.py` to download the 5 datasets, merge them together, and clean up the Swahili text to prepare it for the AI model!
