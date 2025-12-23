import os
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from io import BytesIO
import re
from datetime import datetime

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


def apply_filters(df, process_type_filter, partner_filter, status_filter, payment_filter, date_range):
    df_filtered = df.copy()
    if process_type_filter:
        df_filtered = df_filtered[df_filtered["process_type"].isin(process_type_filter)]
    if partner_filter:
        df_filtered = df_filtered[df_filtered["partner_mc"].isin(partner_filter)]
    if status_filter:
        df_filtered = df_filtered[
            df_filtered["status"].astype(str).str.lower().isin([s.lower() for s in status_filter])]
    if payment_filter:
        df_filtered = df_filtered[df_filtered["payment_method"].isin([p.lower() for p in payment_filter])]
    if date_range and date_range[0] and date_range[1] and "order_date" in df_filtered.columns:
        start_date = pd.to_datetime(date_range[0])
        end_date = pd.to_datetime(date_range[1])
        df_filtered["order_date"] = pd.to_datetime(df_filtered["order_date"], errors='coerce')
        end_date = end_date + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        df_filtered = df_filtered[(df_filtered["order_date"] >= start_date) & (df_filtered["order_date"] <= end_date)]
    return df_filtered


# ----------------------------------------------------------------------
# 💻 STREAMLIT ARAYÜZÜ
# ----------------------------------------------------------------------

def run():
    st.set_page_config(page_title="DB Merge", page_icon="🗂️", layout="centered")
    st.title("🗂️ DB Merge – Dosya Birleştirme ve Standardizasyon")

    # --- Dosyaları Yükle ---
    st.header("📥 Dosyaları Yükle")

    tr_purchase_file = st.file_uploader("TR Alış", type=["xlsx"], key="tr_purchase")
    mc_purchase_file = st.file_uploader("MC Alış", type=["xlsx"], key="mc_purchase")
    tr_sales_file = st.file_uploader("TR Satış", type=["xlsx"], key="tr_sales")
    mc_sales_file = st.file_uploader("MC Satış", type=["xlsx"], key="mc_sales")

    dataframes = []
    if tr_purchase_file: dataframes.append(
        normalize_dataframe(pd.read_excel(tr_purchase_file, engine="openpyxl"), TR_COLUMN_MAPPING, "TR", "Alış"))
    if mc_purchase_file: dataframes.append(
        normalize_dataframe(pd.read_excel(mc_purchase_file, engine="openpyxl"), MC_COLUMN_MAPPING, "MC", "Alış"))
    if tr_sales_file: dataframes.append(
        normalize_dataframe(pd.read_excel(tr_sales_file, engine="openpyxl"), TR_COLUMN_MAPPING, "TR", "Satış"))
    if mc_sales_file: dataframes.append(
        normalize_dataframe(pd.read_excel(mc_sales_file, engine="openpyxl"), MC_COLUMN_MAPPING, "MC", "Satış"))

    if dataframes:
        merged_df = pd.concat(dataframes, ignore_index=True)
        merged_df = clean_merged_ids(merged_df)
        if "payment_method" in merged_df.columns:
            merged_df["payment_method"] = merged_df["payment_method"].astype(str).str.strip().str.lower()

        merged_df = merged_df.assign(
            product_currency=lambda df: df["product_name"].astype(str) + " / " + df["currency"].astype(str))

        st.success(f"🎉 **Dosyalar birleştirildi!** Toplam satır: **{len(merged_df)}**")

        # --- Özet Bilgiler ---
        st.subheader("🗂️ Birleştirilmiş Veri Önizleme")
        st.dataframe(merged_df, use_container_width=True)

        st.subheader("📈 Özet Bilgiler")

        # --- GÜNCELLENEN KISIM BAŞLANGIÇ ---
        # 1. Alış ve Satışları process_type sütununa göre ayırıp topluyoruz
        total_purchase_val = merged_df[merged_df["process_type"] == "Alış"]["total_price"].sum()
        total_sales_val = merged_df[merged_df["process_type"] == "Satış"]["total_price"].sum()

        # 2. Farkı hesaplıyoruz (Satış - Alış)
        diff_val = total_sales_val - total_purchase_val

        # 3. Diğer genel toplamlar (Miktar ve Margin genel kalmaya devam ediyor)
        total_amount = merged_df["amount"].sum()
        avg_margin = merged_df["margin"].mean()

        # 4. Ekrana Yazdırma (Mevcut yapıyı bozmadan yeni metrikleri ekledik)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Toplam Alış Tutarı", value=f"{total_purchase_val:,.2f} TL")
        with col2:
            st.metric(label="Toplam Satış Tutarı", value=f"{total_sales_val:,.2f} TL")
        with col3:
            st.metric(label="Fark (Satış - Alış)", value=f"{diff_val:,.2f} TL", delta_color="normal")

        st.metric(label="Toplam Ürün Miktarı", value=f"{total_amount:,.0f} Adet")
        st.metric(label="Ortalama Margin", value=f"%{avg_margin:,.2f}")
        # --- GÜNCELLENEN KISIM BİTİŞ ---

        # =========================================================================
        # 1. PARTNER ANALİZİ
        # =========================================================================
        st.subheader("📊 Partner Bazlı Analiz")
        partner_metric = st.selectbox("Grafik Kriteri:", ["İşlem Adedi", "Toplam Tutar (TL)"], key="sb_partner")

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
            fig, ax = plt.subplots(figsize=(8, 4))
            chart_data.plot(kind="bar", ax=ax, color=color_bar)
            ax.set_ylabel(ylabel_text)
            ax.set_title(f"Partner Bazlı - {partner_metric}")
            plt.xticks(rotation=0)
            st.pyplot(fig)

            partner_display = partner_agg.copy()
            partner_display.columns = ["İşlem Adedi", "Toplam Tutar (TL)"]
            partner_display["Toplam Tutar (TL)"] = partner_display["Toplam Tutar (TL)"].apply(lambda x: f"{x:,.2f} TL")
            st.write(f"📄 Partner Rapor Tablosu (Sıralama: {partner_metric})")
            st.dataframe(partner_display, use_container_width=True)
        else:
            st.info("Veri yok.")

        # =========================================================================
        # 2. ÖDEME YÖNTEMİ ANALİZİ
        # =========================================================================
        st.subheader("📊 Ödeme Yöntemi Analizi")
        payment_metric = st.selectbox("Grafik Kriteri:", ["İşlem Adedi", "Toplam Tutar (TL)"], key="sb_payment")

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
            fig2, ax2 = plt.subplots(figsize=(8, 4))
            chart_data.plot(kind="bar", ax=ax2, color=color_bar)
            ax2.set_ylabel(ylabel_text)
            ax2.set_title(f"Ödeme Yöntemi - {payment_metric}")
            plt.setp(ax2.get_xticklabels(), rotation=45, ha="right")
            plt.tight_layout()
            st.pyplot(fig2)

            payment_display = payment_agg.copy()
            payment_display.columns = ["İşlem Adedi", "Toplam Tutar (TL)"]
            payment_display["Toplam Tutar (TL)"] = payment_display["Toplam Tutar (TL)"].apply(lambda x: f"{x:,.2f} TL")
            st.write(f"📄 Ödeme Yöntemi Tablosu (Sıralama: {payment_metric})")
            st.dataframe(payment_display, use_container_width=True)
        else:
            st.info("Veri yok.")

        # =========================================================================
        # 3. MÜŞTERİ VE ÜRÜN ANALİZİ
        # =========================================================================
        st.markdown("---")
        st.header("🏆 Detaylı Müşteri ve Ürün Analizi")

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

            prod_display = prod_agg.copy()
            prod_display.columns = ["Satış Miktarı", "Toplam Ciro (TL)"]
            prod_display["Toplam Ciro (TL)"] = prod_display["Toplam Ciro (TL)"].apply(lambda x: f"{x:,.2f} TL")
            st.write(f"📄 Ürün Tablosu (Sıralama: {product_metric})")
            st.dataframe(prod_display, use_container_width=True)
        else:
            st.info("Veri yok.")

        # --- İndirme ---
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            merged_df.to_excel(writer, index=False)
        st.download_button("📥 Excel İndir", output.getvalue(), "merged.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


if __name__ == "__main__":
    run()