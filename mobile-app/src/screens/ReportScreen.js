import React, { useState } from 'react';
import { View, StyleSheet } from 'react-native';
import { Text, TextInput, Button, Card, Snackbar } from 'react-native-paper';
import { sendFeedback } from '../services/api';

export default function ReportScreen({ route, navigation }) {
  const { scan } = route.params;
  const [comment, setComment] = useState('');
  const [sending, setSending] = useState(false);
  const [visible, setVisible] = useState(false);

  const correctVerdict = scan.verdict === 'SPAM' ? 'HAM' : 'SPAM';

  const submitReport = async () => {
    setSending(true);
    // Send feedback to /feedback API
    await sendFeedback({
      sms_id: scan.request_id,
      user_verdict: correctVerdict,
      original_score: scan.spam_score,
      comment: comment
    });
    setSending(false);
    setVisible(true);
    setTimeout(() => {
      navigation.goBack();
    }, 1500);
  };

  return (
    <View style={styles.container}>
      <Card style={styles.card}>
        <Card.Content>
          <Text variant="titleMedium" style={{ marginBottom: 12 }}>Report Classification Mistake</Text>
          <Text style={styles.text}>The system classified this as <Text style={{fontWeight: 'bold', color: '#FFD600'}}>{scan.verdict}</Text>.</Text>
          <Text style={styles.text}>Are you sure it is <Text style={{fontWeight: 'bold', color: '#00C853'}}>{correctVerdict}</Text>?</Text>
          
          <TextInput
            mode="outlined"
            label="Additional Comments (Optional)"
            value={comment}
            onChangeText={setComment}
            multiline
            numberOfLines={4}
            style={styles.input}
            textColor="#fff"
            theme={{ colors: { background: '#121212' } }}
          />

          <Button 
            mode="contained" 
            onPress={submitReport} 
            loading={sending}
            disabled={sending}
            style={styles.btn}
          >
            Submit Report
          </Button>
        </Card.Content>
      </Card>
      
      <Snackbar visible={visible} onDismiss={() => setVisible(false)} duration={1500}>
        Feedback submitted successfully!
      </Snackbar>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#121212', padding: 16 },
  card: { backgroundColor: '#1E1E1E' },
  text: { color: '#ccc', marginBottom: 8, fontSize: 16 },
  input: { marginTop: 16, marginBottom: 24, backgroundColor: '#121212' },
  btn: { paddingVertical: 4 }
});
