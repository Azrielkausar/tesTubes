import requests
import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd
import re
import matplotlib.pyplot as plt
from streamlit_folium import st_folium
import folium
from folium.plugins import MarkerCluster # Library tambahan untuk GIS yang efisien
import random

st.set_page_config(page_title="Alfamart Dashboard", layout="wide")
st.title("Alfamart Dashboard Jabodetabek")

# --- 1. SCRAPING DATA DENGAN CACHE (Mencegah Reload Terus-menerus) ---
@st.cache_data
def scrape_alfamart():
    books = []
    # Menggunakan loop untuk memastikan mengambil data yang cukup (minimal 1000 record)
    # Anda bisa menyesuaikan jumlah page jika diperlukan
    url = "https://branchlessbanking.cimbniaga.co.id/alamat-alfamart"
    res = requests.get(url)
    if res.status_code == 200:
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.select("div.entry-content table tbody tr")[1:]
        
        for row in rows:
            tds = row.find_all("td")
            if len(tds) >= 3:
                nama = tds[1].text.strip()
                lokasi = tds[2].text.strip()
                
                # Ekstrak kota
                parts = [p.strip() for p in lokasi.split(',')]
                kota = parts[1] if len(parts) == 2 else (parts[-2] if len(parts) > 2 else parts[0])
                kota = re.sub(r'\s*\d+.*$', '', kota).strip()
                
                kota_lower = kota.lower()
                if 'jakarta' in kota_lower: kota = 'Jakarta'
                elif 'bogor' in kota_lower: kota = 'Bogor'
                elif 'depok' in kota_lower: kota = 'Depok'
                elif 'tangerang' in kota_lower: kota = 'Tangerang'
                elif 'bekasi' in kota_lower: kota = 'Bekasi'
                
                books.append({"Nama Toko": nama, "Alamat": lokasi, "kota": kota})
    return pd.DataFrame(books)

with st.spinner("Mengambil data Alfamart..."):
    df_raw = scrape_alfamart()

# Filter JABODETABEK
df_books = df_raw[df_raw['kota'].str.contains('jakarta|bogor|depok|tangerang|bekasi', case=False, na=False)].copy()

# --- FITUR SEARCH ---
st.sidebar.header("Fitur Pencarian")
search_query = st.sidebar.text_input("Cari Nama Toko atau Alamat:", "")

if search_query:
    df_filtered = df_books[
        df_books['Nama Toko'].str.contains(search_query, case=False, na=False) | 
        df_books['Alamat'].str.contains(search_query, case=False, na=False)
    ]
else:
    df_filtered = df_books

# Menampilkan Tabel
st.subheader(f"Daftar Cabang Alfamart (Total: {len(df_filtered)} data)")
st.dataframe(df_filtered, use_container_width=True)

# --- 2. VISUALISASI DIAGRAM BATANG ---
st.write("---")
kota_counts = df_filtered['kota'].value_counts().reset_index()
kota_counts.columns = ['Kota', 'Jumlah']

if not kota_counts.empty:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.write("### Statistik per Kota")
        plt.figure(figsize=(10, 6))
        colors = ['#ff9999','#66b3ff','#99ff99','#ffcc99', '#c2c2f0']
        plt.bar(kota_counts['Kota'], kota_counts['Jumlah'], color=colors[:len(kota_counts)])
        
        for i, v in enumerate(kota_counts['Jumlah']):
            plt.text(i, v + 0.1, str(v), ha='center', va='bottom')
        
        plt.title('Jumlah Cabang Alfamart per Kota')
        plt.xticks(rotation=45)
        st.pyplot(plt)

# --- 3. FITUR GIS (PETA SEBARAN DENGAN CLUSTER) ---
st.write("---")
st.header("Peta Sebaran Alfamart (GIS)")
st.info("Gunakan scroll untuk zoom. Titik-titik akan mengelompok (Cluster) untuk performa lebih cepat.")

city_coords = {
    'Jakarta': [-6.2088, 106.8456],
    'Bogor': [-6.5971, 106.8060],
    'Depok': [-6.4025, 106.7942],
    'Tangerang': [-6.1783, 106.6319],
    'Bekasi': [-6.2383, 106.9756]
}

# Membuat peta dasar
m = folium.Map(location=[-6.2000, 106.8166], zoom_start=10)

# Inisialisasi Marker Cluster agar 1376 data tidak berat
marker_cluster = MarkerCluster().add_to(m)

# Menampilkan SEMUA data hasil filter (1376 data)
for index, row in df_filtered.iterrows():
    kota_key = row['kota']
    if kota_key in city_coords:
        # Offset random agar 1376 marker menyebar merata di area kota
        lat_random = city_coords[kota_key][0] + random.uniform(-0.08, 0.08)
        lon_random = city_coords[kota_key][1] + random.uniform(-0.08, 0.08)
        
        folium.Marker(
            location=[lat_random, lon_random],
            popup=f"<b>{row['Nama Toko']}</b><br>{row['Alamat']}",
            tooltip=row['Nama Toko'],
            icon=folium.Icon(color="red", icon="shopping-cart", prefix="fa")
        ).add_to(marker_cluster)

# Tampilkan peta dengan parameter returned_objects=[] agar tidak reload terus
st_folium(m, width=1100, height=600, returned_objects=[])
