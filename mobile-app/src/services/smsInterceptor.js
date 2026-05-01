// SIMS SMS Interceptor
// Listens for incoming SMS using expo-notifications data payload
// (full SMS_RECEIVED broadcast requires ejected Expo / native modules).

import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Notifications from 'expo-notifications';

const SCANS_KEY = '@sims_scan_history';

/**
 * Save a scan result to AsyncStorage history.
 */
export async function saveScan(scanResult) {
  try {
    const existing = await AsyncStorage.getItem(SCANS_KEY);
    const history = existing ? JSON.parse(existing) : [];
    history.unshift({ ...scanResult, scannedAt: new Date().toISOString() });
    // keep last 100 scans
    if (history.length > 100) history.length = 100;
    await AsyncStorage.setItem(SCANS_KEY, JSON.stringify(history));
  } catch (e) {
    console.error('Failed to save scan:', e);
  }
}

/**
 * Load scan history from AsyncStorage.
 */
export async function loadScanHistory() {
  try {
    const data = await AsyncStorage.getItem(SCANS_KEY);
    return data ? JSON.parse(data) : [];
  } catch (e) {
    console.error('Failed to load scan history:', e);
    return [];
  }
}

/**
 * Clear all scan history.
 */
export async function clearScanHistory() {
  try {
    await AsyncStorage.removeItem(SCANS_KEY);
  } catch (e) {
    console.error('Failed to clear scans:', e);
  }
}

/**
 * Request SMS permissions & notification permissions.
 * In Expo Go, we rely on notifications for the demo.
 * For production (ejected), use android.permission.RECEIVE_SMS.
 */
export const requestSMSPermissions = async () => {
  const { status } = await Notifications.requestPermissionsAsync();
  return status === 'granted';
};

/**
 * Register a foreground notification handler.
 * When the app is open, this processes incoming notification data.
 */
export const registerSMSListener = (onSMSReceived) => {
  const subscription = Notifications.addNotificationReceivedListener(
    (notification) => {
      const data = notification.request.content.data || {};
      if (data.smsBody && data.smsSender) {
        onSMSReceived({
          sender: data.smsSender,
          body: data.smsBody,
          timestamp: new Date().toISOString(),
        });
      }
    }
  );
  return subscription;
};

/**
 * Simulate an incoming SMS for demo / testing purposes.
 */
export const simulateIncomingSMS = async (sender, body) => {
  await Notifications.scheduleNotificationAsync({
    content: {
      title: 'New SMS',
      body: `${sender}: ${body.slice(0, 60)}...`,
      data: { smsSender: sender, smsBody: body },
    },
    trigger: null, // immediate
  });
};

