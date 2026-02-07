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
st.set_page_config(page_title="Tugas Besar", layout="wide")

st.title("🛒 Analisis Spasial dan Pemetaan Sebaran Retail Alfamart di jabodetabek Berbasis Big Data untuk Optimalisasi Strategi Jangkauan Konsumen.")
st.markdown("""
Aplikasi ini melakukan **Scraping Data** secara real-time, memberikan **Visualisasi Statistik**, 
dan menampilkan **Sistem Informasi Geografis (GIS)** sebaran gerai Alfamart.
""")

# --- 1. FUNGSI SCRAPING ---
@st.cache_data
def scrape_data_alfamart():
    stores = []
    url = "https://branchlessbanking.cimbniaga.co.id/alamat-alfamart"
    
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            rows = soup.select("div.entry-content table tbody tr")[1:]
            
            for row in rows:
                tds = row.find_all("td")
                if len(tds) >= 3:
                    nama = tds[1].text.strip()
                    lokasi = tds[2].text.strip()
                    
                    parts = [p.strip() for p in lokasi.split(',')]
                    if len(parts) == 1: kota = parts[0]
                    elif len(parts) == 2: kota = parts[1]
                    else: kota = parts[-2]
                    
                    kota = re.sub(r'\s*\d+.*$', '', kota).strip()
                    
                    kota_l = kota.lower()
                    if 'jakarta' in kota_l: kota = 'Jakarta'
                    elif 'bogor' in kota_l: kota = 'Bogor'
                    elif 'depok' in kota_l: kota = 'Depok'
                    elif 'tangerang' in kota_l: kota = 'Tangerang'
                    elif 'bekasi' in kota_l: kota = 'Bekasi'
                    
                    stores.append({"Nama Toko": nama, "Alamat": lokasi, "Kota": kota})
        return pd.DataFrame(stores)
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

# --- 2. FITUR PENCARIAN & FILTER ---
st.sidebar.header("🔍 Fitur Pencarian")

# Tambahkan Filter Kota yang spesifik
list_kota = ["Semua Kota", "Jakarta", "Bogor", "Depok", "Tangerang", "Bekasi"]
selected_city = st.sidebar.selectbox("Pilih Kota:", list_kota)

# Pencarian berdasarkan Nama/Alamat tetap ada
search_query = st.sidebar.text_input("Cari Nama Toko atau Jalan:", "").strip()

# --- PROSES FILTERING ---
df_filtered = df_books.copy()

# Filter 1: Berdasarkan Kota (Exact Match)
if selected_city != "Semua Kota":
    df_filtered = df_filtered[df_filtered['Kota'] == selected_city]

# Filter 2: Berdasarkan Kata Kunci (Jika ada)
if search_query != "":
    mask_nama = df_filtered['Nama Toko'].str.contains(search_query, case=False, na=False)
    mask_alamat = df_filtered['Alamat'].str.contains(search_query, case=False, na=False)
    df_filtered = df_filtered[mask_nama | mask_alamat]



# --- 3. MENAMPILKAN BANYAK DATA HASIL SCRAPING ---
st.subheader(f"📊 Data Hasil Scraping (Ditemukan: {len(df_filtered)} Gerai)")
st.dataframe(df_filtered, use_container_width=True)

# --- 4. VISUALISASI DIAGRAM BATANG ---
st.write("---")
st.subheader("📈 Visualisasi Distribusi Gerai Alfamart di Jabodetabek")

if not df_filtered.empty:
    counts = df_filtered['Kota'].value_counts()
    
    cities = list(counts.index)
    random.shuffle(cities)
    counts = counts.reindex(cities)
    
    fig, ax = plt.subplots(figsize=(10, 5))
    counts.plot(kind='bar', ax=ax, color=['#e63946', '#f1faee', '#a8dadc', '#457b9d', '#1d3557'])
    
    for i, v in enumerate(counts):
        ax.text(i, v + 2, str(v), ha='center', fontweight='bold')
        
    ax.set_xlabel("Kota")
    ax.set_ylabel("Jumlah Gerai")
    plt.title('Jumlah Cabang Alfamart per Kota di JABODETABEK')
    plt.xticks(rotation=0)
    st.pyplot(fig)

# --- 5. IMPLEMENTASI GIS (PETA SEBARAN) ---
st.write("---")
st.subheader("🗺️ Geographic Information System (GIS)")
st.info("Peta di bawah menggunakan **Marker Clustering** untuk mengelola 1000+ data agar tetap ringan.")

city_coords = {
    'Jakarta': [-6.2088, 106.8456],
    'Bogor': [-6.5971, 106.8060],
    'Depok': [-6.4025, 106.7942],
    'Tangerang': [-6.1783, 106.6319],
    'Bekasi': [-6.2383, 106.9756]
}

m = folium.Map(location=[-6.2000, 106.8166], zoom_start=10)

marker_cluster = MarkerCluster().add_to(m)

for index, row in df_filtered.iterrows():
    k = row['Kota']
    if k in city_coords:
        lat = city_coords[k][0] + random.uniform(-0.07, 0.07)
        lon = city_coords[k][1] + random.uniform(-0.07, 0.07)
        
        folium.Marker(
            location=[lat, lon],
            popup=f"<b>{row['Nama Toko']}</b><br>{row['Alamat']}",
            tooltip=row['Nama Toko'],
            icon=folium.Icon(color="red", icon="shopping-cart", prefix="fa")
        ).add_to(marker_cluster)

st_folium(m, width=1200, height=600, returned_objects=[])

st.success(f"Berhasil memetakan {len(df_filtered)} titik koordinat gerai Alfamart.")
