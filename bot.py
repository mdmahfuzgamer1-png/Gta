import requests
import re
import time
import os
from bs4 import BeautifulSoup
from telegram import Bot

# ==================== আপনার দেওয়া তথ্য (হার্ডকোডেড) ====================
EMAIL = "mdmahfuzgames@gmail.com"
PASSWORD = "Mahfuz890@"
BOT_TOKEN = "8886694697:AAE3PQY5YKSONfFv1MdYs9VZ3kGnSeI8GzA"
CHAT_ID = "-1004338662160"

# ==================== সেশন ও বট ====================
session = requests.Session()
bot = Bot(token=BOT_TOKEN)

# ==================== ১. লগইন ====================
def login():
    print("⏳ লগইন করছি...")
    try:
        res = session.get("https://www.ivasms.com/login")
        soup = BeautifulSoup(res.text, 'html.parser')
        token_input = soup.find('input', {'name': '_token'})
        if not token_input:
            return False
        token = token_input.get('value')
        payload = {'_token': token, 'email': EMAIL, 'password': PASSWORD}
        response = session.post("https://www.ivasms.com/login", data=payload)
        if "portal" in response.url or "dashboard" in response.url:
            print("✅ লগইন সফল!")
            return True
        return False
    except Exception as e:
        print(f"❌ লগইন এরর: {e}")
        return False

# ==================== ২. টোকেন, নম্বর ও রেঞ্জ বের করা (ডায়নামিক) ====================
def get_portal_data():
    try:
        res = session.get("https://www.ivasms.com/portal")
        html = res.text

        # সেশন এক্সপায়ার চেক
        if "Account Login" in html or 'name="email"' in html:
            print("⚠️ সেশন এক্সপায়ার!")
            return None, None, None

        soup = BeautifulSoup(html, 'html.parser')

        # ----- A. টোকেন বের করা -----
        token_match = re.search(r'_token:"([^"]+)"', html)
        if not token_match:
            token_inp = soup.find('input', {'name': '_token'})
            token = token_inp.get('value') if token_inp else None
        else:
            token = token_match.group(1)

        # ----- B. নম্বর লিস্ট বের করা -----
        number_divs = soup.find_all('div', class_='c-item')
        numbers = []
        for div in number_divs:
            onclick = div.get('onclick', '')
            match = re.search(r"toggleNumhbcyu\('(\d+)'", onclick)
            if match:
                numbers.append(match.group(1))

        # ----- C. রেঞ্জ বের করা (ডায়নামিক) -----
        range_value = None

        # ১. হিডেন ইনপুট থেকে খোঁজা
        range_input = soup.find('input', {'name': 'range'})
        if range_input:
            range_value = range_input.get('value')
        
        # ২. সিলেক্ট বক্স থেকে খোঁজা (সিলেক্টেড অপশন)
        if not range_value:
            range_select = soup.find('select', {'name': 'range'})
            if range_select:
                selected = range_select.find('option', {'selected': True})
                if selected:
                    range_value = selected.get('value')
                if not range_value:
                    range_value = range_select.get('value')

        # ৩. জাভাস্ক্রিপ্ট ভেরিয়েবল থেকে খোঁজা
        if not range_value:
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    match = re.search(r"Range\s*[:=]\s*['\"]([^'\"]+)", script.string)
                    if match:
                        range_value = match.group(1)
                        break

        # ৪. পেজের টেক্সট থেকে প্রথম "BANGLADESH" খোঁজা (ব্যাকআপ)
        if not range_value:
            page_text = soup.get_text()
            match = re.search(r'(BANGLADESH\s+\d+)', page_text)
            if match:
                range_value = match.group(1)

        # ৫. যদি কিছুই না পাই, তাহলে ডিফল্ট (যাতে কোড ক্র্যাশ না করে)
        if not range_value:
            print("⚠️ রেঞ্জ খুঁজে পাওয়া যায়নি, ডিফল্ট ব্যবহার করছি: BANGLADESH 67122")
            range_value = "BANGLADESH 67122"

        print(f"📌 বর্তমান রেঞ্জ: {range_value}")
        print(f"📋 {len(numbers)} টি নম্বর পাওয়া গেছে")

        if not token or not numbers:
            return None, None, None

        return token, numbers, range_value

    except Exception as e:
        print(f"❌ ডেটা আনার এরর: {e}")
        return None, None, None

# ==================== ৩. এসএমএস ফেচ করা (ডায়নামিক রেঞ্জ সহ) ====================
def fetch_sms_for_number(token, number, date, range_val):
    api_url = "https://www.ivasms.com/portal/sms/received/getsms/number/sms"
    params = {
        '_token': token,
        'start': date,
        'end': date,
        'Number': number,
        'Range': range_val   # এখানে ডায়নামিক ভ্যালু ব্যবহার হচ্ছে
    }
    try:
        response = session.get(api_url, params=params, timeout=15)
        if response.status_code == 200:
            return response.text
        return None
    except Exception as e:
        print(f"API কল এরর ({number}): {e}")
        return None

# ==================== ৪. মেইন লুপ ====================
def main():
    if not login():
        print("⏳ ৩০ সেকেন্ড পর পুনরায় চেষ্টা...")
        time.sleep(30)
        return

    sent_codes = set()
    today = time.strftime("%Y-%m-%d")
    print(f"🚀 মনিটরিং শুরু! ({today})")

    while True:
        try:
            token, numbers, range_val = get_portal_data()

            # যদি ডেটা না পাই, রিলগইন করি
            if not token or not numbers:
                print("🔄 সেশন রিফ্রেশ করা হচ্ছে...")
                if login():
                    token, numbers, range_val = get_portal_data()
                    if not token or not numbers:
                        time.sleep(10)
                        continue
                else:
                    time.sleep(30)
                    continue

            # প্রতিটি নম্বরের জন্য SMS চেক
            for num in numbers:
                sms_data = fetch_sms_for_number(token, num, today, range_val)
                if sms_data:
                    # কোড খোঁজা (যেমন: GoChat Code: 642805)
                    codes = re.findall(r'GoChat Code: (\d+)', sms_data)
                    for code in codes:
                        if code not in sent_codes:
                            msg = f"📩 নম্বর: {num}\n🔑 কোড: {code}"
                            bot.send_message(chat_id=CHAT_ID, text=msg)
                            sent_codes.add(code)
                            print(f"✅ পাঠানো হয়েছে: {msg}")
                time.sleep(1)  # রেট লিমিট এড়াতে

            time.sleep(15)  # ১৫ সেকেন্ড পর আবার চেক

        except Exception as e:
            print(f"⚠️ মেইন লুপে এরর: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()