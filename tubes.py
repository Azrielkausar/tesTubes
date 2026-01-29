import requests
import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd
import re
import matplotlib.pyplot as plt
from streamlit_folium import st_folium
import folium
from folium.plugins import MarkerCluster
import random

# 1. KONFIGURASI HALAMAN (Wajib Paling Atas)
st.set_page_config(page_title="Alfamart Dashboard", layout="wide")

st.title("🛒 Dashboard Sebaran Alfamart Jabodetabek")

# 2. FUNGSI SCRAPING DENGAN CACHE & HEADERS (Agar Tidak Error di Server)
@st.cache_data(ttl=3600) # Data disimpan selama 1 jam
def fetch_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    url = "https://branchlessbanking.cimbniaga.co.id/alamat-alfamart"
    
    try:
        res = requests.get(url, headers=headers, timeout=20)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.select("div.entry-content table tbody tr")[1:]
        
        data = []
        for row in rows:
            tds = row.find_all("td")
            if len(tds) >= 3:
                nama = tds[1].text.strip()
                lokasi = tds[2].text.strip()
                
                # Ekstrak Kota
                parts = [p.strip() for p in lokasi.split(',')]
                kota = parts[1] if len(parts) == 2 else (parts[-2] if len(parts) > 2 else parts[0])
                kota = re.sub(r'\s*\d+.*$', '', kota).strip()
                
                kota_l = kota.lower()
                if 'jakarta' in kota_l: kota = 'Jakarta'
                elif 'bogor' in kota_l: kota = 'Bogor'
                elif 'depok' in kota_l: kota = 'Depok'
                elif 'tangerang' in kota_l: kota = 'Tangerang'
                elif 'bekasi' in kota_l: kota = 'Bekasi'
                
                data.append({"Nama Toko": nama, "Alamat": lokasi, "Kota": kota})
        return pd.DataFrame(data)
    except Exception as e:
        return pd.DataFrame([{"Nama Toko": "Error Koneksi", "Alamat": str(e), "Kota": "N/A"}])

# Jalankan Fungsi
with st.spinner("Sedang mengambil data dari server..."):
    df_raw = fetch_data()

# Filter Jabodetabek
df_books = df_raw[df_raw['Kota'].str.contains('Jakarta|Bogor|Depok|Tangerang|Bekasi', case=False, na=False)].copy()

# 3. SIDEBAR SEARCH
st.sidebar.header("🔍 Pencarian")
search = st.sidebar.text_input("Cari Gerai/Alamat:")
if search:
    df_display = df_books[df_books['Nama Toko'].str.contains(search, case=False) | df_books['Alamat'].str.contains(search, case=False)]
else:
    df_display = df_books

# 4. TABULAR & VISUALISASI
st.subheader(f"📊 Data Tabular ({len(df_display)} Gerai)")
st.dataframe(df_display, use_container_width=True)

if not df_display.empty and len(df_display) > 1:
    st.write("### Grafik Distribusi")
    counts = df_display['Kota'].value_counts()
    fig, ax = plt.subplots()
    counts.plot(kind='bar', ax=ax, color='red')
    st.pyplot(fig)

# 5. GIS (PETA)
st.write("---")
st.subheader("🗺️ Peta Sebaran GIS")

city_coords = {
    'Jakarta': [-6.2088, 106.8456], 'Bogor': [-6.5971, 106.8060],
    'Depok': [-6.4025, 106.7942], 'Tangerang': [-6.1783, 106.6319], 'Bekasi': [-6.2383, 106.9756]
}

m = folium.Map(location=[-6.2000, 106.8166], zoom_start=10)
marker_cluster = MarkerCluster().add_to(m)

for _, row in df_display.iterrows():
    k = row['Kota']
    if k in city_coords:
        lat = city_coords[k][0] + random.uniform(-0.07, 0.07)
        lon = city_coords[k][1] + random.uniform(-0.07, 0.07)
        folium.Marker([lat, lon], popup=row['Nama Toko']).add_to(marker_cluster)

# returned_objects=[] agar tidak loop reload
st_folium(m, width=1100, height=500, returned_objects=[])
