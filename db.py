import os
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import re
from datetime import datetime
from fpdf import FPDF
import tempfile

# ----------------------------------------------------------------------
# 📚 SABİT TANIMLAMALAR
# ----------------------------------------------------------------------

TR_COLUMN_MAPPING = {
    "id": "order_id", "customer_id": "customer_id", "order_id": "order_id", "name-surname": "customer_name",
    "currency": "currency", "amount": "amount", "total": "total_price", "status": "status",
    "dekont": "invoice", "create_date": "order_date", "payment_method": "payment_method",
    "provider_name": "partner_mc", "order_type": "process_type", "spot_price": "spot_price",
    "unit_price": "unit_price", "margin": "margin", "product_name": "product_name", "sku": "sku", "qty": "qty"
}

MC_COLUMN_MAPPING = {
    "id": "order_id", "customer": "customer_name", "partner": "partner_mc", "product": "product_name",
    "amount": "amount", "total": "total_price", "comission": "margin", "payment_type": "payment_method",
    "invoice": "invoice", "receipt": "receipt", "status": "status", "order_date": "order_date"
}

STANDARD_COLUMNS = [
    "source", "process_type", "order_id", "customer_id", "customer_name", "product_name",
    "amount", "total_price", "currency", "payment_method", "status", "order_date",
    "partner_mc", "invoice", "receipt", "spot_price", "unit_price", "margin", "sku", "qty"
]


# ----------------------------------------------------------------------
# ⚙️ YARDIMCI FONKSİYONLAR
# ----------------------------------------------------------------------

def _clean_column_names(columns):
    return [c.strip().lower().replace(" ", "_").replace("-", "_") for c in columns]


def _clean_numeric_column(series):
    s = series.astype(str)
    s = s.str.replace(r"[^0-9,.\-]", "", regex=True)
    tr_format = s.str.contains(r"\.\d{3},\d{2}$")
    s = s.where(~tr_format, s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False))
    only_comma = s.str.contains(",") & ~s.str.contains(r"\.")
    s = s.where(~only_comma, s.str.replace(",", ".", regex=False))
    both = s.str.contains(",") & s.str.contains(r"\.") & ~tr_format
    s = s.where(~both, s.str.replace(",", "", regex=False))
    return pd.to_numeric(s, errors="coerce").fillna(0)


def normalize_dataframe(df, mapping, source, process_type):
    df.columns = _clean_column_names(df.columns)
    rename_dict = {}
    for k, v in mapping.items():
        key = _clean_column_names([k])[0]
        if key in df.columns:
            rename_dict[key] = v
    df = df.rename(columns=rename_dict)
    df = df.loc[:, ~df.columns.duplicated()]


    df["source"] = source
    df["process_type"] = process_type
    if "partner_mc" not in df.columns or source == "TR":
        df["partner_mc"] = "TR"

    for col in ["amount", "total_price", "margin"]:
        if col in df.columns:
            df[col] = _clean_numeric_column(df[col])

    for col in STANDARD_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    df = df[[col for col in STANDARD_COLUMNS if col in df.columns]]
    return df


def clean_merged_ids(df):
    if "order_id" in df.columns:
        df.loc[df["source"] == "TR", "order_id"] = df.loc[df["source"] == "TR", "order_id"].astype(str).str.replace(
            r"[.,]", "", regex=True)
    if "customer_id" in df.columns:
        df.loc[df["source"] == "TR", "customer_id"] = df.loc[df["source"] == "TR", "customer_id"].astype(
            str).str.replace(r"[.,]", "", regex=True)
    return df


# PDF için Türkçe Karakter Temizleyici
def clean_text_for_pdf(text):
    if not isinstance(text, str):
        return str(text)
    replacements = {
        'ş': 's', 'Ş': 'S', 'ı': 'i', 'İ': 'I', 'ğ': 'g', 'Ğ': 'G',
        'ü': 'u', 'Ü': 'U', 'ö': 'o', 'Ö': 'O', 'ç': 'c', 'Ç': 'C'
    }
    for search, replace in replacements.items():
        text = text.replace(search, replace)
    return text


# PDF Oluşturma Motoru
def create_pdf_report(summary_data, figures_list):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)

    # Başlık
    pdf.cell(190, 10, clean_text_for_pdf("Sell ve Buy Raporu"), ln=True, align='C')
    pdf.ln(10)

    # Özet Tablo
    pdf.set_font("Arial", '', 12)
    pdf.cell(190, 10, clean_text_for_pdf("GENEL OZET:"), ln=True)
    pdf.set_font("Arial", '', 10)

    for key, value in summary_data.items():
        pdf.cell(100, 8, clean_text_for_pdf(f"{key}: {value}"), ln=True)

    pdf.ln(5)

    # Grafikleri Sırayla Ekle
    for title, fig in figures_list:
        if fig:
            pdf.add_page()
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(190, 10, clean_text_for_pdf(title), ln=True, align='C')

            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
                fig.savefig(tmpfile.name, format="png", bbox_inches="tight")
                pdf.image(tmpfile.name, x=10, y=30, w=190)
                tmpfile_path = tmpfile.name

            os.remove(tmpfile_path)

    return pdf.output(dest='S').encode('latin-1', 'replace')


# ----------------------------------------------------------------------
# 💻 STREAMLIT ARAYÜZÜ
# ----------------------------------------------------------------------

def run():
    # Sayfa Başlığı ve İkonu (GÜNCELLENDİ)
    st.set_page_config(page_title="DB Merge", page_icon="🗂️", layout="centered")
    st.title("🗂️ DB Merge – Dosya Birleştirme ve Raporlama")

    # --- Dosyaları Yükle (GÜNCELLENDİ: Buy/Sell İsimlendirmesi) ---
    st.header("📥 Dosyaları Yükle")

    tr_purchase_file = st.file_uploader("TR Buy", type=["xlsx"], key="tr_purchase")
    mc_purchase_file = st.file_uploader("MC Buy", type=["xlsx"], key="mc_purchase")
    tr_sales_file = st.file_uploader("TR Sell", type=["xlsx"], key="tr_sales")
    mc_sales_file = st.file_uploader("MC Sell", type=["xlsx"], key="mc_sales")

    dataframes = []
    # (GÜNCELLENDİ: process_type artık "Buy" ve "Sell" olarak işleniyor)
    if tr_purchase_file: dataframes.append(
        normalize_dataframe(pd.read_excel(tr_purchase_file, engine="openpyxl"), TR_COLUMN_MAPPING, "TR", "Buy"))
    if mc_purchase_file: dataframes.append(
        normalize_dataframe(pd.read_excel(mc_purchase_file, engine="openpyxl"), MC_COLUMN_MAPPING, "MC", "Buy"))
    if tr_sales_file: dataframes.append(
        normalize_dataframe(pd.read_excel(tr_sales_file, engine="openpyxl"), TR_COLUMN_MAPPING, "TR", "Sell"))
    if mc_sales_file: dataframes.append(
        normalize_dataframe(pd.read_excel(mc_sales_file, engine="openpyxl"), MC_COLUMN_MAPPING, "MC", "Sell"))

    if dataframes:
        merged_df = pd.concat(dataframes, ignore_index=True)
        merged_df = clean_merged_ids(merged_df)
        if "payment_method" in merged_df.columns:
            merged_df["payment_method"] = merged_df["payment_method"].astype(str).str.strip().str.lower()

        merged_df = merged_df.assign(
            product_currency=lambda df: df["product_name"].astype(str) + " / " + df["currency"].astype(str))

        if "order_date" in merged_df.columns:
            merged_df["order_date"] = pd.to_datetime(merged_df["order_date"], errors='coerce')

        # --- FİLTRELEME ALANI ---
        st.markdown("---")
        st.subheader("🔍 Detaylı Filtreleme")

        col_date1, col_date2 = st.columns(2)
        with col_date1:
            start_date = st.date_input("Başlangıç Tarihi", value=None)
        with col_date2:
            end_date = st.date_input("Bitiş Tarihi", value=None)

        available_payment_methods = sorted(merged_df["payment_method"].dropna().unique().tolist())
        selected_payment_methods = st.multiselect(
            "💳 Ödeme Yöntemi Seçiniz:",
            available_payment_methods
        )

        # Filtreleri Uygula
        if start_date and end_date:
            start_ts = pd.to_datetime(start_date)
            end_ts = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
            merged_df = merged_df[
                (merged_df["order_date"] >= start_ts) &
                (merged_df["order_date"] <= end_ts)
                ]
            st.info(f"📅 Tarih Filtresi: **{start_date}** - **{end_date}**")

        if selected_payment_methods:
            merged_df = merged_df[merged_df["payment_method"].isin(selected_payment_methods)]
            st.info(f"💳 Seçilen Ödeme Yöntemleri: **{', '.join(selected_payment_methods)}**")

        if not (start_date and end_date) and not selected_payment_methods:
            st.info("ℹ️ Herhangi bir filtre uygulanmadı, **tüm veriler** gösteriliyor.")

        st.success(f"🎉 **Analiz Hazır!** Gösterilen Kayıt Sayısı: **{len(merged_df)}**")

        # --- ÖZET BİLGİLER ---
        st.subheader("📈 Özet Bilgiler")

        # Temel Hesaplamalar (GÜNCELLENDİ: Buy/Sell sorguları)
        total_purchase_val = merged_df[merged_df["process_type"] == "Buy"]["total_price"].sum()
        total_sales_val = merged_df[merged_df["process_type"] == "Sell"]["total_price"].sum()
        diff_val = total_sales_val - total_purchase_val
        total_amount = merged_df["amount"].sum()
        avg_margin = merged_df["margin"].mean()

        # AOV ve ORTALAMA (GÜNCELLENDİ: Buy/Sell)
        sales_txn_count = len(merged_df[merged_df["process_type"] == "Sell"])
        aov_sales = total_sales_val / sales_txn_count if sales_txn_count > 0 else 0

        purchase_txn_count = len(merged_df[merged_df["process_type"] == "Buy"])
        aov_purchase = total_purchase_val / purchase_txn_count if purchase_txn_count > 0 else 0

        # Satır 1: Finansal Toplamlar (GÜNCELLENDİ: Etiketler)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Toplam Buy Tutarı", value=f"{total_purchase_val:,.2f} TL")
        with col2:
            st.metric(label="Toplam Sell Tutarı", value=f"{total_sales_val:,.2f} TL")
        with col3:
            st.metric(label="Fark (Sell - Buy)", value=f"{diff_val:,.2f} TL", delta_color="normal")

        # Satır 2: Oranlar ve Ortalamalar
        col4, col5, col6, col7 = st.columns(4)
        with col4:
            st.metric(label="Toplam Ürün Miktarı", value=f"{total_amount:,.0f} Adet")
        with col5:
            st.metric(label="Ortalama Margin", value=f"%{avg_margin:,.2f}")
        with col6:
            st.metric(label="Ort. Sepet (Sell)", value=f"{aov_sales:,.2f} TL")
        with col7:
            st.metric(label="Ort. İşlem (Buy)", value=f"{aov_purchase:,.2f} TL")

        # PDF ÖZET (GÜNCELLENDİ)
        pdf_summary = {
            "Toplam Buy": f"{total_purchase_val:,.2f} TL",
            "Toplam Sell": f"{total_sales_val:,.2f} TL",
            "Fark": f"{diff_val:,.2f} TL",
            "Urun Miktari": f"{total_amount:,.0f}",
            "Margin": f"%{avg_margin:,.2f}",
            "Ortalama Sepet (Sell)": f"{aov_sales:,.2f} TL",
            "Ortalama Islem (Buy)": f"{aov_purchase:,.2f} TL"
        }

        pdf_figures = []

        # =========================================================================
        # 1. ZAMAN SERİSİ GRAFİĞİ (GÜNCELLENDİ: Buy/Sell)
        # =========================================================================
        st.markdown("---")
        st.subheader("📈 Zaman İçindeki İşlem Trendi (Buy vs Sell)")

        sales_data = merged_df[merged_df["process_type"] == "Sell"].copy()
        purchase_data = merged_df[merged_df["process_type"] == "Buy"].copy()

        if not sales_data.empty or not purchase_data.empty:
            fig_line, ax_line = plt.subplots(figsize=(10, 5))

            if not sales_data.empty:
                sales_data["day_only"] = sales_data["order_date"].dt.date
                daily_sales = sales_data.groupby("day_only")["total_price"].sum()
                daily_sales.plot(kind="line", ax=ax_line, marker="o", color="green", linewidth=2, label="Sell")

            if not purchase_data.empty:
                purchase_data["day_only"] = purchase_data["order_date"].dt.date
                daily_purchase = purchase_data.groupby("day_only")["total_price"].sum()
                daily_purchase.plot(kind="line", ax=ax_line, marker="o", color="red", linewidth=2, linestyle="--",
                                    label="Buy")

            ax_line.set_title("Günlük Ciro Karşılaştırması (Buy vs Sell)")
            ax_line.set_ylabel("Tutar (TL)")
            ax_line.set_xlabel("Tarih")
            ax_line.grid(True, linestyle="--", alpha=0.5)
            ax_line.legend()
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig_line)

            pdf_figures.append(("Zaman Bazli Trend", fig_line))
        else:
            st.warning("Grafik için veri yok.")

        # =========================================================================
        # 1.5 HAFTANIN GÜNLERİ ANALİZİ (GÜNCELLENDİ: Buy/Sell)
        # =========================================================================
        st.subheader("📅 Haftanın Günleri Analizi (Buy vs Sell)")

        analysis_df = merged_df.copy()

        if not analysis_df.empty:
            analysis_df["day_of_week"] = analysis_df["order_date"].dt.dayofweek

            day_map = {
                0: "Pazartesi", 1: "Salı", 2: "Çarşamba", 3: "Perşembe",
                4: "Cuma", 5: "Cumartesi", 6: "Pazar"
            }

            pivot_dow = analysis_df.groupby(["day_of_week", "process_type"])["total_price"].sum().unstack(fill_value=0)
            pivot_dow.index = pivot_dow.index.map(day_map)

            # (ÖNEMLİ: Artık Alış/Satış yerine Buy/Sell sütunlarını kontrol ediyoruz)
            if "Buy" not in pivot_dow.columns: pivot_dow["Buy"] = 0
            if "Sell" not in pivot_dow.columns: pivot_dow["Sell"] = 0

            fig_dow, ax_dow = plt.subplots(figsize=(10, 5))

            x_indexes = np.arange(len(pivot_dow.index))
            width = 0.35

            ax_dow.bar(x_indexes + width / 2, pivot_dow["Sell"], width, label="Sell", color="green")
            ax_dow.bar(x_indexes - width / 2, pivot_dow["Buy"], width, label="Buy", color="red")

            ax_dow.set_title("Haftanın Günlerine Göre Dağılım (Buy vs Sell)")
            ax_dow.set_ylabel("Tutar (TL)")
            ax_dow.set_xticks(x_indexes)
            ax_dow.set_xticklabels(pivot_dow.index, rotation=45)
            ax_dow.legend()

            st.pyplot(fig_dow)
            pdf_figures.append(("Haftanin Gunleri (Buy vs Sell)", fig_dow))
        else:
            st.info("Analiz için veri bulunamadı.")

        # =========================================================================
        # 2. PARTNER ANALİZİ
        # =========================================================================
        st.subheader("📊 Partner Bazlı Analiz")

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            partner_metric = st.selectbox("Grafik Kriteri:", ["İşlem Adedi", "Toplam Tutar (TL)"], key="sb_partner")
        with col_p2:
            partner_chart_type = st.radio("Grafik Tipi:", ["Çubuk (Bar)", "Pasta (Pie)"], key="rb_partner",
                                          horizontal=True)

        partner_agg = merged_df.groupby("partner_mc").agg(count=("order_id", "count"), total=("total_price", "sum"))

        if partner_metric == "İşlem Adedi":
            partner_agg = partner_agg.sort_values(by="count", ascending=False)
            chart_data = partner_agg["count"]
            ylabel_text = "İşlem Adedi"
            color_bar = "skyblue"
        else:
            partner_agg = partner_agg.sort_values(by="total", ascending=False)
            chart_data = partner_agg["total"]
            ylabel_text = "Toplam Tutar (TL)"
            color_bar = "steelblue"

        if not partner_agg.empty:
            fig_p, ax_p = plt.subplots(figsize=(8, 4))

            if partner_chart_type == "Çubuk (Bar)":
                chart_data.plot(kind="bar", ax=ax_p, color=color_bar)
                ax_p.set_ylabel(ylabel_text)
                ax_p.set_title(f"Partner Bazlı - {partner_metric}")
                plt.xticks(rotation=0)
            else:
                ax_p.pie(chart_data, labels=chart_data.index, autopct='%1.1f%%', startangle=90,
                         colors=plt.cm.Paired.colors)
                ax_p.set_title(f"Partner Dağılımı ({partner_metric})")

            st.pyplot(fig_p)
            pdf_figures.append((f"Partner Analizi ({partner_metric})", fig_p))

            partner_display = partner_agg.copy()
            partner_display.columns = ["İşlem Adedi", "Toplam Tutar (TL)"]
            partner_display["Toplam Tutar (TL)"] = partner_display["Toplam Tutar (TL)"].apply(lambda x: f"{x:,.2f} TL")
            st.write(f"📄 Partner Rapor Tablosu")
            st.dataframe(partner_display, use_container_width=True)
        else:
            st.info("Veri yok.")

        # =========================================================================
        # 3. ÖDEME YÖNTEMİ ANALİZİ
        # =========================================================================
        st.subheader("📊 Ödeme Yöntemi Analizi")

        col_pm1, col_pm2 = st.columns(2)
        with col_pm1:
            payment_metric = st.selectbox("Grafik Kriteri:", ["İşlem Adedi", "Toplam Tutar (TL)"], key="sb_payment")
        with col_pm2:
            payment_chart_type = st.radio("Grafik Tipi:", ["Çubuk (Bar)", "Pasta (Pie)"], key="rb_payment",
                                          horizontal=True)

        payment_agg = merged_df.groupby("payment_method").agg(count=("order_id", "count"), total=("total_price", "sum"))

        if payment_metric == "İşlem Adedi":
            payment_agg = payment_agg.sort_values(by="count", ascending=False)
            chart_data = payment_agg["count"]
            ylabel_text = "İşlem Adedi"
            color_bar = "lightcoral"
        else:
            payment_agg = payment_agg.sort_values(by="total", ascending=False)
            chart_data = payment_agg["total"]
            ylabel_text = "Toplam Tutar (TL)"
            color_bar = "darkred"

        if not payment_agg.empty:
            fig_pm, ax_pm = plt.subplots(figsize=(8, 4))

            if payment_chart_type == "Çubuk (Bar)":
                chart_data.plot(kind="bar", ax=ax_pm, color=color_bar)
                ax_pm.set_ylabel(ylabel_text)
                ax_pm.set_title(f"Ödeme Yöntemi - {payment_metric}")
                plt.setp(ax_pm.get_xticklabels(), rotation=45, ha="right")
            else:
                ax_pm.pie(chart_data, labels=chart_data.index, autopct='%1.1f%%', startangle=140,
                          colors=plt.cm.Pastel1.colors)
                ax_pm.set_title(f"Ödeme Yöntemi Dağılımı ({payment_metric})")

            plt.tight_layout()
            st.pyplot(fig_pm)
            pdf_figures.append((f"Odeme Yontemi ({payment_metric})", fig_pm))

            payment_display = payment_agg.copy()
            payment_display.columns = ["İşlem Adedi", "Toplam Tutar (TL)"]
            payment_display["Toplam Tutar (TL)"] = payment_display["Toplam Tutar (TL)"].apply(lambda x: f"{x:,.2f} TL")
            st.write(f"📄 Ödeme Yöntemi Tablosu")
            st.dataframe(payment_display, use_container_width=True)
        else:
            st.info("Veri yok.")

        # =========================================================================
        # 4. MÜŞTERİ VE ÜRÜN ANALİZİ
        # =========================================================================
        st.markdown("---")
        st.header("🏆 Detaylı Müşteri ve Ürün Analizi")

        # --- MÜŞTERİ ---
        st.subheader("👤 En Çok İşlem Yapan Müşteriler (Top 10)")
        customer_metric = st.selectbox("Grafik Kriteri:", ["İşlem Adedi", "Toplam Harcama (TL)"], key="sb_customer")

        cust_agg = merged_df.groupby("customer_name").agg(count=("order_id", "count"), total=("total_price", "sum"))

        if customer_metric == "İşlem Adedi":
            cust_agg = cust_agg.sort_values(by="count", ascending=False).head(10)
            chart_data = cust_agg["count"]
            ylabel_text = "İşlem Adedi"
            color_bar = "green"
        else:
            cust_agg = cust_agg.sort_values(by="total", ascending=False).head(10)
            chart_data = cust_agg["total"]
            ylabel_text = "Toplam Harcama (TL)"
            color_bar = "darkgreen"

        if not cust_agg.empty:
            fig_cust, ax_cust = plt.subplots(figsize=(8, 4))
            chart_data.plot(kind="bar", ax=ax_cust, color=color_bar)
            ax_cust.set_ylabel(ylabel_text)
            ax_cust.set_title(f"Müşteri (Top 10) - {customer_metric}")
            plt.setp(ax_cust.get_xticklabels(), rotation=45, ha="right")
            plt.tight_layout()
            st.pyplot(fig_cust)
            pdf_figures.append(("Musteri Top 10", fig_cust))

            cust_display = cust_agg.copy()
            cust_display.columns = ["İşlem Adedi", "Toplam Harcama (TL)"]
            cust_display["Toplam Harcama (TL)"] = cust_display["Toplam Harcama (TL)"].apply(lambda x: f"{x:,.2f} TL")
            st.write(f"📄 Müşteri Tablosu (Sıralama: {customer_metric})")
            st.dataframe(cust_display, use_container_width=True)
        else:
            st.info("Veri yok.")

        # --- ÜRÜN ---
        st.subheader("🛒 En Çok Satılan Ürünler (Top 10)")
        product_metric = st.selectbox("Grafik Kriteri:", ["Satış Miktarı (Qty)", "Toplam Ciro (TL)"], key="sb_product")

        prod_agg = merged_df.groupby("product_currency").agg(amount=("amount", "sum"), total=("total_price", "sum"))

        if product_metric == "Satış Miktarı (Qty)":
            prod_agg = prod_agg.sort_values(by="amount", ascending=False).head(10)
            chart_data = prod_agg["amount"]
            ylabel_text = "Miktar"
            color_bar = "purple"
        else:
            prod_agg = prod_agg.sort_values(by="total", ascending=False).head(10)
            chart_data = prod_agg["total"]
            ylabel_text = "Ciro (TL)"
            color_bar = "indigo"

        if not prod_agg.empty:
            fig_prod, ax_prod = plt.subplots(figsize=(8, 4))
            chart_data.plot(kind="bar", ax=ax_prod, color=color_bar)
            ax_prod.set_ylabel(ylabel_text)
            ax_prod.set_title(f"Ürün (Top 10) - {product_metric}")
            plt.setp(ax_prod.get_xticklabels(), rotation=45, ha="right")
            plt.tight_layout()
            st.pyplot(fig_prod)
            pdf_figures.append(("Urun Top 10", fig_prod))

            prod_display = prod_agg.copy()
            prod_display.columns = ["Satış Miktarı", "Toplam Ciro (TL)"]
            prod_display["Toplam Ciro (TL)"] = prod_display["Toplam Ciro (TL)"].apply(lambda x: f"{x:,.2f} TL")
            st.write(f"📄 Ürün Tablosu (Sıralama: {product_metric})")
            st.dataframe(prod_display, use_container_width=True)
        else:
            st.info("Veri yok.")

        # =========================================================================
        # 📥 İNDİRME ALANI
        # =========================================================================
        st.markdown("---")
        st.header("📑 Rapor İndir")

        col_d1, col_d2 = st.columns(2)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            merged_df.to_excel(writer, index=False)
        with col_d1:
            st.download_button("📥 Excel Olarak İndir", output.getvalue(), "merged_data.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        with col_d2:
            if st.button("📄 PDF Raporu Oluştur"):
                with st.spinner("PDF hazırlanıyor..."):
                    pdf_bytes = create_pdf_report(pdf_summary, pdf_figures)
                    st.download_button(
                        label="⬇️ PDF'i İndir",
                        data=pdf_bytes,
                        file_name="Rapor.pdf",
                        mime="application/pdf"
                    )


    st.markdown("---")
    st.markdown("<div style='text-align: center; color: grey; font-size: 12px;'>Created by E.Güven</div>",
                unsafe_allow_html=True)


if __name__ == "__main__":
    run()