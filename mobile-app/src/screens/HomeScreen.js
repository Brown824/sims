import React, { useState, useEffect } from 'react';
import { View, FlatList, StyleSheet, RefreshControl } from 'react-native';
import { Text, Card, Title, Paragraph, useTheme, Badge, IconButton, FAB } from 'react-native-paper';
import { loadScanHistory, clearScanHistory, registerSMSListener } from '../services/smsInterceptor';
import { predictSMS } from '../services/api';

export default function HomeScreen({ navigation }) {
  const [scans, setScans] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const theme = useTheme();

  const fetchHistory = async () => {
    const history = await loadScanHistory();
    setScans(history);
  };

  useEffect(() => {
    fetchHistory();
    const unsubscribe = navigation.addListener('focus', () => {
      fetchHistory();
    });
    
    // Register background/foreground SMS listener
    const smsSub = registerSMSListener(async (smsData) => {
       await predictSMS(smsData.body, smsData.sender);
       fetchHistory();
    });

    return () => {
      unsubscribe();
      smsSub.remove();
    };
  }, [navigation]);

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchHistory();
    setRefreshing(false);
  };

  const spamCount = scans.filter(s => s.verdict === 'SPAM').length;

  const renderItem = ({ item }) => {
    const color = item.verdict === 'SPAM' ? theme.colors.error : 
                  item.verdict === 'SUSPICIOUS' ? '#FFD600' : theme.colors.primary;

    return (
      <Card style={styles.card} onPress={() => navigation.navigate('Detail', { scan: item })}>
        <Card.Content>
          <View style={styles.cardHeader}>
            <Title style={{ fontSize: 16 }}>{item.sender || 'Unknown Sender'}</Title>
            <Badge style={{ backgroundColor: color, paddingHorizontal: 8 }}>{item.verdict}</Badge>
          </View>
          <Paragraph numberOfLines={2} style={styles.snippet}>{item.sms_text || item.text || 'No content'}</Paragraph>
          <Text style={styles.time}>{new Date(item.timestamp || item.scannedAt).toLocaleString()}</Text>
        </Card.Content>
      </Card>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <Text variant="titleMedium">Recent Scans</Text>
        <View style={styles.badgeRow}>
          <Text>Spam Blocked: </Text>
          <Badge>{spamCount}</Badge>
          <IconButton icon="cog" onPress={() => navigation.navigate('Settings')} />
        </View>
      </View>
      
      {scans.length === 0 ? (
        <View style={styles.emptyState}>
          <IconButton icon="message-text-outline" size={60} />
          <Text variant="titleMedium">No Scans Yet</Text>
          <Text style={{ textAlign: 'center', marginTop: 8 }}>
            Incoming SMS will be automatically scanned and appear here.
          </Text>
        </View>
      ) : (
        <FlatList
          data={scans}
          keyExtractor={(item, index) => item.request_id || index.toString()}
          renderItem={renderItem}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#fff" />}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#121212', padding: 16 },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  badgeRow: { flexDirection: 'row', alignItems: 'center' },
  card: { marginBottom: 12, backgroundColor: '#1E1E1E' },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  snippet: { color: '#bbb', marginBottom: 8 },
  time: { fontSize: 12, color: '#888' },
  emptyState: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 32 },
});
