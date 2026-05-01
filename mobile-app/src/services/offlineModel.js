// SIMS Offline Model — TFLite Inference
// Uses @tensorflow/tfjs-react-native for on-device spam detection.

import * as tf from '@tensorflow/tfjs';
import { bundleResourceIO } from '@tensorflow/tfjs-react-native';
import '@tensorflow/tfjs-react-native';

import * as FileSystem from 'expo-file-system';
import AsyncStorage from '@react-native-async-storage/async-storage';

let tfliteModel = null;
let vocab = null;
let modelLoaded = false;

const MAX_LEN = 150;

/**
 * Sync the latest model from the cloud backend.
 */
export const syncOfflineModel = async () => {
  try {
    const savedUrl = await AsyncStorage.getItem('@sims_api_url') || 'http://10.0.2.2:8000';
    console.log("Checking for updated model at:", savedUrl);
    
    const modelUri = FileSystem.documentDirectory + 'sims_offline.tflite';
    const vocabUri = FileSystem.documentDirectory + 'vocab.json';

    // Download latest TFLite and Vocab
    await FileSystem.downloadAsync(`${savedUrl}/api/predict/model/latest`, modelUri);
    await FileSystem.downloadAsync(`${savedUrl}/api/predict/model/vocab`, vocabUri);
    
    console.log("Offline models synced successfully from cloud!");
    return { modelUri, vocabUri };
  } catch (error) {
    console.warn("Failed to sync model from cloud. Relying on local assets.", error.message);
    return null;
  }
};

/**
 * Load the TFLite model and vocab.
 */
export const loadOfflineModel = async () => {
  try {
    await tf.ready();
    console.log("TensorFlow.js ready for React Native");

    // Attempt to sync first if online (in background)
    // We will just try loading what we have
    const modelUri = FileSystem.documentDirectory + 'sims_offline.tflite';
    const vocabUri = FileSystem.documentDirectory + 'vocab.json';
    
    let localModelPath = null;
    let localVocabPath = null;

    const mInfo = await FileSystem.getInfoAsync(modelUri);
    const vInfo = await FileSystem.getInfoAsync(vocabUri);

    if (mInfo.exists && vInfo.exists) {
      localModelPath = `file://${modelUri}`;
      const vocabStr = await FileSystem.readAsStringAsync(vocabUri);
      vocab = JSON.parse(vocabStr);
    } else {
      // Fallback to assets
      try {
        vocab = require('../../assets/vocab.json');
      } catch (e) {
        vocab = { "<PAD>": 0, "<OOV>": 1 };
      }
      localModelPath = require('../../assets/sims_offline.tflite');
    }

    // Load TFLite Model
    try {
      const tflite = require('@tensorflow/tfjs-tflite');
      tfliteModel = await tflite.loadTFLiteModel(localModelPath);
      modelLoaded = true;
      console.log("Offline TFLite model loaded successfully");
    } catch (e) {
      console.warn("Could not load sims_offline.tflite, falling back to heuristic", e);
      modelLoaded = false;
    }

    return modelLoaded;
  } catch (error) {
    console.error("Failed to load offline model:", error);
    modelLoaded = false;
    return false;
  }
};

/**
 * Preprocess text exactly like the Python backend
 */
function preprocess(text) {
  let cleanText = text.toLowerCase();
  cleanText = cleanText.replace(/https?:\/\/\S+|www\.\S+/gi, " url_token ");
  cleanText = cleanText.replace(/\+?\d[\d\s\-]{7,}\d/g, " phone_token ");
  
  // Simple punctuation removal
  cleanText = cleanText.replace(/[!"#$%&'()*+,\-.\/:;<=>?@[\\\]^_`{|}~]/g, " ");
  cleanText = cleanText.replace(/\s+/g, ' ').trim();

  const words = cleanText.split(' ');
  const seq = [];
  for (let i = 0; i < MAX_LEN; i++) {
    if (i < words.length) {
      seq.push(vocab[words[i]] !== undefined ? vocab[words[i]] : 1); // 1 is <OOV>
    } else {
      seq.push(0); // 0 is <PAD>
    }
  }
  return tf.tensor2d([seq], [1, MAX_LEN], 'int32');
}

/**
 * Simple heuristic-based prediction when TFLite model is not yet available.
 */
function heuristicPredict(text) {
  const lower = text.toLowerCase();
  const spamKeywords = [
    "umeshinda", "zawadi", "bonyeza hapa", "tuma pesa", "nambari",
    "akaunti imezuiwa", "thibitisha", "bila malipo", "haraka",
    "winner", "free", "click here", "claim now", "urgent",
    "verify account", "bank suspended", "password reset",
    "lottery", "prize", "send money", "reply now"
  ];

  let score = 0.1;
  spamKeywords.forEach(kw => {
    if (lower.includes(kw)) score += 0.15;
  });

  if (/https?:\/\/\S+/i.test(lower)) score += 0.2;
  if (/\+?\d[\d\s\-]{7,}\d/.test(lower)) score += 0.1;
  if (/\b(haraka|urgent|sasa hivi|leo tu|immediately)\b/i.test(lower)) score += 0.1;

  score = Math.min(score, 0.99);

  if (score >= 0.85) return { verdict: "SPAM", spam_score: score, confidence: "HIGH" };
  if (score >= 0.60) return { verdict: "SUSPICIOUS", spam_score: score, confidence: "MEDIUM" };
  return { verdict: "HAM", spam_score: score, confidence: "HIGH" };
}

/**
 * Run offline spam detection.
 */
export const predictSMSOffline = async (text) => {
  let result;
  
  if (!modelLoaded || !tfliteModel) {
    console.warn("Offline model not loaded yet — using heuristic fallback.");
    result = heuristicPredict(text);
  } else {
    try {
      const inputTensor = preprocess(text);
      const outputTensor = tfliteModel.predict(inputTensor);
      const scoreArray = await outputTensor.data();
      const score = scoreArray[0];
      
      // Cleanup tensors
      inputTensor.dispose();
      outputTensor.dispose();

      let verdict = "HAM";
      let confidence = "HIGH";
      if (score >= 0.85) { verdict = "SPAM"; }
      else if (score >= 0.60) { verdict = "SUSPICIOUS"; confidence = "MEDIUM"; }

      result = { verdict, spam_score: score, confidence };
    } catch (e) {
      console.error("Inference error:", e);
      result = heuristicPredict(text);
    }
  }

  return {
    request_id: `offline-${Date.now()}`,
    spam_score: Math.round(result.spam_score * 100) / 100,
    verdict: result.verdict,
    confidence: result.confidence,
    url_threat: false,
    urls_found: text.match(/https?:\/\/\S+/gi) || [],
    url_details: [],
    model_version: "1.0.0-offline",
    inference_mode: "offline",
    model_loaded: modelLoaded,
    timestamp: new Date().toISOString(),
  };
};

export const isOfflineModelLoaded = () => modelLoaded;

