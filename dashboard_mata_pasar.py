"""
Dashboard MATA PASAR
====================
Pemantauan Harga Bahan Pokok Kota Bontang
Dinas Koperasi, Usaha Mikro, Perindustrian dan Perdagangan

Dependensi:
  pip install streamlit pandas plotly numpy

Penggunaan:
  streamlit run dashboard_mata_pasar.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ── Konfigurasi halaman ───────────────────────────────────────────────

st.set_page_config(
    page_title="MATA PASAR — Kota Bontang",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS: expander panduan berwarna orange ──────────────────────
st.markdown("""
<style>
    /* Style untuk expander panduan (biru tua menarik) */
    div[data-testid="stExpander"] details summary {
        background: linear-gradient(135deg, #1B3A5C, #2C5F8A);
        color: white !important;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        font-weight: 500;
    }
    div[data-testid="stExpander"] details summary:hover {
        background: linear-gradient(135deg, #15304D, #1B3A5C);
        cursor: pointer;
    }
    div[data-testid="stExpander"] details summary svg {
        fill: white !important;
    }
    div[data-testid="stExpander"] details[open] summary {
        border-radius: 8px 8px 0 0;
    }
    div[data-testid="stExpander"] details {
        border: 1px solid #2C5F8A;
        border-radius: 8px;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Zona z-score ──────────────────────────────────────────────────────

ZONA_COLORS = {
    'Investigasi':        '#085041',
    'Evaluasi penurunan': '#0F6E56',
    'Terkendali':         '#EF9F27',
    'Perlu perhatian':    '#D85A30',
    'Intervensi segera':  '#A32D2D',
    'Di bawah':           '#0F6E56',
    'Wajar':              '#EF9F27',
    'Di atas':            '#D85A30',
}


def zona_label_disparitas(z):
    if abs(z) <= 1:  return 'Wajar'
    elif z > 1:      return 'Di atas'
    else:            return 'Di bawah'


def zona_label_stabilisasi(z):
    if abs(z) <= 1:  return 'Terkendali'
    elif abs(z) <= 2: return 'Perlu perhatian' if z > 0 else 'Evaluasi penurunan'
    else:            return 'Intervensi segera' if z > 0 else 'Investigasi'


# ── Helper format Indonesia ───────────────────────────────────────────

def fid(val, decimals=1):
    """Format angka dengan koma sebagai pemisah desimal (standar Indonesia)."""
    return f"{val:.{decimals}f}".replace('.', ',')


def fmt_rp(val):
    """Format angka ke Rupiah Indonesia: Rp 25.000"""
    try:
        v = int(round(float(val)))
        formatted = f"{v:,}".replace(',', '.')
        return f"Rp {formatted}"
    except (ValueError, TypeError):
        return str(val)


def fmt_pct(val, decimals=1):
    """Format persentase Indonesia: 78,7%"""
    try:
        return f"{float(val):.{decimals}f}%".replace('.', ',')
    except (ValueError, TypeError):
        return str(val)


def fmt_z(val):
    """Format z-score Indonesia: +1,56 atau -2,34"""
    try:
        return f"{float(val):+.2f}".replace('.', ',')
    except (ValueError, TypeError):
        return str(val)


def fmt_rp_delta(val):
    """Format selisih harga: +Rp 5.000 atau -Rp 3.000"""
    try:
        v = int(round(float(val)))
        sign = '+' if v > 0 else ''
        formatted = f"{abs(v):,}".replace(',', '.')
        return f"{sign}Rp {formatted}" if v >= 0 else f"-Rp {formatted}"
    except (ValueError, TypeError):
        return str(val)


def format_table(df, col_formats):
    """
    Format kolom-kolom tabel ke string dengan format Indonesia.
    col_formats: dict {nama_kolom: fungsi_format}
    """
    result = df.copy()
    for col, func in col_formats.items():
        if col in result.columns:
            result[col] = result[col].apply(func)
    return result


# ── Load & proses data ────────────────────────────────────────────────

GRP_COLS = ['kode_komoditas', 'kategori', 'nama_bahan_pokok', 'satuan']

@st.cache_data
def load_data():
    df = pd.read_csv('data_harga_bahan_pokok.csv')
    df['tanggal'] = pd.to_datetime(df['tanggal'])
    df['harga'] = pd.to_numeric(df['harga'], errors='coerce')
    df = df.dropna(subset=['harga'])
    return df


@st.cache_data
def calc_monthly_avg(df):
    monthly = df.groupby(
        ['bulan', 'pasar'] + GRP_COLS
    )['harga'].mean().reset_index()
    monthly.rename(columns={'harga': 'harga_rata2'}, inplace=True)
    monthly['harga_rata2'] = monthly['harga_rata2'].round(0)
    return monthly


@st.cache_data
def calc_disparitas(monthly):
    grp = ['bulan'] + GRP_COLS
    city = monthly.groupby(grp)['harga_rata2'].agg(
        ['mean', 'std', 'max', 'min']).reset_index()
    city.columns = grp + ['harga_kota', 'sd_kota', 'harga_max', 'harga_min']

    # Pasar termahal dan termurah
    idx_max = monthly.groupby(grp)['harga_rata2'].idxmax()
    idx_min = monthly.groupby(grp)['harga_rata2'].idxmin()
    pasar_max = monthly.loc[idx_max][grp + ['pasar']].rename(
        columns={'pasar': 'pasar_termahal'})
    pasar_min = monthly.loc[idx_min][grp + ['pasar']].rename(
        columns={'pasar': 'pasar_termurah'})
    city = city.merge(pasar_max, on=grp, how='left')
    city = city.merge(pasar_min, on=grp, how='left')

    # Koefisien Variasi (KV) = SD / Rata-rata × 100%
    city['kv'] = np.where(
        city['harga_kota'] > 0,
        (city['sd_kota'] / city['harga_kota']) * 100, 0)

    # Klasifikasi KV
    city['kategori_kv'] = city['kv'].apply(lambda x:
        'Sangat Rendah' if x < 1 else
        'Rendah' if x < 3 else
        'Sedang' if x < 5 else 'Tinggi')

    disp = monthly.merge(city, on=grp)
    disp['z_score'] = np.where(
        disp['sd_kota'] > 0,
        (disp['harga_rata2'] - disp['harga_kota']) / disp['sd_kota'], 0)
    disp['zona'] = disp['z_score'].apply(zona_label_disparitas)

    return disp, city


@st.cache_data
def calc_stabilisasi(monthly):
    grp = ['bulan'] + GRP_COLS
    city_monthly = monthly.groupby(grp)['harga_rata2'].mean().reset_index()
    city_monthly.rename(columns={'harga_rata2': 'harga_kota'}, inplace=True)
    city_monthly = city_monthly.sort_values(['kode_komoditas', 'bulan'])

    city_monthly['delta_harga'] = city_monthly.groupby(GRP_COLS)['harga_kota'].diff()

    hist_stats = city_monthly.dropna(subset=['delta_harga']).groupby(
        GRP_COLS)['delta_harga'].agg(['mean', 'std']).reset_index()
    hist_stats.columns = GRP_COLS + ['mu_delta', 'sigma_delta']

    stab = city_monthly.merge(hist_stats, on=GRP_COLS, how='left')
    stab['z_score'] = np.where(
        stab['sigma_delta'] > 0,
        (stab['delta_harga'] - stab['mu_delta']) / stab['sigma_delta'],
        np.where(stab['delta_harga'] == 0, 0, np.nan))
    stab['zona'] = stab['z_score'].apply(
        lambda z: zona_label_stabilisasi(z) if pd.notna(z) else '')
    stab['stabil'] = stab['z_score'].apply(
        lambda z: abs(z) <= 1 if pd.notna(z) else None)

    return stab


# ── Sidebar ───────────────────────────────────────────────────────────

st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/b/b0/Lambang_Kota_Bontang.png/120px-Lambang_Kota_Bontang.png", width=60)
st.sidebar.title("MATA PASAR")
st.sidebar.caption("Pemantauan Harga Bahan Pokok\nKota Bontang")

halaman = st.sidebar.radio(
    "Navigasi",
    ["📋 Monitoring Harga BAPOK",
     "📊 Disparitas Harga",
     "📈 Stabilisasi & Tren"],
    label_visibility="collapsed",
)

try:
    df = load_data()
    monthly = calc_monthly_avg(df)
    disp_detail, disp_summary = calc_disparitas(monthly)
    stab = calc_stabilisasi(monthly)
    bulan_list = sorted(df['bulan'].unique())
    kategori_list = sorted(df['kategori'].unique())
except Exception as e:
    st.error(f"Gagal memuat data: {e}")
    st.info("Pastikan file `data_harga_bahan_pokok.csv` ada di folder yang sama.")
    st.stop()

st.sidebar.markdown("---")
bulan_selected = st.sidebar.selectbox(
    "Periode bulan", bulan_list, index=len(bulan_list) - 1)


# ══════════════════════════════════════════════════════════════════════
# HALAMAN 1: MONITORING HARGA BAPOKTING
# ══════════════════════════════════════════════════════════════════════

if halaman == "📋 Monitoring Harga BAPOK":

    disp_bulan = disp_summary[disp_summary['bulan'] == bulan_selected]
    n_total_kom = disp_bulan['kode_komoditas'].nunique()

    st.markdown(
        f'<div style="margin-bottom:.5rem;">'
        f'<h1 style="margin-bottom:.1rem;">Pemantauan Harga Bahan Pokok Kota Bontang</h1>'
        f'<p style="color:gray;font-size:.95rem;margin-top:0;">'
        f'Periode: {bulan_selected} &nbsp;|&nbsp; '
        f'3 pasar (Rawa Indah, Telihan, Citra Mas) &nbsp;|&nbsp; '
        f'{n_total_kom} komoditas</p></div>', unsafe_allow_html=True)

    stab_bulan = stab[(stab['bulan'] == bulan_selected) & (stab['stabil'].notna())]

    # Hitung jumlah per klasifikasi KV
    n_kv_sangat_rendah = int((disp_bulan['kv'] < 1).sum()) if n_total_kom > 0 else 0
    n_kv_rendah = int(((disp_bulan['kv'] >= 1) & (disp_bulan['kv'] < 3)).sum()) if n_total_kom > 0 else 0
    n_kv_sedang = int(((disp_bulan['kv'] >= 3) & (disp_bulan['kv'] < 5)).sum()) if n_total_kom > 0 else 0
    n_kv_tinggi = int((disp_bulan['kv'] >= 5).sum()) if n_total_kom > 0 else 0
    kv_rata2 = disp_bulan['kv'].mean() if n_total_kom > 0 else 0

    if len(stab_bulan) > 0:
        pct_stabil = stab_bulan['stabil'].mean() * 100
        n_stabil = int(stab_bulan['stabil'].sum())
        n_total_stab = len(stab_bulan)
        n_tidak_stabil = n_total_stab - n_stabil
    else:
        pct_stabil = None; n_stabil = 0; n_total_stab = 0; n_tidak_stabil = 0

    # --- KPI Cards ---
    col1, col2 = st.columns(2)
    with col1:
        clr = '#1D9E75' if kv_rata2 < 1 else '#D85A30'
        icon = "🟢" if kv_rata2 < 1 else "🔴"
        st.markdown(
            f'<div style="background:#f8f9fa;border-radius:12px;padding:1.2rem;border-left:4px solid {clr};">'
            f'<p style="color:#555;font-size:.85rem;margin:0 0 .2rem;">Indikator 1 — Disparitas Harga Antar Pasar</p>'
            f'<h2 style="margin:.3rem 0;">{icon} KV rata-rata: {fid(kv_rata2)}%</h2>'
            f'<p style="color:#666;font-size:.8rem;margin:0;line-height:1.7;">'
            f'Disparitas diukur dengan <b>Koefisien Variasi (KV)</b> = standar deviasi harga di 3 pasar dibagi rata-rata harga, dikali 100%.<br><br>'
            f'Dari <b>{n_total_kom}</b> komoditas yang dipantau:<br>'
            f'• <b>{n_kv_sangat_rendah}</b> komoditas KV &lt; 1% (Sangat Rendah — harga seragam)<br>'
            f'• <b>{n_kv_rendah}</b> komoditas KV 1–3% (Rendah — variasi wajar)<br>'
            f'• <b>{n_kv_sedang}</b> komoditas KV 3–5% (Sedang — perlu dipantau)<br>'
            f'• <b>{n_kv_tinggi}</b> komoditas KV &gt; 5% (Tinggi — perlu intervensi)'
            f'</p></div>', unsafe_allow_html=True)

    with col2:
        if pct_stabil is not None:
            clr2 = '#1D9E75' if pct_stabil >= 71.5 else '#D85A30'
            icon2 = "🟢" if pct_stabil >= 71.5 else "🔴"
            tercapai = "tercapai ✓" if pct_stabil >= 71.5 else "belum tercapai ✗"
            st.markdown(
                f'<div style="background:#f8f9fa;border-radius:12px;padding:1.2rem;border-left:4px solid {clr2};">'
                f'<p style="color:#555;font-size:.85rem;margin:0 0 .2rem;">Indikator 2 — Persentase Komoditas yang Harganya Stabil</p>'
                f'<h2 style="margin:.3rem 0;">{icon2} {fid(pct_stabil)}%</h2>'
                f'<p style="color:#666;font-size:.8rem;margin:0;line-height:1.7;">'
                f'Kestabilan harga setiap komoditas ditentukan dengan cara:<br>'
                f'• Menghitung perubahan harga rata-rata kota (3 pasar) bulan ini vs bulan lalu<br>'
                f'• Membandingkan perubahan tersebut dengan pola historisnya menggunakan z-score<br>'
                f'• Komoditas dianggap <b>stabil</b> jika perubahannya masih dalam batas wajar (|z| ≤ 1)<br><br>'
                f'Target Kota Bontang: <b>≥ 71,5%</b> komoditas harganya stabil<br><br>'
                f'Realisasi: <b>{n_stabil}</b> dari <b>{n_total_stab}</b> komoditas stabil = <b>{fid(pct_stabil)}%</b><br>'
                f'<span style="color:{clr2};font-weight:500;">Target {tercapai}</span>'
                f'</p></div>', unsafe_allow_html=True)
        else:
            st.markdown(
                '<div style="background:#f8f9fa;border-radius:12px;padding:1.2rem;border-left:4px solid #888;">'
                '<p style="color:#555;font-size:.85rem;margin:0 0 .2rem;">Indikator 2 — Persentase Komoditas yang Harganya Stabil</p>'
                '<h2 style="margin:.3rem 0;">⏳ Belum tersedia</h2>'
                '<p style="color:#666;font-size:.8rem;margin:0;line-height:1.7;">'
                'Memerlukan data minimal 2 bulan untuk menghitung perubahan harga dan z-score.</p></div>',
                unsafe_allow_html=True)

    st.markdown("")

    # ── PENJELASAN KV DAN Z-SCORE ─────────────────────────────────────
    col_exp1, col_exp2 = st.columns(2)

    with col_exp1:
        with st.expander("📖 💡 Mengapa menggunakan Koefisien Variasi untuk mengukur disparitas? (klik untuk membaca)", expanded=False):
            st.markdown("""
**Masalah yang ingin diselesaikan:**

Selisih harga Rp 5.000 punya arti yang berbeda tergantung komoditasnya. Untuk Telur (Rp 2.000/butir), selisih Rp 5.000 artinya harga bisa 2,5 kali lipat lebih mahal di satu pasar. Tapi untuk Daging Sapi (Rp 160.000/kg), selisih Rp 5.000 hanya 3% perbedaan. Kita butuh ukuran yang adil untuk semua komoditas.

**Solusi: Koefisien Variasi (KV)**

KV mengukur seberapa besar perbedaan harga antar pasar **relatif terhadap level harganya**. Rumusnya:
""")
            st.latex(r"KV = \frac{\text{Standar Deviasi harga di 3 pasar}}{\text{Rata-rata harga di 3 pasar}} \times 100\%")
            st.markdown("""
**Contoh dari data Januari 2026:**

| Komoditas | Rawa Indah | Telihan | Citra Mas | Rata-rata | SD | KV |
|---|---|---|---|---|---|---|
| Beras Tawon | Rp 16.100 | Rp 16.100 | Rp 16.100 | Rp 16.100 | 0 | **0,0%** 🟢 |
| Cabe Rawit | Rp 80.000 | Rp 100.000 | Rp 100.000 | Rp 93.333 | Rp 11.547 | **12,4%** 🔴 |

KV Beras Tawon = 0% karena harganya identik di ketiga pasar. KV Cabe Rawit = 12,4% karena Rawa Indah menjual Rp 20.000 lebih murah dari dua pasar lainnya.

**Klasifikasi KV:**

| KV (%) | Kategori | Arti | Tindakan |
|---|---|---|---|
| < 1% | **Sangat Rendah** 🟢 | Harga seragam | Tidak perlu tindakan |
| 1% – 3% | **Rendah** 🟡 | Variasi wajar | Amati |
| 3% – 5% | **Sedang** 🟠 | Perbedaan cukup terlihat | Pantau |
| > 5% | **Tinggi** 🔴 | Sangat bervariasi | Intervensi |
""")

    with col_exp2:
        with st.expander("📖 💡 Mengapa menggunakan z-score untuk mengukur kestabilan harga? (klik untuk membaca)", expanded=False):
            st.markdown("""
**Masalah yang ingin diselesaikan:**

Setiap komoditas punya karakter harga yang berbeda. Cabe rawit biasanya berfluktuasi Rp 10.000 – Rp 20.000 per bulan, sedangkan beras hanya Rp 100 – Rp 200. Kalau kita pakai patokan yang sama (misalnya "naik Rp 5.000 = tidak stabil"), maka beras selalu dianggap tidak stabil tapi cabe selalu dianggap stabil — padahal kenyataannya bisa sebaliknya.

**Solusi: z-score**

Z-score mengukur seberapa jauh perubahan harga bulan ini **dibandingkan dengan pola biasanya** untuk komoditas tersebut. Rumusnya:
""")
            st.latex(r"z = \frac{\text{Perubahan harga bulan ini} - \text{Rata-rata perubahan historis}}{\text{Standar deviasi perubahan historis}}")
            st.markdown("""
**Cara membaca z-score:**

- **z = 0** → perubahan harga bulan ini **persis sama** dengan pola biasanya
- **z = +1** → perubahan harga **1 langkah di atas** pola biasa (mulai tidak biasa)
- **z = +2** → perubahan harga **2 langkah di atas** pola biasa (sangat tidak biasa)
- **z = -1** → harga turun **1 langkah di bawah** pola biasa

**Contoh konkret** (berdasarkan kisaran harga Januari 2026)**:**

| | Beras Tawon (Rp 16.100/kg) | Cabe Rawit (Rp 93.333/kg) |
|---|---|---|
| Rata-rata perubahan bulanan | Rp 200 | Rp 12.000 |
| Standar deviasi | Rp 300 | Rp 15.000 |
| Perubahan bulan ini | **Rp 1.500** | **Rp 25.000** |
| z-score | (1.500 − 200) / 300 = **+4,33** | (25.000 − 12.000) / 15.000 = **+0,87** |
| Status | 🔴 **Intervensi segera** | 🟡 **Terkendali** |

Beras Tawon yang harganya Rp 16.100/kg biasanya hanya berubah sekitar Rp 200 per bulan. Ketika tiba-tiba naik Rp 1.500, itu **sangat tidak biasa** (z = +4,33 → intervensi segera). Sebaliknya, Cabe Rawit yang harganya Rp 93.333/kg memang biasa berfluktuasi Rp 12.000 per bulan. Kenaikan Rp 25.000 meskipun angkanya jauh lebih besar, **masih dalam pola wajar** (z = +0,87 → terkendali).

**Klasifikasi:**

| z-score | Status | Tindakan |
|---|---|---|
| −1 s.d +1 | **Terkendali** | Tidak perlu tindakan |
| +1 s.d +2 atau −2 s.d −1 | **Perlu perhatian** | Tingkatkan pemantauan |
| > +2 atau < −2 | **Intervensi segera** | Koordinasi TPID |
""")

    # ── TABEL DISPARITAS ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Disparitas harga antar pasar")
    st.caption("Semua komoditas dikelompokkan berdasarkan Koefisien Variasi (KV)")

    if n_total_kom > 0:
        disp_all = disp_bulan.copy().sort_values('kv', ascending=False)
        disp_all['harga_min'] = disp_all['harga_min'].round(0).astype(int)
        disp_all['harga_max'] = disp_all['harga_max'].round(0).astype(int)
        disp_all['harga_kota'] = disp_all['harga_kota'].round(0).astype(int)
        disp_all['kv'] = disp_all['kv'].round(1)

        groups = [
            ("Intervensi", "KV > 5%", disp_all[disp_all['kv'] >= 5], "🔴",
             "Harga antar pasar sangat bervariasi — kemungkinan ada masalah distribusi atau kebijakan harga yang tidak seragam"),
            ("Perlu perhatian", "KV 3–5%", disp_all[(disp_all['kv'] >= 3) & (disp_all['kv'] < 5)], "🟠",
             "Terdapat perbedaan harga yang cukup terlihat antar pasar — perlu dipantau"),
            ("Variasi wajar", "KV 1–3%", disp_all[(disp_all['kv'] >= 1) & (disp_all['kv'] < 3)], "🟡",
             "Ada sedikit variasi harga, tetapi masih dalam batas wajar"),
            ("Harga seragam", "KV < 1%", disp_all[disp_all['kv'] < 1], "🟢",
             "Harga hampir seragam di semua pasar, distribusi sangat merata"),
        ]

        # Ringkasan jumlah per kelompok
        kcol1, kcol2, kcol3, kcol4 = st.columns(4)
        kv_cols = [kcol1, kcol2, kcol3, kcol4]
        kv_colors = ["#A32D2D", "#D85A30", "#BA7517", "#1D9E75"]
        for i, (label, rentang, grp, icon, desc) in enumerate(groups):
            with kv_cols[i]:
                st.markdown(
                    f'<div style="background:{kv_colors[i]};color:white;border-radius:8px;padding:10px;text-align:center;">'
                    f'<div style="font-size:11px;">{icon} {label}</div>'
                    f'<div style="font-size:22px;font-weight:500;">{len(grp)}</div>'
                    f'<div style="font-size:10px;opacity:.8;">{rentang}</div></div>',
                    unsafe_allow_html=True)

        st.markdown("")

        for label, rentang, grp, icon, desc in groups:
            if len(grp) == 0: continue
            with st.expander(f"{icon} {label} ({rentang}) — {len(grp)} komoditas", expanded=(label == "Intervensi")):
                st.caption(desc)
                tbl = grp[['nama_bahan_pokok',
                           'harga_min', 'pasar_termurah', 'harga_max', 'pasar_termahal',
                           'harga_kota', 'kv']].copy()
                tbl = tbl.reset_index(drop=True); tbl.index += 1
                tbl.columns = ['Komoditas',
                               'Harga Termurah', 'Pasar Termurah',
                               'Harga Termahal', 'Pasar Termahal',
                               'Rata-rata Kota', 'KV (%)']
                tbl = format_table(tbl, {
                    'Harga Termurah': fmt_rp, 'Harga Termahal': fmt_rp,
                    'Rata-rata Kota': fmt_rp, 'KV (%)': fmt_pct,
                })
                st.dataframe(tbl, use_container_width=True)

        st.caption(
            f"Ringkasan: KV > 5% = {n_kv_tinggi}, KV 3–5% = {n_kv_sedang}, "
            f"KV 1–3% = {n_kv_rendah}, KV < 1% = {n_kv_sangat_rendah}. "
            f"KV = Koefisien Variasi = (Standar Deviasi / Rata-rata) × 100%"
        )

    # ── TABEL STABILISASI ─────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Stabilisasi harga")
    st.caption("Semua komoditas dikelompokkan berdasarkan zona z-score perubahan harga bulanan")

    stab_bulan_all = stab[stab['bulan'] == bulan_selected].copy()

    if len(stab_bulan_all) > 0 and stab_bulan_all['z_score'].notna().any():
        sd = stab_bulan_all[stab_bulan_all['z_score'].notna()].copy()
        sd['harga_bulan_lalu'] = sd['harga_kota'] - sd['delta_harga']
        sd['pct_perubahan'] = np.where(
            sd['harga_bulan_lalu'] > 0,
            (sd['delta_harga'] / sd['harga_bulan_lalu']) * 100, 0)
        sd['harga_kota'] = sd['harga_kota'].round(0).astype(int)
        sd['harga_bulan_lalu'] = sd['harga_bulan_lalu'].round(0).astype(int)
        sd['delta_harga'] = sd['delta_harga'].round(0).astype(int)
        sd['pct_perubahan'] = sd['pct_perubahan'].round(2)
        sd['z_score'] = sd['z_score'].round(2)

        zona_defs = [
            ("Intervensi segera",  "> +2 SD",      lambda z: z > 2,
             "🔴🔴", "#712B13", "Kenaikan harga jauh di atas pola — koordinasi TPID, cek pasokan"),
            ("Perlu perhatian",    "+1 s.d +2 SD",  lambda z: (z > 1) & (z <= 2),
             "🔴",   "#993C1D", "Kenaikan harga di atas pola — tingkatkan pemantauan"),
            ("Terkendali",         "−1 s.d +1 SD",  lambda z: (z >= -1) & (z <= 1),
             "🟡",   "#BA7517", "Perubahan harga masih dalam pola normal"),
            ("Evaluasi penurunan", "−2 s.d −1 SD",  lambda z: (z >= -2) & (z < -1),
             "🟢",   "#0F6E56", "Harga turun di bawah pola — periksa kualitas/pasokan"),
            ("Investigasi",        "< −2 SD",       lambda z: z < -2,
             "🟢🟢", "#085041", "Harga turun jauh — investigasi penyebab"),
        ]

        zona_counts = {}
        for zn, _, cond, _, _, _ in zona_defs:
            zona_counts[zn] = len(sd[cond(sd['z_score'])])

        zcols = st.columns(5)
        for i, (zn, rentang, _, icon, bg, _) in enumerate(zona_defs):
            with zcols[i]:
                st.markdown(
                    f'<div style="background:{bg};color:white;border-radius:8px;padding:10px;text-align:center;">'
                    f'<div style="font-size:11px;">{icon} {zn}</div>'
                    f'<div style="font-size:22px;font-weight:500;">{zona_counts[zn]}</div>'
                    f'<div style="font-size:10px;opacity:.8;">{rentang}</div></div>',
                    unsafe_allow_html=True)

        st.markdown("")

        for zn, rentang, cond, icon, bg, desc in zona_defs:
            grp = sd[cond(sd['z_score'])].copy()
            if len(grp) == 0: continue
            expanded = zn in ("Intervensi segera", "Perlu perhatian")
            with st.expander(f"{icon} {zn} ({rentang}) — {len(grp)} komoditas", expanded=expanded):
                st.caption(desc)
                asc = zn in ('Evaluasi penurunan', 'Investigasi')
                tbl = grp.sort_values('z_score', ascending=asc)
                tbl = tbl[['nama_bahan_pokok',
                           'harga_bulan_lalu', 'harga_kota', 'delta_harga',
                           'pct_perubahan', 'z_score']].copy()
                tbl = tbl.reset_index(drop=True); tbl.index += 1
                tbl.columns = ['Komoditas', 'Harga Bulan Lalu',
                               'Harga Bulan Ini', 'Δ Harga (Rp)', 'Perubahan (%)', 'z-score']
                tbl = format_table(tbl, {
                    'Harga Bulan Lalu': fmt_rp, 'Harga Bulan Ini': fmt_rp,
                    'Δ Harga (Rp)': fmt_rp_delta, 'Perubahan (%)': fmt_pct,
                    'z-score': fmt_z,
                })
                st.dataframe(tbl, use_container_width=True)

        st.caption(f"Ringkasan: Intervensi segera = {zona_counts['Intervensi segera']}, "
                   f"Perlu perhatian = {zona_counts['Perlu perhatian']}, "
                   f"Terkendali = {zona_counts['Terkendali']}, "
                   f"Evaluasi penurunan = {zona_counts['Evaluasi penurunan']}, "
                   f"Investigasi = {zona_counts['Investigasi']}.")
    else:
        st.info("Perlu data ≥ 2 bulan untuk menghitung z-score stabilisasi.")


# ══════════════════════════════════════════════════════════════════════
# HALAMAN 2: DISPARITAS HARGA
# ══════════════════════════════════════════════════════════════════════

elif halaman == "📊 Disparitas Harga":
    st.title("Disparitas Harga Antar Pasar")
    st.caption(f"Indikator 1 — Periode: {bulan_selected}")

    kat_filter = st.multiselect("Filter kategori", kategori_list, placeholder="Semua kategori")
    disp_b = disp_detail[disp_detail['bulan'] == bulan_selected].copy()
    summ_b = disp_summary[disp_summary['bulan'] == bulan_selected].copy()
    if kat_filter:
        disp_b = disp_b[disp_b['kategori'].isin(kat_filter)]
        summ_b = summ_b[summ_b['kategori'].isin(kat_filter)]

    # Heatmap z-score
    st.subheader("Heatmap z-score per pasar")

    if len(disp_b) > 0:
        pivot = disp_b.pivot_table(
            index='nama_bahan_pokok', columns='pasar', values='z_score', aggfunc='mean')
        pivot = pivot.reindex(columns=['RAWA INDAH', 'TELIHAN', 'CITRA MAS'])
        fig_heat = go.Figure(data=go.Heatmap(
            z=pivot.values, x=pivot.columns, y=pivot.index,
            colorscale=[[0,'#085041'],[0.35,'#5DCAA5'],[0.5,'#FAEEDA'],[0.65,'#F0997B'],[1,'#A32D2D']],
            zmid=0, zmin=-1.5, zmax=1.5,
            text=np.round(pivot.values, 2), texttemplate='%{text}', textfont=dict(size=10),
            colorbar=dict(title='z-score'),
            hovertemplate='%{y}<br>%{x}<br>z-score: %{z:.2f}<extra></extra>'))
        fig_heat.update_layout(height=max(400, len(pivot)*22), margin=dict(l=10,r=10,t=30,b=10),
                               yaxis=dict(dtick=1, autorange='reversed'))
        st.plotly_chart(fig_heat, use_container_width=True)

        # Panduan membaca heatmap
        st.markdown("---")
        with st.expander("📖 💡 Cara membaca heatmap z-score (klik untuk membaca)", expanded=False):
            st.markdown("""
**Apa yang ditampilkan:**
- Setiap **baris** = satu komoditas
- Setiap **kolom** = satu pasar (Rawa Indah, Telihan, Citra Mas)
- **Angka dan warna** di setiap sel = z-score, yaitu seberapa jauh harga di pasar tersebut menyimpang dari rata-rata harga ketiga pasar

**Cara membaca warna:**
- 🟤 **Merah/gelap** (z-score positif tinggi) → harga di pasar ini **lebih mahal** dari rata-rata kota
- 🟡 **Kuning/netral** (z-score mendekati 0) → harga **wajar**, sesuai rata-rata kota
- 🟢 **Hijau** (z-score negatif) → harga di pasar ini **lebih murah** dari rata-rata kota

**Cara membaca per baris (satu komoditas):**
- Jika satu baris semuanya **kuning** → harga komoditas ini **seragam** di ketiga pasar (disparitas rendah)
- Jika ada sel **merah** dan **hijau** dalam satu baris → ada **kesenjangan harga** antar pasar untuk komoditas ini

**Cara membaca per kolom (satu pasar):**
- Jika satu kolom didominasi **merah** → pasar ini cenderung **lebih mahal** secara umum
- Jika satu kolom didominasi **hijau** → pasar ini cenderung **lebih murah** secara umum
- Pola ini bisa menunjukkan perbedaan rantai distribusi atau biaya operasional antar pasar
""")
            # Contoh konkret dari data
            st.markdown("**Contoh dari data bulan ini:**")
            examples = []
            for _, row in disp_b.iterrows():
                examples.append((row['nama_bahan_pokok'], row['pasar'],
                                 row['harga_rata2'], row['harga_kota'], row['z_score']))

            # Cari komoditas seragam (semua z ≈ 0)
            for nama in pivot.index:
                zvals = pivot.loc[nama]
                if all(abs(z) < 0.3 for z in zvals):
                    harga = disp_b[disp_b['nama_bahan_pokok'] == nama]['harga_kota'].iloc[0]
                    st.markdown(f"- **{nama}**: semua sel kuning (z ≈ 0) → harga seragam {fmt_rp(harga)} di ketiga pasar")
                    break

            # Cari komoditas dengan disparitas tinggi
            for nama in pivot.index:
                zvals = pivot.loc[nama]
                if zvals.max() > 0.8 and zvals.min() < -0.8:
                    mahal_p = zvals.idxmax()
                    murah_p = zvals.idxmin()
                    h_mahal = disp_b[(disp_b['nama_bahan_pokok']==nama) & (disp_b['pasar']==mahal_p)]['harga_rata2'].iloc[0]
                    h_murah = disp_b[(disp_b['nama_bahan_pokok']==nama) & (disp_b['pasar']==murah_p)]['harga_rata2'].iloc[0]
                    st.markdown(
                        f"- **{nama}**: sel merah di {mahal_p} ({fmt_rp(h_mahal)}), "
                        f"sel hijau di {murah_p} ({fmt_rp(h_murah)}) "
                        f"→ {mahal_p} menjual lebih mahal, perlu ditelusuri penyebabnya")
                    break

            # Pola kolom
            col_means = pivot.mean()
            mahal_pasar = col_means.idxmax()
            murah_pasar = col_means.idxmin()
            n_merah = {p: (pivot[p] > 1).sum() for p in pivot.columns}
            st.markdown(
                f"- **Pola kolom**: {mahal_pasar} memiliki rata-rata z-score tertinggi "
                f"({fid(col_means[mahal_pasar], 2)}) dengan {n_merah[mahal_pasar]} komoditas "
                f"di zona merah → pasar ini cenderung lebih mahal secara umum"
            )

    # Grafik batang KV
    st.subheader("Koefisien Variasi (KV) per komoditas")
    if len(summ_b) > 0:
        ss = summ_b.copy()
        # Urutan: KV=0 di atas, lalu KV terbesar → terkecil
        ss['sort_key'] = ss['kv'].apply(lambda x: -1 if x < 0.01 else x)
        ss = ss.sort_values('sort_key', ascending=True)
        ss = ss.drop(columns=['sort_key'])
        fig_bar = px.bar(ss, x='kv', y='nama_bahan_pokok', orientation='h',
                         color='kv',
                         color_continuous_scale=['#1D9E75', '#5DCAA5', '#BA7517', '#D85A30', '#A32D2D'],
                         labels={'kv': 'KV (%)', 'nama_bahan_pokok': ''})
        fig_bar.add_vline(x=1, line_dash="dash", line_color="#1D9E75", line_width=3)
        fig_bar.add_vline(x=3, line_dash="dash", line_color="#D85A30", line_width=3)
        fig_bar.add_vline(x=5, line_dash="dash", line_color="#A32D2D", line_width=3)
        fig_bar.update_layout(
            height=max(500, len(ss)*22),
            margin=dict(l=10, r=10, t=30, b=10),
            showlegend=False,
            xaxis=dict(title='KV (%)'),
            yaxis=dict(autorange='reversed'),
            coloraxis_colorbar=dict(title='KV (%)'),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        with st.expander("📖 💡 Cara membaca grafik KV (klik untuk membaca)", expanded=False):
            st.markdown("""
**Apa yang ditampilkan:**
- Setiap batang horizontal = satu komoditas
- Panjang batang = Koefisien Variasi (KV), yaitu standar deviasi harga dibagi rata-rata harga dari 3 pasar × 100%
- Garis putus-putus menandai batas klasifikasi: hijau (1%), orange (3%), merah (5%)

**Cara membaca:**
- Batang **pendek dan hijau** (KV < 1%) → harga komoditas ini sangat seragam di ketiga pasar
- Batang **kuning** (KV 1–3%) → ada sedikit variasi, masih wajar
- Batang **orange** (KV 3–5%) → perbedaan cukup terlihat, perlu dipantau
- Batang **panjang dan merah** (KV > 5%) → harga sangat bervariasi, perlu intervensi
""")

    # Perbandingan harga 3 pasar
    st.subheader("Perbandingan harga antar pasar")
    if len(disp_b) > 0:
        kom_list = sorted(disp_b['nama_bahan_pokok'].unique())
        sel = st.selectbox("Pilih komoditas", kom_list)
        kd = disp_b[disp_b['nama_bahan_pokok'] == sel]
        fig_c = px.bar(kd, x='pasar', y='harga_rata2', color='zona', color_discrete_map=ZONA_COLORS,
                       text='harga_rata2', labels={'harga_rata2':'Harga (Rp)','pasar':'Pasar'})
        avg = kd['harga_kota'].iloc[0] if len(kd) > 0 else 0
        fig_c.add_hline(y=avg, line_dash="dash", line_color="gray",
                        annotation_text=f"Rata-rata kota: Rp{avg:,.0f}")
        fig_c.update_traces(texttemplate='Rp%{text:,.0f}', textposition='outside')
        fig_c.update_layout(height=400, margin=dict(l=10,r=10,t=30,b=10))
        st.plotly_chart(fig_c, use_container_width=True)

        with st.expander("📖 💡 Cara membaca grafik perbandingan harga (klik untuk membaca)", expanded=False):
            st.markdown("""
**Apa yang ditampilkan:**
- 3 batang vertikal = harga rata-rata bulanan di masing-masing pasar untuk komoditas yang dipilih
- Garis putus-putus abu-abu = rata-rata harga dari ketiga pasar (rata-rata kota)
- Warna batang menunjukkan posisi terhadap rata-rata kota

**Cara membaca:**
- Batang **di atas** garis rata-rata → pasar ini menjual **lebih mahal** dari rata-rata kota
- Batang **di bawah** garis rata-rata → pasar ini menjual **lebih murah**
- Jika ketiga batang **hampir sama tinggi** → harga komoditas ini seragam (disparitas rendah)
- Jika ada batang yang **jauh lebih tinggi atau rendah** → pasar tersebut perlu ditelusuri penyebabnya
""")
    if len(bulan_list) > 1:
        st.subheader("Tren Koefisien Variasi rata-rata per bulan")
        kv_trend = disp_summary.groupby('bulan')['kv'].mean().reset_index()
        kv_trend.columns = ['bulan', 'kv_rata2']
        fig_t = px.line(kv_trend, x='bulan', y='kv_rata2', markers=True,
                        labels={'kv_rata2': 'KV rata-rata (%)','bulan': 'Bulan'})
        fig_t.add_hline(y=1, line_dash="dash", line_color="green",
                        annotation_text="Sangat Rendah < 1%")
        fig_t.add_hline(y=3, line_dash="dash", line_color="orange",
                        annotation_text="Sedang 3%")
        fig_t.add_hline(y=5, line_dash="dash", line_color="red",
                        annotation_text="Tinggi 5%")
        fig_t.update_layout(height=350)
        st.plotly_chart(fig_t, use_container_width=True)

        with st.expander("📖 💡 Cara membaca grafik tren KV (klik untuk membaca)", expanded=False):
            st.markdown("""
**Apa yang ditampilkan:**
- Sumbu horizontal = bulan
- Sumbu vertikal = rata-rata Koefisien Variasi (KV) dari seluruh komoditas
- Garis batas: hijau (1% — sangat rendah), orange (3% — sedang), merah (5% — tinggi)

**Cara membaca:**
- Garis **menurun** dari bulan ke bulan → disparitas harga antar pasar **membaik**
- Garis **naik** → disparitas **memburuk**
- Garis **di bawah 1%** → kondisi ideal, harga hampir seragam di semua pasar
- Garis **di atas 5%** → perlu intervensi untuk memperbaiki distribusi
""")


# ══════════════════════════════════════════════════════════════════════
# HALAMAN 3: STABILISASI & TREN
# ══════════════════════════════════════════════════════════════════════

elif halaman == "📈 Stabilisasi & Tren":
    st.title("Stabilisasi & Tren Harga")
    st.caption(f"Indikator 2 — Periode: {bulan_selected}")

    stab_b = stab[stab['bulan'] == bulan_selected].copy()

    st.subheader("Status stabilisasi per komoditas")
    if len(stab_b) > 0 and stab_b['z_score'].notna().any():
        sd = stab_b[stab_b['z_score'].notna()].sort_values('z_score', ascending=False)
        fig_sb = px.bar(sd, x='z_score', y='nama_bahan_pokok', orientation='h',
                        color='zona', color_discrete_map=ZONA_COLORS,
                        labels={'z_score':'z-score','nama_bahan_pokok':''})
        fig_sb.add_vline(x=-1, line_dash="dash", line_color="gray", opacity=0.5)
        fig_sb.add_vline(x=1, line_dash="dash", line_color="gray", opacity=0.5)
        fig_sb.add_vline(x=-2, line_dash="dot", line_color="red", opacity=0.5)
        fig_sb.add_vline(x=2, line_dash="dot", line_color="red", opacity=0.5)
        fig_sb.add_vrect(x0=-1, x1=1, fillcolor="#FAEEDA", opacity=0.15,
                         annotation_text="Terkendali (±1 SD)", annotation_position="top")
        fig_sb.update_layout(height=max(500, len(sd)*22), margin=dict(l=10,r=10,t=40,b=10))
        st.plotly_chart(fig_sb, use_container_width=True)

        with st.expander("📖 💡 Cara membaca grafik z-score stabilisasi (klik untuk membaca)", expanded=False):
            st.markdown("""
**Apa yang ditampilkan:**
- Setiap batang horizontal = satu komoditas
- Panjang dan arah batang = z-score perubahan harga bulan ini dibandingkan pola historisnya
- Area kuning (±1 SD) = zona **Terkendali**
- Garis putus-putus abu-abu = batas ±1 SD, garis titik-titik merah = batas ±2 SD

**Cara membaca:**
- Batang **di dalam area kuning** (antara −1 dan +1) → perubahan harga **masih wajar**
- Batang **ke kanan melewati +1** → harga **naik lebih dari biasanya** (perlu perhatian)
- Batang **ke kanan melewati +2** → harga **naik sangat tidak biasa** (perlu intervensi segera)
- Batang **ke kiri melewati −1** → harga **turun lebih dari biasanya** (evaluasi penurunan)
- Batang **ke kiri melewati −2** → harga **turun sangat tidak biasa** (investigasi)
""")
    else:
        st.info("Perlu data ≥ 2 bulan untuk menghitung z-score stabilisasi.")

    st.markdown("---")
    st.subheader("Tren harga harian")
    kat_sel = st.selectbox("Kategori", kategori_list, key="tren_kat")
    kom_opts = sorted(df[df['kategori'] == kat_sel]['nama_bahan_pokok'].unique())
    kom_sel = st.selectbox("Komoditas", kom_opts, key="tren_kom")
    df_tren = df[df['nama_bahan_pokok'] == kom_sel].sort_values('tanggal')
    if len(df_tren) > 0:
        fig_th = px.line(df_tren, x='tanggal', y='harga', color='pasar', markers=True,
                         labels={'harga':'Harga (Rp)','tanggal':'Tanggal','pasar':'Pasar'},
                         color_discrete_sequence=['#378ADD','#D85A30','#1D9E75'])
        fig_th.update_layout(height=400, margin=dict(l=10,r=10,t=30,b=10), hovermode='x unified')
        st.plotly_chart(fig_th, use_container_width=True)

        with st.expander("📖 💡 Cara membaca grafik tren harga harian (klik untuk membaca)", expanded=False):
            st.markdown("""
**Apa yang ditampilkan:**
- Sumbu horizontal = tanggal (harian, Senin–Jumat)
- Sumbu vertikal = harga komoditas yang dipilih
- 3 garis warna berbeda = harga di masing-masing pasar (Rawa Indah, Telihan, Citra Mas)

**Cara membaca:**
- Ketiga garis **berhimpitan** → harga seragam di semua pasar (disparitas rendah)
- Garis **saling berjauhan** → ada kesenjangan harga antar pasar
- Garis **naik tajam** → terjadi kenaikan harga yang perlu diperhatikan
- Garis **berfluktuasi naik-turun** → harga tidak stabil untuk komoditas ini
- Gunakan filter Kategori dan Komoditas di atas grafik untuk memilih komoditas yang ingin diamati
""")

    if len(bulan_list) > 1:
        st.subheader("Tren pencapaian target stabilisasi")
        pct_bl = stab[stab['stabil'].notna()].groupby('bulan')['stabil'].mean() * 100
        pdf = pct_bl.reset_index(); pdf.columns = ['bulan','pct_stabil']
        fig_tg = px.line(pdf, x='bulan', y='pct_stabil', markers=True,
                         labels={'pct_stabil':'Komoditas Stabil (%)','bulan':'Bulan'})
        fig_tg.add_hline(y=71.5, line_dash="dash", line_color="red", annotation_text="Target 71,5%")
        fig_tg.update_layout(height=350)
        st.plotly_chart(fig_tg, use_container_width=True)

        with st.expander("📖 💡 Cara membaca grafik tren stabilisasi (klik untuk membaca)", expanded=False):
            st.markdown("""
**Apa yang ditampilkan:**
- Sumbu horizontal = bulan
- Sumbu vertikal = persentase komoditas yang harganya stabil (z-score dalam ±1 SD)
- Garis merah putus-putus = target Kota Bontang (71,5%)

**Cara membaca:**
- Garis **di atas target merah** → target stabilisasi **tercapai** pada bulan tersebut
- Garis **di bawah target merah** → target **belum tercapai**, perlu tindakan pengendalian harga
- Garis **naik** dari bulan ke bulan → kondisi harga **semakin stabil**
- Garis **turun** → semakin banyak komoditas yang harganya bergejolak
""")


# ── Footer ────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.caption("MATA PASAR © 2026\n\nDinas Koperasi, Usaha Mikro,\nPerindustrian dan Perdagangan\nKota Bontang")
