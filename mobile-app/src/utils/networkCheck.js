import * as Network from 'expo-network';

// Phase 5: Helper to detect WiFi/Cellular vs Offline
export const isOnline = async () => {
  try {
    const networkState = await Network.getNetworkStateAsync();
    return networkState.isConnected && networkState.isInternetReachable;
  } catch {
    return false;
  }
};
