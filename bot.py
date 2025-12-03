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
# 🔥 STREAMLIT LOG PANELİNE MESAJ YAZMA FUNKSIYONU
# =============================================================
def streamlit_log(msg, log_box):
    logging.info(msg)
    log_box.write(f"🟢 {msg}")


# =============================================================
# BOT FUNKSIYONU
# =============================================================
def start_bot(phone, password, momento_code, log_box):
    try:
        streamlit_log("Bot başlatılıyor...", log_box)

        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--window-size=1920,1080")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        wait = WebDriverWait(driver, 20)

        streamlit_log("Giriş sayfasına gidiliyor...", log_box)
        driver.get("https://market.staging.minted.com.tr/giris-yap")

        wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(phone)
        wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys(password)
        streamlit_log("Telefon ve şifre girildi.", log_box)

        devam = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'Devam Et')]")))
        devam.click()
        streamlit_log("Devam Et tıklandı.", log_box)

        # OTP
        wait.until(EC.presence_of_element_located((By.ID, "code"))).send_keys("1")
        driver.find_element(By.ID, "code2").send_keys("2")
        driver.find_element(By.ID, "code3").send_keys("3")
        driver.find_element(By.ID, "code4").send_keys("4")

        driver.execute_script("""
            let btn = document.querySelector('.otp-submit-button');
            btn.removeAttribute('disabled');
            btn.classList.remove('button-disabled');
        """)

        dogrula = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".otp-submit-button")))
        dogrula.click()
        streamlit_log("OTP doğrulandı.", log_box)

        # Ürün adımları
        streamlit_log("Gümüş kategorisine gidiliyor...", log_box)
        time.sleep(5)
        driver.get("https://market.staging.minted.com.tr/gumus")

        streamlit_log("Ürün sayfasına gidiliyor...", log_box)
        time.sleep(5)
        driver.get("https://market.staging.minted.com.tr/minted-50-gr-gumus")

        streamlit_log("Ürün sepete ekleniyor...", log_box)
        sepete_ekle = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "cartbutton-add-basket")))
        sepete_ekle.click()

        # Adres & sepet
        time.sleep(5)
        streamlit_log("Adres sayfasına gidiliyor...", log_box)
        driver.get("https://market.staging.minted.com.tr/adres")

        time.sleep(5)
        streamlit_log("Sepet sayfasına gidiliyor...", log_box)
        driver.get("https://market.staging.minted.com.tr/sepet")

        time.sleep(5)
        streamlit_log("Ödeme sayfasına gidiliyor...", log_box)
        driver.get("https://market.staging.minted.com.tr/odeme")

        # Momento
        streamlit_log("Momento ödeme seçiliyor...", log_box)
        momento_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[.//img[contains(@src, 'momento-logo')]]"))
        )
        momento_button.click()

        time.sleep(5)
        kod_input = wait.until(EC.presence_of_element_located((By.ID, "momentoNumber")))
        kod_input.send_keys(momento_code)
        streamlit_log("Momento kodu girildi.", log_box)

        # Sözleşmeler
        for checkbox_id in ["_contract", "_contract2"]:
            checkbox = wait.until(EC.presence_of_element_located((By.ID, checkbox_id)))
            driver.execute_script("arguments[0].click();", checkbox)
        streamlit_log("Sözleşmeler işaretlendi.", log_box)

        # Alışverişi tamamla
        complete = wait.until(EC.element_to_be_clickable((By.XPATH, '//span[text()="Alışverişi Tamamla"]')))
        driver.execute_script("arguments[0].click();", complete)
        streamlit_log("Alışveriş tamamlandı!", log_box)

        driver.quit()
        return True

    except Exception as e:
        logging.error(f"Hata oluştu: {e}")
        streamlit_log(f"❌ HATA: {e}", log_box)
        return str(e)


# =============================================================
# STREAMLIT ARAYÜZ
# =============================================================
def run():
    st.title("💳 Minted Staging Test")
    st.write("Staging ortamında otomatik alım işlemi yapan bot")

    phone = st.text_input("Telefon Numarası")
    password = st.text_input("Şifre", type="password")
    momento_code = st.text_input("Momento Kodu")

    log_box = st.empty()  # canlı log alanı

    if st.button("Başlat"):
        if not phone or not password or not momento_code:
            st.error("Lütfen tüm bilgileri eksiksiz girin!")
        else:
            with st.spinner("Bot çalışıyor..."):
                result = start_bot(phone, password, momento_code, log_box)

            if result is True:
                st.success("🏁 Bot işlemi başarıyla tamamladı!")
            else:
                st.error("❌ Bot hata verdi. Logları inceleyin.")
