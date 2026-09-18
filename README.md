# MATA PASAR — Dashboard Pemantauan Harga Bahan Pokok Kota Bontang

Dashboard interaktif untuk memantau harga bahan pokok dan penting (bapokting) di 3 pasar Kota Bontang: Rawa Indah, Telihan, dan Citra Mas.

Dikembangkan untuk mendukung kegiatan **MATA PASAR** (Monitor Akurat dan Transparansi Harga Pasar), Dinas Koperasi, Usaha Mikro, Perindustrian dan Perdagangan Kota Bontang.

## Indikator Utama

### Indikator 1 — Persentase Komoditas dengan Disparitas Harga di Atas Target

Mengukur keseragaman harga antar pasar. Disparitas setiap komoditas dihitung dengan rumus:

**Disparitas = (Harga Termahal − Harga Termurah) / Rata-rata 3 Pasar × 100%**

Target Kota Bontang: **≤ 1%** per komoditas.

### Indikator 2 — Persentase Komoditas yang Harganya Stabil

Mengukur kestabilan harga dari waktu ke waktu menggunakan z-score. Perubahan harga bulanan setiap komoditas dibandingkan dengan pola historisnya:

**z = (Perubahan harga bulan ini − Rata-rata perubahan historis) / Standar deviasi perubahan historis**

Komoditas dianggap stabil jika |z| ≤ 1. Target Kota Bontang: **≥ 71,5%** komoditas stabil.

## Halaman Dashboard

| Halaman | Isi |
|---|---|
| **Monitoring Harga BAPOK** | KPI kedua indikator, tabel disparitas per kelompok tingkat, tabel stabilisasi per zona z-score |
| **Disparitas Harga** | Heatmap z-score per pasar, grafik batang disparitas, perbandingan harga 3 pasar, tren persentase di atas target |
| **Stabilisasi & Tren** | Grafik z-score per komoditas, tren harga harian, tren pencapaian target stabilisasi |

## Cara Menjalankan

### 1. Install dependensi

```bash
pip install -r requirements.txt
```

### 2. Siapkan data

Letakkan file `data_harga_bahan_pokok.csv` di folder yang sama dengan `dashboard_mata_pasar.py`.

Format CSV:

```
pasar,tanggal,bulan,hari,kode_komoditas,kategori,nama_bahan_pokok,satuan,harga,harga_rata2_bulan_lalu,harga_rata2_bulan_ini,perubahan_rp,perubahan_persen,keterangan
```

### 3. Jalankan dashboard

```bash
streamlit run dashboard_mata_pasar.py
```

Dashboard akan terbuka di browser pada `http://localhost:8501`.

## Deploy ke Streamlit Cloud

1. Push repository ini ke GitHub
2. Buka [share.streamlit.io](https://share.streamlit.io)
3. Hubungkan dengan repository GitHub
4. Pilih `dashboard_mata_pasar.py` sebagai Main file
5. Klik Deploy

## Struktur File

```
├── dashboard_mata_pasar.py      # Dashboard Streamlit
├── data_harga_bahan_pokok.csv   # Data harga (CSV)
├── requirements.txt             # Dependensi Python
└── README.md                    # Dokumentasi
```

## Metodologi

### Disparitas Harga (Indikator 1)

Disparitas dihitung dari harga rata-rata bulanan per komoditas per pasar, menggunakan rumus KAK. Setiap pasar juga dievaluasi dengan z-score terhadap rata-rata kota untuk mengidentifikasi pasar mana yang menyimpang.

### Stabilisasi Harga (Indikator 2)

Kestabilan diukur menggunakan z-score perubahan harga bulanan. Klasifikasi berdasarkan standar deviasi:

| z-score | Status | Tindakan |
|---|---|---|
| −1 s.d +1 | Terkendali | Tidak perlu tindakan |
| +1 s.d +2 | Perlu perhatian | Tingkatkan pemantauan |
| > +2 | Intervensi segera | Koordinasi TPID |
| −2 s.d −1 | Evaluasi penurunan | Periksa kualitas/pasokan |
| < −2 | Investigasi | Investigasi penyebab |

Klasifikasi ini merupakan penyempurnaan dari metode PIHPS Bank Indonesia, dimana rentang ±1 SD dijadikan zona wajar (sesuai kaidah distribusi normal yang mencakup 68,3% data).

## Referensi

- Kerangka Acuan Kerja (KAK) Kegiatan MATA PASAR, Dinas Koperasi, Usaha Mikro, Perindustrian dan Perdagangan Kota Bontang, Tahun Anggaran 2026
- Pusat Informasi Harga Pangan Strategis (PIHPS), Bank Indonesia
- Peraturan Presiden Nomor 71 Tahun 2015 tentang Penetapan dan Penyimpanan Barang Kebutuhan Pokok dan Barang Penting

---

**MATA PASAR** © 2026 — Dinas Koperasi, Usaha Mikro, Perindustrian dan Perdagangan Kota Bontang
