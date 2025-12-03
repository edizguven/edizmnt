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
# 🔥 BOT ADIMLARI
# =============================================================
STEP_LIST = [
    "Giriş sayfasına gidiliyor",
    "Telefon ve şifre girildi",
    "Devam Et tıklandı",
    "OTP doğrulandı",
    "Gümüş kategorisine gidiliyor",
    "Ürün sayfasına gidiliyor",
    "Ürün sepete ekleniyor",
    "Adres sayfasına gidiliyor",
    "Sepet sayfasına gidiliyor",
    "Ödeme sayfasına gidiliyor",
    "Momento ödeme seçiliyor",
    "Momento kodu girildi",
    "Sözleşmeler işaretlendi",
    "Alışveriş tamamlandı"
]

# =============================================================
# STREAMLIT LOG PANELİNE MESAJ YAZMA FUNKSIYONU
# =============================================================
def streamlit_log(step_name, step_containers):
    step_containers[step_name].markdown(f"✅ **{step_name}**")
    logging.info(step_name)

# =============================================================
# BOT FUNKSIYONU
# =============================================================
def start_bot(phone, password, momento_code, step_containers):
    try:
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--window-size=1920,1080")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        wait = WebDriverWait(driver, 20)

        # 1) Giriş sayfası
        driver.get("https://market.staging.minted.com.tr/giris-yap")
        streamlit_log("Giriş sayfasına gidiliyor", step_containers)

        # 2) Telefon & şifre
        wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(phone)
        wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys(password)
        streamlit_log("Telefon ve şifre girildi", step_containers)

        # 3) Devam Et
        devam = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'Devam Et')]")))
        devam.click()
        streamlit_log("Devam Et tıklandı", step_containers)

        # 4) OTP
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
        streamlit_log("OTP doğrulandı", step_containers)

        # 5) Gümüş kategorisi
        time.sleep(5)
        driver.get("https://market.staging.minted.com.tr/gumus")
        streamlit_log("Gümüş kategorisine gidiliyor", step_containers)

        # 6) Ürün sayfası
        time.sleep(5)
        driver.get("https://market.staging.minted.com.tr/minted-50-gr-gumus")
        streamlit_log("Ürün sayfasına gidiliyor", step_containers)

        # 7) Sepete ekle
        sepete_ekle = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "cartbutton-add-basket")))
        sepete_ekle.click()
        streamlit_log("Ürün sepete ekleniyor", step_containers)

        # 8) Adres sayfası
        time.sleep(5)
        driver.get("https://market.staging.minted.com.tr/adres")
        streamlit_log("Adres sayfasına gidiliyor", step_containers)

        # 9) Sepet sayfası
        time.sleep(5)
        driver.get("https://market.staging.minted.com.tr/sepet")
        streamlit_log("Sepet sayfasına gidiliyor", step_containers)

        # 10) Ödeme sayfası
        time.sleep(5)
        driver.get("https://market.staging.minted.com.tr/odeme")
        streamlit_log("Ödeme sayfasına gidiliyor", step_containers)

        # 11) Momento ödeme
        momento_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[.//img[contains(@src, 'momento-logo')]]"))
        )
        momento_button.click()
        streamlit_log("Momento ödeme seçiliyor", step_containers)

        # 12) Momento kodu
        time.sleep(5)
        kod_input = wait.until(EC.presence_of_element_located((By.ID, "momentoNumber")))
        kod_input.send_keys(momento_code)
        streamlit_log("Momento kodu girildi", step_containers)

        # 13) Sözleşmeler
        for checkbox_id in ["_contract", "_contract2"]:
            checkbox = wait.until(EC.presence_of_element_located((By.ID, checkbox_id)))
            driver.execute_script("arguments[0].click();", checkbox)
        streamlit_log("Sözleşmeler işaretlendi", step_containers)

        # 14) Alışverişi tamamla
        complete = wait.until(EC.element_to_be_clickable((By.XPATH, '//span[text()="Alışverişi Tamamla"]')))
        driver.execute_script("arguments[0].click();", complete)
        streamlit_log("Alışveriş tamamlandı", step_containers)

        driver.quit()
        return True

    except Exception as e:
        logging.error(f"Hata oluştu: {e}")
        st.error(f"❌ Hata oluştu: {e}")
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

    # Adım kutucukları (başta kırmızı ❌)
    step_containers = {}
    for step in STEP_LIST:
        step_containers[step] = st.empty()
        step_containers[step].markdown(f"❌ **{step}**")

    if st.button("Başlat"):
        if not phone or not password or not momento_code:
            st.error("Lütfen tüm bilgileri eksiksiz girin!")
        else:
            with st.spinner("Bot çalışıyor..."):
                result = start_bot(phone, password, momento_code, step_containers)

            if result is True:
                st.success("🏁 Bot işlemi başarıyla tamamlandı!")
            else:
                st.error("❌ Bot hata verdi. Logları inceleyin.")
