"""
SIMS Text Preprocessor
Handles the full NLP pipeline for SMS text before model inference.

Pipeline (from blueprint):
  Raw SMS
  → Lowercase
  → Strip punctuation
  → Swahili slang normalization
  → URL extraction (save separately — handled by predict.py)
  → Multilingual BERT tokenization / custom vocab tokenization
  → Pad sequences to max_len=150
"""

import re
import string
import numpy as np
from typing import List, Dict, Tuple, Optional
from loguru import logger


# ── Swahili Slang Normalization Map ──────────────────────────────────────────
# Common SMS shorthand/slang in Tanzanian SMS — expand before tokenizing.
# Extend this dict as you discover more patterns in your datasets (Phase 2).

SWAHILI_SLANG_MAP: Dict[str, str] = {
    # Mobile money / fraud keywords
    "m-pesa": "mpesa",
    "m pesa": "mpesa",
    "bonyeza": "bonyeza",       # "press" — keep as-is (key fraud word)
    "piga kura": "pigakura",    # "vote" scam
    "umeshinda": "umeshinda",   # "you've won" — keep as-is (key spam phrase)
    "zawadi": "zawadi",         # "prize/gift"
    "tuma": "tuma",             # "send"
    "nambari": "nambari",       # "number"
    "simu": "simu",             # "phone"
    "pesa": "pesa",             # "money"
    "akaunti": "akaunti",       # "account"
    "nywila": "nywila",         # "password"
    "siri": "siri",             # "secret/PIN"
    "haraka": "haraka",         # "quickly/urgent"
    "sasa hivi": "sasahivi",    # "right now" — urgency cue
    "leo tu": "leotu",          # "today only" — urgency cue
    "bila malipo": "bimalipo",  # "free of charge"
    "jaza": "jaza",             # "fill/top-up"
    "omba": "omba",             # "request/apply"
    # Common abbreviations
    "tz": "tanzania",
    "ke": "kenya",
    "gh": "ghana",
    "ng": "nigeria",
    "u": "wewe",
    "r": "ni",
    "2": "kwa",
    "4": "kwa",
    "b4": "kabla",
    "asap": "haraka",
    "fwd": "forward",
    "pls": "tafadhali",
    "plz": "tafadhali",
    "thx": "asante",
    "msg": "ujumbe",
    "acc": "akaunti",
    "pin": "nywila",
}

# Regex to strip URLs (handled separately before NLP)
URL_REGEX = re.compile(r'https?://\S+|www\.\S+', re.IGNORECASE)

# Phone number pattern
PHONE_REGEX = re.compile(r'\+?\d[\d\s\-]{7,}\d')

# Max sequence length (from blueprint)
MAX_LEN = 150


class SMSPreprocessor:
    """
    Transforms raw SMS text into padded integer token sequences
    ready for the CNN-GRU model.

    Two tokenization modes:
      - "bert"   : uses HuggingFace multilingual BERT tokenizer (Phase 3)
      - "custom" : uses a custom vocab built from training data (fallback)
    """

    def __init__(
        self,
        mode: str = "custom",
        vocab_path: Optional[str] = None,
        max_len: int = MAX_LEN,
    ):
        """
        Args:
            mode: "bert" or "custom"
            vocab_path: path to saved vocab JSON (custom mode)
            max_len: sequence length to pad/truncate to
        """
        self.mode = mode
        self.max_len = max_len
        self._tokenizer = None
        self._word2idx: Dict[str, int] = {}
        self._vocab_size = 0

        if vocab_path:
            self.load_vocab(vocab_path)

    # ── Vocab / Tokenizer Loading ─────────────────────────────────────────────

    def load_vocab(self, vocab_path: str) -> None:
        """Load a custom word→index vocabulary from a JSON file."""
        import json
        with open(vocab_path, "r", encoding="utf-8") as f:
            self._word2idx = json.load(f)
        self._vocab_size = len(self._word2idx)
        logger.info(f"Loaded custom vocab: {self._vocab_size:,} tokens from {vocab_path}")

    def load_bert_tokenizer(
        self,
        model_name: str = "bert-base-multilingual-cased",
    ) -> None:
        """
        Load HuggingFace multilingual BERT tokenizer.
        Covers Swahili + English + 100 other languages.
        Called during Phase 3 training setup.
        """
        from transformers import AutoTokenizer
        logger.info(f"Loading BERT tokenizer: {model_name} ...")
        self._tokenizer = AutoTokenizer.from_pretrained(model_name)
        self._vocab_size = self._tokenizer.vocab_size
        self.mode = "bert"
        logger.info(f"BERT tokenizer loaded. Vocab size: {self._vocab_size:,}")

    @property
    def vocab_size(self) -> int:
        return self._vocab_size if self._vocab_size > 0 else 10000  # fallback

    # ── Text Cleaning Pipeline ────────────────────────────────────────────────

    @staticmethod
    def extract_and_remove_urls(text: str) -> Tuple[List[str], str]:
        """
        Extract URLs from text before cleaning (URLs are scanned by VirusTotal).
        Returns (list_of_urls, text_with_urls_replaced_by_token).
        """
        urls = URL_REGEX.findall(text)
        cleaned = URL_REGEX.sub(" URL_TOKEN ", text)
        return urls, cleaned

    @staticmethod
    def normalize_swahili_slang(text: str) -> str:
        """Replace known Swahili SMS abbreviations with canonical forms."""
        for slang, canonical in SWAHILI_SLANG_MAP.items():
            text = re.sub(r'\b' + re.escape(slang) + r'\b', canonical, text, flags=re.IGNORECASE)
        return text

    @staticmethod
    def clean_text(text: str) -> str:
        """
        Core text cleaning:
          1. Lowercase
          2. Replace phone numbers with token
          3. Strip punctuation (keep spaces)
          4. Collapse multiple spaces
        """
        text = text.lower()
        text = PHONE_REGEX.sub(" PHONE_TOKEN ", text)
        text = text.translate(str.maketrans(string.punctuation, " " * len(string.punctuation)))
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def preprocess(self, text: str) -> Tuple[List[str], str]:
        """
        Full pipeline: raw SMS → cleaned string + extracted URLs.
        Returns (urls, cleaned_text).
        """
        urls, text = self.extract_and_remove_urls(text)
        text = self.normalize_swahili_slang(text)
        text = self.clean_text(text)
        return urls, text

    # ── Tokenization ──────────────────────────────────────────────────────────

    def tokenize(self, text: str) -> List[int]:
        """
        Convert cleaned text to a list of integer token IDs.
        Truncated to max_len automatically.
        """
        if self.mode == "bert" and self._tokenizer:
            encoded = self._tokenizer.encode(
                text,
                max_length=self.max_len,
                truncation=True,
                padding=False,
            )
            return encoded
        else:
            # Custom vocab lookup — unknown words map to index 1 (OOV)
            tokens = text.split()[:self.max_len]
            return [self._word2idx.get(tok, 1) for tok in tokens]

    def pad_sequence(self, token_ids: List[int]) -> np.ndarray:
        """Pad or truncate to max_len with zeros (post-padding)."""
        seq = token_ids[:self.max_len]
        padded = seq + [0] * (self.max_len - len(seq))
        return np.array(padded, dtype=np.int32)

    def encode(self, text: str) -> np.ndarray:
        """
        Full encode pipeline: raw SMS → padded integer array (max_len,).
        This is the main method called by the /predict route.
        """
        _, cleaned = self.preprocess(text)
        token_ids = self.tokenize(cleaned)
        return self.pad_sequence(token_ids)

    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """
        Encode a batch of SMS texts.
        Returns np.ndarray of shape (batch_size, max_len).
        """
        return np.stack([self.encode(t) for t in texts], axis=0)


# ── Singleton ─────────────────────────────────────────────────────────────────

_preprocessor_instance: Optional[SMSPreprocessor] = None


def get_preprocessor() -> SMSPreprocessor:
    """FastAPI dependency — returns the global preprocessor instance."""
    global _preprocessor_instance
    if _preprocessor_instance is None:
        import os
        vocab_path = os.getenv("VOCAB_PATH", "./data/models/vocab.json")
        mode = "custom"
        if os.path.exists(vocab_path):
            _preprocessor_instance = SMSPreprocessor(mode=mode, vocab_path=vocab_path)
        else:
            logger.warning(
                f"Vocab not found at '{vocab_path}'. "
                "Preprocessor running in no-vocab mode until Phase 3 training."
            )
            _preprocessor_instance = SMSPreprocessor(mode=mode)
    return _preprocessor_instance
