"""
core.py - Logika perhitungan SPK Grup: Linear BWM + MARCOS + TOPSIS + SAW + Sensitivitas.

Tidak bergantung pada Streamlit, sehingga bisa diuji terpisah (lihat tests/).
Rumus mengikuti literatur dan file Excel:
- Rezaei (2016) untuk Linear BWM
- Liang et al. (2020) untuk CR input-based
- Aczél & Saaty (1983) untuk agregasi bobot rata-rata geometrik berbobot
- Stević et al. (2020) untuk MARCOS
- Hwang & Yoon (1981) untuk TOPSIS pembanding
- Kendall & Babington Smith (1939) untuk Kendall's W
- Analisis sensitivitas 8 skenario (S0 s.d. S7)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.stats import rankdata

SKALA_MIN, SKALA_MAX = 1, 9


# ----------------------------------------------------------------------------
# Validasi
# ----------------------------------------------------------------------------
def validasi_vektor_bwm(ids, best, worst, bo, ow):
    """Kembalikan list pesan error (kosong = valid).

    ids   : list id kriteria
    bo/ow : dict {id: nilai}; nilai boleh None (kosong)
    """
    err = []
    if best is None or worst is None:
        return ["Kriteria Best dan Worst harus dipilih."]
    if best == worst:
        err.append("Best dan Worst tidak boleh kriteria yang sama.")
    for nama, vec in (("Best-to-Others", bo), ("Others-to-Worst", ow)):
        for k in ids:
            v = vec.get(k)
            if v is None or (isinstance(v, float) and np.isnan(v)):
                err.append(f"{nama}: nilai {k} masih kosong.")
            elif not (SKALA_MIN <= v <= SKALA_MAX):
                err.append(f"{nama}: nilai {k} = {v} di luar skala {SKALA_MIN}-{SKALA_MAX}.")
    if err:
        return err
    if bo[best] != 1:
        err.append(f"Best-to-Others untuk Best ({best}) harus 1.")
    if ow[worst] != 1:
        err.append(f"Others-to-Worst untuk Worst ({worst}) harus 1.")
    if bo[worst] != ow[best]:
        err.append(
            f"Nilai Best terhadap Worst harus sama di kedua vektor "
            f"(BO[{worst}] = {bo[worst]} tetapi OW[{best}] = {ow[best]})."
        )
    return err


def validasi_alternatif(df, kriteria):
    """Validasi tabel alternatif. Mengembalikan list pesan error."""
    err = []
    ids = [k["id"] for k in kriteria]
    if len(kriteria) < 2:
        err.append("Minimal 2 kriteria.")
    if len(df) < 2:
        err.append("Minimal 2 alternatif.")
    if err:
        return err
    nama = df["Kabupaten"].astype(str).str.strip()
    if (nama == "").any() or df["Kabupaten"].isna().any():
        err.append("Nama alternatif tidak boleh kosong.")
    if nama.duplicated().any():
        dup = ", ".join(sorted(set(nama[nama.duplicated()])))
        err.append(f"Nama alternatif harus unik (duplikat: {dup}).")
    for k in kriteria:
        kol = pd.to_numeric(df[k["id"]], errors="coerce")
        if kol.isna().any():
            err.append(f"Kriteria {k['id']} ({k['nama']}): ada nilai kosong atau bukan angka.")
            continue
        if k["tipe"] == "Cost" and (kol <= 0).any():
            err.append(f"Kriteria {k['id']} bertipe Cost: semua nilai harus > 0 (pembagian dengan nol pada normalisasi).")
        if k["tipe"] == "Benefit" and kol.max() <= 0:
            err.append(f"Kriteria {k['id']} bertipe Benefit: nilai maksimum harus > 0.")
    return err


# ----------------------------------------------------------------------------
# Linear BWM
# ----------------------------------------------------------------------------
def linear_bwm(ids, best, worst, bo, ow):
    """Hitung bobot Linear BWM (Rezaei, 2016) dengan LP.

    Mengembalikan (w: dict id->bobot, xi: float).
    """
    n = len(ids)
    idx = {k: i for i, k in enumerate(ids)}
    b, w_ = idx[best], idx[worst]
    # variabel: w_1..w_n, xi
    c = np.zeros(n + 1)
    c[-1] = 1.0
    A, rhs = [], []
    for j, k in enumerate(ids):
        # wB - aBj*wj <= xi   dan   -(wB - aBj*wj) <= xi
        row = np.zeros(n + 1)
        row[b] += 1.0
        row[j] -= float(bo[k])
        row[-1] = -1.0
        A.append(row.copy())
        rhs.append(0.0)
        row2 = -row
        row2[-1] = -1.0
        A.append(row2)
        rhs.append(0.0)
        # wj - ajW*wW <= xi   dan   -(wj - ajW*wW) <= xi
        row = np.zeros(n + 1)
        row[j] += 1.0
        row[w_] -= float(ow[k])
        row[-1] = -1.0
        A.append(row.copy())
        rhs.append(0.0)
        row2 = -row
        row2[-1] = -1.0
        A.append(row2)
        rhs.append(0.0)
    A_eq = np.zeros((1, n + 1))
    A_eq[0, :n] = 1.0
    res = linprog(c, A_ub=np.array(A), b_ub=np.array(rhs), A_eq=A_eq, b_eq=[1.0],
                  bounds=[(0, None)] * (n + 1), method="highs")
    if not res.success:
        raise ValueError("Linear BWM tidak dapat diselesaikan: " + str(res.message))
    return {k: float(res.x[i]) for k, i in idx.items()}, float(res.x[-1])


def cr_input_based(ids, best, worst, bo, ow):
    """Input-based consistency ratio (Liang, Brunelli & Rezaei, 2020)."""
    abw = float(bo[worst])
    if abw <= 1:
        return 0.0
    maks = max(abs(float(bo[k]) * float(ow[k]) - abw) for k in ids)
    return maks / (abw ** 2 - abw)


# ----------------------------------------------------------------------------
# Agregasi bobot grup
# ----------------------------------------------------------------------------
def agregasi_bobot(bobot_dm: pd.DataFrame, lam: pd.Series) -> pd.Series:
    """Rata-rata geometrik berbobot (Aczél & Saaty, 1983).

    bobot_dm : DataFrame, index = id kriteria, kolom = id DM
    lam      : Series, index = id DM (dinormalisasi otomatis)
    """
    lam = lam / lam.sum()
    gm = np.exp((np.log(bobot_dm.clip(lower=1e-12)) * lam[bobot_dm.columns]).sum(axis=1))
    return gm / gm.sum()


def korelasi_dan_cv_kriteria(bobot_dm: pd.DataFrame) -> pd.DataFrame:
    """Hitung rata-rata, standar deviasi, dan Koefisien Variasi (CV) bobot kriteria antar-DM."""
    mean = bobot_dm.mean(axis=1)
    std = bobot_dm.std(axis=1, ddof=1)
    cv = std / mean
    return pd.DataFrame({"Mean": mean, "Std": std, "CV": cv})


# ----------------------------------------------------------------------------
# MARCOS
# ----------------------------------------------------------------------------
def marcos(X: pd.DataFrame, tipe: dict, w: pd.Series) -> dict:
    """Hitung MARCOS lengkap beserta hasil antara (Stević et al., 2020).

    X    : DataFrame alternatif x kriteria (index = nama alternatif)
    tipe : dict id -> 'Benefit' / 'Cost'
    w    : Series bobot (index = id kriteria)
    """
    X = X.astype(float)
    w = w[X.columns]
    ai = pd.Series({k: X[k].max() if tipe[k] == "Benefit" else X[k].min() for k in X.columns})
    aai = pd.Series({k: X[k].min() if tipe[k] == "Benefit" else X[k].max() for k in X.columns})

    def norm(row):
        return pd.Series({
            k: (row[k] / ai[k]) if tipe[k] == "Benefit" else (ai[k] / row[k])
            for k in X.columns
        })

    N = X.apply(norm, axis=1)
    N_aai = norm(aai)
    V = N * w
    S = V.sum(axis=1)
    S_aai = float((N_aai * w).sum())
    S_ai = float(w.sum())                 # N_AI = 1 untuk semua kriteria
    K_min = S / S_aai
    K_plus = S / S_ai
    f_min = K_plus / (K_plus + K_min)
    f_plus = K_min / (K_plus + K_min)
    fK = (K_plus + K_min) / (1 + (1 - f_plus) / f_plus + (1 - f_min) / f_min)
    rank = fK.rank(ascending=False, method="min").astype(int)

    # Indeks keparahan relatif V_rel = (N - N_aai) / (1 - N_aai)
    denom = (1 - N_aai).replace(0, np.nan)
    V_rel = (N - N_aai) / denom
    paling_kritis = V_rel.fillna(0).idxmax(axis=1)

    hasil = pd.DataFrame({
        "S": S, "K-": K_min, "K+": K_plus, "f(K-)": f_min, "f(K+)": f_plus,
        "f(K)": fK, "Rank": rank, "Kriteria paling kritis": paling_kritis,
    })
    return {"AI": ai, "AAI": aai, "N": N, "N_aai": N_aai, "V": V,
            "V_rel": V_rel, "S_aai": S_aai, "S_ai": S_ai, "hasil": hasil}


# ----------------------------------------------------------------------------
# Pembanding: TOPSIS & SAW
# ----------------------------------------------------------------------------
def topsis(X: pd.DataFrame, tipe: dict, w: pd.Series) -> dict:
    """Hitung TOPSIS lengkap (Hwang & Yoon, 1981) sesuai sheet Pembanding Excel."""
    X = X.astype(float)
    w = w[X.columns]
    denom = np.sqrt((X ** 2).sum(axis=0))
    R_norm = X / denom
    Y = R_norm * w

    A_plus = pd.Series({
        k: Y[k].max() if tipe[k] == "Benefit" else Y[k].min()
        for k in X.columns
    })
    A_minus = pd.Series({
        k: Y[k].min() if tipe[k] == "Benefit" else Y[k].max()
        for k in X.columns
    })

    D_plus = np.sqrt(((Y - A_plus) ** 2).sum(axis=1))
    D_minus = np.sqrt(((Y - A_minus) ** 2).sum(axis=1))
    CC = D_minus / (D_plus + D_minus)
    rank = CC.rank(ascending=False, method="min").astype(int)

    hasil = pd.DataFrame({
        "D+": D_plus, "D-": D_minus, "CC": CC, "Rank": rank
    })
    return {"denom": denom, "R_norm": R_norm, "Y": Y, "A_plus": A_plus,
            "A_minus": A_minus, "hasil": hasil}


def saw(X: pd.DataFrame, tipe: dict, w: pd.Series) -> dict:
    """Hitung SAW dengan normalisasi linear yang sama dengan MARCOS."""
    X = X.astype(float)
    w = w[X.columns]
    ai = pd.Series({k: X[k].max() if tipe[k] == "Benefit" else X[k].min() for k in X.columns})

    def norm(row):
        return pd.Series({
            k: (row[k] / ai[k]) if tipe[k] == "Benefit" else (ai[k] / row[k])
            for k in X.columns
        })

    N = X.apply(norm, axis=1)
    skor = (N * w).sum(axis=1)
    rank = skor.rank(ascending=False, method="min").astype(int)
    hasil = pd.DataFrame({"Skor": skor, "Rank": rank})
    return {"N": N, "hasil": hasil}


# ----------------------------------------------------------------------------
# Konsensus antar-DM & Korelasi
# ----------------------------------------------------------------------------
def spearman(r1, r2):
    """Korelasi rank Spearman."""
    d = np.asarray(r1, float) - np.asarray(r2, float)
    n = len(d)
    if n <= 1:
        return 1.0
    return float(1 - 6 * (d ** 2).sum() / (n * (n ** 2 - 1)))


def kendall_w(rank_matrix: pd.DataFrame) -> float:
    """rank_matrix: baris = alternatif, kolom = DM (berisi peringkat)."""
    n, m = rank_matrix.shape
    R = rank_matrix.sum(axis=1)
    S = ((R - R.mean()) ** 2).sum()
    return float(12 * S / (m ** 2 * (n ** 3 - n)))


def konsensus_lengkap(X: pd.DataFrame, tipe: dict, bobot_dm: pd.DataFrame, w_grup: pd.Series):
    """Perhitungan konsensus lengkap: MARCOS per DM, Spearman antar DM & Grup, Kendall's W,

    serta identifikasi 5 alternatif paling diperdebatkan dan 5 paling disepakati.
    """
    ranks = {}
    fK_per_dm = {}
    for dm in bobot_dm.columns:
        res = marcos(X, tipe, bobot_dm[dm])
        fK_per_dm[dm] = res["hasil"]["f(K)"]
        ranks[dm] = res["hasil"]["Rank"]

    # Rank grup
    res_grup = marcos(X, tipe, w_grup)
    ranks["Grup"] = res_grup["hasil"]["Rank"]
    fK_per_dm["Grup"] = res_grup["hasil"]["f(K)"]

    R_semua = pd.DataFrame(ranks, index=X.index)
    fK_df = pd.DataFrame(fK_per_dm, index=X.index)

    # Matriks Spearman antar seluruh pihak termasuk Grup
    sp_matrix = pd.DataFrame(
        [[spearman(R_semua[a], R_semua[b]) for b in R_semua.columns] for a in R_semua.columns],
        index=R_semua.columns, columns=R_semua.columns,
    )

    # Kendall's W hanya antar DM (bukan dengan grup)
    dm_cols = [c for c in bobot_dm.columns]
    R_dm_only = R_semua[dm_cols]
    W = kendall_w(R_dm_only)

    # Rentang rank antar-DM
    rentang = R_dm_only.max(axis=1) - R_dm_only.min(axis=1)
    std_rank = R_dm_only.std(axis=1)
    perdebatan = pd.DataFrame({
        "Rentang": rentang,
        "Std": std_rank,
        "Rank Grup": R_semua["Grup"],
    }).join(R_dm_only)

    paling_diperdebatkan = perdebatan.sort_values(by=["Rentang", "Std"], ascending=False).head(5)
    paling_disepakati = perdebatan.sort_values(by=["Rentang", "Std"], ascending=True).head(5)

    return {
        "R_semua": R_semua,
        "R_dm_only": R_dm_only,
        "fK_df": fK_df,
        "spearman": sp_matrix,
        "kendall_w": W,
        "paling_diperdebatkan": paling_diperdebatkan,
        "paling_disepakati": paling_disepakati,
    }


# ----------------------------------------------------------------------------
# Analisis Sensitivitas (S0 s.d. S7)
# ----------------------------------------------------------------------------
def analisis_sensitivitas(X: pd.DataFrame, tipe: dict, w_basis: pd.Series,
                          bobot_dm: pd.DataFrame, kriteria_target: str = "C1",
                          delta: float = 0.2) -> dict:
    """Hitung 8 skenario analisis sensitivitas sesuai sheet Sensitivitas Excel.

    S0: Basis (bobot agregat BWM grup)
    S1: Bobot kriteria sama rata (1/n)
    S2: Hanya bobot DM1 Bappeda
    S3: Hanya bobot DM2 Pendidikan
    S4: Hanya bobot DM3 Kesehatan
    S5: Bobot DM sama (lambda = 1/3)
    S6: Bobot kriteria_target dinaikkan +delta (default +20%), dinormalisasi
    S7: Bobot kriteria_target diturunkan -delta (default -20%), dinormalisasi
    """
    ids = list(X.columns)
    scenarios = {}

    # S0
    scenarios["S0"] = {"desc": "Basis: bobot agregat (λ = 0,4/0,3/0,3)", "w": w_basis}

    # S1
    scenarios["S1"] = {"desc": "Bobot kriteria sama rata (1/n)",
                       "w": pd.Series({k: 1.0 / len(ids) for k in ids})}

    # S2, S3, S4
    dm_keys = list(bobot_dm.columns)
    if len(dm_keys) >= 1:
        scenarios["S2"] = {"desc": f"Hanya bobot DM1 ({dm_keys[0]})", "w": bobot_dm[dm_keys[0]]}
    if len(dm_keys) >= 2:
        scenarios["S3"] = {"desc": f"Hanya bobot DM2 ({dm_keys[1]})", "w": bobot_dm[dm_keys[1]]}
    if len(dm_keys) >= 3:
        scenarios["S4"] = {"desc": f"Hanya bobot DM3 ({dm_keys[2]})", "w": bobot_dm[dm_keys[2]]}

    # S5: equal lambda
    equal_lam = pd.Series({dm: 1.0 / len(dm_keys) for dm in dm_keys})
    w_s5 = agregasi_bobot(bobot_dm, equal_lam)
    scenarios["S5"] = {"desc": "Bobot DM sama (λ = 1/3 masing-masing)", "w": w_s5}

    # S6: kriteria_target +delta
    if kriteria_target in w_basis.index:
        w_s6 = w_basis.copy()
        w_s6[kriteria_target] *= (1.0 + delta)
        w_s6 = w_s6 / w_s6.sum()
        scenarios["S6"] = {"desc": f"Kriteria {kriteria_target} dinaikkan {int(delta*100)}%, lalu dinormalisasi",
                           "w": w_s6}

        w_s7 = w_basis.copy()
        w_s7[kriteria_target] *= max(0.0, (1.0 - delta))
        w_s7 = w_s7 / w_s7.sum()
        scenarios["S7"] = {"desc": f"Kriteria {kriteria_target} diturunkan {int(delta*100)}%, lalu dinormalisasi",
                           "w": w_s7}

    # Run MARCOS for all scenarios
    hasil_m = {}
    fK_table = {}
    rank_table = {}
    weights_table = {}

    for sc_id, sc_info in scenarios.items():
        res = marcos(X, tipe, sc_info["w"])
        hasil_m[sc_id] = res
        fK_table[sc_id] = res["hasil"]["f(K)"]
        rank_table[sc_id] = res["hasil"]["Rank"]
        weights_table[sc_id] = sc_info["w"]

    fK_df = pd.DataFrame(fK_table, index=X.index)
    rank_df = pd.DataFrame(rank_table, index=X.index)
    weights_df = pd.DataFrame(weights_table, index=ids)

    # Calculate summary metrics vs S0
    rank_s0 = rank_df["S0"]
    top5_s0 = set(rank_s0.nsmallest(5).index)
    top10_s0 = set(rank_s0.nsmallest(10).index)

    summary_rows = []
    for sc_id, sc_info in scenarios.items():
        r_sc = rank_df[sc_id]
        rho = spearman(rank_s0, r_sc)
        top1 = r_sc.idxmin()
        top5_sc = set(r_sc.nsmallest(5).index)
        top10_sc = set(r_sc.nsmallest(10).index)
        top5_retained = f"{len(top5_s0.intersection(top5_sc))} / 5"
        top10_retained = f"{len(top10_s0.intersection(top10_sc))} / 10"
        max_shift = int((r_sc - rank_s0).abs().max()) if sc_id != "S0" else 0

        summary_rows.append({
            "Skenario": sc_id,
            "Keterangan": sc_info["desc"],
            "ρ Spearman vs S0": rho,
            "Peringkat 1": top1,
            "Top-5 Tetap": top5_retained,
            "Top-10 Tetap": top10_retained,
            "Pergeseran Maks.": max_shift if sc_id != "S0" else "-",
        })

    summary_df = pd.DataFrame(summary_rows)
    return {
        "summary": summary_df,
        "weights": weights_df,
        "fK": fK_df,
        "ranks": rank_df,
        "scenarios": scenarios,
    }


# ----------------------------------------------------------------------------
# Alur lengkap (hitung_semua)
# ----------------------------------------------------------------------------
def hitung_semua(kriteria, alternatif: pd.DataFrame, dm_list):
    """Jalankan seluruh alur dari data state:

    BWM per DM -> Agregasi bobot grup -> MARCOS -> TOPSIS -> SAW -> Konsensus -> Sensitivitas.
    dm_list: list dict DM dengan kunci id, nama, lambda, best, worst, bo, ow.
    """
    ids = [k["id"] for k in kriteria]
    tipe = {k["id"]: k["tipe"] for k in kriteria}
    X = alternatif.set_index("Kabupaten")[ids].astype(float)

    # 1. Linear BWM per DM
    bobot, info = {}, {}
    for d in dm_list:
        w, xi = linear_bwm(ids, d["best"], d["worst"], d["bo"], d["ow"])
        bobot[d["id"]] = pd.Series(w)
        info[d["id"]] = {"xi": xi, "CRI": cr_input_based(ids, d["best"], d["worst"], d["bo"], d["ow"])}
    bobot_dm = pd.DataFrame(bobot)[[d["id"] for d in dm_list]].loc[ids]
    lam = pd.Series({d["id"]: float(d["lambda"]) for d in dm_list})

    # 2. Agregasi bobot grup
    w_grup = agregasi_bobot(bobot_dm, lam)
    cv_kriteria = korelasi_dan_cv_kriteria(bobot_dm)

    # 3. MARCOS
    m = marcos(X, tipe, w_grup)

    # 4. Pembanding TOPSIS & SAW
    t = topsis(X, tipe, w_grup)
    s_saw = saw(X, tipe, w_grup)
    rho_topsis = spearman(m["hasil"]["Rank"], t["hasil"]["Rank"])
    rho_saw = spearman(m["hasil"]["Rank"], s_saw["hasil"]["Rank"])

    # 5. Konsensus lengkap
    kons = konsensus_lengkap(X, tipe, bobot_dm, w_grup)

    # 6. Analisis Sensitivitas
    sens = analisis_sensitivitas(X, tipe, w_grup, bobot_dm, kriteria_target=ids[0] if ids else "C1")

    # Backward compatibility with existing keys in test_core.py
    return {
        "ids": ids,
        "tipe": tipe,
        "X": X,
        "bobot_dm": bobot_dm,
        "info": info,
        "w_grup": w_grup,
        "cv_kriteria": cv_kriteria,
        "marcos": m,
        "topsis": t,
        "saw": s_saw,
        "rho_topsis": rho_topsis,
        "rho_saw": rho_saw,
        "rank_dm": kons["R_dm_only"],
        "spearman": kons["spearman"],
        "kendall_w": kons["kendall_w"],
        "konsensus_lengkap": kons,
        "sensitivitas": sens,
    }
