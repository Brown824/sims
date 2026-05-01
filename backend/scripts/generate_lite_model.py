import os, json, re, string
import pandas as pd
import numpy as np
from pathlib import Path
from collections import Counter
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "data" / "models"
RAW_DIR = BASE_DIR / "data" / "raw"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_JSON = MODEL_DIR / "sims_lite_model.json"
VOCAB_JSON = MODEL_DIR / "vocab.json"

def clean(text):
    text = str(text).lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    return re.sub(r"\s+", " ", text).strip()

def main():
    print("Generating Lite Model (JSON)...")
    
    # Load data
    syn = [
        ("WIN a FREE iPhone! Click now!", 1),
        ("Your bank account compromised. Verify now", 1),
        ("Congratulations! $1000 prize. Reply YES", 1),
        ("Pata mpesa 50,000 bila malipo! Tuma nambari", 1),
        ("UMESHINDA! Piga kura na upate zawadi", 1),
        ("Are you coming to the meeting tomorrow?", 0),
        ("Hi mom, I'll be home by 6pm.", 0),
        ("Habari yako? Je, utakuwa shuleni kesho?", 0),
        ("Mama, nitakuwa nyumbani saa nne usiku.", 0),
    ]
    df = pd.DataFrame(syn, columns=["text", "label"])
    
    # Load raw data if exists
    multi_csv = RAW_DIR / "sms_multilingual.csv"
    if multi_csv.exists():
        try:
            mdf = pd.read_csv(multi_csv)
            if "v2" in mdf.columns:
                mdf = mdf.rename(columns={"v2":"text","v1":"label"})
            if "text" in mdf.columns:
                mdf["label"] = mdf["label"].map({"spam":1,"ham":0}).fillna(mdf["label"]).astype(int)
                df = pd.concat([df, mdf[["text","label"]]], ignore_index=True)
        except: pass

    df["clean"] = df["text"].apply(clean)
    
    vectorizer = CountVectorizer(max_features=2000)
    X = vectorizer.fit_transform(df["clean"])
    y = df["label"]
    
    model = MultinomialNB()
    model.fit(X, y)
    
    vocab = vectorizer.vocabulary_
    feature_log_prob = model.feature_log_prob_ 
    class_log_prior = model.class_log_prior_
    
    # Convert to standard python types
    clean_vocab = {str(k): int(v) for k, v in vocab.items()}
    
    export_data = {
        "class_log_prior": class_log_prior.tolist(),
        "feature_log_prob": feature_log_prob.tolist(),
        "vocab": clean_vocab,
        "classes": [int(c) for c in model.classes_]
    }
    
    with open(MODEL_JSON, "w") as f:
        json.dump(export_data, f)
        
    with open(VOCAB_JSON, "w") as f:
        json.dump(clean_vocab, f)
        
    print(f"Saved Lite Model to {MODEL_JSON}")
    print(f"Saved Vocab to {VOCAB_JSON}")

if __name__ == "__main__":
    main()
