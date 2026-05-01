// SIMS Offline Model — Hybrid Inference (TFLite + Naive Bayes)
// Optimized for React Native performance.

import * as tf from '@tensorflow/tfjs';
import '@tensorflow/tfjs-react-native';
import * as FileSystem from 'expo-file-system';
import AsyncStorage from '@react-native-async-storage/async-storage';

let tfliteModel = null;
let liteModel = null; // Naive Bayes JSON
let vocab = null;
let modelLoaded = false;
let liteLoaded = false;

const MAX_LEN = 150;

/**
 * Sync the latest model from the cloud backend.
 */
export const syncOfflineModel = async () => {
  try {
    const savedUrl = await AsyncStorage.getItem('@sims_api_url') || 'http://10.0.2.2:8000';
    console.log("Syncing models from:", savedUrl);
    
    const modelUri = FileSystem.documentDirectory + 'sims_offline.tflite';
    const vocabUri = FileSystem.documentDirectory + 'vocab.json';
    const liteUri = FileSystem.documentDirectory + 'sims_lite_model.json';

    await Promise.all([
      FileSystem.downloadAsync(`${savedUrl}/api/predict/model/latest`, modelUri),
      FileSystem.downloadAsync(`${savedUrl}/api/predict/model/vocab`, vocabUri),
      FileSystem.downloadAsync(`${savedUrl}/api/predict/model/lite`, liteUri)
    ]);
    
    console.log("Offline models synced successfully!");
    return true;
  } catch (error) {
    console.warn("Sync failed. Using local versions.", error.message);
    return false;
  }
};

/**
 * Load models from storage or assets.
 */
export const loadOfflineModel = async () => {
  try {
    const modelUri = FileSystem.documentDirectory + 'sims_offline.tflite';
    const vocabUri = FileSystem.documentDirectory + 'vocab.json';
    const liteUri = FileSystem.documentDirectory + 'sims_lite_model.json';

    // 1. Load Vocab
    try {
      const vInfo = await FileSystem.getInfoAsync(vocabUri);
      if (vInfo.exists) {
        vocab = JSON.parse(await FileSystem.readAsStringAsync(vocabUri));
      } else {
        vocab = require('../../assets/vocab.json');
      }
    } catch (e) { 
      vocab = { "<PAD>": 0, "<OOV>": 1 }; 
    }

    // 2. Load Lite Model (Naive Bayes)
    try {
      const lInfo = await FileSystem.getInfoAsync(liteUri);
      if (lInfo.exists) {
        liteModel = JSON.parse(await FileSystem.readAsStringAsync(liteUri));
        liteLoaded = true;
      }
    } catch (e) {
      console.warn("Lite model not found");
    }

    // 3. Load TFLite Model
    try {
      await tf.ready();
      const mInfo = await FileSystem.getInfoAsync(modelUri);
      const localPath = mInfo.exists ? `file://${modelUri}` : require('../../assets/sims_offline.tflite');
      
      const tflite = require('@tensorflow/tfjs-tflite');
      tfliteModel = await tflite.loadTFLiteModel(localPath);
      modelLoaded = true;
      console.log("TFLite model loaded");
    } catch (e) {
      console.warn("TFLite load failed, falling back to Lite NB", e.message);
    }

    return modelLoaded || liteLoaded;
  } catch (error) {
    console.error("Model load error:", error);
    return false;
  }
};

/**
 * Naive Bayes Inference in JS
 */
function predictLite(text) {
  if (!liteLoaded || !liteModel) return 0.5;
  
  const tokens = text.toLowerCase().split(/\s+/);
  const scores = [...liteModel.class_log_prior];
  
  tokens.forEach(token => {
    if (liteModel.vocab[token] !== undefined) {
      const idx = liteModel.vocab[token];
      scores[0] += liteModel.feature_log_prob[0][idx];
      scores[1] += liteModel.feature_log_prob[1][idx];
    }
  });

  // Softmax
  const maxScore = Math.max(...scores);
  const expScores = scores.map(s => Math.exp(s - maxScore));
  const sumExp = expScores.reduce((a, b) => a + b, 0);
  return expScores[1] / sumExp;
}

/**
 * Run Prediction
 */
export const predictSMSOffline = async (text) => {
  let score = 0.5;
  let mode = "lite";

  if (modelLoaded && tfliteModel) {
    try {
      mode = "tflite";
      // ... TFLite preproc ...
      const cleanText = text.toLowerCase().replace(/[^\w\s]/g, " ");
      const words = cleanText.split(/\s+/);
      const seq = new Int32Array(MAX_LEN);
      for (let i = 0; i < MAX_LEN; i++) {
        if (i < words.length) {
          seq[i] = vocab[words[i]] !== undefined ? vocab[words[i]] : 1;
        } else {
          seq[i] = 0;
        }
      }
      const input = tf.tensor2d([seq], [1, MAX_LEN], 'int32');
      const output = tfliteModel.predict(input);
      const data = await output.data();
      score = data[0];
      input.dispose();
      output.dispose();
    } catch (e) {
      mode = "lite";
      score = predictLite(text);
    }
  } else {
    score = predictLite(text);
  }

  // Final Verdict
  let verdict = "HAM";
  let confidence = "HIGH";
  if (score >= 0.85) { verdict = "SPAM"; }
  else if (score >= 0.60) { verdict = "SUSPICIOUS"; confidence = "MEDIUM"; }

  return {
    request_id: `offline-${Date.now()}`,
    spam_score: Math.round(score * 100) / 100,
    verdict,
    confidence,
    url_threat: false,
    urls_found: text.match(/https?:\/\/\S+/gi) || [],
    url_details: [],
    model_version: "1.0.0-hybrid",
    inference_mode: "offline",
    model_loaded: true,
    timestamp: new Date().toISOString(),
  };
};

export const isOfflineModelLoaded = () => modelLoaded || liteLoaded;
