# Proyek Analisis Data: E-Commerce Public Dataset (Olist)

Analisis data transaksi marketplace Olist (Brasil) pada periode Januari 2017 sampai Agustus 2018, lengkap dengan notebook analisis dan dashboard interaktif Streamlit.

## Pertanyaan bisnis
1. Kategori produk apa saja yang masuk 10 besar berdasarkan total revenue (R$) dan berapa persen kontribusinya terhadap total revenue pada periode Januari 2017 sampai Agustus 2018, sebagai dasar menentukan prioritas stok, anggaran promosi, dan rekrutmen seller?
2. Bagaimana sebaran jumlah pelanggan dan total revenue pada setiap segmen RFM pada periode Januari 2017 sampai Agustus 2018, dan segmen mana yang menyumbang revenue terbesar, sebagai dasar menyusun strategi retensi dan win-back untuk setiap segmen?
3. Di state mana pelanggan dan revenue paling terkonsentrasi, dan berapa rata-rata waktu pengiriman (hari) serta rata-rata review score di setiap state pada periode Januari 2017 sampai Agustus 2018, sebagai dasar menentukan wilayah prioritas perbaikan logistik?

## Struktur proyek
```
submission/
├── dashboard/
│   ├── dashboard.py        # aplikasi Streamlit
│   ├── main_data.csv       # data hasil cleaning (dibuat oleh notebook)
│   ├── state_geo.csv       # titik tengah koordinat tiap state (dibuat oleh notebook)
│   └── requirements.txt
├── data/                   # 9 file CSV dataset asli (unduh dari sumber dataset)
├── notebook.ipynb          # proses analisis lengkap
├── requirements.txt
├── README.md
└── url.txt                 # tautan dashboard di Streamlit Cloud
```

## Menjalankan di komputer lokal
```bash
# 1. (opsional) buat virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 2. pasang library
pip install -r requirements.txt

# 3. jalankan dashboard
streamlit run dashboard/dashboard.py
```

Untuk menjalankan ulang notebook, letakkan 9 file CSV dataset di folder `data/`, lalu jalankan semua sel pada `notebook.ipynb`. Library tambahan `folium` (opsional, untuk peta interaktif di notebook) dipasang dengan `pip install folium`.

## Deploy ke Streamlit Community Cloud
1. Unggah folder proyek ke repository GitHub **publik**.
2. Buka https://share.streamlit.io, pilih **New app**, lalu pilih repository dan branch.
3. Isi **Main file path** dengan `dashboard/dashboard.py`, lalu **Deploy**.
4. Salin tautan aplikasi ke `url.txt`.
