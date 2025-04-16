
import streamlit as st
import pandas as pd
import time
from io import BytesIO
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

st.set_page_config(page_title="GSTIN Scraper + Email", layout="centered")
st.title("📤 Bulk GSTIN Scraper + Email Report")

# Email fields
st.subheader("✉️ Email Configuration")
sender_email = st.text_input("Sender Gmail Address")
app_password = st.text_input("App Password", type="password")
receiver_email = st.text_input("Receiver Email Address")

uploaded_file = st.file_uploader("📁 Upload Excel file with GSTIN list", type=["xlsx"])

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-notifications")
    return webdriver.Chrome(service=Service(), options=options)

def extract_data(gstin):
    driver = setup_driver()
    row = {
        "GSTIN": gstin,
        "Trade Name": "",
        "Legal Name of Business": "",
        "Principal Place of Business": "",
        "Additional Place of Business": "",
        "State Jurisdiction": "",
        "Status": "Error"
    }
    try:
        driver.get("https://irisgst.com/irisperidot/")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "gstinno"))
        )
        input_box = driver.find_element(By.ID, "gstinno")
        input_box.clear()
        input_box.send_keys(gstin)
        driver.find_element(By.XPATH, "//button[contains(text(), 'SEARCH')]").click()
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//strong[contains(text(),'Trade Name')]"))
        )

        def get_field(label):
            try:
                el = driver.find_element(By.XPATH, f"//strong[contains(text(), '{label}')]")
                return el.find_element(By.XPATH, "..").text.replace(label, "").strip()
            except:
                return ""

        row["Trade Name"] = get_field("Trade Name -")
        row["Legal Name of Business"] = get_field("Legal Name of Business -")
        row["Principal Place of Business"] = get_field("Principal Place of Business -")
        row["Additional Place of Business"] = get_field("Additional Place of Business -")
        row["State Jurisdiction"] = get_field("State Jurisdiction -")
        row["Status"] = "Success"
    except Exception as e:
        row["Status"] = f"Error: {str(e)}"
    finally:
        driver.quit()
    return row

def send_email(sender, password, receiver, file_bytes, filename):
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = receiver
    msg['Subject'] = 'GSTIN Extraction Report'

    part = MIMEBase('application', "octet-stream")
    part.set_payload(file_bytes.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
    msg.attach(part)

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Email failed: {str(e)}")
        return False

if uploaded_file and sender_email and app_password and receiver_email:
    df = pd.read_excel(uploaded_file)
    gstin_list = df.iloc[:, 0].dropna().astype(str).tolist()
    st.info(f"⏳ Processing {len(gstin_list)} GSTINs using 3 Chrome instances...")

    results = []
    progress = st.progress(0)

    with ThreadPoolExecutor(max_workers=3) as executor:
        for i, result in enumerate(executor.map(extract_data, gstin_list)):
            results.append(result)
            progress.progress((i + 1) / len(gstin_list))

    output_df = pd.DataFrame(results)
    st.success("✅ Extraction Complete!")

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        output_df.to_excel(writer, index=False)
    buffer.seek(0)

    if send_email(sender_email, app_password, receiver_email, buffer, "GSTIN_Report.xlsx"):
        st.success("📤 Email sent successfully with report attached!")
