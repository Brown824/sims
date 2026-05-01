import React, { useEffect, useState } from 'react';
import { NavigationContainer, DarkTheme } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Provider as PaperProvider, MD3DarkTheme } from 'react-native-paper';
import { StatusBar } from 'expo-status-bar';

// Screens
import HomeScreen from './src/screens/HomeScreen';
import DetailScreen from './src/screens/DetailScreen';
import SettingsScreen from './src/screens/SettingsScreen';
import ReportScreen from './src/screens/ReportScreen';

// Services
import { loadOfflineModel } from './src/services/offlineModel';
import { requestSMSPermissions } from './src/services/smsInterceptor';

const Stack = createNativeStackNavigator();

const customDarkTheme = {
  ...MD3DarkTheme,
  colors: {
    ...MD3DarkTheme.colors,
    primary: '#00C853',
    background: '#121212',
    surface: '#1E1E1E',
  },
};

export default function App() {
  const [modelReady, setModelReady] = useState(false);

  useEffect(() => {
    async function init() {
      await requestSMSPermissions();
      await loadOfflineModel();
      setModelReady(true);
    }
    init();
  }, []);

  if (!modelReady) {
    return null; // Or a splash screen
  }

  return (
    <PaperProvider theme={customDarkTheme}>
      <NavigationContainer theme={DarkTheme}>
        <StatusBar style="light" />
        <Stack.Navigator 
          initialRouteName="Home"
          screenOptions={{
            headerStyle: { backgroundColor: '#1E1E1E' },
            headerTintColor: '#fff',
          }}
        >
          <Stack.Screen name="Home" component={HomeScreen} options={{ title: 'SIMS' }} />
          <Stack.Screen name="Detail" component={DetailScreen} options={{ title: 'SMS Details' }} />
          <Stack.Screen name="Settings" component={SettingsScreen} options={{ title: 'Settings' }} />
          <Stack.Screen name="Report" component={ReportScreen} options={{ title: 'Report Mistake' }} />
        </Stack.Navigator>
      </NavigationContainer>
    </PaperProvider>
  );
}
