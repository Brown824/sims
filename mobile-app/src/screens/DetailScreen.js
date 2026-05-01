import React, { useRef, useEffect } from 'react';
import { View, StyleSheet, ScrollView, Animated } from 'react-native';
import { Text, Card, Title, Paragraph, Button, useTheme, Divider } from 'react-native-paper';

export default function DetailScreen({ route, navigation }) {
  const { scan } = route.params;
  const theme = useTheme();
  
  // Animated Score Bar
  const scoreAnim = useRef(new Animated.Value(0)).current;
  const scorePercent = (scan.spam_score || 0) * 100;

  useEffect(() => {
    Animated.timing(scoreAnim, {
      toValue: scorePercent,
      duration: 1000,
      useNativeDriver: false,
    }).start();
  }, [scorePercent]);

  const barColor = scoreAnim.interpolate({
    inputRange: [0, 50, 85, 100],
    outputRange: [theme.colors.primary, '#FFD600', theme.colors.error, theme.colors.error]
  });

  const verdictColor = scan.verdict === 'SPAM' ? theme.colors.error : 
                       scan.verdict === 'SUSPICIOUS' ? '#FFD600' : theme.colors.primary;

  return (
    <ScrollView style={styles.container}>
      <Card style={styles.card}>
        <Card.Content>
          <View style={styles.header}>
            <Title>Sender: {scan.sender || 'Unknown'}</Title>
            <Text style={{ color: verdictColor, fontWeight: 'bold', fontSize: 16 }}>{scan.verdict}</Text>
          </View>
          
          <Text style={styles.label}>Score: {scorePercent.toFixed(1)}%</Text>
          <View style={styles.barBackground}>
            <Animated.View style={[styles.barFill, { width: scoreAnim.interpolate({ inputRange: [0, 100], outputRange: ['0%', '100%'] }), backgroundColor: barColor }]} />
          </View>
          
          <Divider style={styles.divider} />
          
          <Text style={styles.label}>Message:</Text>
          <Paragraph style={styles.message}>{scan.sms_text || scan.text || 'No text content'}</Paragraph>
          
          {scan.url_threat && (
            <View style={styles.alertBox}>
              <Text style={styles.alertText}>⚠️ Malicious URL Detected</Text>
            </View>
          )}

          <Divider style={styles.divider} />

          <Text style={styles.label}>Details:</Text>
          <Text style={styles.detailText}>Inference Mode: {scan.inference_mode}</Text>
          <Text style={styles.detailText}>Confidence: {scan.confidence}</Text>
          <Text style={styles.detailText}>Scanned: {new Date(scan.timestamp || scan.scannedAt).toLocaleString()}</Text>

        </Card.Content>
      </Card>

      <Button 
        mode="contained" 
        style={styles.reportBtn} 
        buttonColor="#333"
        onPress={() => navigation.navigate('Report', { scan })}
      >
        Report Mistake
      </Button>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#121212', padding: 16 },
  card: { backgroundColor: '#1E1E1E' },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  label: { fontSize: 14, color: '#888', marginBottom: 4 },
  message: { fontSize: 16, color: '#fff', backgroundColor: '#2C2C2C', padding: 12, borderRadius: 8 },
  divider: { marginVertical: 16, backgroundColor: '#333' },
  detailText: { color: '#ccc', marginBottom: 4 },
  barBackground: { height: 12, backgroundColor: '#333', borderRadius: 6, overflow: 'hidden', marginBottom: 8 },
  barFill: { height: '100%' },
  reportBtn: { marginTop: 24, marginBottom: 40 },
  alertBox: { marginTop: 12, backgroundColor: 'rgba(255, 23, 68, 0.2)', padding: 12, borderRadius: 8, borderWidth: 1, borderColor: '#FF1744' },
  alertText: { color: '#FF1744', fontWeight: 'bold' }
});
