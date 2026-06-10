#!/usr/bin/env python3
"""
polar_daily.py — Sync Polar AccessLink v3 (Open AccessLink)
Utilise /v3/exercises?from=&to= pour accéder aux séances passées ET futures
Crontab : 9h30 et 17h
Stocke  : /root/polar/data/sync_YYYYMMDD_HHMMSS.json
Log     : /root/polar/sync_log.txt
"""

import os, json, time, requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path="/root/polar/.env")
except ImportError:
    pass

# ─── CONFIG ───────────────────────────────────────────────────
POLAR_DIR    = Path(os.getenv("KDRIVE_PATH", "/root/polar"))
DATA_DIR     = POLAR_DIR / "data"
LOG_FILE     = POLAR_DIR / "sync_log.txt"
DATA_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL      = "https://www.polaraccesslink.com"
USER_ID       = None  # sera détecté automatiquement depuis tokens.json

def _load_access_token():
    """Lit le token depuis tokens.json en priorité, fallback .env."""
    tf = Path(os.getenv("KDRIVE_PATH", "/root/polar")) / "tokens.json"
    if tf.exists():
        try:
            t = json.loads(tf.read_text())
            tok = t.get("access_token") or t.get("POLAR_ACCESS_TOKEN")
            if tok:
                return tok
        except Exception:
            pass
    tok = os.getenv("POLAR_ACCESS_TOKEN")
    if not tok:
        raise RuntimeError("Token introuvable : tokens.json absent/invalide et POLAR_ACCESS_TOKEN non défini dans .env")
    return tok

ACCESS_TOKEN = _load_access_token()


# ─── LOG ──────────────────────────────────────────────────────
def log(msg):
    ts   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] DAILY | {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ─── HTTP ─────────────────────────────────────────────────────
def _h(accept="application/json"):
    return {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Accept": accept,
        "Content-Type": "application/json"
    }

def polar_get(path, accept="application/json", params=None):
    url = path if path.startswith("http") else BASE_URL + path
    r   = requests.get(url, headers=_h(accept), params=params, timeout=30)
    r.raise_for_status()
    if accept == "application/gpx+xml":
        return r.text
    return r.json() if r.content else {}


# ─── TOKEN / USER ID ──────────────────────────────────────────
def load_user_id():
    global USER_ID
    # Essayer depuis tokens.json
    tokens_file = POLAR_DIR / "tokens.json"
    if tokens_file.exists():
        try:
            t = json.loads(tokens_file.read_text())
            USER_ID = t.get("x_user_id")
            if USER_ID:
                log(f"User ID depuis tokens.json: {USER_ID}")
                return
        except Exception:
            pass
    # Fallback : appel API
    try:
        me = polar_get("/v3/users/me")
        USER_ID = me.get("polar-user-id")
        log(f"User ID depuis API: {USER_ID}")
    except Exception as e:
        log(f"Impossible de récupérer user_id: {e}")


# ─── SAMPLES ──────────────────────────────────────────────────
SAMPLE_TYPES = [
    "heart-rate",
    "speed",
    "cadence",
    "altitude",
    "distance",
    "power",
    "rr-interval",
]

def fetch_samples(exercise_id):
    """Récupère les samples via /v3/exercises/{id}?samples=true
    
    DÉPANNAGE TOKEN/API :
    - 401 Unauthorized → token expiré, renouveler via OAuth (voir /root/polar/tokens.json)
    - 404 Not Found    → exercice non disponible ou endpoint incorrect
    - 403 Forbidden    → droits insuffisants sur l'application Polar AccessLink
    - samples vides    → l'exercice n'a pas de données GPS/FC détaillées
    Pour renouveler le token : relancer l'authentification OAuth depuis /root/polar/app.py
    """
    SAMPLE_TYPE_MAP = {
        0: "heart-rate",
        1: "speed",
        2: "cadence",
        3: "altitude",
        4: "power",
        9: "temperature",
        10: "distance-cumul",
    }
    samples = {}
    try:
        url  = f"/v3/exercises/{exercise_id}?samples=true"
        data = polar_get(url)
        if not data:
            return {}
        raw_list = data.get("samples", [])
        zones_list = data.get("zones", [])
        # Aussi essayer le format _samples.raw
        if not raw_list and isinstance(data.get("_samples"), dict):
            raw_list = data["_samples"].get("raw", [])
            zones_list = data["_samples"].get("zones", [])
        for s in raw_list:
            t = s.get("sample_type")
            raw = s.get("data", "")
            if t is None or not raw:
                continue
            name = SAMPLE_TYPE_MAP.get(int(t), f"type_{t}")
            try:
                vals = [float(v) for v in raw.split(",") if v.strip()]
                if vals:
                    samples[name] = {
                        "data": vals,
                        "rate": float(s.get("recording_rate", 1)),
                        "count": len(vals),
                    }
            except Exception:
                pass
        if zones_list:
            samples["zones"] = zones_list
        if samples:
            log(f"    samples: {len(samples)} type(s) via ?samples=true")
        else:
            log(f"    samples: vides (pas de données détaillées)")
    except Exception as e:
        log(f"    samples erreur: {e}")
    return samples
def _extract_values(item):
    if not item:
        return []
    if isinstance(item, list):
        return item
    if isinstance(item, dict):
        for k in ("data", "samples", "values", "recording", "data_samples"):
            v = item.get(k)
            if isinstance(v, list):
                return v
    return []

def _get_rate(item):
    if not isinstance(item, dict):
        return 1.0
    for k in ("recording_rate_in_seconds", "recording_rate", "interval_in_seconds"):
        try:
            v = item.get(k)
            if v is not None:
                return float(v)
        except Exception:
            pass
    return 1.0


# ─── ANALYSE COURSE ───────────────────────────────────────────
def build_km_splits(samples, total_distance_m):
    """Construit les splits au km depuis les samples.
    Supporte ancien format (clés nommées) et nouveau format (speed/distance-cumul).
    """
    # Nouveau format : utiliser speed (m/s) pour calculer distance cumulée
    speed_data = (samples.get("speed") or {}).get("data", [])
    dist_cumul  = (samples.get("distance-cumul") or {}).get("data", [])
    hr_data     = (samples.get("heart-rate") or {}).get("data", [])
    cad_data    = (samples.get("cadence") or {}).get("data", [])
    pwr_data    = (samples.get("power") or {}).get("data", [])
    alt_data    = (samples.get("altitude") or {}).get("data", [])
    rate        = (samples.get("speed") or samples.get("distance") or {}).get("rate", 1.0)

    # Construire distance cumulée depuis speed si pas de dist_cumul
    if not dist_cumul and speed_data:
        dist_cumul = []
        cum = 0.0
        for s in speed_data:
            cum += float(s) * rate
            dist_cumul.append(cum)

    # Fallback ancien format
    if not dist_cumul:
        old_dist = (samples.get("distance") or {}).get("data", [])
        if old_dist:
            dist_cumul = [float(x) for x in old_dist]

    if not dist_cumul:
        return []

    splits   = []
    km_idx   = 1
    km_start = 0
    km_target = 1000.0

    for i, d in enumerate(dist_cumul):
        if d >= km_target:
            n_pts   = i - km_start + 1
            time_s  = n_pts * rate
            d_start = dist_cumul[km_start] if km_start > 0 else 0
            d_km    = d - d_start
            pace_s  = time_s / d_km * 1000 if d_km > 0 else 0
            pace_min = int(pace_s // 60)
            pace_sec = int(pace_s % 60)

            avg_hr  = int(sum(hr_data[km_start:i+1]) / n_pts) if hr_data and len(hr_data) > i else None
            max_hr  = int(max(hr_data[km_start:i+1])) if hr_data and len(hr_data) > i else None
            min_hr  = int(min(hr_data[km_start:i+1])) if hr_data and len(hr_data) > i else None
            avg_cad = int(sum(cad_data[km_start:i+1]) / n_pts) if cad_data and len(cad_data) > i else None
            avg_pwr = int(sum(pwr_data[km_start:i+1]) / n_pts) if pwr_data and len(pwr_data) > i else None
            max_pwr = int(max(pwr_data[km_start:i+1])) if pwr_data and len(pwr_data) > i else None

            # Dénivelé depuis altitude
            d_plus = d_minus = 0
            if alt_data and len(alt_data) > i:
                alts = alt_data[km_start:i+1]
                for j in range(1, len(alts)):
                    diff = alts[j] - alts[j-1]
                    if diff > 0: d_plus += diff
                    else: d_minus += abs(diff)

            splits.append({
                "km":      km_idx,
                "pace":    f"{pace_min}:{pace_sec:02d}",
                "pace_s":  round(pace_s, 1),
                "hr_avg":  avg_hr,
                "hr_max":  max_hr,
                "hr_min":  min_hr,
                "cadence": avg_cad * 2 if avg_cad else None,
                "pwr_avg": avg_pwr,
                "pwr_max": max_pwr,
                "d_plus":  round(d_plus, 1),
                "d_minus": round(d_minus, 1),
            })
            km_start  = i
            km_idx   += 1
            km_target = km_idx * 1000.0
            if km_target > total_distance_m + 200:
                break

    return splits
def compute_samples_5s(samples, total_distance_m):
    """
    Génère _samples_5s depuis les samples bruts Polar :
    - Sous-échantillonne à 1 point toutes les 5s (ou rate naturel)
    - Calcule BPM, pace_s, speed_kmh, dist_m pour le graphique
    - Identifie les blocs d'intensité (reps) via seuils FC/allure
    Retourne un dict avec toutes les séries + quality_blocks.
    """
    speed_data  = (samples.get("speed") or {}).get("data", [])
    hr_data     = (samples.get("heart-rate") or {}).get("data", [])
    dist_cumul  = (samples.get("distance-cumul") or {}).get("data", [])
    rate        = float((samples.get("speed") or samples.get("heart-rate") or {}).get("rate", 1))

    if not speed_data and not hr_data:
        return None

    # Construire dist_cumul si absent
    if not dist_cumul and speed_data:
        cum = 0.0
        dist_cumul = []
        for s in speed_data:
            cum += float(s) * rate
            dist_cumul.append(cum)

    n = max(len(speed_data), len(hr_data), len(dist_cumul))
    if n == 0:
        return None

    # Sous-échantillonnage : 1 point toutes les 5s
    step = max(1, round(5 / rate)) if rate > 0 else 5

    bpm_5s      = []
    pace_s_5s   = []
    speed_kmh_5s = []
    dist_m_5s   = []

    for i in range(0, n, step):
        # BPM
        hr_val = hr_data[i] if i < len(hr_data) else None
        bpm_5s.append(int(hr_val) if hr_val and 30 < hr_val < 250 else None)

        # Vitesse → pace
        spd = speed_data[i] if i < len(speed_data) else None
        if spd and spd > 0.5:  # Polar speed = km/h (type 1)
            pace_s = round(3600 / spd)
            pace_s_5s.append(pace_s if 60 < pace_s < 900 else None)
            speed_kmh_5s.append(round(spd, 1))
        else:
            pace_s_5s.append(None)
            speed_kmh_5s.append(None)

        # Distance
        d = dist_cumul[i] if i < len(dist_cumul) else None
        dist_m_5s.append(round(d, 1) if d else None)

    # ── Détection blocs qualité depuis les samples 5s ──────────
    # Beaucoup plus précis que les km splits pour les reps courtes
    quality_blocks = []
    in_block = False
    block_start = None
    HR_THRESHOLD = 158   # Z3+ → effort
    PACE_THRESHOLD = 305  # < 5:05/km → effort

    for i, (bpm, pace) in enumerate(zip(bpm_5s, pace_s_5s)):
        is_fast = (bpm and bpm >= HR_THRESHOLD) or (pace and pace <= PACE_THRESHOLD)
        if is_fast and not in_block:
            in_block = True
            block_start = i
        elif not is_fast and in_block:
            # Fin du bloc — garder si ≥ 45s (9 points × 5s)
            duration = (i - block_start) * 5
            if duration >= 45:
                block_paces = [p for p in pace_s_5s[block_start:i] if p]
                block_hrs   = [b for b in bpm_5s[block_start:i] if b]
                quality_blocks.append({
                    "start_s":    block_start * 5,
                    "end_s":      i * 5,
                    "duration_s": duration,
                    "pace_avg_s": round(sum(block_paces)/len(block_paces)) if block_paces else None,
                    "hr_avg":     round(sum(block_hrs)/len(block_hrs)) if block_hrs else None,
                    "hr_max":     max(block_hrs) if block_hrs else None,
                })
            in_block = False

    return {
        "bpm":            bpm_5s,
        "pace_s":         pace_s_5s,
        "speed_kmh":      speed_kmh_5s,
        "dist_m":         dist_m_5s,
        "quality_blocks": quality_blocks,  # reps détectées avec précision
        "n_samples":      len(bpm_5s),
        "interval_s":     5,
    }


def save_splits_cache(exercise_id, km_splits, samples_5s, summary):
    """Sauvegarde le cache splits dans /root/polar/data/splits/{id}.json"""
    splits_dir = DATA_DIR / "splits"
    splits_dir.mkdir(parents=True, exist_ok=True)
    cache = {
        "exercise_id": exercise_id,
        "generated":   datetime.now(timezone.utc).isoformat(),
        "km_splits":   km_splits,
        "samples_5s":  samples_5s,
        "summary":     summary,
    }
    out = splits_dir / f"{exercise_id}.json"
    tmp = splits_dir / f"{exercise_id}.tmp"
    tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(out)
    return out


def fetch_exercises(days_back=14):
    """
    Récupère les séances via Open AccessLink /v3/exercises
    Beaucoup plus fiable que le flux transaction.
    """
    end   = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")

    log(f"Fetch exercises {start} → {end}")
    try:
        items = polar_get("/v3/exercises", params={"from": start, "to": end})
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response else 0
        log(f"fetch_exercises HTTP {code}: {e}")
        return []
    except Exception as e:
        log(f"fetch_exercises erreur: {e}")
        return []

    if not items:
        log("Aucune séance dans la période")
        return []

    log(f"{len(items)} séance(s) trouvée(s)")
    exercises = []

    for ex in items:
        ex_id  = ex.get("id", "")
        sport  = ex.get("sport", "")
        date   = (ex.get("start_time") or "")[:10]
        dist_m = ex.get("distance") or 0
        dist   = dist_m / 1000

        ex["date"] = date  # normaliser le champ date
        log(f"  [{sport}] {date} {dist:.1f}km (id={ex_id})")

        if sport in ("RUNNING", "CYCLING") and ex_id:
            log(f"    Récupération des samples...")
            smp = fetch_samples(ex_id)
            ex["_samples"] = smp
            splits = build_km_splits(smp, dist_m)
            if splits:
                ex["_km_splits"] = splits
                ex["splits"] = splits
                for s in splits:
                    hr_str  = f" | FC={s.get('hr_avg')}" if s.get('hr_avg') else ""
                    cad_str = f" | cad={s.get('cadence')}" if s.get('cadence') else ""
                    pwr_str = f" | pwr={s.get('pwr_avg')}W" if s.get('pwr_avg') else ""
                    log(f"    km {s['km']}: {s['pace']}/km{hr_str}{cad_str}{pwr_str}")
            # Calculer _samples_summary
            hr_data  = smp.get("heart-rate", {}).get("data", [])
            cad_data = smp.get("cadence", {}).get("data", [])
            pwr_data = smp.get("power", {}).get("data", [])
            spd_data = smp.get("speed", {}).get("data", [])
            alt_data = smp.get("altitude", {}).get("data", [])
            summary = {}
            if hr_data:
                hr_valid = [h for h in hr_data if 40 < h < 220]
                if hr_valid:
                    summary["hr_avg"] = int(sum(hr_valid)/len(hr_valid))
                    summary["hr_max"] = int(max(hr_valid))
                    summary["hr_min"] = int(min(hr_valid))
            if cad_data:
                cad_nz = [c for c in cad_data if c > 0]
                if cad_nz:
                    summary["cadence_avg"] = int(sum(cad_nz)/len(cad_nz)) * 2
                    summary["cadence_max"] = int(max(cad_nz)) * 2
            if pwr_data:
                # Filtrer puissance aberrante (running: 50-600W, cycling: 50-2000W)
                pwr_max_filter = 600 if sport == "RUNNING" else 2000
                pwr_nz = [p for p in pwr_data if 10 < p < pwr_max_filter]
                if pwr_nz:
                    summary["pwr_avg"] = int(sum(pwr_nz)/len(pwr_nz))
                    summary["pwr_max"] = int(max(pwr_nz))
            if spd_data:
                # Filtrer vitesses aberrantes (>25 km/h pour running = 6.9 m/s)
                # Vitesse en km/h (format Polar AccessLink)
                max_spd_filter = 25.0 if sport == "RUNNING" else 80.0
                spd_nz = [s for s in spd_data if 1.0 < s < max_spd_filter]
                if spd_nz:
                    avg_spd_kmh = sum(spd_nz)/len(spd_nz)
                    max_spd_kmh = max(spd_nz)
                    # Convertir km/h → pace min/km
                    pace_avg_s = 3600/avg_spd_kmh if avg_spd_kmh > 0 else 0
                    pace_max_s = 3600/max_spd_kmh if max_spd_kmh > 0 else 0
                    summary["pace_avg"] = f"{int(pace_avg_s//60)}:{int(pace_avg_s%60):02d}/km"
                    summary["pace_max"] = f"{int(pace_max_s//60)}:{int(pace_max_s%60):02d}/km"
                    if sport == "CYCLING":
                        summary["speed_avg_kmh"] = round(avg_spd_kmh, 1)
                        summary["speed_max_kmh"] = round(max_spd_kmh, 1)
            ex["_samples_summary"] = summary

            # ── Générer et stocker _samples_5s ──────────────────
            s5 = compute_samples_5s(smp, dist_m)
            if s5:
                ex["_samples_5s"] = s5
                nb_blocks = len(s5.get("quality_blocks", []))
                log(f"    samples_5s: {s5['n_samples']} pts | {nb_blocks} bloc(s) qualité détecté(s)")
                if nb_blocks:
                    for b in s5["quality_blocks"]:
                        pace_str = f"{b['pace_avg_s']//60}:{b['pace_avg_s']%60:02d}" if b.get('pace_avg_s') else "?"
                        log(f"      rep {b['duration_s']}s @ {pace_str}/km FC={b.get('hr_avg')}bpm (pic={b.get('hr_max')})")

            # ── Sauvegarder le cache splits ──────────────────────
            if ex_id and (splits or s5):
                cache_file = save_splits_cache(ex_id, splits, s5, summary)
                log(f"    Cache splits sauvegardé: {cache_file.name}")

            # Calculer _elevation
            if alt_data:
                d_plus = d_minus = 0.0
                for j in range(1, len(alt_data)):
                    diff = alt_data[j] - alt_data[j-1]
                    if diff > 0: d_plus += diff
                    else: d_minus += abs(diff)
                ex["_elevation"] = {"d_plus": round(d_plus,1), "d_minus": round(d_minus,1)}
        if sport in ("SWIMMING", "POOL_SWIMMING") and ex_id:
            smp2 = fetch_samples(ex_id)
            if smp2.get("zones"):
                ex["_hr_zones"] = smp2["zones"]
        exercises.append(ex)
        time.sleep(0.3)

    return exercises


# ─── SLEEP ────────────────────────────────────────────────────
def fetch_sleep(days_back=14):
    end   = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
    try:
        data   = polar_get("/v3/users/sleep", params={"from": start, "to": end})
        nights = data if isinstance(data, list) else data.get("nights", data.get("data", []))
        log(f"Sleep: {len(nights)} nuit(s)")
        return nights
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response else 0
        log(f"fetch_sleep HTTP {code}: {e}")
        return []
    except requests.exceptions.RequestException as e:
        # Attrape ConnectionError, SSLError, Timeout, ChunkedEncodingError, etc.
        log(f"fetch_sleep erreur réseau: {type(e).__name__}: {e}")
        return []
    except Exception as e:
        log(f"fetch_sleep erreur inattendue: {type(e).__name__}: {e}")
        return []


# ─── NIGHTLY RECHARGE ─────────────────────────────────────────
def fetch_nightly_recharge(days_back=14):
    end   = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
    try:
        data  = polar_get("/v3/users/nightly-recharge", params={"from": start, "to": end})
        items = data if isinstance(data, list) else data.get("recharges", data.get("data", []))
        log(f"Nightly recharge: {len(items)} entrée(s)")
        return items
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response else 0
        log(f"fetch_nightly_recharge HTTP {code}: {e}")
        return []
    except requests.exceptions.RequestException as e:
        log(f"fetch_nightly_recharge erreur réseau: {type(e).__name__}: {e}")
        return []
    except Exception as e:
        log(f"fetch_nightly_recharge erreur inattendue: {type(e).__name__}: {e}")
        return []


# ─── DAILY ACTIVITY ───────────────────────────────────────────
def fetch_daily_activity(days_back=14):
    end   = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
    try:
        if USER_ID:
            data = polar_get(f"/v3/users/{USER_ID}/activity-summary/transaction-list")
        else:
            data = polar_get("/v3/users/me/activity-summary/transaction-list")
        items = data if isinstance(data, list) else data.get("activity-log", data.get("data", []))
        log(f"Daily activity: {len(items)} entrée(s)")
        return items
    except Exception as e:
        log(f"fetch_daily_activity: {e} (normal si pas d'activité)")
        return []


# ─── VÉRIFICATION CONSOLIDATION LUNDI ────────────────────────
def check_and_run_consolidation():
    """
    Si on est lundi et que week_{semaine_precedente}.json n'existe pas encore,
    lance polar_consolidate.py avant la sync daily.
    Critère fiable : existence du fichier produit, pas un log.
    """
    from datetime import timedelta as _td
    today = datetime.now(timezone.utc).date()
    if today.weekday() != 0:  # 0 = lundi
        return

    last_week_key = (today - _td(days=7)).isoformat()
    weeks_dir = DATA_DIR / "weeks"
    already_done = (weeks_dir / f"week_{last_week_key}.json").exists()

    if already_done:
        log(f"Consolidation semaine {last_week_key} deja presente — skip")
        return

    log(f"LUNDI : week_{last_week_key}.json absent — lancement polar_consolidate.py")
    import subprocess
    try:
        r = subprocess.run(
            ["/root/venv/bin/python3", str(POLAR_DIR / "polar_consolidate.py")],
            capture_output=True, text=True, timeout=300
        )
        if r.returncode == 0:
            log(f"Consolidation terminee — week_{last_week_key}.json cree")
        else:
            log(f"ERREUR consolidation (code {r.returncode}) : {r.stderr[-300:]}")
    except Exception as e:
        log(f"ERREUR lancement polar_consolidate.py : {e}")


# ─── ENRICHISSEMENT NUIT ──────────────────────────────────────
def enrich_night(night):
    """Enrichit une nuit Polar API avec les champs calculés utiles pour le dashboard."""
    import re as _re
    n = dict(night)

    # Calculer FC nocturne depuis heart_rate_samples
    hr_samples = n.get("heart_rate_samples") or {}
    hr_vals = [v for v in hr_samples.values() if isinstance(v, (int, float)) and v > 20]
    if hr_vals:
        n["heart_rate_avg"] = round(sum(hr_vals) / len(hr_vals))
        n["heart_rate_min"] = min(hr_vals)

    # Calculer total_sleep_minutes depuis timestamps
    if not n.get("total_sleep_minutes"):
        t0 = n.get("sleep_start_time", "")
        t1 = n.get("sleep_end_time", "")
        if t0 and t1:
            try:
                from datetime import datetime as _dt
                def _parse(s):
                    s = _re.sub(r'(\.\d+)?([+-]\d{2}):(\d{2})$', r'\2\3', s)
                    for fmt in ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M%z"]:
                        try: return _dt.strptime(s, fmt)
                        except: pass
                    return None
                d0, d1 = _parse(t0), _parse(t1)
                if d0 and d1:
                    n["total_sleep_minutes"] = round((d1 - d0).total_seconds() / 60)
            except Exception:
                pass
        # Fallback : somme des phases (en secondes → minutes)
        if not n.get("total_sleep_minutes"):
            phases_s = sum(filter(None, [
                n.get("light_sleep"), n.get("deep_sleep"),
                n.get("rem_sleep"), n.get("total_interruption_duration", 0)
            ]))
            if phases_s > 0:
                n["total_sleep_minutes"] = round(phases_s / 60)

    # Mapper sleep_charge (int) → nightly_recharge_status (string lisible)
    charge_map = {1: "DEPLETED", 2: "COMPROMISED", 3: "SUSTAINED", 4: "RECOVERED"}
    if not n.get("nightly_recharge_status") and n.get("sleep_charge"):
        n["nightly_recharge_status"] = charge_map.get(n["sleep_charge"], "UNKNOWN")

    return n


# ─── MAIN ─────────────────────────────────────────────────────
def main():
    log("=============================================")
    log("POLAR DAILY SYNC — Collecte donnees")
    log("=============================================")

    if not ACCESS_TOKEN:
        log("ERREUR: POLAR_ACCESS_TOKEN manquant dans .env")
        return

    log(f"Token chargé: {ACCESS_TOKEN[:8]}...")

    # Vérifier et lancer la consolidation si nécessaire (lundi uniquement)
    check_and_run_consolidation()

    # Charger le user_id
    load_user_id()

    # Collecter les données
    exercises       = fetch_exercises(days_back=14)
    sleep_data      = fetch_sleep(days_back=14)
    recharge_data   = fetch_nightly_recharge(days_back=14)
    activity_data   = fetch_daily_activity(days_back=14)

    # Résumé
    n_run = sum(1 for e in exercises if e.get("sport") == "RUNNING")
    log(f"Total: {len(exercises)} séances dont {n_run} running")

    # Mettre à jour week_current.json avec les données de la semaine en cours
    from datetime import date
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    week_key = monday.strftime("%Y-%m-%d")
    week_current_file = DATA_DIR / "weeks" / "week_current.json"
    week_current_file.parent.mkdir(parents=True, exist_ok=True)
    week_exercises = [e for e in exercises if (e.get("date") or e.get("start_time",""))[:10] >= week_key]
    # Charger le programme pour corriger les distances natation
    prog_dir = POLAR_DIR / "programme"
    programme = {}
    if prog_dir.exists():
        for f in prog_dir.glob("semaine_*.json"):
            try:
                d = json.loads(f.read_text())
                sem_name = d.get("semaine", f.stem)
                programme[sem_name] = d
            except Exception:
                pass

    def get_week_key_d(date_str):
        """Retourne le lundi de la semaine d'une date ISO 'YYYY-MM-DD'."""
        from datetime import date as _date
        try:
            d = _date.fromisoformat(date_str[:10])
            return (d - timedelta(days=d.weekday())).isoformat()
        except Exception:
            return date_str[:10]

    # Corriger les distances natation dans week_exercises
    def correct_swim_distance(exercises, programme):
        """Remplace la distance API (souvent fausse) par la distance du programme."""
        corrected = []
        for ex in exercises:
            ex2 = dict(ex)
            sport = ex2.get("sport", "")
            if "SWIM" in sport.upper():
                ex_date = (ex2.get("start_time") or ex2.get("date",""))[:10]
                # Chercher la séance correspondante dans le programme
                for sem_data in programme.values():
                    for s in sem_data.get("seances", []):
                        if s.get("date") == ex_date and s.get("sport") == "Natation":
                            planned_m = s.get("dist_cible_m")
                            if planned_m:
                                api_dist = ex2.get("distance", 0) or 0
                                if abs(api_dist - planned_m) > 50:  # correction si écart > 50m
                                    ratio = planned_m / api_dist if api_dist > 0 else 1
                                    ex2["distance"] = planned_m
                                    ex2["_distance_corrected"] = True
                                    ex2["_distance_original"] = api_dist
                                    # Corriger calories et charge au prorata
                                    if ratio != 1:
                                        if ex2.get("calories"):
                                            ex2["calories"] = round(ex2["calories"] * ratio)
                                        tl = ex2.get("training_load_pro") or ex2.get("training-load-pro") or {}
                                        if isinstance(tl, dict) and tl.get("cardio-load"):
                                            tl2 = dict(tl)
                                            tl2["cardio-load"] = round(float(tl2["cardio-load"]) * ratio, 1)
                                            ex2["training_load_pro"] = tl2
                                    log(f"  🏊 Natation {ex_date}: {int(api_dist)}m → {planned_m}m (programme)")
                            break
            corrected.append(ex2)
        return corrected

    week_exercises = correct_swim_distance(week_exercises, programme)

    # Calculer le label de semaine depuis le programme
    sem_label = ""
    for sn, sd in programme.items():
        for s in sd.get("seances", []):
            if get_week_key_d(s["date"]) == week_key:
                try: sem_label = f"S{int(sn.strip().split()[-1])}"
                except: sem_label = sn
                break
        if sem_label: break

    # Archiver la semaine précédente si week_current.json existe et correspond à une semaine différente
    weeks_dir_p = DATA_DIR / "weeks"
    if week_current_file.exists():
        try:
            old_data = json.loads(week_current_file.read_text())
            old_wk = old_data.get("week_key", "")
            if old_wk and old_wk != week_key:
                # Archiver l'ancienne semaine
                archive_file = weeks_dir_p / f"week_{old_wk}.json"
                if not archive_file.exists():
                    week_current_file.read_bytes()  # lecture pour forcer flush
                    archive_file.write_text(
                        json.dumps(old_data, indent=2, ensure_ascii=False), encoding="utf-8")
                    log(f"  📦 Semaine {old_wk} archivée → {archive_file.name}")
        except Exception as e:
            log(f"  ⚠️ Archivage semaine précédente: {e}")

    week_data = {
        "week_key": week_key,
        "sem_label": sem_label,
        "generated": datetime.now(timezone.utc).isoformat(),
        "source": "polar_daily",
        "exercises": week_exercises,
        "sleep": [enrich_night(s) for s in (sleep_data or []) if s.get("date","")[:10] >= week_key],
        "recharge": [r for r in (recharge_data or []) if r.get("date","")[:10] >= week_key],
    }
    # Écriture atomique
    _tmp_wc = week_current_file.with_suffix(".tmp")
    _tmp_wc.write_text(json.dumps(week_data, indent=2, ensure_ascii=False), encoding="utf-8")
    _tmp_wc.replace(week_current_file)
    log(f"week_current.json mis à jour → {len(week_exercises)} séances semaine {week_key} ({sem_label or 'hors programme'})")

    # Vérifier que week_current.json est valide
    try:
        written = json.loads(week_current_file.read_text())
        if written.get("generated") and isinstance(written.get("exercises"), list):
            log("week_current.json validé ✓")
        else:
            log("⚠️ week_current.json semble invalide — vérifier manuellement")
    except Exception as e:
        log(f"⚠️ Erreur lecture week_current.json après écriture: {e}")

    log("=============================================")
    log("SYNC QUOTIDIENNE TERMINÉE")
    log("=============================================")


if __name__ == "__main__":
    main()
