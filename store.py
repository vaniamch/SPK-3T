"""
store.py - Penyimpanan state bersama (file JSON).

State disimpan di data/state.json agar beberapa DM yang membuka aplikasi dari
browser/laptop berbeda (satu server) melihat data yang sama. Jika file belum
ada, state dibuat dari data contoh (62 kabupaten daerah tertinggal + vektor BWM
dari laporan & Excel), sehingga hasil awal sama persis dengan file Excel.
"""
from __future__ import annotations

import copy
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd

BASE = Path(__file__).parent
DATA_DIR = BASE / "data"
STATE_FILE = Path(os.environ.get("SPK_STATE_FILE", DATA_DIR / "state.json"))

KRITERIA_DEFAULT = [
    {
        "id": "C1",
        "kode_sumber": "P0",
        "nama": "Persentase Penduduk Miskin (P0)",
        "tipe": "Benefit",
        "satuan": "%",
        "arah": "Makin tinggi P0, makin butuh intervensi",
        "program": "Bansos & pemberdayaan ekonomi",
    },
    {
        "id": "C2",
        "kode_sumber": "RLS",
        "nama": "Rata-rata Lama Sekolah 15+",
        "tipe": "Cost",
        "satuan": "tahun",
        "arah": "Makin rendah RLS, makin butuh intervensi",
        "program": "Akses & beasiswa pendidikan",
    },
    {
        "id": "C3",
        "kode_sumber": "PENG",
        "nama": "Pengeluaran per Kapita Disesuaikan",
        "tipe": "Cost",
        "satuan": "ribu Rp/orang/tahun",
        "arah": "Makin rendah daya beli, makin butuh intervensi",
        "program": "Peningkatan daya beli / padat karya",
    },
    {
        "id": "C4",
        "kode_sumber": "UHH",
        "nama": "Umur Harapan Hidup",
        "tipe": "Cost",
        "satuan": "tahun",
        "arah": "Makin rendah UHH, makin butuh intervensi",
        "program": "Layanan kesehatan dasar",
    },
    {
        "id": "C5",
        "kode_sumber": "SAN",
        "nama": "Defisit Sanitasi Layak (100 - % akses)",
        "tipe": "Benefit",
        "satuan": "% RT tanpa akses",
        "arah": "Makin besar defisit, makin butuh intervensi",
        "program": "Program sanitasi (STBM)",
    },
    {
        "id": "C6",
        "kode_sumber": "AIR",
        "nama": "Defisit Air Minum Layak (100 - % akses)",
        "tipe": "Benefit",
        "satuan": "% RT tanpa akses",
        "arah": "Makin besar defisit, makin butuh intervensi",
        "program": "Penyediaan air minum (SPAM)",
    },
    {
        "id": "C7",
        "kode_sumber": "TPT",
        "nama": "Tingkat Pengangguran Terbuka",
        "tipe": "Benefit",
        "satuan": "%",
        "arah": "Makin tinggi TPT, makin butuh intervensi",
        "program": "Pelatihan kerja & UMKM",
    },
    {
        "id": "C8",
        "kode_sumber": "PDRB",
        "nama": "PDRB ADHK (total)",
        "tipe": "Cost",
        "satuan": "Rupiah",
        "arah": "Makin kecil ekonomi daerah, makin butuh intervensi",
        "program": "Infrastruktur ekonomi wilayah",
    },
]

# Vektor BO/OW dari laporan & Excel (Sheet Input!C23:J25 & C29:J31)
_DM_DEFAULT = [
    {
        "id": "bappeda",
        "nama": "Jeno",
        "instansi": "Bappeda (Perencanaan Ekonomi Wilayah)",
        "peran": "Koordinator Perencanaan Wilayah",
        "lambda": 0.4,
        "password": "bappeda",
        "best": "C1",
        "worst": "C4",
        "justifikasi": "Koordinator perencanaan; fokus kemiskinan (P0) & ekonomi wilayah. Isu kesehatan dipandang ranah dinas teknis.",
        "bo": [1, 5, 2, 8, 5, 5, 3, 4],
        "ow": [8, 2, 5, 1, 2, 2, 3, 2],
    },
    {
        "id": "pendidikan",
        "nama": "James",
        "instansi": "Dinas Pendidikan (Pembangunan Pendidikan)",
        "peran": "Perencana Kebijakan Pendidikan",
        "lambda": 0.3,
        "password": "pendidikan",
        "best": "C2",
        "worst": "C8",
        "justifikasi": "Fokus lama sekolah (RLS); kemiskinan & pengangguran memengaruhi akses sekolah. PDRB paling jauh dari tupoksi.",
        "bo": [3, 1, 4, 5, 5, 5, 4, 8],
        "ow": [3, 8, 2, 2, 2, 2, 2, 1],
    },
    {
        "id": "kesehatan",
        "nama": "Karina",
        "instansi": "Dinas Kesehatan (Kesehatan Masyarakat)",
        "peran": "Perencana Pelayanan Kesehatan",
        "lambda": 0.3,
        "password": "kesehatan",
        "best": "C4",
        "worst": "C8",
        "justifikasi": "UHH sebagai outcome kesehatan; sanitasi & air minum instrumen kesehatan lingkungan. PDRB paling jauh dari tupoksi.",
        "bo": [4, 6, 5, 1, 2, 2, 7, 8],
        "ow": [2, 2, 2, 8, 5, 5, 1, 1],
    },
]


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def state_default(dm_terisi: bool = True) -> dict:
    """Bangun state awal. dm_terisi=False -> penilaian DM kosong (mode demo)."""
    ids = [k["id"] for k in KRITERIA_DEFAULT]
    alt = pd.read_csv(DATA_DIR / "alternatif_3T.csv")
    dms = []
    for d in _DM_DEFAULT:
        item = {
            "id": d["id"],
            "nama": d["nama"],
            "instansi": d["instansi"],
            "peran": d.get("peran", d["instansi"]),
            "lambda": d["lambda"],
            "password": d["password"],
            "justifikasi": d.get("justifikasi", ""),
        }
        if dm_terisi:
            item.update({
                "best": d["best"],
                "worst": d["worst"],
                "bo": dict(zip(ids, d["bo"])),
                "ow": dict(zip(ids, d["ow"])),
                "submitted": True,
                "waktu": _now(),
            })
        else:
            item.update({
                "best": None,
                "worst": None,
                "bo": {},
                "ow": {},
                "submitted": False,
                "waktu": None,
            })
        dms.append(item)
    return {
        "kriteria": copy.deepcopy(KRITERIA_DEFAULT),
        "alternatif": alt.to_dict(orient="records"),
        "dm": dms,
        "admin_password": "admin",
        "cr_threshold": 0.284,
        "diskusi": [],
        "riwayat": [],
    }


def load() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    s = state_default()
    save(s)
    return s


def save(state: dict) -> None:
    """Tulis atomik agar tidak rusak bila dua pengguna menyimpan bersamaan."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=STATE_FILE.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_FILE)


def reset(dm_terisi: bool = True) -> dict:
    s = state_default(dm_terisi)
    save(s)
    return s


def alternatif_df(state: dict) -> pd.DataFrame:
    ids = [k["id"] for k in state["kriteria"]]
    df = pd.DataFrame(state["alternatif"])
    for col in ["Provinsi", "Kabupaten"] + ids:
        if col not in df.columns:
            df[col] = None
    return df[["Provinsi", "Kabupaten"] + ids]


def dm_by_id(state: dict, dm_id: str) -> dict:
    return next(d for d in state["dm"] if d["id"] == dm_id)


def sinkronkan_dm(state: dict) -> list[str]:
    """Pastikan penilaian DM konsisten dengan daftar kriteria.

    Bila kriteria berubah (ditambah/dihapus), penilaian DM yang sudah dikirim
    tidak lagi valid -> status dikembalikan ke 'belum mengisi'.
    """
    ids = [k["id"] for k in state["kriteria"]]
    direset = []
    for d in state["dm"]:
        d["bo"] = {k: v for k, v in d.get("bo", {}).items() if k in ids}
        d["ow"] = {k: v for k, v in d.get("ow", {}).items() if k in ids}
        if d.get("best") not in ids:
            d["best"] = None
        if d.get("worst") not in ids:
            d["worst"] = None
        lengkap = (
            d.get("best")
            and d.get("worst")
            and all(k in d["bo"] and k in d["ow"] for k in ids)
        )
        if d.get("submitted") and not lengkap:
            d["submitted"] = False
            direset.append(d["nama"])
    return direset
