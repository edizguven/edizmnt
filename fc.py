import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO

def fraud_page():

    st.title(" Fraud Kontrol")
    st.write("Kullanıcının toplam **Total** değerine göre olası fraud işlemleri tespit edin.")

    uploaded_file = st.file_uploader("📂 Excel veya CSV dosyanızı yükleyin", type=["xlsx", "csv"])

    if uploaded_file:

        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.success("✅ Dosya başarıyla yüklendi!")
        st.dataframe(df.head(), use_container_width=True)

        df.columns = df.columns.str.strip().str.lower()

        if "create date" not in df.columns:
            st.error("❌ 'Create Date' sütunu bulunamadı. Lütfen kontrol edin.")
            st.stop()

        try:
            df["create date"] = pd.to_datetime(df["create date"])
        except Exception:
            st.error("❌ 'Create Date' sütunu tarih formatında değil. Lütfen kontrol edin.")
            st.stop()

        min_date = df["create date"].min().date()
        max_date = df["create date"].max().date()

        st.markdown("### 🗓️ Tarih Aralığı Filtreleme")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Başlangıç tarihi", min_date)
        with col2:
            end_date = st.date_input("Bitiş tarihi", max_date)

        if start_date > end_date:
            st.error("❌ Başlangıç tarihi bitiş tarihinden sonra olamaz.")
            st.stop()

        mask = (df["create date"].dt.date >= start_date) & (df["create date"].dt.date <= end_date)
        filtered_df = df.loc[mask]

        if filtered_df.empty:
            st.warning(f"⚠️ {start_date} → {end_date} tarihleri arasında hiçbir kayıt bulunamadı.")
            st.stop()

        st.info(f"📅 Seçilen aralık: {start_date} → {end_date} ({len(filtered_df)} kayıt)")

        limit = st.number_input("🚨 Fraud limitini belirleyin (örnek: 900.00)", min_value=0.0, step=100.0)

        if st.button("Fraud Kontrolünü Başlat"):

            if "name-surname" not in filtered_df.columns or "total" not in filtered_df.columns:
                st.error("❌ Gerekli sütunlar ('Name-Surname' ve 'Total') bulunamadı.")
                st.stop()

            filtered_df["total"] = (
                filtered_df["total"]
                .astype(str)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
                .str.extract(r"([0-9]+\.?[0-9]*)", expand=False)
                .astype(float)
            )

            grouped = filtered_df.groupby("name-surname", as_index=False)["total"].sum()

            grouped = grouped.sort_values(by="total", ascending=False).head(20)

            frauds = grouped[grouped["total"] > limit]
            normal = grouped[grouped["total"] <= limit]

            total_users = len(grouped)
            fraud_count = len(frauds)
            normal_count = len(normal)

            if fraud_count > 0:
                st.error(f"🚨 {fraud_count} adet olası fraud tespit edildi!")
                st.dataframe(frauds, use_container_width=True)
            else:
                st.success("✅ Hiçbir fraud tespit edilmedi.")

            fraud_ratio = (fraud_count / total_users) * 100 if total_users > 0 else 0
            normal_ratio = 100 - fraud_ratio

            st.markdown("### 📊 Fraud / Normal İşlem Oranı")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Fraud Oranı", f"{fraud_ratio:.2f}%")
            with col2:
                st.metric("Normal Oranı", f"{normal_ratio:.2f}%")

            if total_users > 0:
                fig, ax = plt.subplots()
                ax.pie(
                    [fraud_count, normal_count],
                    labels=["Fraud", "Normal"],
                    autopct="%1.1f%%",
                    colors=["#FF4B4B", "#4CAF50"],
                    startangle=90,
                    explode=(0.1, 0)
                )
                ax.axis("equal")
                st.pyplot(fig)

            st.markdown("### 🧍‍♂️ Kullanıcı Bazlı Toplam Total Grafiği")
            colors = grouped["total"].apply(lambda x: "#FF4B4B" if x > limit else "#4CAF50")
            fig2, ax2 = plt.subplots(figsize=(10, 5))
            ax2.bar(grouped["name-surname"], grouped["total"], color=colors)
            ax2.axhline(y=limit, color="orange", linestyle="--", label=f"Limit ({limit})")
            ax2.set_ylabel("Toplam Total")
            ax2.set_xlabel("Kullanıcılar")
            ax2.set_xticks(range(len(grouped)))
            ax2.set_xticklabels(grouped["name-surname"], rotation=45, ha="right")
            ax2.legend()
            st.pyplot(fig2)

            st.markdown("### 📥 Rapor İndir")

            def convert_df_to_excel(df):
                output = BytesIO()
                df.to_excel(output, index=False, engine='openpyxl')
                output.seek(0)
                return output

            if fraud_count > 0:
                excel_fraud = convert_df_to_excel(frauds)
                st.download_button(
                    label="📥 Fraud Liste Excel Olarak İndir",
                    data=excel_fraud,
                    file_name="fraud_list.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            if normal_count > 0:
                excel_normal = convert_df_to_excel(normal)
                st.download_button(
                    label="📥 Normal Liste Excel Olarak İndir",
                    data=excel_normal,
                    file_name="normal_list.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    else:
        st.info("Lütfen bir dosya yükleyin ve limiti girin.")

    st.markdown("---")
    st.caption("MintedTR")

def run():
    fraud_page()
