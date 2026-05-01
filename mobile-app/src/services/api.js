// SIMS API Client
// Communicates with the FastAPI backend. Base URL is read dynamically
// from AsyncStorage so the Settings screen can change it at runtime.

import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { predictSMSOffline } from './offlineModel';
import { saveScan } from './smsInterceptor';

const DEFAULT_API_URL = 'http://10.0.2.2:8000';

/**
 * Return an axios instance pointed at the user-configured backend URL.
 */
const getApi = async () => {
  const savedUrl = await AsyncStorage.getItem('@sims_api_url');
  const baseURL = savedUrl || DEFAULT_API_URL;
  return axios.create({
    baseURL,
    timeout: 15000,
    headers: { 'Content-Type': 'application/json' },
  });
};

// ── Cloud Prediction ──────────────────────────────────────────────────────────

/**
 * Send SMS to cloud backend for classification.
 */
export const predictSMSCloud = async (text, phone) => {
  const api = await getApi();
  const response = await api.post('/api/predict', {
    sms_text: text,
    phone_number: phone,
  });
  return response.data;
};

// ── Health Check ─────────────────────────────────────────────────────────────

/**
 * Check if backend is online and healthy.
 */
export const checkHealth = async () => {
  const api = await getApi();
  try {
    const response = await api.get('/health');
    return response.data.status === 'ok';
  } catch {
    return false;
  }
};

// ── Feedback ──────────────────────────────────────────────────────────────────

/**
 * Submit user feedback for a previous prediction.
 */
export const sendFeedback = async (feedbackData) => {
  const api = await getApi();
  try {
    const response = await api.post('/api/feedback', {
      request_id: feedbackData.sms_id,
      reported_verdict: feedbackData.user_verdict,
      original_verdict: feedbackData.original_verdict,
      user_comment: feedbackData.comment,
    });
    return response.data;
  } catch (error) {
    console.error('Feedback submission failed:', error.message);
    // Don't throw — feedback is non-critical
    return null;
  }
};

// ── Smart Hybrid Prediction ───────────────────────────────────────────────────

/**
 * Smart prediction: checks settings, tries cloud, falls back to offline TFLite/heuristic.
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
        console.warn('Cloud prediction failed, falling back to offline:', err.message);
        result = await predictSMSOffline(text);
      }
    }
  } catch (err) {
    console.error('predictSMS total failure:', err.message);
    result = await predictSMSOffline(text);
  }

  // Persist to local scan history
  await saveScan({
    ...result,
    sms_text: text,
    sender: phone || 'Unknown',
    timestamp: new Date().toISOString(),
  });

  return result;
};

// ── Bilingual Helpers ─────────────────────────────────────────────────────────

/**
 * Bilingual (Swahili + English) notification messages.
 */
export const getNotificationText = (verdict, lang = 'sw') => {
  const messages = {
    SPAM: {
      sw: 'Ujumbe hatari umegunduliwa! SIMS imezuia spam.',
      en: 'Threat detected! SIMS blocked spam.',
    },
    SUSPICIOUS: {
      sw: 'Ujumbe mashaka. Tafadhali kuwa mwangalifu.',
      en: 'Suspicious message. Please be cautious.',
    },
    HAM: {
      sw: 'Ujumbe salama.',
      en: 'Message is safe.',
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
