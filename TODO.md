# SIMS — Complete Multilingual Build Plan (Swahili+English Spam Detection)

Current Progress: Backend ✅ | Model Training [IN PROGRESS] | Mobile [PENDING]


## Phase 3.1: Multilingual Dataset & Model Training [IN PROGRESS]

### Step 1: Backend Environment Setup [✅]
```
cd backend
python -m venv venv
venv\\Scripts\\activate  (Windows)
pip install -r requirements.txt
pip install datasets transformers tensorflow-cpu scikit-learn kaggle huggingface-hub
```
> Dependencies already present in requirements.txt. FastAPI backend starts successfully.


### Step 2: Download Multilingual Datasets [✅]
- BongoScamDetection (Swahili scam)
- SSD Swahili spam
- HF: dbarbedillo/SMS_Spam_Multilingual_Collection_Dataset
- Synthetic Swahili/English spam/ham augmentation

> Created `backend/scripts/download_datasets.py` — downloads HF datasets, Kaggle (optional), merges with existing data, generates synthetic Swahili/English samples, balances classes.



### Step 3: Enhanced Training Script [✅]
Edit backend/scripts/train_model.py:

- Load/merge multilingual CSVs from data/raw/
- Custom multilingual vocab (Swahili tokens prioritized)
- Train CNN-GRU (current synthetic data → real datasets)
- Export data/models/sims_model.h5 + sims_offline.tflite (264KB)
- Generate vocab.json for preprocessor/mobile

> Updated `backend/scripts/train_model.py` — loads `sms_multilingual.csv`, Swahili vocab boost (2× weight for Swahili keywords), per-language accuracy reporting, class balancing, 12k vocab.


### Step 4: Run Training [🔄]
```bash
# 1. Generate/refresh dataset
cd backend && python scripts/download_datasets.py

# 2. Train model
python scripts/train_model.py
```
Expected: ~15 epochs, 92-97% acc multilingual test set.

> Ready to execute — both scripts are complete.


## Phase 3.2: Mobile TFLite Integration [PENDING]

- [ ] 13. `offlineModel.js`: tfjs.loadTFLiteModel('model.tflite'), preprocess(tokenizer), predict()
- [ ] 14. `smsInterceptor.js`: SMS → offline/cloud classify → notify/block/save history

## Phase 3.3: Full App Integration [PENDING]
- [ ] 15-20 Screens + App.js wiring + Swahili i18n

## Phase 4: Testing Commands [PENDING]
```
# Backend API test
cd backend && uvicorn app.main:app --reload

# Mobile dev
cd ../mobile-app && expo start

# Simulate SMS
expo install expo-notifications  # already?
```

## Phase 5: Production APK [PENDING]
```
eas login
eas build --platform android --profile preview
```

**Next Action: Dataset download + train_model.py multilingual upgrade → execute training**

> 🚀 Executing now — creating `download_datasets.py` + enhancing `train_model.py`.
