import React, { useState, useEffect } from 'react';
import { View, StyleSheet } from 'react-native';
import { Text, Switch, TextInput, Button, Card, useTheme } from 'react-native-paper';
import AsyncStorage from '@react-native-async-storage/async-storage';

export default function SettingsScreen({ navigation }) {
  const [offlineMode, setOfflineMode] = useState(false);
  const [apiUrl, setApiUrl] = useState('http://10.0.2.2:8000');
  const theme = useTheme();

  useEffect(() => {
    const loadSettings = async () => {
      const savedOffline = await AsyncStorage.getItem('@sims_offline_mode');
      const savedUrl = await AsyncStorage.getItem('@sims_api_url');
      if (savedOffline !== null) setOfflineMode(savedOffline === 'true');
      if (savedUrl) setApiUrl(savedUrl);
    };
    loadSettings();
  }, []);

  const saveSettings = async () => {
    await AsyncStorage.setItem('@sims_offline_mode', String(offlineMode));
    await AsyncStorage.setItem('@sims_api_url', apiUrl);
    navigation.goBack();
  };

  return (
    <View style={styles.container}>
      <Card style={styles.card}>
        <Card.Content>
          <View style={styles.row}>
            <Text variant="titleMedium">Force Offline Mode</Text>
            <Switch value={offlineMode} onValueChange={setOfflineMode} color={theme.colors.primary} />
          </View>
          <Text style={styles.desc}>Uses local TFLite model even when internet is available. Saves data but uses older heuristic/model.</Text>
        </Card.Content>
      </Card>

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
          />
          <Text style={styles.desc}>Backend FastAPI server address. Use http://10.0.2.2:8000 for Android emulator.</Text>
        </Card.Content>
      </Card>

      <Button mode="contained" onPress={saveSettings} style={styles.btn}>Save Settings</Button>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#121212', padding: 16 },
  card: { backgroundColor: '#1E1E1E', marginBottom: 16 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  desc: { color: '#888', fontSize: 12 },
  input: { marginBottom: 8, backgroundColor: '#121212' },
  btn: { marginTop: 16, paddingVertical: 4 }
});
