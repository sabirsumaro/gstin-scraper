
import streamlit as st
import pandas as pd
import time
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

st.set_page_config(page_title="Parallel GSTIN Scraper", layout="centered")
st.title("⚡ Superfast GSTIN Scraper – 3x Speed with Parallel Chrome")

# === Rerun prevention ===
if "has_run" not in st.session_state:
    st.session_state.has_run = False

uploaded_file = st.file_uploader("📤 Upload Excel file with GSTIN list", type=["xlsx"])

# Setup Chrome driver
def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-notifications")
    return webdriver.Chrome(service=Service(), options=options)

# Extract function per GSTIN
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

if uploaded_file and not st.session_state.has_run:
    st.session_state.has_run = True

    df = pd.read_excel(uploaded_file)
    gstin_list = df.iloc[:, 0].dropna().astype(str).tolist()
    total = len(gstin_list)
    st.info(f"⏳ Processing {total} GSTINs using 3 Chrome instances...")

    results = []
    progress = st.progress(0)

    with ThreadPoolExecutor(max_workers=3) as executor:
        for i, result in enumerate(executor.map(extract_data, gstin_list)):
            results.append(result)
            progress.progress((i + 1) / total)

    output_df = pd.DataFrame(results)
    st.success("✅ Extraction Complete!")

    # Download Excel file
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        output_df.to_excel(writer, index=False)
    buffer.seek(0)

    st.download_button(
        label="📥 Download Extracted Excel",
        data=buffer,
        file_name="Parallel_GSTIN_Data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
