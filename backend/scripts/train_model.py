"""
SIMS CNN-GRU Training Script — Multilingual (Swahili + English)
Run: cd backend && python scripts/train_model.py
Outputs: data/models/sims_model.h5, sims_offline.tflite, vocab.json
"""
import os, sys, json, re, string
import numpy as np
import pandas as pd
from pathlib import Path
from collections import Counter

BASE_DIR  = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "data" / "models"
RAW_DIR   = BASE_DIR / "data" / "raw"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_H5  = str(MODEL_DIR / "sims_model.h5")
TFLITE    = str(MODEL_DIR / "sims_offline.tflite")
VOCAB     = str(MODEL_DIR / "vocab.json")

MAX_LEN=150; VOCAB_SIZE=12000; EMBED=128; FILTERS=128
KERNEL=3; GRU=64; EPOCHS=20; BATCH=64

SLANG = {"m-pesa":"mpesa","sasa hivi":"sasahivi","leo tu":"leotu",
         "bila malipo":"bimalipo","asap":"haraka","pls":"tafadhali",
         "plz":"tafadhali","thx":"asante","acc":"akaunti","pin":"nywila",
         "siri":"nywila","jaza":"jaza","omba":"omba","tz":"tanzania",
         "u":"wewe","r":"ni","2":"kwa","4":"kwa","b4":"kabla",
         "fwd":"forward","msg":"ujumbe","watoto":"watoto","mama":"mama",
         "baba":"baba","shule":"shule","nyumbani":"nyumbani"}
URL_RE   = re.compile(r'https?://\S+|www\.\S+', re.I)
PHONE_RE = re.compile(r'\+?\d[\d\s\-]{7,}\d')

# ── Swahili keyword boost list (prioritize in vocab) ──────────────────────────
SWAHILI_KEYWORDS = {
    "mpesa", "tuma", "nambari", "akaunti", "nywila", "siri", "zawadi",
    "umeshinda", "bonyeza", "haraka", "sasahivi", "leotu", "bimalipo",
    "mkopo", "pesa", "simu", "mshindi", "zawadi", "thibitisha", "fungua",
    "fursa", "maisha", "kupata", "kushinda", "kudai", "kujiunga",
    "habari", "asante", "shule", "watoto", "nyumbani", "kesho", "leo",
    "mama", "baba", "kazi", "chakula", "jioni", "asubuhi", "mchana",
    "karibu", "safari", "mizigo", "daktari", "dawa", "hospitali",
    "kanisa", "msikiti", "soko", "biashara", "mkutano", "chama",
    "rafiki", "jirani", "ndugu", "familia", "mtoto", "mke", "mume",
}


def clean(text):
    text = str(text).lower()
    text = URL_RE.sub(" url_token ", text)
    text = PHONE_RE.sub(" phone_token ", text)
    for s,c in SLANG.items():
        text = re.sub(r'\b'+re.escape(s)+r'\b', c, text, flags=re.I)
    text = text.translate(str.maketrans(string.punctuation," "*len(string.punctuation)))
    return re.sub(r'\s+',' ',text).strip()

def load_data():
    frames = []
    
    # 1. Try multilingual CSV first (from download_datasets.py)
    multi_csv = RAW_DIR / "sms_multilingual.csv"
    if multi_csv.exists():
        try:
            df = pd.read_csv(multi_csv, encoding="utf-8")
            # Ensure required columns
            if "text" not in df.columns and "v2" in df.columns:
                df = df.rename(columns={"v2":"text","v1":"label"})
            if "lang" not in df.columns:
                df["lang"] = "en"
            df = df[["text","label","lang"]].copy()
            df["label"] = df["label"].astype(int)
            frames.append(df)
            print(f"  Loaded {len(df)} rows from sms_multilingual.csv")
        except Exception as e:
            print(f"  Skip sms_multilingual.csv: {e}")
    
    # 2. Classic datasets
    for fname, (tc,lc) in [("SMSSpamCollection",("text","label")),("spam.csv",("v2","v1"))]:
        fp = RAW_DIR/fname
        if fp.exists():
            try:
                sep = "\t" if fname=="SMSSpamCollection" else ","
                df = pd.read_csv(fp,encoding="latin-1",sep=sep)
                df = df[[tc,lc]].rename(columns={tc:"text",lc:"label"})
                df["label"]=df["label"].map({"spam":1,"ham":0}).fillna(df["label"]).astype(int)
                df["lang"] = "en"
                frames.append(df); print(f"  Loaded {len(df)} rows from {fname}")
            except Exception as e: print(f"  Skip {fname}: {e}")
    
    # 3. Synthetic fallback (small set for robustness)
    syn = [
        ("WIN a FREE iPhone! Click http://win.fake.com NOW!", 1, "en"),
        ("Your bank account compromised. Verify: http://secure-bank.fake", 1, "en"),
        ("Congratulations! $1000 prize. Reply YES to claim.", 1, "en"),
        ("FREE entry to WIN $500. Text WIN to 12345!", 1, "en"),
        ("Loan approved! http://fastloan.fake.com", 1, "en"),
        ("ALERT: Suspicious login. Verify password: http://phish.com", 1, "en"),
        ("You are lucky winner! Call 0800-FAKE-123 to collect.", 1, "en"),
        ("Send your PIN to 45678 to unlock your account.", 1, "en"),
        ("Earn $500/day from home! http://work.scam", 1, "en"),
        ("Final notice: Pay debt now or face legal action", 1, "en"),
        ("Umeshinda! Bonyeza hapa: http://scam.link", 1, "sw"),
        ("HARAKA! Akaunti yako imezuiwa. Thibitisha: http://mpesa-fake.com", 1, "sw"),
        ("Pata mpesa 50,000 bila malipo! Tuma nambari kwa 456", 1, "sw"),
        ("UMESHINDA! Piga kura na upate zawadi 100,000", 1, "sw"),
        ("Tuma PIN yako kwa 12345 kupata zawadi leo tu", 1, "sw"),
        ("Are you coming to the meeting tomorrow?", 0, "en"),
        ("Hi mom, I'll be home by 6pm. Love you!", 0, "en"),
        ("Your appointment is confirmed for 3pm Friday.", 0, "en"),
        ("Can you pick up some milk on your way home?", 0, "en"),
        ("The report has been submitted successfully.", 0, "en"),
        ("Habari yako? Je, utakuwa shuleni kesho?", 0, "sw"),
        ("Mama, nitakuwa nyumbani saa nne usiku. Salama.", 0, "sw"),
        ("Mkutano wetu utafanyika kesho saa tatu asubuhi.", 0, "sw"),
        ("Ahsante kwa malipo yako ya shilingi 5000.", 0, "sw"),
        ("Watoto wako wamesimama salama shuleni.", 0, "sw"),
    ]
    syn_df = pd.DataFrame(syn,columns=["text","label","lang"])
    frames.append(syn_df); print(f"  Added {len(syn_df)} synthetic samples")
    
    df = pd.concat(frames,ignore_index=True).sample(frac=1,random_state=42).reset_index(drop=True)
    
    # Balance classes
    spam = df[df["label"]==1]
    ham = df[df["label"]==0]
    print(f"  Raw — Spam: {len(spam)} | Ham: {len(ham)}")
    
    if len(spam) < len(ham):
        spam = spam.sample(n=min(len(ham), len(spam)*3), replace=True, random_state=42)
        df = pd.concat([spam, ham], ignore_index=True).sample(frac=1, random_state=42).reset_index(drop=True)
    elif len(ham) < len(spam):
        ham = ham.sample(n=min(len(spam), len(ham)*3), replace=True, random_state=42)
        df = pd.concat([spam, ham], ignore_index=True).sample(frac=1, random_state=42).reset_index(drop=True)
    
    print(f"  Total: {len(df)} | Spam: {df['label'].sum()} | Ham: {(df['label']==0).sum()}")
    print(f"  Swahili: {(df['lang']=='sw').sum()} | English: {(df['lang']=='en').sum()}")
    return df

def build_vocab(texts, langs=None):
    """Build vocab with Swahili token prioritization."""
    c = Counter()
    for i, t in enumerate(texts):
        tokens = t.split()
        # Boost Swahili tokens if this is a Swahili sample
        if langs is not None and i < len(langs) and langs[i] == "sw":
            # Double-count Swahili keywords to boost their priority
            boosted = []
            for tok in tokens:
                boosted.append(tok)
                if tok in SWAHILI_KEYWORDS:
                    boosted.append(tok)  # count twice
            tokens = boosted
        c.update(tokens)
    
    v = {"<PAD>":0,"<OOV>":1}
    for w,_ in c.most_common(VOCAB_SIZE-2): v[w]=len(v)
    return v

def encode(texts, vocab):
    out = []
    for t in texts:
        ids = [vocab.get(w,1) for w in t.split()[:MAX_LEN]]
        ids += [0]*(MAX_LEN-len(ids))
        out.append(ids)
    return np.array(out,dtype=np.int32)

def build_model(vsz):
    import tensorflow as tf
    from tensorflow.keras import layers
    inp = tf.keras.Input(shape=(MAX_LEN,))
    x = layers.Embedding(vsz,EMBED)(inp)
    x = layers.Conv1D(FILTERS,KERNEL,padding="same",activation="relu")(x)
    x = layers.MaxPooling1D(pool_size=2)(x)
    x = layers.GRU(GRU,dropout=0.3)(x)
    x = layers.Dense(64,activation="relu")(x)
    x = layers.Dropout(0.4)(x)
    out = layers.Dense(1,activation="sigmoid")(x)
    m = tf.keras.Model(inp,out,name="SIMS_CNN_GRU")
    m.compile(optimizer="adam",loss="binary_crossentropy",metrics=["accuracy","AUC"])
    return m

def main():
    print("\n"+"="*50)
    print("  SIMS Multilingual Model Training"); print("="*50)
    df = load_data()
    df["clean"] = df["text"].apply(clean)
    
    from sklearn.model_selection import train_test_split
    
    # Track indices for per-language evaluation
    indices = np.arange(len(df))
    X_clean = df["clean"].values
    y = df["label"].values
    lang = df["lang"].values if "lang" in df.columns else None
    
    tr_idx, te_idx = train_test_split(
        indices, test_size=0.1, random_state=42, stratify=y
    )
    tr_idx, val_idx = train_test_split(
        tr_idx, test_size=0.15, random_state=42, stratify=y[tr_idx]
    )
    
    X_tr, X_val, X_te = X_clean[tr_idx], X_clean[val_idx], X_clean[te_idx]
    y_tr, y_val, y_te = y[tr_idx], y[val_idx], y[te_idx]
    lang_tr = lang[tr_idx] if lang is not None else None
    
    vocab = build_vocab(X_tr, lang_tr)
    with open(VOCAB, "w", encoding="utf-8") as f:
        json.dump(vocab, f, ensure_ascii=False)
    print(f"  Vocab: {len(vocab)} tokens saved to {VOCAB}")
    
    Xtr = encode(X_tr, vocab)
    Xv = encode(X_val, vocab)
    Xte = encode(X_te, vocab)
    
    import tensorflow as tf
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
    
    model = build_model(len(vocab))
    model.summary()
    
    cbs = [
        EarlyStopping(monitor="val_loss", patience=3, restore_best_weights=True, verbose=1),
        ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=2, verbose=1),
        ModelCheckpoint(MODEL_H5, save_best_only=True, monitor="val_accuracy", verbose=0),
    ]
    
    print("\n  Starting training...")
    model.fit(
        Xtr, y_tr,
        validation_data=(Xv, y_val),
        epochs=EPOCHS,
        batch_size=BATCH,
        callbacks=cbs,
        verbose=1,
    )
    
    loss, acc, auc = model.evaluate(Xte, y_te, verbose=0)
    print(f"\n  Overall Test Accuracy: {acc*100:.2f}% | AUC: {auc:.4f}")
    
    # Per-language evaluation
    if lang is not None:
        te_lang = lang[te_idx]
        for lg, name in [("sw", "Swahili"), ("en", "English")]:
            mask = te_lang == lg
            if mask.sum() > 0:
                lg_loss, lg_acc, lg_auc = model.evaluate(Xte[mask], y_te[mask], verbose=0)
                print(f"  {name} Test Accuracy: {lg_acc*100:.2f}% | AUC: {lg_auc:.4f}  (n={mask.sum()})")
    
    model.save(MODEL_H5)
    print(f"  Saved: {MODEL_H5}")
    
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite_model = converter.convert()
    with open(TFLITE, "wb") as f:
        f.write(tflite_model)
    print(f"  Saved: {TFLITE} ({os.path.getsize(TFLITE)/1024:.1f} KB)")
    
    print("\n" + "="*50)
    print("  Training complete!")
    print("="*50)


if __name__ == "__main__":
    main()
