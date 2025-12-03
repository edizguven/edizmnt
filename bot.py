import logging
import time
import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Log dosyası
logging.basicConfig(filename="bot_log.txt", level=logging.INFO, format="%(asctime)s - %(message)s")


# =============================================================
# BOT FUNKSIYONU
# =============================================================
def start_bot(phone, password, momento_code):
    try:
        logging.info("Başlatılıyor...")

        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        # chrome_options.add_argument("--headless=new")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        wait = WebDriverWait(driver, 20)

        driver.get("https://market.staging.minted.com.tr/giris-yap")

        wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(phone)
        wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys(password)

        devam_et_buton = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'Devam Et')]")))
        devam_et_buton.click()
        logging.info("Giriş bilgileri gönderildi.")

        # OTP
        wait.until(EC.presence_of_element_located((By.ID, "code"))).send_keys("1")
        driver.find_element(By.ID, "code2").send_keys("2")
        driver.find_element(By.ID, "code3").send_keys("3")
        driver.find_element(By.ID, "code4").send_keys("4")

        driver.execute_script("""
            let button = document.querySelector('.otp-submit-button');
            button.removeAttribute('disabled');
            button.classList.remove('button-disabled');
        """)

        dogrula_buton = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".otp-submit-button")))
        dogrula_buton.click()
        logging.info("OTP doğrulandı.")

        time.sleep(5)
        driver.get("https://market.staging.minted.com.tr/gumus")
        time.sleep(5)

        driver.get("https://market.staging.minted.com.tr/minted-50-gr-gumus")
        time.sleep(5)

        sepete_ekle_buton = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "cartbutton-add-basket")))
        sepete_ekle_buton.click()
        logging.info("Ürün sepete eklendi.")
        time.sleep(5)

        driver.get("https://market.staging.minted.com.tr/adres")
        time.sleep(10)

        driver.get("https://market.staging.minted.com.tr/sepet")
        time.sleep(5)

        driver.get("https://market.staging.minted.com.tr/odeme")
        time.sleep(5)

        # Momento seçimi
        momento_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[.//img[contains(@src, 'momento-logo')]]"))
        )
        momento_button.click()
        logging.info("Momento ile Öde seçildi.")

        time.sleep(5)
        kod_input = wait.until(EC.presence_of_element_located((By.ID, "momentoNumber")))
        kod_input.send_keys(momento_code)

        # sözleşmeler
        for checkbox_id in ["_contract", "_contract2"]:
            checkbox = wait.until(EC.presence_of_element_located((By.ID, checkbox_id)))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox)
            driver.execute_script("arguments[0].click();", checkbox)

        complete_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//span[text()="Alışverişi Tamamla"]')))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", complete_button)
        driver.execute_script("arguments[0].click();", complete_button)

        driver.quit()
        return True

    except Exception as e:
        logging.error(f"Hata oluştu.Lütfen logları inceleyin: {e}")
        return str(e)


# =============================================================
# STREAMLIT UI (run() içine alındı!)
# =============================================================
def run():
    st.title("💳 Minted Staging Test")
    st.write("Staging ortamında otomatik alım işlemi yapan bot")

    phone = st.text_input("Minted Uygulanasına Kayıtlı Telefon No")
    password = st.text_input("Minted Uyguluması Kayıtlı Şifre", type="password")
    momento = st.text_input("Momento Kodu")

    if st.button("Başlat"):
        if not phone or not password or not momento:
            st.error("Lütfen tüm bilgileri doldurun!")
        else:
            with st.spinner(" Çalışıyor..."):
                result = start_bot(phone, password, momento)

            if result is True:
                st.success("İşlemi başarıyla tamamladı!")
            else:
                st.error(f"Hata oluştu...Lütfen logları inceleyin:\n{result}")
