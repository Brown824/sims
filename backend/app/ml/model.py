"""
SIMS ML Model Loader
Phase 1: Stub with full interface defined.
Phase 3: Real CNN-GRU model weights loaded here.

Architecture (from blueprint):
  Input (max_len=150)
  → Embedding (dim=128, trainable)
  → Conv1D (filters=128, kernel=3, ReLU) → GlobalMaxPool1D
  → GRU (units=64, dropout=0.3)
  → Dense(64) → Dropout(0.4)
  → Sigmoid → spam_score [0.0–1.0]
"""

import os
import numpy as np
from loguru import logger
from typing import Optional


class SIMSModel:
    """
    Wrapper for the trained CNN-GRU spam detection model.
    Handles lazy loading, inference, and version tracking.
    """

    def __init__(self, model_path: str, model_version: str = "1.0.0"):
        self.model_path = model_path
        self.model_version = model_version
        self._model = None          # Keras model (loaded lazily)
        self._is_loaded = False

    # ── Loading ───────────────────────────────────────────────────────────────

    def load(self) -> bool:
        """
        Load the .h5 model from disk.
        Returns True if successful, False if model file not found yet.
        Phase 3 will train and export the model to MODEL_PATH.
        """
        if not os.path.exists(self.model_path):
            logger.warning(
                f"Model file not found at '{self.model_path}'. "
                "Run Phase 3 training to generate sims_model.h5"
            )
            return False

        try:
            # Import TF here to keep startup fast when model not yet trained
            import tensorflow as tf
            self._model = tf.keras.models.load_model(self.model_path)
            self._is_loaded = True
            logger.info(f"✅ CNN-GRU model loaded from {self.model_path}")
            logger.info(f"   Version : {self.model_version}")
            logger.info(f"   Summary : {self._model.count_params():,} parameters")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    # ── Inference ─────────────────────────────────────────────────────────────

    def _heuristic_predict(self, token_sequence: np.ndarray) -> float:
        """Fallback prediction when model is not loaded"""
        # Since we don't have the text here (only tokens), we can't easily 
        # do string matching without reverse-mapping from vocab.
        # However, for simplicity if model is not loaded, return 0.1
        # It's better to update predict.py to handle heuristic text-based prediction.
        return 0.1

    def predict(self, token_sequences: np.ndarray) -> np.ndarray:
        """
        Run inference on a batch of tokenized sequences.

        Args:
            token_sequences: np.ndarray of shape (batch_size, max_len=150)
                             containing integer token IDs.

        Returns:
            np.ndarray of shape (batch_size,) — spam scores in [0.0, 1.0].
        """
        if not self._is_loaded:
            logger.warning("Model not loaded, falling back to dummy scores")
            return np.full((token_sequences.shape[0],), 0.1)

        raw = self._model.predict(token_sequences, verbose=0)
        # raw shape: (batch_size, 1) — squeeze to (batch_size,)
        return raw.squeeze(axis=-1)

    def predict_single(self, token_sequence: np.ndarray) -> float:
        """
        Predict a single tokenized SMS. Convenience wrapper around predict().

        Args:
            token_sequence: 1D np.ndarray of shape (max_len,)

        Returns:
            float spam score in [0.0, 1.0]
        """
        batch = np.expand_dims(token_sequence, axis=0)  # (1, max_len)
        scores = self.predict(batch)
        return float(scores[0])

    # ── Architecture Definition ───────────────────────────────────────────────

    @staticmethod
    def build(
        vocab_size: int,
        max_len: int = 150,
        embed_dim: int = 128,
        cnn_filters: int = 128,
        cnn_kernel: int = 3,
        gru_units: int = 64,
        gru_dropout: float = 0.3,
        dense_units: int = 64,
        dense_dropout: float = 0.4,
    ):
        """
        Build and return the CNN-GRU hybrid model (uncompiled).
        Called by Phase 3 training script.

        Architecture (from blueprint):
          Embedding → Conv1D → GlobalMaxPool1D → GRU → Dense → Sigmoid
        """
        import tensorflow as tf
        from tensorflow.keras import layers, Model

        inputs = tf.keras.Input(shape=(max_len,), name="token_input")

        # Embedding
        x = layers.Embedding(
            input_dim=vocab_size,
            output_dim=embed_dim,
            trainable=True,
            name="embedding",
        )(inputs)

        # CNN branch — captures local fraud keywords
        x = layers.Conv1D(
            filters=cnn_filters,
            kernel_size=cnn_kernel,
            padding="same",
            activation="relu",
            name="conv1d",
        )(x)
        x = layers.MaxPooling1D(pool_size=2, name="max_pool")(x)

        # GRU branch — captures sentence context
        x = layers.GRU(
            units=gru_units,
            dropout=gru_dropout,
            return_sequences=False,
            name="gru",
        )(x)

        # Classification head
        x = layers.Dense(dense_units, activation="relu", name="dense")(x)
        x = layers.Dropout(dense_dropout, name="dropout")(x)
        outputs = layers.Dense(1, activation="sigmoid", name="output")(x)

        return Model(inputs=inputs, outputs=outputs, name="SIMS_CNN_GRU")


# ── Singleton ─────────────────────────────────────────────────────────────────
# Instantiated at startup; .load() called in main.py on_event("startup")
# after Phase 3 training completes.

_model_instance: Optional[SIMSModel] = None


def get_model() -> SIMSModel:
    """FastAPI dependency — returns the global model instance."""
    global _model_instance
    if _model_instance is None:
        from app.config import settings
        _model_instance = SIMSModel(
            model_path=settings.MODEL_PATH,
            model_version=settings.MODEL_VERSION,
        )
    return _model_instance
