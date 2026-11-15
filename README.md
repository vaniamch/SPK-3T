# Prototype SPK Grup: Linear BWM + MARCOS + TOPSIS + Sensitivitas

Prioritas intervensi pengentasan kemiskinan pada 62 kabupaten daerah tertinggal (Perpres No. 63/2020).
Mata kuliah Sistem Pengambilan Keputusan, Universitas Klabat. Kelompok Aliansi Kyubi.

Aplikasi web modern (Streamlit) dengan antarmuka **Frosted Glassmorphism & Clean Neomorphic (Healthcare / Executive Style)** yang menjalankan seluruh alur DSS kelompok terdistribusi secara utuh dan 100% sinkron matematis dengan lembar kerja Excel:

```
input alternatif & kriteria -> penilaian tiap DM (BO & OW) -> optimasi Linear BWM (metode A)
-> agregasi bobot grup (rata-rata geometrik berbobot) -> ranking kompromi MARCOS (metode B) 
-> pembanding TOPSIS & SAW -> analisis sensitivitas 8 skenario (S0-S7) -> konsensus Kendall's W -> hasil
```

---

## Fitur Utama Sesuai Lembar Kerja Excel & Rubrik Penilaian 6

1. **Alur Lengkap DSS Kelompok (Butir 6.1)**:
   - Evaluasi 62 kabupaten tertinggal 3T terhadap 8 kriteria data resmi BPS.
   - Metode A: Pembobotan kriteria **Linear BWM (Rezaei, 2016)** via LP Simplex.
   - Agregasi bobot kelompok: **Weighted Geometric Mean (Aczél & Saaty, 1983)** sesuai bobot pengaruh $\lambda$.
   - Metode B: Perangkingan kompromi **MARCOS (Stević et al., 2020)** berbasis solusi ideal ($AI$) dan anti-ideal ($AAI$).
   - Metode Pembanding: **TOPSIS (Hwang & Yoon, 1981)** dan **SAW** dengan uji korelasi rank Spearman.
   - Analisis Sensitivitas: 8 skenario bobot kriteria & DM (S0 s.d. S7) + simulasi interaktif dinamis.
   - Analisis Konsensus: Koefisien Konkordansi **Kendall's W = 0.9378** (Kesepakatan Sangat Kuat).

2. **Dukungan Banyak Pengambil Keputusan / DM (Butir 6.2)**:
   - Akun dan login terpisah untuk 3 Decision Makers:
     - **Jeno** (Bappeda - Perencanaan Ekonomi Wilayah, $\lambda = 0.40$)
     - **James** (Dinas Pendidikan - Pembangunan Pendidikan, $\lambda = 0.30$)
     - **Karina** (Dinas Kesehatan - Kesehatan Masyarakat, $\lambda = 0.30$)
     - **Admin** (Fasilitator & Pengelola Model)
   - Setiap DM mengisi preferensi kriteria *Best* dan *Worst* serta matriks perbandingan berpasangan (BO & OW skala 1–9) secara independen.

3. **Data Dinamis / Tidak Di-Hardcode (Butir 6.3)**:
   - Kriteria dan alternatif dapat ditambah, diubah, atau dihapus langsung melalui Data Editor.
   - Fitur impor dan ekspor file CSV untuk dataset kabupaten 3T.
   - Sinkronisasi otomatis: perubahan struktur kriteria otomatis mereset status DM untuk diisi ulang.

4. **100% Identik dengan Hasil Excel (Butir 6.4)**:
   - Teruji secara otomatis via test suite matematis (`test_core.py` dan `test_excel_sync.py`).
   - Selisih skor utilitas $f(K) \le 10^{-6}$ dan urutan ranking 1 s.d. 62 identik 100%.
   - Kabupaten **Nduga** konsisten menempati **Peringkat #1** ($f(K) = 0.7664$).

5. **Hasil Antara Transparan & Lengkap (Butir 6.5)**:
   - Menampilkan matriks keputusan $X$, solusi ideal ($AI$) dan anti-ideal ($AAI$).
   - Matriks ternormalisasi $N$, matriks terbobot $V = N \times w$.
   - Bobot kriteria per DM, deviasi optimal $\xi$, dan rasio konsistensi $CR_I$.
   - Nilai $S_i, K_i^-, K_i^+, f(K_i^-), f(K_i^+), f(K_i)$, serta **Indeks Keparahan Relatif ($V_{rel}$)**.

6. **Visualisasi Data Interaktif (Butir 6.6)**:
   - Grafik horizontal bar chart interaktif untuk ranking prioritas intervensi (dengan slider Top-N).
   - Grouped bar chart perbandingan bobot kriteria antar-DM dan grup.
   - Visualisasi perbandingan metode (MARCOS vs TOPSIS vs SAW).

7. **Validasi Input Menyeluruh (Butir 6.7)**:
   - Validasi realtime pada isian BWM: menolak nilai kosong, nilai di luar skala 1–9, Best = Worst, dan perbedaan nilai Best-Worst antar vektor.
   - Validasi data alternatif: menolak nama kosong, nama duplikat, dan nilai kriteria Cost $\le 0$ (mencegah pembagian dengan nol).

8. **Antarmuka Konsisten Sesuai Desain Acuan (Butir 6.8)**:
   - Desain Neomorphic Clean & Frosted Glassmorphism dengan palet warna modern, floating capsule navbar, showcase hero card, dan card grid sektoral.
   - Responsif dan mudah dipahami baik oleh pimpinan pengambil kebijakan maupun teknisi.

9. **Fitur Nilai Tambah Pengambilan Keputusan Grup (Butir 6.9)**:
   - Live Status Board & Progress Bar pengisian penilaian seluruh DM di Beranda.
   - Forum diskusi tim secara realtime untuk pertukaran catatan argumen kebijakan.
   - Arsip riwayat keputusan tersimpan lengkap dengan catatan, nilai $\lambda$, dan Top-10 ranking.

10. **Kesiapan Demo Tanpa Error (Butir 6.10, 6.11, 6.12)**:
    - Tombol pemulihan data contoh dan simulasi mode demo interaktif.
    - Tab panduan tanya jawab presentasi untuk membekali setiap anggota tim dalam sesi evaluasi.

---

## Petunjuk Instalasi & Menjalankan Aplikasi

Pastikan Python versi 3.10 hingga 3.13 terpasang.

```bash
cd spk_prototype

# 1. Buat dan aktifkan virtual environment (opsional jika sudah ada)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 2. Pasang dependensi
pip install -r requirements.txt

# 3. Jalankan aplikasi Streamlit
streamlit run app.py
```

Aplikasi dapat diakses melalui browser di alamat `http://localhost:8501`.

---

## Akun Pengguna Prototype

| Akun / Role | Username | Password | Otoritas & Peran |
|---|---|---|---|
| **Admin (Fasilitator)** | `admin` | `admin` | Kelola kriteria, alternatif, bobot $\lambda$, reset data demo, dan arsip riwayat keputusan |
| **Jeno (Bappeda)** | `bappeda` | `bappeda` | Mengisi perbandingan BWM perspektif Perencanaan Ekonomi Wilayah ($\lambda = 0.40$) |
| **James (Dinas Pendidikan)** | `pendidikan` | `pendidikan` | Mengisi perbandingan BWM perspektif Pembangunan Pendidikan ($\lambda = 0.30$) |
| **Karina (Dinas Kesehatan)** | `kesehatan` | `kesehatan` | Mengisi perbandingan BWM perspektif Kesehatan Masyarakat ($\lambda = 0.30$) |

---

## Pemetaan Rubrik Penilaian 6

| No | Butir Penilaian | Implementasi pada Prototype |
|---|---|---|
| **6.1** | Alur lengkap (Input -> BWM -> Agregasi -> MARCOS -> Hasil) | Alur utuh tanpa putus di menu Kelola Kriteria/Alternatif, Penilaian Saya, hingga Hasil (8 Tab) |
| **6.2** | Mendukung banyak DM (login, peran, form per DM) | Login multi-role dengan hak akses terisolasi untuk Jeno, James, Karina, dan Admin |
| **6.3** | Alternatif & kriteria dapat ditambah, diubah, dihapus | Data Editor dinamis pada Kelola Kriteria & Alternatif + Dukungan Impor/Ekspor CSV |
| **6.4** | Hasil prototype sama dengan hasil Excel untuk data sama | Tab 5 "Verifikasi vs Excel" membuktikan selisih $f(K) \le 10^{-6}$ dan urutan ranking 1..62 identik |
| **6.5** | Hasil antara ditampilkan (matriks N, bobot, skor tiap DM) | Tab 2 (Bobot BWM & CV) dan Tab 3 (Matriks X, AI, AAI, N, V, Si, Ki-, Ki+, f(K), V_rel) |
| **6.6** | Visualisasi hasil (grafik ranking & preferensi antar-DM) | Tab 2 (Grouped bar chart bobot antar-DM) dan Tab 3 (Horizontal bar chart ranking) |
| **6.7** | Validasi input (menolak kosong atau di luar skala 1–9) | Validasi realtime form BWM (skala 1-9, Best!=Worst, BO=OW) dan validasi Cost > 0 |
| **6.8** | Antarmuka mudah dipahami dan konsisten | Desain Frosted Glassmorphism / Neomorphic modern sesuai foto referensi |
| **6.9** | Fitur pendukung grup (status pengisian, diskusi, riwayat) | Live status board di Beranda, forum chat diskusi tim, dan arsip riwayat snapshot keputusan |
| **6.10** | Demo langsung berjalan tanpa error | Tersedia tombol reset data contoh dan mode simulasi penilaian tanpa kendala runtime |
| **6.11** | Laporan akhir, source code, dan panduan instalasi | Dokumentasi lengkap di README.md dan source code terstruktur rapi |
| **6.12** | Setiap anggota mampu menjelaskan bagiannya | Tab Panduan Tanya Jawab dan catatan rujukan ilmiah per metode |

---

## Verifikasi Otomatis (Unit & Integration Tests)

Untuk memverifikasi kebenaran logika matematis dan antarmuka:

```bash
# Uji kecocokan matematis dengan Excel
python tests/test_core.py
python tests/test_excel_sync.py

# Uji alur antarmuka dan interaksi pengguna
python tests/smoke_ui.py
```
