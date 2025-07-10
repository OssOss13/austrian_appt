import os
import time
import smtplib
import requests
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from selenium.common.exceptions import NoSuchElementException
# from twilio.rest import Client


# Load credentials from .env file
load_dotenv()

# Email config
EMAIL = os.getenv("EMAIL_ADDRESS")
EMAIL_PASS = os.getenv("EMAIL_PASSWORD")

# WhatsApp (Twilio)
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM")
WHATSAPP_TO = os.getenv("TWILIO_WHATSAPP_TO")

# client = Client(TWILIO_SID, TWILIO_TOKEN)


# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- NOTIFICATION FUNCTIONS ---

def send_email(subject, message):
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL
        msg["To"] = EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(message, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL, EMAIL_PASS)
            server.send_message(msg)
        print("[✔] Email sent.")
    except Exception as e:
        print(f"[✖] Email failed: {e}")

def send_whatsapp(message):
    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
        data = {
            "From": WHATSAPP_FROM,
            "To": WHATSAPP_TO,
            "Body": message
        }
        response = requests.post(url, data=data, auth=(TWILIO_SID, TWILIO_TOKEN))
        response.raise_for_status()
        print("[✔] WhatsApp message sent.")
    except Exception as e:
        print(f"[✖] WhatsApp failed: {e}")

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        }
        r = requests.post(url, data=payload)
        r.raise_for_status()
        print("[✔] Telegram sent.")
    except Exception as e:
        print(f"[✖] Telegram failed: {e}")

# --- CHECK APPOINTMENT PAGE FUNCTION ---

def check_appointment():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    print("[⋯] Launching browser...")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get("https://appointment.bmeia.gv.at/")
        wait = WebDriverWait(driver, 10)

        # STEP 1: Select "KAIRO"
        office_select = Select(wait.until(EC.presence_of_element_located((By.ID, "Office"))))
        office_select.select_by_visible_text("KAIRO")
        print("[✔] Selected office: KAIRO")

        # Click "Next"
        next_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//input[@type="submit" and @value="Next"]')))
        next_btn.click()

        # STEP 2: Select master/PhD category
        calendar_select = Select(wait.until(EC.presence_of_element_located((By.ID, "CalendarId"))))
        calendar_select.select_by_value("44279679")  # Master, PhD, etc.
        # calendar_select.select_by_value("32528820")  # Famielein...
        print("[✔] Selected category: Aufenthaltsbewilligung Student (Master, PhD...)")

        # Click "Next"
        next_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//input[@type="submit" and @value="Next"]')))
        next_btn.click()

        # STEP 3: Skip "number of persons" — click "Next"
        next_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//input[@type="submit" and @value="Next"]')))
        next_btn.click()

        # STEP 4: Final form — click "Next"
        next_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//input[@type="submit" and @value="Next"]')))
        next_btn.click()

        # STEP 5: Now we're at the calendar/slots page
        time.sleep(2)  # wait for content to load


        # Check if there are available appointments
        try:
            driver.find_element(By.XPATH, '//input[@name="Start" and @type="radio"]')
            print("[✔] Appointment FOUND!")
            message = "🚨 Appointment available at the Austrian Embassy in Cairo!\nCheck: https://appointment.bmeia.gv.at/"
            send_email("📅 Visa Appointment Found!", message)
            send_whatsapp(message)
            # send_telegram(message)
        except NoSuchElementException:
            print("[✘] No appointments available.")
       

    except Exception as e:
        print(f"[✖] Error: {e}")
    finally:
        driver.quit()
# --- LOOPING TASK ---

if __name__ == "__main__":
    # while True:
        print("\n[🔁] Checking for appointments...")
        check_appointment()
        # time.sleep(60)  # wait 1 minute before checking again
