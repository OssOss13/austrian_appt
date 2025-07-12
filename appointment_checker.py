import os
import time
import smtplib
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException

from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

from datetime import datetime
import pytz

# Load credentials from .env file
if os.path.exists(".env"):
    from dotenv import load_dotenv
    load_dotenv()

# Email config
EMAIL = os.environ["EMAIL_ADDRESS"] or os.getenv("EMAIL_ADDRESS")
EMAIL_PASS = os.environ["EMAIL_PASSWORD"] or os.getenv("EMAIL_PASSWORD")

EMAIL_2 = os.environ["EMAIL_2_ADDRESS"] or os.getenv("EMAIL_2_ADDRESS")

# SMS (Twilio)
TWILIO_SID = os.environ["TWILIO_ACCOUNT_SID"] or os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.environ["TWILIO_AUTH_TOKEN"] or os.getenv("TWILIO_AUTH_TOKEN")    

SMS_FROM = os.environ["TWILIO_SMS_FROM"] or os.getenv("TWILIO_SMS_FROM")
SMS_TO = os.environ["TWILIO_SMS_TO"] or os.getenv("TWILIO_SMS_TO")


# --- NOTIFICATION FUNCTIONS ---
def send_email(subject, message, recipient):
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(message, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL, EMAIL_PASS)
            server.send_message(msg)
        print("[✔] Email sent.")
    except Exception as e:
        print(f"[✖] Email failed: {e}")

def send_sms(message, recipient):
    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
        data = {
            "From": SMS_FROM,  # This should be your Twilio phone number (e.g., "+1234567890")
            "To": recipient,      # The recipient's phone number
            "Body": message
        }
        response = requests.post(url, data=data, auth=(TWILIO_SID, TWILIO_TOKEN))
        response.raise_for_status()
        print("[✔] SMS message sent.")
    except Exception as e:
        print(f"[✖] SMS failed: {e}")

def safe_click(driver, wait, xpath, retries=2):
    for _ in range(retries):
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            driver.find_element(By.XPATH, xpath).click()
            return
        except StaleElementReferenceException:
            print("[!] Retrying click due to stale element...")
            time.sleep(1)

# --- CHECK APPOINTMENT PAGE FUNCTION ---          
def check_appointment():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    print("[⋯] Launching browser...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get("https://appointment.bmeia.gv.at/")
        wait = WebDriverWait(driver, 10)

        # STEP 1: Select "KAIRO"
        wait.until(EC.presence_of_element_located((By.ID, "Office")))
        Select(driver.find_element(By.ID, "Office")).select_by_visible_text("KAIRO")
        # print("[✔] Selected office: KAIRO")

        # Click "Next"
        safe_click(driver, wait, '//input[@type="submit" and @value="Next"]')

        # STEP 2: Print cairo and select category
        wait.until(EC.presence_of_element_located((By.ID, "CalendarId")))

        kairo_td = driver.find_element(By.XPATH, '//td[input[@id="Office"]]')
        print(f"[ℹ] Office Text: {kairo_td.text.strip()}")

        Select(driver.find_element(By.ID, "CalendarId")).select_by_value("44279679")

        # Click "Next"
        safe_click(driver, wait, '//input[@type="submit" and @value="Next"]')

        # STEP 3: Skip "number of persons"
        safe_click(driver, wait, '//input[@type="submit" and @value="Next"]')

        # STEP 4: Final confirmation
        safe_click(driver, wait, '//input[@type="submit" and @value="Next"]')

        # STEP 5: Calendar/slot view
        time.sleep(2)  # Let dynamic content load

        # Print the H2 header to confirm the category and appointment context
        try:
            h2_element = driver.find_element(By.XPATH, '//h2[contains(text(), "Appointments available")]')
            print(f"[ℹ] Heading: {h2_element.text}")
        except NoSuchElementException:
            print("[!] No heading found — might be no appointments or wrong step.")

        try:
            driver.find_element(By.XPATH, '//input[@name="Start" and @type="radio"]')
            print("[✔] Appointment FOUND!")
            message = "🚨 Appointment available at the Austrian Embassy in Cairo!\nCheck: https://appointment.bmeia.gv.at/"
            sms = f"Appointment available at the Austrian Embassy"
            send_email("📅 Visa Appointment Found!", message, EMAIL)
            send_email("📅 Visa Appointment Found!", message, EMAIL_2)
            try:
                send_sms(sms, SMS_TO)
            except Exception as sms_error:
                print(f"[✖] SMS failed: {sms_error}")

            print("[✔] notification sent")
        except NoSuchElementException:
            print("[✘] No appointments available.")

    except Exception as e:
        print(f"[✖] Error: {e}")
    finally:
        driver.quit()

# --- LOOPING TASK ---

if __name__ == "__main__":

    cairo = pytz.timezone("Africa/Cairo")
    start_time = datetime.now(cairo)
    print(f"\n[🟢] Script started at: {start_time.strftime('%Y-%m-%d %H:%M:%S %Z%z')}")


    start = time.time()
    counter = 0 
    while time.time() - start < (60*60):  # Run for 1 hour  
        print("\n[🔁] Checking for appointments...")
        print(f"[⏳] Attempt #{counter + 1}")
        counter += 1
        check_appointment()
        time.sleep(60)  # wait 1 minute before checking again

    end_time = datetime.now(cairo)
    print(f"\n[🔴] Script ended at:   {end_time.strftime('%Y-%m-%d %H:%M:%S %Z%z')}")

