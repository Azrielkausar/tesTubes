import requests
import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd
import re
import matplotlib.pyplot as plt
from streamlit_folium import st_folium
import folium
import random

st.title("Alfamart Dashboard")

# 1. SCRAPING DATA DARI WEB (Kodingan Asli Anda)

with st.spinner("Scraping Cabang Alfamart..."):
    books = []
    url = "https://branchlessbanking.cimbniaga.co.id/alamat-alfamart"
    res = requests.get(url)
    if res.status_code == 200:
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Pilih semua baris tabel (tr) di dalam div.entry-content, mulai dari baris kedua (skip header)
        rows = soup.select("div.entry-content table tbody tr")[1:]
        
        for row in rows:
            tds = row.find_all("td")
            if len(tds) >= 3:
                nama = tds[1].text.strip()
                lokasi = tds[2].text.strip()
                
                # Ekstrak kota dari alamat
                parts = [p.strip() for p in lokasi.split(',')]
                if len(parts) == 1:
                    kota = parts[0]
                elif len(parts) == 2:
                    kota = parts[1]
                else:
                    kota = parts[-2]
                
                # Hapus kode pos atau bagian numerik di akhir jika ada
                kota = re.sub(r'\s*\d+.*$', '', kota).strip()
                
                # Bersihkan kota (Jakarta, Bogor, Depok, Tangerang, Bekasi)
                kota_lower = kota.lower()
                if 'jakarta' in kota_lower:
                    kota = 'Jakarta'
                elif 'bogor' in kota_lower:
                    kota = 'Bogor'
                elif 'depok' in kota_lower:
                    kota = 'Depok'
                elif 'tangerang' in kota_lower:
                    kota = 'Tangerang'
                elif 'bekasi' in kota_lower:
                    kota = 'Bekasi'
                else:
                    kota = kota
                
                books.append({"Nama Toko": nama, "Alamat": lokasi, "kota": kota})

    df_raw = pd.DataFrame(books)
    # Filter JABODETABEK (case-insensitive)
    df_books = df_raw[df_raw['kota'].str.contains('jakarta|bogor|depok|tangerang|bekasi', case=False, na=False)].copy()

# --- FITUR SEARCH (TAMBAHAN BARU) ---
st.sidebar.header("Fitur Pencarian")
search_query = st.sidebar.text_input("Cari Nama Toko atau Alamat:", "")

# Filter dataframe berdasarkan input search
if search_query:
    df_filtered = df_books[
        df_books['Nama Toko'].str.contains(search_query, case=False, na=False) | 
        df_books['Alamat'].str.contains(search_query, case=False, na=False)
    ]
else:
    df_filtered = df_books

# Menampilkan Tabel Hasil Filter
st.subheader("Daftar Cabang Alfamart")
st.dataframe(df_filtered, use_container_width=True)
st.write(f"Jumlah data ditampilkan: {len(df_filtered)}")

# 2. VISUALISASI DATA MENGGUNAKAN DIAGRAM BATANG (Kodingan Asli Anda)

# Hitung banyak data tiap kota dari hasil filter
kota_counts = df_filtered['kota'].value_counts().reset_index()
kota_counts.columns = ['Kota', 'Jumlah']
# Acak urutan kota
kota_counts = kota_counts.sample(frac=1).reset_index(drop=True)

if not kota_counts.empty:
    st.write("Visualisasi Jumlah Cabang per Kota:")
    plt.figure(figsize=(10, 6))
    plt.bar(kota_counts['Kota'], kota_counts['Jumlah'], color=['red', 'yellow', 'green', 'blue', 'purple'])
    
    for i, v in enumerate(kota_counts['Jumlah']):
        plt.text(i, v + 0.1, str(v), ha='center', va='bottom')
    
    plt.xlabel('Kota')
    plt.ylabel('Jumlah Branch')
    plt.title('Jumlah Cabang Alfamart per Kota (Hasil Filter)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(plt)

# 3. FITUR GIS (PETA SEBARAN)

st.write("---")
st.header("Peta Sebaran Alfamart (GIS)")

# Data koordinat titik tengah kota
city_coords = {
    'Jakarta': [-6.2088, 106.8456],
    'Bogor': [-6.5971, 106.8060],
    'Depok': [-6.4025, 106.7942],
    'Tangerang': [-6.1783, 106.6319],
    'Bekasi': [-6.2383, 106.9756]
}

# Membuat peta dasar
m = folium.Map(location=[-6.2000, 106.8166], zoom_start=10)

# Looping data hasil filter ke peta (maksimal 100 titik agar tetap ringan)
df_map = df_filtered.head(100)

for index, row in df_map.iterrows():
    kota_key = row['kota']
    if kota_key in city_coords:
        # Menambahkan random offset agar marker tidak menumpuk
        lat_random = city_coords[kota_key][0] + random.uniform(-0.04, 0.04)
        lon_random = city_coords[kota_key][1] + random.uniform(-0.04, 0.04)
        
        folium.Marker(
            location=[lat_random, lon_random],
            popup=f"<b>{row['Nama Toko']}</b><br>{row['Alamat']}",
            tooltip=row['Nama Toko'],
            icon=folium.Icon(color="red", icon="shopping-cart", prefix="fa")
        ).add_to(m)

st_folium(m, width=900, height=500)