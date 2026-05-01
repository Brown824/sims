// SIMS API Client
// Communicates with the FastAPI backend.

import axios from 'axios';

// Update this to your backend URL (use ngrok or local IP for physical device)
const BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Send SMS to cloud backend for classification.
 */
export const predictSMSCloud = async (text, phone) => {
  try {
    const response = await api.post('/predict', {
      sms_text: text,
      phone_number: phone,
    });
    return response.data;
  } catch (error) {
    console.error('Cloud inference failed:', error.message);
    throw error;
  }
};

/**
 * Check if backend is online and healthy.
 */
export const checkHealth = async () => {
  try {
    const response = await api.get('/health');
    return response.data.status === 'ok';
  } catch {
    return false;
  }
};

import { predictSMSOffline, isOfflineModelLoaded } from './offlineModel';
import { saveScan } from './smsInterceptor';
import AsyncStorage from '@react-native-async-storage/async-storage';

/**
 * Submit user feedback for a previous prediction.
 */
export const sendFeedback = async (feedbackData) => {
  try {
    const response = await api.post('/feedback', {
      sms_id: feedbackData.smsId,
      user_verdict: feedbackData.userVerdict,
      original_score: feedbackData.originalScore,
      comment: feedbackData.comment,
    });
    return response.data;
  } catch (error) {
    console.error('Feedback submission failed:', error.message);
    throw error;
  }
};

/**
 * Smart prediction that checks settings, tries cloud, and falls back to offline.
 */
export const predictSMS = async (text, phone) => {
  let result;
  try {
    const savedOffline = await AsyncStorage.getItem('@sims_offline_mode');
    const forceOffline = savedOffline === 'true';

    if (forceOffline) {
      result = await predictSMSOffline(text);
    } else {
      try {
        result = await predictSMSCloud(text, phone);
      } catch (err) {
        console.warn("Cloud prediction failed, falling back to offline", err);
        result = await predictSMSOffline(text);
      }
    }
  } catch (err) {
    result = await predictSMSOffline(text);
  }

  // Save the final result to history
  await saveScan({
    ...result,
    sms_text: text,
    sender: phone || "Unknown",
    timestamp: new Date().toISOString()
  });

  return result;
};

/**
 * Bilingual (Swahili + English) notification messages.
 */
export const getNotificationText = (verdict, lang = 'sw') => {
  const messages = {
    SPAM: {
      sw: '🚨 Ujumbe hatari umegunduliwa! SIMS imezuia spam.',
      en: '🚨 Threat detected! SIMS blocked spam.',
    },
    SUSPICIOUS: {
      sw: '⚠️ Ujumbe mashaka. Tafadhali kuwa mwangalifu.',
      en: '⚠️ Suspicious message. Please be cautious.',
    },
    HAM: {
      sw: '✅ Ujumbe salama.',
      en: '✅ Message is safe.',
    },
  };
  return messages[verdict]?.[lang] || messages[verdict]?.['en'] || '';
};

export const getVerdictLabel = (verdict, lang = 'sw') => {
  const labels = {
    SPAM: { sw: 'SPAM / UJUMBE HATARI', en: 'SPAM / THREAT' },
    SUSPICIOUS: { sw: 'SUSPICIOUS / MASHAKA', en: 'SUSPICIOUS' },
    HAM: { sw: 'HAM / SALAMA', en: 'SAFE' },
  };
  return labels[verdict]?.[lang] || verdict;
};

