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

# Konfigurasi Halaman
st.set_page_config(page_title="Dashboard Alfamart Jabodetabek", layout="wide")

st.title("🛒 Analisis Spasial Sebaran Alfamart Jabodetabek")
st.markdown("""
Aplikasi ini melakukan **Scraping Data** secara real-time, memberikan **Visualisasi Statistik**, 
dan menampilkan **Sistem Informasi Geografis (GIS)** sebaran gerai Alfamart.
""")

# --- 1. FUNGSI SCRAPING (DENGAN CACHE) ---
@st.cache_data
def scrape_data_alfamart():
    books = []
    # URL sumber data (CIMB Niaga Alamat Alfamart)
    url = "https://branchlessbanking.cimbniaga.co.id/alamat-alfamart"
    
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # Seleksi baris tabel, skip header
            rows = soup.select("div.entry-content table tbody tr")[1:]
            
            for row in rows:
                tds = row.find_all("td")
                if len(tds) >= 3:
                    nama = tds[1].text.strip()
                    lokasi = tds[2].text.strip()
                    
                    # Logika ekstraksi kota
                    parts = [p.strip() for p in lokasi.split(',')]
                    if len(parts) == 1: kota = parts[0]
                    elif len(parts) == 2: kota = parts[1]
                    else: kota = parts[-2]
                    
                    # Bersihkan kode pos/angka
                    kota = re.sub(r'\s*\d+.*$', '', kota).strip()
                    
                    # Standarisasi Nama Kota Jabodetabek
                    kota_l = kota.lower()
                    if 'jakarta' in kota_l: kota = 'Jakarta'
                    elif 'bogor' in kota_l: kota = 'Bogor'
                    elif 'depok' in kota_l: kota = 'Depok'
                    elif 'tangerang' in kota_l: kota = 'Tangerang'
                    elif 'bekasi' in kota_l: kota = 'Bekasi'
                    
                    books.append({"Nama Toko": nama, "Alamat": lokasi, "Kota": kota})
        return pd.DataFrame(books)
    except Exception as e:
        st.error(f"Gagal Scraping: {e}")
        return pd.DataFrame()

# Menjalankan Scraping
with st.spinner("Sedang melakukan Scraping data..."):
    df_raw = scrape_data_alfamart()

# Filter Data Jabodetabek
if not df_raw.empty:
    df_books = df_raw[df_raw['Kota'].str.contains('Jakarta|Bogor|Depok|Tangerang|Bekasi', case=False, na=False)].copy()
else:
    df_books = pd.DataFrame()

# --- 2. SIDEBAR PENCARIAN ---
st.sidebar.header("🔍 Fitur Pencarian")
search_query = st.sidebar.text_input("Cari Nama Toko atau Jalan:", "")

if search_query:
    df_filtered = df_books[
        df_books['Nama Toko'].str.contains(search_query, case=False, na=False) | 
        df_books['Alamat'].str.contains(search_query, case=False, na=False)
    ]
else:
    df_filtered = df_books

# --- 3. TAMPILAN DATA TABULAR ---
st.subheader(f"📊 Data Tabular (Ditemukan: {len(df_filtered)} Gerai)")
st.dataframe(df_filtered, use_container_width=True)

# --- 4. VISUALISASI DIAGRAM BATANG ---
st.write("---")
st.subheader("📈 Visualisasi Distribusi Gerai")

if not df_filtered.empty:
    counts = df_filtered['Kota'].value_counts()
    
    fig, ax = plt.subplots(figsize=(10, 5))
    counts.plot(kind='bar', ax=ax, color=['#e63946', '#f1faee', '#a8dadc', '#457b9d', '#1d3557'])
    
    # Tambah label angka di atas batang
    for i, v in enumerate(counts):
        ax.text(i, v + 2, str(v), ha='center', fontweight='bold')
        
    ax.set_xlabel("Kota/Kabupaten")
    ax.set_ylabel("Jumlah Gerai")
    plt.xticks(rotation=0)
    st.pyplot(fig)

# --- 5. IMPLEMENTASI GIS (PETA SEBARAN) ---
st.write("---")
st.subheader("🗺️ Geographic Information System (GIS)")
st.info("Peta di bawah menggunakan **Marker Clustering** untuk mengelola 1000+ data agar tetap ringan.")

# Koordinat pusat tiap kota untuk sebaran random
city_coords = {
    'Jakarta': [-6.2088, 106.8456],
    'Bogor': [-6.5971, 106.8060],
    'Depok': [-6.4025, 106.7942],
    'Tangerang': [-6.1783, 106.6319],
    'Bekasi': [-6.2383, 106.9756]
}

# Membuat Peta Dasar (Pusat di Jabodetabek)
m = folium.Map(location=[-6.2000, 106.8166], zoom_start=10)

# Tambahkan Fitur Cluster
marker_cluster = MarkerCluster().add_to(m)

# Menampilkan semua data hasil filter ke peta
for index, row in df_filtered.iterrows():
    k = row['Kota']
    if k in city_coords:
        # Random offset agar marker tidak menumpuk di satu titik pusat
        lat = city_coords[k][0] + random.uniform(-0.07, 0.07)
        lon = city_coords[k][1] + random.uniform(-0.07, 0.07)
        
        folium.Marker(
            location=[lat, lon],
            popup=f"<b>{row['Nama Toko']}</b><br>{row['Alamat']}",
            tooltip=row['Nama Toko'],
            icon=folium.Icon(color="red", icon="shopping-cart", prefix="fa")
        ).add_to(marker_cluster)

# Tampilkan Peta di Streamlit
# returned_objects=[] kunci agar peta tidak reload terus menerus
st_folium(m, width=1200, height=600, returned_objects=[])

st.success(f"Berhasil memetakan {len(df_filtered)} titik koordinat gerai Alfamart.")
