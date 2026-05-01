# 🛡️ SIMS — SMS Intelligent Monitoring System

> **Bilingual (Swahili + English) spam & phishing detector for Tanzanian Android users**

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue)](https://python.org)
[![TensorFlow 2.x](https://img.shields.io/badge/TensorFlow-2.x-orange)](https://tensorflow.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green)](https://fastapi.tiangolo.com)
[![React Native](https://img.shields.io/badge/React_Native-Expo-blue)](https://expo.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## Overview

SIMS is a Final Year Project that detects SMS spam and phishing attacks targeting Tanzanian mobile users. It combines:

- 🤖 **Hybrid CNN-GRU neural network** trained on Swahili + English SMS datasets
- 🌐 **FastAPI cloud backend** with VirusTotal URL threat intelligence
- 📱 **React Native Android app** with real-time SMS interception
- 📡 **Offline-first design** — `.tflite` edge model works without internet

---

## Project Structure

```
sparm/
├── backend/                  # FastAPI Python backend
│   ├── app/
│   │   ├── api/              # Route handlers (predict, feedback, health)
│   │   ├── ml/               # Model loading & preprocessing
│   │   ├── services/         # VirusTotal, notifications
│   │   └── db/               # MongoDB / SQLite connection
│   ├── data/
│   │   ├── raw/              # Downloaded datasets (gitignored)
│   │   ├── processed/        # Cleaned master.csv (gitignored)
│   │   └── models/           # Trained .h5 and .tflite files
│   ├── scripts/              # Data download, training, validation
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── requirements.txt
├── mobile-app/               # React Native / Expo app
│   ├── src/
│   │   ├── screens/          # HomeScreen, DetailScreen, etc.
│   │   ├── services/         # API client, SMS interceptor, TFLite
│   │   └── utils/            # Network checker, storage helpers
│   └── package.json
├── .env.example              # Required environment variables
├── .gitignore
└── README.md
```

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **ML / AI** | TensorFlow 2.x, Keras, HuggingFace Transformers, TFLite, scikit-learn |
| **Backend** | FastAPI, Python 3.11, Uvicorn, Pydantic v2 |
| **Database** | MongoDB Atlas (cloud) / SQLite (local dev) |
| **Mobile** | React Native, Expo, TFLite React Native, expo-notifications |
| **DevOps** | Docker, Docker Hub, DigitalOcean, GitHub Actions |
| **APIs** | VirusTotal v3 |

---

## Quick Start

### Backend (Local)

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Copy and configure env
cp ../.env.example .env
# Edit .env with your API keys

# Run dev server
uvicorn app.main:app --reload --port 8000
```

### Backend (Docker)

```bash
cd backend
docker-compose up --build
```

### Mobile App

```bash
cd mobile-app
npm install
npx expo start
# Press 'a' to open on Android emulator
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/predict` | Classify SMS + scan URLs |
| `POST` | `/feedback` | Submit correction for retraining |
| `GET` | `/health` | Service health + model version |
| `POST` | `/retrain` | (Admin) Trigger retraining pipeline |

### Example: `/predict`

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"sms_text": "Umeshinda! Bonyeza hapa: http://scam.link", "phone_number": "+255712345678"}'
```

```json
{
  "spam_score": 0.94,
  "verdict": "SPAM",
  "url_threat": true,
  "confidence": "HIGH",
  "model_version": "1.0.0"
}
```

---

## Datasets

| Dataset | Source | Type |
|---------|--------|------|
| Swahili SMS Detection | github.com/patrick-paul/ssd | Tanzanian SMS |
| BongoScam Detection | github.com/Henryle-hd/BongoScamDetection | Swahili Scam |
| Mendeley SMS | data.mendeley.com/datasets/dzgt8z42fk/3 | Academic |
| Kaggle Swahili SMS | kaggle.com/datasets/henrydioniz | Kaggle-ready |
| SMS Spam Multilingual | HuggingFace dbarbedillo | Multilingual |

---

## 16-Week Execution Plan

| Phase | Weeks | Deliverable |
|-------|-------|------------|
| 1 | 1–2 | Environment & Foundation ✅ |
| 2 | 3–5 | Data Engineering & NLP |
| 3 | 6–9 | CNN-GRU Model Training |
| 4 | 10–11 | FastAPI Backend & Cloud |
| 5 | 12–13 | Mobile App & Edge AI |
| 6 | 14–15 | Integration & Testing |
| 7 | 16 | Deployment & Defense Prep |

---

## Decision Thresholds

| Score | Verdict | Action |
|-------|---------|--------|
| ≥ 0.85 | 🚨 SPAM | Block + Alert |
| 0.60–0.84 | ⚠️ SUSPICIOUS | Warn + Flag |
| < 0.60 | ✅ HAM | Pass through |
| URL flagged | 🚫 BLOCK | Regardless of text score |

---

## Target Metrics

- **Accuracy** ≥ 97%
- **Precision** ≥ 95%
- **Recall** ≥ 96%
- **F1 Score** ≥ 0.96
- **AUC-ROC** ≥ 0.99

---

## License

MIT License — Final Year Project, 2026.
