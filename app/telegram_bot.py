import requests
import os

def send_telegram_notification(token, chat_id, message, image_path):

    if image_path:
        url = f'https://api.telegram.org/bot{token}/sendPhoto'
        data = {'chat_id': chat_id, 'caption': message, 'parse_mode': 'HTML'}
    else:
        url = f'https://api.telegram.org/bot{token}/sendMessage'
        data = {'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}

    if image_path:
        try:
            # Open the image file in binary mode
            with open(image_path, 'rb') as image_file:
                files = {
                    'photo': image_file
                }
            
                # Send the request
                response = requests.post(url, data=data, files=files, timeout=5)
                
                # Log if the API returns an error (e.g., bot blocked, chat not found)
                if not response.ok:
                    print(f'Telegram API Error: {response.status_code} - {response.text}')
                    
        except Exception as e:
            print(f"An error occurred: {e}")
        
        finally:
            # This will run regardless of whether the request succeeded or failed
            if os.path.exists(image_path):
                os.remove(image_path)
                print("Temporary image file deleted.")
    else:
        try:
         # Send the request
            response = requests.post(url, data=data, timeout=5)
            
            # Log if the API returns an error (e.g., bot blocked, chat not found)
            if not response.ok:
                print(f'Telegram API Error: {response.status_code} - {response.text}')
        except Exception as e:
            print(f"An error occurred: {e}")