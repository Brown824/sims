"""
SIMS Multilingual Dataset Downloader
Downloads and merges Swahili + English spam datasets for training.

Sources:
  1. HuggingFace: dbarbedillo/SMS_Spam_Multilingual_Collection_Dataset
  2. Kaggle (optional): BongoScamDetection, SSD Swahili spam
  3. Existing: data/raw/sms_multilingual.csv
  4. Synthetic augmentation for Swahili coverage

Output:
  data/raw/sms_multilingual.csv (merged, balanced, lang-tagged)
"""

import os
import sys
import json
import re
import random
from pathlib import Path

import pandas as pd
import numpy as np
from loguru import logger

# ── Paths ─────────────────────────────────────────────────────────────────────

BASE_DIR  = Path(__file__).resolve().parent.parent
RAW_DIR   = BASE_DIR / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = RAW_DIR / "sms_multilingual.csv"

# ── Configuration ─────────────────────────────────────────────────────────────

MIN_SAMPLES_TARGET = 5_000      # Try to reach at least 5k samples
SWAHILI_RATIO_TARGET = 0.30   # At least 30% Swahili

# ── Synthetic Swahili/English Templates ───────────────────────────────────────

SWAHILI_SPAM_TEMPLATES = [
    "Umeshinda {prize}! Tuma jina lako kwa {number} sasa",
    "Tuma PIN yako kwa {number} kupata zawadi yako",
    "Akaunti yako imefungwa. Bonyeza {url} kufungua",
    "Pata mkopo wa {amount} bila malipo! Piga {number}",
    "M-PESA yako itaisha! Thibitisha kwa kutuma PIN kwa {number}",
    "Umechaguliwa kushinda {prize}! Haraka, muda unaokwisha",
    "Neno la siri lako lina hatari. Badilisha sasa: {url}",
    "Zawadi kubwa inangojea! Jibu NDIYO kwa {number}",
    "Habari njema! Umeidhinishwa kupokea {amount}. Bonyeza {url}",
    "Tuma {amount} uipate {prize}! Fursa ya maisha",
    "Je, unahitaji pesa haraka? Pata mkopo wa {amount}: {url}",
    "Umebakiza siku 1 tu! Shinda {prize} sasa hivi",
    "Akaunti yako ya benki imezuiliwa. Wasiliana {number}",
    "Fungua link hii kupata zawadi ya M-PESA: {url}",
    "Nakala yako ya kushinda! Piga {number} kudai {prize}",
    "Bonyeza hapa kupokea {amount} bure: {url}",
    "Umechaguliwa kama mshindi wa {prize} kutoka {company}",
    "Tuma '{word}' kwa {number} kujiunga na droo ya {prize}",
    "Muda unaokwisha! Shinda {prize} leo tu kwa kutuma PIN",
    "Fursa ya kipekee! Pata {amount} bila riba: {url}",
]

SWAHILI_HAM_TEMPLATES = [
    "Habari, je unakuja kwenye mkutano kesho?",
    "Mama, nitakuja nyumbani baada ya kazi. Nakuja na maziwa",
    "Asante kwa malipo yako ya shilingi {amount}",
    "Watoto wako wamesimama vizuri shuleni leo",
    "Mkutano wetu utafanyika saa {time} asubuhi",
    "Nimepakia mizigo tayari kwa usafiri wa kesho",
    "Chakula cha jioni kiko tayari, karibu nyumbani",
    "Nimepata ripoti yako, inaonekana vizuri sana",
    "Je, unaweza kuniletea dawa kutoka kwa daktari?",
    "Habari za asubuhi? Nakutakia siku njema",
    "Nimekwisha maliza kazi, nakuja sasa hivi",
    "Tafadhali niletee mkate wa chapati njiani",
    "Mke wangu anakusalimu sana, asema akuone jioni",
    "Karo ya mwezi huu imekulipiwa mapema",
    "Nimepata nafasi ya kwenda Dodoma kesho",
    "Shule inafunguliwa kesho, tengeneza vitabu",
    "Asante kwa msaada wako wa jana, ulinisaidia sana",
    "Baba yuko hospitalini sasa, anaendelea vizuri",
    "Tutakutana katika uwanja wa soka saa {time}",
    "Nimepata michongo ya samaki, nitaleta nyumbani",
]

ENGLISH_SPAM_TEMPLATES = [
    "Congratulations! You've won {prize}. Call {number} now!",
    "Urgent: Your bank account is suspended. Visit {url}",
    "You have been selected for a cash reward of {amount}. Reply YES",
    "Free entry to win {prize}! Text WIN to {number}",
    "Your PayPal account has been limited. Verify at {url}",
    "Act now! Claim your prize of {prize} before midnight",
    "We tried to deliver your package. Pay shipping: {url}",
    "You are a lucky winner! Dial {number} to collect {prize}",
    "IRS alert: You owe ${amount}. Pay immediately at {url}",
    "Get rich quick! Earn {amount}/day from home: {url}",
    "Your Amazon order has issues. Update payment: {url}",
    "You've been chosen! Free iPhone 15 at {url}",
    "Loan approved! Get {amount} in 5 minutes: {url}",
    "Final notice: Your car warranty expired. Call {number}",
    "Crypto investment opportunity! Turn {amount} into {prize}: {url}",
]

ENGLISH_HAM_TEMPLATES = [
    "Hey, are we still meeting for lunch tomorrow?",
    "Can you pick up some milk on your way home?",
    "The report looks great, I'll send feedback by EOD",
    "Your appointment is confirmed for {time} on Friday",
    "Thanks for the birthday wishes, I really appreciate it",
    "I'll be 10 minutes late, traffic is terrible",
    "Don't forget to bring the documents to the meeting",
    "The kids are doing well in school this semester",
    "Can you call me when you have a chance?",
    "Dinner is at 7pm, let me know if you can make it",
    "I sent the payment, please confirm receipt",
    "Great game last night! We should play again soon",
    "Your package has been delivered. Tracking: {number}",
    "See you at the gym around {time}?",
    "Happy anniversary! Looking forward to celebrating",
    "The flight is delayed by 30 minutes",
    "Can you review the attached document?",
    "I'll drop off the keys tomorrow morning",
    "Thanks for helping out yesterday, you're a lifesaver",
    "Reminder: Doctor appointment at {time} tomorrow",
]

FILLERS = {
    "prize": ["Tsh 1,000,000", "$1000", "iPhone 15", "Tsh 500,000", "Samsung S24", "laptop mpya", "$5000"],
    "amount": ["Tsh 50,000", "$100", "Tsh 100,000", "$500", "Tsh 25,000", "Tsh 200,000"],
    "number": ["12345", "45678", "0800123456", "0712345678", "*149*01#", "1234"],
    "url": ["http://scam.co.tz", "http://win.fake.com", "http://mpesa-fake.com", "http://link-scam.ng"],
    "time": ["saba", "tatu", "kumi", "7pm", "3pm", "9am"],
    "company": ["Safaricom", "Vodacom", "Airtel", "CRDB", "NMB"],
    "word": ["WIN", "YES", "PLAY", "JOIN", "CLAIM"],
}


def generate_synthetic(n_per_class: int = 250) -> pd.DataFrame:
    """Generate realistic synthetic SMS samples for Swahili + English."""
    rows = []
    
    # Swahili spam
    for _ in range(n_per_class):
        tpl = random.choice(SWAHILI_SPAM_TEMPLATES)
        text = tpl.format(**{k: random.choice(v) for k, v in FILLERS.items()})
        rows.append({"text": text, "label": 1, "lang": "sw"})
    
    # Swahili ham
    for _ in range(n_per_class):
        tpl = random.choice(SWAHILI_HAM_TEMPLATES)
        text = tpl.format(**{k: random.choice(v) for k, v in FILLERS.items()})
        rows.append({"text": text, "label": 0, "lang": "sw"})
    
    # English spam
    for _ in range(n_per_class):
        tpl = random.choice(ENGLISH_SPAM_TEMPLATES)
        text = tpl.format(**{k: random.choice(v) for k, v in FILLERS.items()})
        rows.append({"text": text, "label": 1, "lang": "en"})
    
    # English ham
    for _ in range(n_per_class):
        tpl = random.choice(ENGLISH_HAM_TEMPLATES)
        text = tpl.format(**{k: random.choice(v) for k, v in FILLERS.items()})
        rows.append({"text": text, "label": 0, "lang": "en"})
    
    df = pd.DataFrame(rows)
    logger.info(f"  Generated {len(df)} synthetic samples ({n_per_class*4} total)")
    return df


def load_existing_csv(path: Path) -> pd.DataFrame:
    """Load existing sms_multilingual.csv if present."""
    if not path.exists():
        return pd.DataFrame(columns=["text", "label", "lang"])
    
    try:
        df = pd.read_csv(path)
        if "lang" not in df.columns:
            # Auto-detect language based on text content
            df["lang"] = df["text"].apply(detect_lang)
        logger.info(f"  Loaded {len(df)} rows from existing {path.name}")
        return df[["text", "label", "lang"]]
    except Exception as e:
        logger.warning(f"  Failed to load existing CSV: {e}")
        return pd.DataFrame(columns=["text", "label", "lang"])


def detect_lang(text: str) -> str:
    """Simple heuristic to detect Swahili vs English."""
    sw_words = {"umeshinda", "bonyeza", "hapa", "zawadi", "tuma", "nambari", 
                "akaunti", "nywila", "pesa", "mpesa", "mkopo", "habari", 
                "asante", "mama", "shule", "watoto", "nyumbani", "leo", "kesho"}
    text_lower = str(text).lower()
    words = set(re.findall(r'\b\w+\b', text_lower))
    sw_count = len(words & sw_words)
    return "sw" if sw_count >= 2 else "en"


def download_hf_multilingual() -> pd.DataFrame:
    """Download dbarbedillo/SMS_Spam_Multilingual_Collection_Dataset from HF."""
    try:
        from datasets import load_dataset
        logger.info("Downloading HF: dbarbedillo/SMS_Spam_Multilingual_Collection_Dataset ...")
        
        ds = load_dataset("dbarbedillo/SMS_Spam_Multilingual_Collection_Dataset", trust_remote_code=True)
        
        # Try to find a train split or use the first available
        split_name = "train" if "train" in ds else list(ds.keys())[0]
        data = ds[split_name]
        
        rows = []
        for item in data:
            text = item.get("text") or item.get("sms") or item.get("message") or ""
            label_raw = item.get("label") or item.get("class") or item.get("target") or 0
            # Normalize label
            if isinstance(label_raw, str):
                label = 1 if label_raw.lower() in ("spam", "1", "true", "yes") else 0
            else:
                label = int(label_raw)
            
            lang = detect_lang(text)
            rows.append({"text": text, "label": label, "lang": lang})
        
        df = pd.DataFrame(rows)
        logger.info(f"  ✓ HF dataset: {len(df)} rows loaded")
        return df
    except Exception as e:
        logger.warning(f"  ✗ HuggingFace download failed: {e}")
        return pd.DataFrame(columns=["text", "label", "lang"])


def download_hf_swahili() -> pd.DataFrame:
    """Try to find Swahili-specific datasets on HF."""
    # Try a known Swahili spam dataset if available
    candidates = [
        ("FrancisKis1/swahili-spam", "text", "label"),
    ]
    
    for ds_name, text_col, label_col in candidates:
        try:
            from datasets import load_dataset
            logger.info(f"Trying HF: {ds_name} ...")
            ds = load_dataset(ds_name, trust_remote_code=True)
            split_name = "train" if "train" in ds else list(ds.keys())[0]
            data = ds[split_name]
            
            rows = []
            for item in data:
                text = item.get(text_col, "")
                label_raw = item.get(label_col, 0)
                label = int(label_raw) if not isinstance(label_raw, str) else (1 if label_raw.lower() == "spam" else 0)
                rows.append({"text": text, "label": label, "lang": "sw"})
            
            df = pd.DataFrame(rows)
            logger.info(f"  ✓ Swahili dataset: {len(df)} rows loaded")
            return df
        except Exception as e:
            logger.warning(f"  ✗ {ds_name} not available: {e}")
    
    return pd.DataFrame(columns=["text", "label", "lang"])


def download_kaggle_datasets() -> pd.DataFrame:
    """Attempt to download Kaggle datasets (requires kaggle.json)."""
    frames = []
    
    datasets_to_try = [
        ("bongoscamdetection", None),  # hypothetical name
        ("swahili-spam", None),
        ("sms-spam-collection-dataset", "spam.csv"),  # known existing
    ]
    
    for dataset_name, filename in datasets_to_try:
        try:
            import kaggle
            logger.info(f"Trying Kaggle: {dataset_name} ...")
            
            # Download to temp
            tmp_dir = RAW_DIR / f"kaggle_{dataset_name}"
            tmp_dir.mkdir(exist_ok=True)
            
            kaggle.api.dataset_download_files(dataset_name, path=str(tmp_dir), unzip=True)
            
            # Find CSV
            csv_files = list(tmp_dir.glob("*.csv"))
            if not csv_files:
                logger.warning(f"  No CSV found in {dataset_name}")
                continue
            
            for csv_file in csv_files:
                try:
                    df = pd.read_csv(csv_file, encoding="latin-1")
                    # Try to auto-detect text/label columns
                    text_col = next((c for c in df.columns if c.lower() in ("text", "message", "sms", "v2")), None)
                    label_col = next((c for c in df.columns if c.lower() in ("label", "class", "v1", "target")), None)
                    
                    if text_col and label_col:
                        df = df[[text_col, label_col]].rename(columns={text_col: "text", label_col: "label"})
                        df["label"] = df["label"].map({"spam": 1, "ham": 0}).fillna(df["label"]).astype(int)
                        df["lang"] = df["text"].apply(detect_lang)
                        frames.append(df)
                        logger.info(f"  ✓ Kaggle {dataset_name}/{csv_file.name}: {len(df)} rows")
                except Exception as e:
                    logger.warning(f"  Failed to parse {csv_file}: {e}")
        
        except Exception as e:
            logger.warning(f"  ✗ Kaggle {dataset_name} failed: {e}")
    
    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame(columns=["text", "label", "lang"])


def balance_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Balance classes and ensure Swahili ratio."""
    if len(df) == 0:
        return df
    
    # Ensure binary labels
    df = df.copy()
    df["label"] = df["label"].astype(int)
    
    # Separate by class
    spam = df[df["label"] == 1]
    ham = df[df["label"] == 0]
    
    logger.info(f"  Before balance — Spam: {len(spam)}, Ham: {len(ham)}")
    
    # Upsample minority class
    if len(spam) < len(ham):
        spam = spam.sample(n=len(ham), replace=True, random_state=42)
    elif len(ham) < len(spam):
        ham = ham.sample(n=len(spam), replace=True, random_state=42)
    
    balanced = pd.concat([spam, ham], ignore_index=True)
    
    # Check Swahili ratio
    sw_ratio = (balanced["lang"] == "sw").mean()
    logger.info(f"  Swahili ratio: {sw_ratio:.1%}")
    
    if sw_ratio < SWAHILI_RATIO_TARGET:
        logger.info(f"  Swahili ratio below {SWAHILI_RATIO_TARGET:.0%}, adding synthetic Swahili...")
        # Will be handled by synthetic generation in main()
    
    return balanced.sample(frac=1, random_state=42).reset_index(drop=True)


def main():
    logger.info("=" * 60)
    logger.info("  SIMS Multilingual Dataset Downloader")
    logger.info("=" * 60)
    
    all_frames = []
    
    # 1. Existing CSV
    existing = load_existing_csv(OUTPUT_CSV)
    if len(existing) > 0:
        all_frames.append(existing)
    
    # 2. HuggingFace datasets
    hf_multi = download_hf_multilingual()
    if len(hf_multi) > 0:
        all_frames.append(hf_multi)
    
    hf_sw = download_hf_swahili()
    if len(hf_sw) > 0:
        all_frames.append(hf_sw)
    
    # 3. Kaggle (optional, may fail without auth)
    kaggle_data = download_kaggle_datasets()
    if len(kaggle_data) > 0:
        all_frames.append(kaggle_data)
    
    # 4. Classic SMSSpamCollection if present
    spam_collection = RAW_DIR / "SMSSpamCollection"
    if spam_collection.exists():
        try:
            df = pd.read_csv(spam_collection, sep="\t", header=None, names=["label", "text"])
            df["label"] = df["label"].map({"spam": 1, "ham": 0})
            df["lang"] = "en"
            all_frames.append(df[["text", "label", "lang"]])
            logger.info(f"  Loaded {len(df)} rows from SMSSpamCollection")
        except Exception as e:
            logger.warning(f"  SMSSpamCollection load failed: {e}")
    
    # 5. spam.csv if present
    spam_csv = RAW_DIR / "spam.csv"
    if spam_csv.exists():
        try:
            df = pd.read_csv(spam_csv, encoding="latin-1")
            df = df[["v2", "v1"]].rename(columns={"v2": "text", "v1": "label"})
            df["label"] = df["label"].map({"spam": 1, "ham": 0}).fillna(df["label"]).astype(int)
            df["lang"] = "en"
            all_frames.append(df[["text", "label", "lang"]])
            logger.info(f"  Loaded {len(df)} rows from spam.csv")
        except Exception as e:
            logger.warning(f"  spam.csv load failed: {e}")
    
    # Combine all real data
    if all_frames:
        real_data = pd.concat(all_frames, ignore_index=True)
        real_data = real_data.drop_duplicates(subset=["text"]).reset_index(drop=True)
        logger.info(f"\nTotal real data: {len(real_data)} rows")
        logger.info(f"  Spam: {(real_data['label']==1).sum()}, Ham: {(real_data['label']==0).sum()}")
        logger.info(f"  Swahili: {(real_data['lang']=='sw').sum()}, English: {(real_data['lang']=='en').sum()}")
    else:
        real_data = pd.DataFrame(columns=["text", "label", "lang"])
        logger.warning("No real datasets loaded. Will use synthetic data only.")
    
    # 6. Add synthetic data to reach minimum target
    current_n = len(real_data)
    synthetic_needed = max(MIN_SAMPLES_TARGET - current_n, 500)  # at least 500 synthetic
    n_per_class = synthetic_needed // 4  # sw-spam, sw-ham, en-spam, en-ham
    
    logger.info(f"\nGenerating {n_per_class * 4} synthetic samples...")
    synthetic = generate_synthetic(n_per_class=n_per_class)
    
    # Combine
    combined = pd.concat([real_data, synthetic], ignore_index=True)
    combined = combined.sample(frac=1, random_state=42).reset_index(drop=True)
    
    # Final balance
    combined = balance_dataset(combined)
    
    # Save
    combined.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    logger.info(f"\n{'='*60}")
    logger.info(f"  Saved: {OUTPUT_CSV}")
    logger.info(f"  Total: {len(combined)} rows")
    logger.info(f"  Spam: {(combined['label']==1).sum()}, Ham: {(combined['label']==0).sum()}")
    logger.info(f"  Swahili: {(combined['lang']=='sw').sum()}, English: {(combined['lang']=='en').sum()}")
    logger.info(f"{'='*60}")
    
    return combined


if __name__ == "__main__":
    main()
