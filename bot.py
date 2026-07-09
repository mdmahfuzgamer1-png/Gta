import requests
import re
import time
import os
from bs4 import BeautifulSoup
from telegram import Bot

# ==================== আপনার তথ্য ====================
EMAIL = "mdmahfuzgames@gmail.com"
PASSWORD = "Mahfuz890@"
BOT_TOKEN = "8886694697:AAE3PQY5YKSONfFv1MdYs9VZ3kGnSeI8GzA"
CHAT_ID = "-1004338662160"

# ==================== সেশন ও বট ====================
session = requests.Session()
# ব্রাউজারের মতো দেখাতে User-Agent যোগ করা (Cloudflare এড়াতে)
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
})

bot = Bot(token=BOT_TOKEN)

# ==================== ১. লগইন (আপডেটেড + এরর ডিটেকশন) ====================
def login():
    print("⏳ লগইন করছি...")
    try:
        # লগইন পেজ থেকে CSRF টোকেন নেওয়া
        res = session.get("https://www.ivasms.com/login", timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        token_input = soup.find('input', {'name': '_token'})
        if not token_input:
            print("❌ পেজে _token খুঁজে পাওয়া যায়নি!")
            return False
        
        token = token_input.get('value')
        payload = {
            '_token': token,
            'email': EMAIL,
            'password': PASSWORD
        }
        
        # লগইন রিকোয়েস্ট পাঠানো
        response = session.post("https://www.ivasms.com/login", data=payload, timeout=10)
        
        # সফল লগইন চেক করার ২টি উপায়:
        # ১. URL এ 'portal' আছে কিনা
        # ২. রেসপন্সের বডিতে 'Account Login' (লগইন ফর্ম) নেই কিনা
        if "portal" in response.url:
            print("✅ লগইন সফল!")
            return True
        elif "Account Login" in response.text:
            print(f"❌ লগইন ব্যর্থ! (স্ট্যাটাস কোড: {response.status_code}) - হয়তো ইমেইল/পাসওয়ার্ড ভুল অথবা ক্যাপচা ব্লক করছে।")
            return False
        else:
            # অজানা রেসপন্স
            print(f"⚠️ অজানা রেসপন্স! স্ট্যাটাস: {response.status_code}, URL: {response.url}")
            return False

    except requests.exceptions.Timeout:
        print("❌ লগইন টাইমআউট! (সাইট সাড়া দিচ্ছে না)")
        return False
    except Exception as e:
        print(f"❌ লগইন এরর: {e}")
        return False

# ==================== ২. টোকেন, নম্বর ও রেঞ্জ বের করা ====================
def get_portal_data():
    try:
        res = session.get("https://www.ivasms.com/portal", timeout=10)
        html = res.text

        # সেশন এক্সপায়ার চেক (লগইন ফর্ম দেখলে বুঝবেন)
        if "Account Login" in html or 'name="email"' in html:
            print("⚠️ সেশন এক্সপায়ার!")
            return None, None, None

        soup = BeautifulSoup(html, 'html.parser')

        # টোকেন
        token_match = re.search(r'_token:"([^"]+)"', html)
        if not token_match:
            token_inp = soup.find('input', {'name': '_token'})
            token = token_inp.get('value') if token_inp else None
        else:
            token = token_match.group(1)

        # নম্বর লিস্ট
        number_divs = soup.find_all('div', class_='c-item')
        numbers = []
        for div in number_divs:
            onclick = div.get('onclick', '')
            match = re.search(r"toggleNumhbcyu\('(\d+)'", onclick)
            if match:
                numbers.append(match.group(1))

        # রেঞ্জ ডিটেক্ট (ডায়নামিক)
        range_val = None
        range_select = soup.find('select', {'name': 'range'})
        if range_select:
            selected = range_select.find('option', {'selected': True})
            if selected:
                range_val = selected.get('value')
        if not range_val:
            range_input = soup.find('input', {'name': 'range'})
            if range_input:
                range_val = range_input.get('value')
        if not range_val:
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    match = re.search(r"Range\s*[:=]\s*['\"]([^'\"]+)", script.string)
                    if match:
                        range_val = match.group(1)
                        break
        if not range_val:
            page_text = soup.get_text()
            match = re.search(r'(BANGLADESH\s+\d+)', page_text)
            if match:
                range_val = match.group(1)
        if not range_val:
            range_val = "BANGLADESH 67122"  # ডিফল্ট

        print(f"📌 বর্তমান রেঞ্জ: {range_val}")
        print(f"📋 {len(numbers)} টি নম্বর পাওয়া গেছে")

        if not token or not numbers:
            return None, None, None

        return token, numbers, range_val

    except Exception as e:
        print(f"❌ ডেটা আনার এরর: {e}")
        return None, None, None

# ==================== ৩. এসএমএস ফেচ ====================
def fetch_sms_for_number(token, number, date, range_val):
    api_url = "https://www.ivasms.com/portal/sms/received/getsms/number/sms"
    params = {
        '_token': token,
        'start': date,
        'end': date,
        'Number': number,
        'Range': range_val
    }
    try:
        response = session.get(api_url, params=params, timeout=10)
        if response.status_code == 200:
            return response.text
        return None
    except Exception as e:
        print(f"API কল এরর ({number}): {e}")
        return None

# ==================== ৪. মেইন ফাংশন (টেস্ট মেসেজ + ইনফিনিট রিট্রাই) ====================
def main():
    # 🚀 **সর্বপ্রথম টেস্ট মেসেজ পাঠান** (যাতে বুঝতে পারেন বট টেলিগ্রামে পৌঁছাতে পারছে কিনা)
    try:
        bot.send_message(chat_id=CHAT_ID, text="🚀 বট চালু হয়েছে! (টেস্ট মেসেজ - রেলওয়ে থেকে)")
        print("✅ টেস্ট মেসেজ টেলিগ্রামে পাঠানো হয়েছে!")
    except Exception as e:
        print(f"❌ টেস্ট মেসেজ পাঠাতে ব্যর্থ! চেক করুন টোকেন/চ্যাট আইডি: {e}")

    # ---------- লগইন রিট্রাই লুপ (কখনো ক্র্যাশ হবে না) ----------
    while True:
        if login():
            break
        print("⏳ ৩০ সেকেন্ড পর আবার লগইন চেষ্টা করব...")
        time.sleep(30)

    # ---------- মনিটরিং লুপ ----------
    sent_codes = set()
    today = time.strftime("%Y-%m-%d")
    print(f"🚀 মনিটরিং শুরু হয়েছে! ({today})")

    while True:
        try:
            token, numbers, range_val = get_portal_data()

            if not token or not numbers:
                print("🔄 ডেটা না পেয়ে লগইন রিফ্রেশ করছি...")
                if login():
                    token, numbers, range_val = get_portal_data()
                    if not token or not numbers:
                        time.sleep(10)
                        continue
                else:
                    time.sleep(30)
                    continue

            for num in numbers:
                sms_data = fetch_sms_for_number(token, num, today, range_val)
                if sms_data:
                    codes = re.findall(r'GoChat Code: (\d+)', sms_data)
                    for code in codes:
                        if code not in sent_codes:
                            msg = f"📩 নম্বর: {num}\n🔑 কোড: {code}"
                            bot.send_message(chat_id=CHAT_ID, text=msg)
                            sent_codes.add(code)
                            print(f"✅ পাঠানো হয়েছে: {msg}")
                time.sleep(1)

            time.sleep(15)

        except Exception as e:
            print(f"⚠️ মেইন লুপে এরর: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
