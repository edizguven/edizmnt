import streamlit as st
import pandas as pd
import hashlib
import json
from pathlib import Path
import importlib

# =========================================================
# Kullanıcı Yönetimi – JSON Dosyası
# =========================================================
#https://indexpy-bx48m9fcvqpmvqq49s6z9g.streamlit.app
#https://indexpy-bx48m9fcvqpmvqq49s6z9g.streamlit.app

USERS_FILE = Path("users.json")

def init_users():
    """Varsayılan admin kullanıcısını oluşturur."""
    if not USERS_FILE.exists():
        default_users = {
            "admin": {
                "password": hashlib.sha256("admin123".encode()).hexdigest(),
                "role": "admin"
            }
        }
        USERS_FILE.write_text(json.dumps(default_users, indent=4))

def load_users():
    if USERS_FILE.exists():
        return json.loads(USERS_FILE.read_text())
    return {}

def save_users(users):
    USERS_FILE.write_text(json.dumps(users, indent=4))

def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()

# =========================================================
# Login Sayfası
# =========================================================

def login_page():
    st.title("🔐 Admin Giriş Paneli")

    username = st.text_input("Kullanıcı Adı")
    password = st.text_input("Şifre", type="password")

    if st.button("Giriş Yap"):
        users = load_users()

        if username in users and users[username]["password"] == hash_password(password):
            st.session_state["logged_in"] = True
            st.session_state["username"] = username

            st.success("Giriş başarılı!")
            st.rerun()
        else:
            st.error("Hatalı kullanıcı adı veya şifre!")

# =========================================================
# Kullanıcı Yönetimi Sayfası
# =========================================================

def user_management():
    st.subheader("👥 Kullanıcı Yönetimi")

    users = load_users()

    st.write("### 📌 Mevcut Kullanıcılar")
    st.table(pd.DataFrame([
        {"username": u, "role": users[u]["role"]}
        for u in users
    ]))

    st.write("### ➕ Yeni Kullanıcı Ekle")
    new_user = st.text_input("Kullanıcı Adı")
    new_pass = st.text_input("Şifre", type="password")
    new_role = st.selectbox("Rol", ["admin", "user"])

    if st.button("Kullanıcı Ekle"):
        if new_user in users:
            st.error("Bu kullanıcı zaten var!")
        else:
            users[new_user] = {
                "password": hash_password(new_pass),
                "role": new_role
            }
            save_users(users)
            st.success("Kullanıcı başarıyla eklendi!")
            st.rerun()

    st.write("---")
    st.write("### 🗑 Kullanıcı Sil")
    delete_user = st.selectbox("Silinecek Kullanıcı", list(users.keys()))

    if st.button("Kullanıcıyı Sil"):
        if delete_user == "admin":
            st.error("Admin silinemez!")
        else:
            del users[delete_user]
            save_users(users)
            st.success("Kullanıcı silindi!")
            st.rerun()

# =========================================================
# Ana Menü Paneli
# =========================================================

def call_module(module_name: str):
    """Module import eder ve run() fonksiyonunu çalıştırır."""
    try:
        module = importlib.import_module(module_name)
        if hasattr(module, "run"):
            module.run()
        else:
            st.error(f"❌ {module_name}.py içinde run() fonksiyonu yok!")
    except Exception as e:
        st.error(f"Modül yüklenirken hata oluştu: {e}")

def main_panel():
    st.title("🏠 Admin Paneli")
    st.success(f"Hoş geldin, **{st.session_state['username']}** 👋")

    menu = st.sidebar.radio(
        "Menü",
        [
            "Fraud Kontrol",
            "DB Merge",
            "OCR Dekont Okuma",
            "Staging Momento Test",
            "Kullanıcı Yönetimi",
            "Çıkış"
        ]
    )

    if menu == "Fraud Kontrol":
        call_module("fc")

    elif menu == "DB Merge":
        call_module("db")

    elif menu == "OCR Dekont Okuma":
        call_module("ocr")

    elif menu == "Staging Momento Test":
        call_module("bot")

    elif menu == "Kullanıcı Yönetimi":
        user_management()

    elif menu == "Çıkış":
        st.session_state.clear()
        st.rerun()

# =========================================================
# Uygulamayı Başlat
# =========================================================

def main():
    init_users()

    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        login_page()
    else:
        main_panel()

if __name__ == "__main__":
    main()
