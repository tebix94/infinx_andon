import requests

def send_telegram_notification(token, chat_id, message):

    url = f'https://api.telegram.org/bot{token}/sendMessage'
    try:
        response = requests.post(url, json={
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }, timeout=5)
        
        # Log if the API returns an error (e.g., bot blocked, chat not found)
        if not response.ok:
            print(f'Telegram API Error: {response.status_code} - {response.text}')
            
    except Exception as e:
        print(f'Failed to send Telegram message: {e}')