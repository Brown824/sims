import React, { useState, useEffect } from 'react';
import { View, StyleSheet, Alert } from 'react-native';
import { Text, Switch, TextInput, Button, Card, useTheme, ActivityIndicator } from 'react-native-paper';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { syncOfflineModel, loadOfflineModel, isOfflineModelLoaded } from '../services/offlineModel';
import { checkHealth } from '../services/api';

export default function SettingsScreen({ navigation }) {
  const [offlineMode, setOfflineMode] = useState(false);
  const [apiUrl, setApiUrl] = useState('http://10.0.2.2:8000');
  const [syncing, setSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState('');
  const [modelLoaded, setModelLoaded] = useState(false);
  const theme = useTheme();

  useEffect(() => {
    const loadSettings = async () => {
      const savedOffline = await AsyncStorage.getItem('@sims_offline_mode');
      const savedUrl = await AsyncStorage.getItem('@sims_api_url');
      if (savedOffline !== null) setOfflineMode(savedOffline === 'true');
      if (savedUrl) setApiUrl(savedUrl);
      setModelLoaded(isOfflineModelLoaded());
    };
    loadSettings();
  }, []);

  const saveSettings = async () => {
    await AsyncStorage.setItem('@sims_offline_mode', String(offlineMode));
    await AsyncStorage.setItem('@sims_api_url', apiUrl);
    Alert.alert('Saved', 'Settings saved successfully!');
    navigation.goBack();
  };

  const handleSyncModel = async () => {
    setSyncing(true);
    setSyncStatus('Checking backend connection...');
    try {
      const healthy = await checkHealth();
      if (!healthy) {
        setSyncStatus('Backend offline. Cannot sync.');
        setSyncing(false);
        return;
      }
      setSyncStatus('Downloading latest model...');
      const result = await syncOfflineModel();
      if (result) {
        setSyncStatus('Loading new model into memory...');
        await loadOfflineModel();
        setModelLoaded(isOfflineModelLoaded());
        setSyncStatus('Model synced successfully!');
      } else {
        setSyncStatus('Sync failed. Check backend URL.');
      }
    } catch (e) {
      setSyncStatus(`Error: ${e.message}`);
    } finally {
      setSyncing(false);
    }
  };

  return (
    <View style={styles.container}>
      {/* Offline Mode Toggle */}
      <Card style={styles.card}>
        <Card.Content>
          <View style={styles.row}>
            <Text variant="titleMedium">Force Offline Mode</Text>
            <Switch value={offlineMode} onValueChange={setOfflineMode} color={theme.colors.primary} />
          </View>
          <Text style={styles.desc}>Uses local TFLite model even when internet is available. Useful for low-data environments.</Text>
        </Card.Content>
      </Card>

      {/* API URL */}
      <Card style={styles.card}>
        <Card.Content>
          <Text variant="titleMedium" style={{ marginBottom: 8 }}>Cloud API URL</Text>
          <TextInput
            mode="outlined"
            value={apiUrl}
            onChangeText={setApiUrl}
            style={styles.input}
            textColor="#fff"
            theme={{ colors: { background: '#121212' } }}
            placeholder="http://10.0.2.2:8000"
          />
          <Text style={styles.desc}>Backend FastAPI address. Use 10.0.2.2:8000 for Android emulator, or your server's public IP.</Text>
        </Card.Content>
      </Card>

      {/* Model Sync */}
      <Card style={styles.card}>
        <Card.Content>
          <Text variant="titleMedium" style={{ marginBottom: 4 }}>Offline Model</Text>
          <View style={styles.row}>
            <Text style={styles.desc}>
              Status: <Text style={{ color: modelLoaded ? theme.colors.primary : '#FFD600' }}>
                {modelLoaded ? 'Loaded (TFLite)' : 'Heuristic Fallback'}
              </Text>
            </Text>
          </View>
          <Text style={styles.desc} numberOfLines={2}>{syncStatus}</Text>
          {syncing && <ActivityIndicator animating color={theme.colors.primary} style={{ marginVertical: 8 }} />}
          <Button
            mode="outlined"
            onPress={handleSyncModel}
            disabled={syncing}
            style={{ marginTop: 8 }}
            textColor={theme.colors.primary}
          >
            Sync Latest Model from Cloud
          </Button>
        </Card.Content>
      </Card>

      <Button mode="contained" onPress={saveSettings} style={styles.btn}>
        Save Settings
      </Button>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#121212', padding: 16 },
  card: { backgroundColor: '#1E1E1E', marginBottom: 16 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  desc: { color: '#888', fontSize: 12, marginBottom: 4 },
  input: { marginBottom: 8, backgroundColor: '#121212' },
  btn: { marginTop: 8, paddingVertical: 4 },
});
