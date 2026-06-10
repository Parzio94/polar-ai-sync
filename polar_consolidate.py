#!/usr/bin/env python3
"""
polar_consolidate.py — Consolidation hebdomadaire Polar

Lit les sync_*.json → génère /root/polar/data/weeks/week_YYYY-MM-DD.json

Format week_*.json :
  exercises[] → running, swimming, cycling avec tous les champs
    - splits: [{km, pace, hr_avg, hr_min, hr_max, cadence_spm, d_plus, d_minus, d_net}]
  sleep[]     → score, durée, cycles, phases, FC noc., respiration

Usage :
  python3 polar_consolidate.py               # consolide toutes les semaines passées
  python3 polar_consolidate.py --force       # re-génère même si fichier existe
  python3 polar_consolidate.py --week 2026-02-17  # une semaine précise
  python3 polar_consolidate.py --current     # inclut semaine courante

FIXES v2:
  - Backup automatique de week_current.json AVANT toute opération
  - Fusion des données de week_current.json dans load_week_data()
    pour ne plus perdre les données en fin de semaine
  - Garde-fou renforcé : conserve le fichier existant si plus riche
"""

import os, json, sys, re, time, shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv("/root/polar/.env")
except ImportError:
    pass

# ─── CONFIG ────────────────────────────────────────────────────────────────────
DATA_DIR  = Path(os.getenv("POLAR_DATA_DIR", "/root/polar/data"))
WEEKS_DIR = DATA_DIR / "weeks"
WEEKS_DIR.mkdir(parents=True, exist_ok=True)

TOKEN = os.getenv("POLAR_ACCESS_TOKEN", "")
BASE  = "https://www.polaraccesslink.com"

FORCE      = "--force"   in sys.argv
DO_CURRENT = "--current" in sys.argv
WEEK_ARG   = None
for i, a in enumerate(sys.argv[1:]):
    if a == "--week" and i + 2 < len(sys.argv):
        WEEK_ARG = sys.argv[i + 2]
        break

# ─── HELPERS ───────────────────────────────────────────────────────────────────

def log(msg): print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def week_monday(date_str):
    try:
        d = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
        return (d - timedelta(days=d.weekday())).strftime("%Y-%m-%d")
    except:
        return None

def parse_duration(s):
    if not s: return 0
    m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?', str(s))
    if not m: return 0
    return int(m.group(1) or 0)*3600 + int(m.group(2) or 0)*60 + float(m.group(3) or 0)

def pace_run(dist_m, dur_s):
    if not dist_m or not dur_s or dist_m < 50: return None
    p = dur_s / dist_m * 1000
    return f"{int(p//60)}:{int(p%60):02d}"

def pace_swim(dist_m, dur_s):
    if not dist_m or not dur_s or dist_m < 20: return None
    p = dur_s / dist_m * 100
    return f"{int(p//60)}:{int(p%60):02d}"

def speed_bike(dist_m, dur_s):
    if not dist_m or not dur_s: return None
    return round(dist_m / dur_s * 3.6, 1)

def fmt_hm(s):
    if not s: return None
    s = int(s)
    h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    if h: return f"{h}h {m:02d}min" + (f" {sec:02d}s" if sec else "")
    return f"{m}min {sec:02d}s" if sec else f"{m}min"

def is_within_30_days(start_time_str):
    try:
        st = datetime.strptime(str(start_time_str)[:19], "%Y-%m-%dT%H:%M:%S")
        return (datetime.now() - st).days <= 28
    except:
        return False

# ─── FIX 1 : BACKUP week_current.json ─────────────────────────────────────────

def backup_week_current():
    """
    Sauvegarde week_current.json avec horodatage AVANT toute consolidation.
    Conserve les 7 derniers backups.
    """
    src = WEEKS_DIR / "week_current.json"
    if not src.exists():
        return
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = WEEKS_DIR / f"week_current_backup_{ts}.json"
    shutil.copy2(src, dst)
    log(f"📦 Backup week_current → {dst.name}")

    # Nettoyer les vieux backups (garder les 7 derniers)
    backups = sorted(WEEKS_DIR.glob("week_current_backup_*.json"), reverse=True)
    for old in backups[7:]:
        old.unlink()
        log(f"🗑  Ancien backup supprimé : {old.name}")

# ─── FIX 2 : FUSION week_current dans load_week_data ──────────────────────────

def load_week_current_exercises():
    """
    Lit week_current.json et retourne ses exercices sous forme normalisée,
    indexés par (start_time[:16], sport) pour déduplication.
    """
    src = WEEKS_DIR / "week_current.json"
    if not src.exists():
        return {}
    try:
        d = json.loads(src.read_text())
        result = {}
        for ex in d.get("exercises", []):
            # week_current stocke déjà le format snake_case consolidé
            # On reconstitue un pseudo-raw compatible avec normalize_ex
            st   = ex.get("start_time", ex.get("start-time", ""))
            sport = ex.get("sport", "")
            if not st: continue
            slot = (st[:16], sport.upper())
            # Marquer comme provenant de week_current pour priorité
            ex["_from_week_current"] = True
            result[slot] = ex
        log(f"  📂 week_current.json : {len(result)} exercices chargés")
        return result
    except Exception as e:
        log(f"  ⚠ Erreur lecture week_current.json : {e}")
        return {}

def load_week_current_sleep(start_str, end_str):
    """
    Lit sleep + recharge de week_current.json pour la période donnée.
    """
    src = WEEKS_DIR / "week_current.json"
    if not src.exists():
        return [], {}
    try:
        d = json.loads(src.read_text())
        sleep = [n for n in d.get("sleep", [])
                 if start_str <= n.get("date","")[:10] < end_str]
        recharge = {}
        for r in d.get("recharge", d.get("nightly_recharge", [])):
            dt = r.get("date","")[:10]
            if dt and start_str <= dt < end_str:
                recharge[dt] = r
        return sleep, recharge
    except Exception as e:
        log(f"  ⚠ Erreur lecture sleep week_current.json : {e}")
        return [], {}

def normalize_ex(ex):
    if not isinstance(ex, dict): return ex
    e = dict(ex)
    if not e.get("start_time") and e.get("start-time"):
        e["start_time"] = e["start-time"]
    if not e.get("heart_rate") and e.get("heart-rate"):
        e["heart_rate"] = e["heart-rate"]
    tl = e.get("training_load_pro") or e.get("training-load-pro") or {}
    if tl:
        e["training_load_pro"] = tl
    if e.get("running-index") is not None and e.get("running_index") is None:
        e["running_index"] = e["running-index"]
    if e.get("fat-percentage") is not None and e.get("fat_percentage") is None:
        e["fat_percentage"] = e["fat-percentage"]
    if e.get("carbohydrate-percentage") is not None and e.get("carbohydrate_percentage") is None:
        e["carbohydrate_percentage"] = e["carbohydrate-percentage"]
    if e.get("has-route") is not None and e.get("has_route") is None:
        e["has_route"] = e["has-route"]
    e["_sport"] = (e.get("detailed_sport_info") or e.get("detailed-sport-info") or e.get("sport") or "").upper()
    raw_splits = e.get("_splits_km") or []
    e["_splits_ok"] = [{
        "km":          s.get("km"),
        "pace":        s.get("pace"),
        "hr_avg":      s.get("hr_avg"),
        "hr_min":      s.get("hr_min"),
        "hr_max":      s.get("hr_max"),
        "cadence_spm": int(s["cadence"]*2) if s.get("cadence") else None,
        "d_plus":      s.get("d_plus"),
        "d_minus":     s.get("d_minus"),
        "d_net":       round((s.get("d_plus") or 0) - (s.get("d_minus") or 0), 1),
    } for s in raw_splits]

    if e.get("_samples"):
        try:
            raw = e["_samples"].get("raw", [])
            if raw:
                sd = parse_samples(raw)
                sport = e.get("_sport", e.get("sport", ""))
                splits, summary, elevation = compute_splits(sd, sport)
                if splits:
                    e["_splits_ok"] = splits
        except Exception:
            pass

    return e

# ─── API SAMPLES ───────────────────────────────────────────────────────────────

def api_fetch(exercise_id):
    import urllib.request
    if not TOKEN: return None
    url = f"{BASE}/v3/exercises/{exercise_id}?samples=true"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json"
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except Exception as e:
        log(f"    ⚠ API {exercise_id}: HTTP {getattr(e,'code','?')}")
        return None

def parse_samples(raw_samples):
    result = {}
    for s in (raw_samples or []):
        t, raw, rate = s.get("sample_type"), s.get("data",""), float(s.get("recording_rate",1))
        if t is None or not raw: continue
        try:
            result[int(t)] = {"data": [float(v) if v.strip() else 0.0 for v in str(raw).split(",")], "rate": rate}
        except: pass
    return result

def compute_splits(sd, sport="RUNNING"):
    def s(t): return sd.get(t, {}).get("data", []) if isinstance(sd.get(t), dict) else []
    def r(t): return sd.get(t, {}).get("rate", 1.0) if isinstance(sd.get(t), dict) else 1.0

    dist, hr, cad, alt, pwr = s(10), s(0), s(2), s(3), s(4)
    rate = r(10) or r(0) or 1.0
    n = len(dist)
    if not dist or max(dist) < 200: return [], {}, {}

    splits, km, km_start, km_target = [], 1, 0, 1000.0

    def seg(i0, i1, actual_m=None):
        np = i1 - i0
        if np <= 0: return None
        dur = np * rate
        d_seg = actual_m if (actual_m and actual_m > 10) else max(dist[i1-1] - dist[i0], 1)

        if sport == "RUNNING":
            ps = dur / d_seg * 1000 if d_seg > 10 else 0
            allure = f"{int(ps//60)}:{int(ps%60):02d}" if ps > 0 else None
        elif sport == "CYCLING":
            ps = dur / d_seg * 1000 if d_seg > 10 else 0
            kmh = round(3600/ps, 1) if ps > 0 else None
            allure = f"{kmh}" if kmh else None
        else:
            allure = None

        hr_v   = [hr[j]  for j in range(i0, i1) if j < len(hr)  and hr[j] > 30]
        cad_v  = [cad[j] for j in range(i0, i1) if j < len(cad) and cad[j] > 0]
        pwr_v  = [pwr[j] for j in range(i0, i1) if j < len(pwr) and pwr[j] > 0]
        dplus = dminus = 0.0
        if len(alt) >= i1:
            for j in range(i0+1, i1):
                diff = alt[j] - alt[j-1]
                if diff > 0.05:    dplus  += diff
                elif diff < -0.05: dminus += abs(diff)

        out = {
            "pace":        allure,
            "hr_avg":      round(sum(hr_v)/len(hr_v))  if hr_v  else None,
            "hr_min":      round(min(hr_v))  if hr_v  else None,
            "hr_max":      round(max(hr_v))  if hr_v  else None,
            "cadence_spm": round(sum(cad_v)/len(cad_v)*2) if cad_v else None,
            "d_plus":      round(dplus,  1) if dplus  > 0.2 else None,
            "d_minus":     round(dminus, 1) if dminus > 0.2 else None,
            "d_net":       round(dplus - dminus, 1),
        }
        if pwr_v:
            out["power_avg"] = round(sum(pwr_v)/len(pwr_v))
            out["power_max"] = round(max(pwr_v))
        return out

    for i in range(1, n):
        if dist[i] >= km_target:
            s_data = seg(km_start, i)
            if s_data:
                splits.append({"km": km, **s_data})
            km_start, km, km_target = i, km+1, (km+1)*1000.0
            if km_target > max(dist) + 300: break

    if n > km_start + 10:
        pm = dist[n-1] - dist[km_start]
        if pm > 100:
            s_data = seg(km_start, n, pm)
            if s_data:
                splits.append({"km": f"{km}*", **s_data})

    if not splits: return [], {}, {}

    hr_all  = [hr[j]  for j in range(n) if j < len(hr)  and hr[j] > 30]
    cad_all = [cad[j] for j in range(n) if j < len(cad) and cad[j] > 0]
    pwr_all = [pwr[j] for j in range(n) if j < len(pwr) and pwr[j] > 0]

    paces_s = []
    for sp in splits:
        p = str(sp.get("pace",""))
        if ":" in p:
            try: parts = p.split(":"); paces_s.append(int(parts[0])*60+int(parts[1]))
            except: pass

    hr_zones = None
    if sport == "SWIMMING" and hr_all:
        fcm = max(hr_all)
        zn = {"z1":0,"z2":0,"z3":0,"z4":0,"z5":0}
        for v in hr_all:
            ratio = v/fcm if fcm else 0
            if ratio < 0.60:   zn["z1"] += rate
            elif ratio < 0.70: zn["z2"] += rate
            elif ratio < 0.80: zn["z3"] += rate
            elif ratio < 0.90: zn["z4"] += rate
            else:              zn["z5"] += rate
        hr_zones = {k: round(v/60, 1) for k, v in zn.items() if v > 0}

    summary = {
        "pace_avg":    f"{round(sum(paces_s)/len(paces_s))//60}:{round(sum(paces_s)/len(paces_s))%60:02d}" if paces_s else None,
        "pace_best":   f"{min(paces_s)//60}:{min(paces_s)%60:02d}" if paces_s else None,
        "hr_avg":      round(sum(hr_all)/len(hr_all))  if hr_all  else None,
        "hr_max":      max(hr_all)  if hr_all  else None,
        "cadence_avg": round(sum(cad_all)/len(cad_all)*2) if cad_all else None,
        "cadence_max": round(max(cad_all)*2) if cad_all else None,
        "power_avg":   round(sum(pwr_all)/len(pwr_all)) if pwr_all else None,
        "power_max":   round(max(pwr_all)) if pwr_all else None,
        "hr_zones_min":hr_zones,
    }

    elevation = {
        "d_plus":  round(sum((sp.get("d_plus")  or 0) for sp in splits), 1) or None,
        "d_minus": round(sum((sp.get("d_minus") or 0) for sp in splits), 1) or None,
    }
    return splits, summary, elevation

# ─── BUILD EXERCICE ────────────────────────────────────────────────────────────

def build_exercise(ex_raw):
    ex = normalize_ex(ex_raw)
    sport   = ex["_sport"]
    st      = ex.get("start_time","")
    ex_id   = ex.get("id","")
    dur_s   = int(parse_duration(ex.get("duration","")) or ex.get("duration_s", 0))
    dist_m  = int(ex.get("distance") or ex.get("distance_m") or 0)
    hr      = ex.get("heart_rate") or {}
    tl      = ex.get("training_load_pro") or {}
    kcal    = ex.get("calories") or ex.get("kcal") or 0
    fat_p   = int(ex.get("fat_percentage") or 0)
    carb_p  = int(ex.get("carbohydrate_percentage") or 0)
    has_rt  = bool(ex.get("has_route"))

    cl = tl.get("cardio-load") or tl.get("cardio_load") or tl.get("cardio-load") or 0
    ml = tl.get("muscle-load") or tl.get("muscle_load") or -1
    cardio_load = round(float(cl), 1) if cl else None
    muscle_load = round(float(ml), 1) if ml and float(ml) > 0 else None

    # Si l'exercice vient de week_current (déjà consolidé), on peut
    # récupérer hr_avg/hr_max directement depuis les champs plats
    if isinstance(hr, dict):
        hr_avg = hr.get("average") or hr.get("avg")
        hr_max = hr.get("maximum") or hr.get("max")
    else:
        hr_avg = ex.get("hr_avg")
        hr_max = ex.get("hr_max")

    base = {
        "id":                ex_id,
        "start_time":        st,
        "date":              st[:10],
        "sport":             sport,
        "device":            ex.get("device","Polar Pacer Pro"),
        "duration_s":        dur_s,
        "duration":          fmt_hm(dur_s),
        "distance_m":        dist_m,
        "hr_avg":            hr_avg,
        "hr_max":            hr_max,
        "kcal":              kcal or None,
        "kcal_carb":         round(kcal*carb_p/100) if kcal and carb_p else None,
        "kcal_fat":          round(kcal*fat_p/100)  if kcal and fat_p  else None,
        "kcal_carb_pct":     carb_p or None,
        "kcal_fat_pct":      fat_p  or None,
        "cardio_load":       cardio_load,
        "cardio_load_level": tl.get("cardio-load-interpretation") or tl.get("cardio_load_interpretation"),
        "muscle_load":       muscle_load,
        "muscle_load_level": (tl.get("muscle-load-interpretation") or tl.get("muscle_load_interpretation")) if muscle_load else None,
    }

    # ── RUNNING ─────────────────────────────────────────────────
    if "RUNNING" in sport:
        base["distance_km"] = round(dist_m/1000, 2)
        base["vo2max"]      = ex.get("running_index") or ex.get("vo2max")
        base["power_avg"]   = ex.get("power_avg") or (ex.get("_samples_summary") or {}).get("pwr_avg")
        base["power_max"]   = ex.get("power_max")

        # Si vient de week_current, récupérer les splits déjà calculés
        splits_ok = ex.get("splits") or ex["_splits_ok"]
        if splits_ok:
            paces_s = []
            for sp in splits_ok:
                p = str(sp.get("pace",""))
                if ":" in p:
                    try: parts = p.split(":"); paces_s.append(int(parts[0])*60+int(parts[1]))
                    except: pass
            if paces_s:
                avg_s  = round(sum(paces_s)/len(paces_s))
                best_s = min(paces_s)
                base["pace_avg"]  = f"{avg_s//60}:{avg_s%60:02d}"
                base["pace_best"] = f"{best_s//60}:{best_s%60:02d}"
            else:
                base["pace_avg"]  = ex.get("pace_avg") or pace_run(dist_m, dur_s)
                base["pace_best"] = ex.get("pace_best")
            cads = [sp.get("cadence_spm") or sp.get("cadence") for sp in splits_ok]
            cads = [c for c in cads if c]
            base["cadence_avg"]      = round(sum(cads)/len(cads)) if cads else ex.get("cadence_avg")
            base["cadence_max"]      = max(cads) if cads else ex.get("cadence_max")
            base["elevation_up_m"]   = ex.get("elevation_up_m") or (round(sum((sp.get("d_plus") or 0) for sp in splits_ok), 1) or None)
            base["elevation_down_m"] = ex.get("elevation_down_m") or (round(sum((sp.get("d_minus") or 0) for sp in splits_ok), 1) or None)
            pwrs = [sp["power_avg"] for sp in splits_ok if sp.get("power_avg")]
            base["power_avg"] = base["power_avg"] or (round(sum(pwrs)/len(pwrs)) if pwrs else None)
            base["power_max"] = base["power_max"] or (max(sp.get("power_max",0) or 0 for sp in splits_ok) or None)
            base["splits"] = splits_ok
        else:
            base["pace_avg"]         = ex.get("pace_avg") or pace_run(dist_m, dur_s)
            base["pace_best"]        = ex.get("pace_best")
            base["cadence_avg"]      = ex.get("cadence_avg")
            base["cadence_max"]      = ex.get("cadence_max")
            base["elevation_up_m"]   = ex.get("elevation_up_m")
            base["elevation_down_m"] = ex.get("elevation_down_m")
            base["splits"]           = []

            if ex_id and is_within_30_days(st):
                log(f"    → Fetch samples API {ex_id}")
                time.sleep(0.4)
                data = api_fetch(ex_id)
                if data and data.get("samples"):
                    sd = parse_samples(data["samples"])
                    splits, summary, elevation = compute_splits(sd, "RUNNING")
                    if splits:
                        base["splits"]           = splits
                        base["pace_best"]        = summary.get("pace_best")
                        base["cadence_avg"]      = summary.get("cadence_avg")
                        base["cadence_max"]      = summary.get("cadence_max")
                        base["elevation_up_m"]   = elevation.get("d_plus")
                        base["elevation_down_m"] = elevation.get("d_minus")
                        base["power_avg"]        = summary.get("power_avg")
                        base["power_max"]        = summary.get("power_max")
                        log(f"    ✓ {len(splits)} splits | D+{elevation.get('d_plus')}m | cad {summary.get('cadence_avg')} spm")

    # ── SWIMMING ────────────────────────────────────────────────
    elif "SWIM" in sport or "POOL" in sport:
        base["pace_100m"]    = ex.get("pace_100m") or pace_swim(dist_m, dur_s)
        base["hr_zones_min"] = ex.get("hr_zones_min")

        if not base["hr_zones_min"] and ex_id and is_within_30_days(st):
            log(f"    → Fetch zones FC piscine {ex_id}")
            time.sleep(0.4)
            data = api_fetch(ex_id)
            if data and data.get("samples"):
                sd = parse_samples(data["samples"])
                hr_data = sd.get(0, {}).get("data", [])
                if hr_data:
                    rate_hr = sd.get(0, {}).get("rate", 1.0)
                    fcm = max(hr_data)
                    zn = {"z1":0,"z2":0,"z3":0,"z4":0,"z5":0}
                    for v in hr_data:
                        ratio = v/fcm if fcm else 0
                        if ratio < 0.60:   zn["z1"] += rate_hr
                        elif ratio < 0.70: zn["z2"] += rate_hr
                        elif ratio < 0.80: zn["z3"] += rate_hr
                        elif ratio < 0.90: zn["z4"] += rate_hr
                        else:              zn["z5"] += rate_hr
                    base["hr_zones_min"] = {k: round(v/60,1) for k,v in zn.items() if v > 0}
                    log(f"    ✓ Zones FC : {base['hr_zones_min']}")

    # ── CYCLING ─────────────────────────────────────────────────
    elif "CYCL" in sport:
        base["distance_km"]   = round(dist_m/1000, 2)
        base["speed_avg_kmh"] = ex.get("speed_avg_kmh") or speed_bike(dist_m, dur_s)
        base["speed_max_kmh"] = ex.get("speed_max_kmh")
        base["elevation_up_m"]   = ex.get("elevation_up_m")
        base["elevation_down_m"] = ex.get("elevation_down_m")
        base["splits"]        = ex.get("splits") or []
        base["power_avg"]     = ex.get("power_avg")
        base["power_max"]     = ex.get("power_max")

        if not base["splits"] and ex_id and is_within_30_days(st):
            log(f"    → Fetch samples vélo {ex_id}")
            time.sleep(0.4)
            data = api_fetch(ex_id)
            if data and data.get("samples"):
                sd = parse_samples(data["samples"])
                splits, summary, elevation = compute_splits(sd, "CYCLING")
                if splits:
                    speeds = []
                    for sp in splits:
                        p = str(sp.get("pace",""))
                        if p:
                            try: speeds.append(float(p))
                            except: pass
                    base["splits"]           = splits
                    base["speed_max_kmh"]    = round(max(speeds), 1) if speeds else None
                    base["elevation_up_m"]   = elevation.get("d_plus")
                    base["elevation_down_m"] = elevation.get("d_minus")
                    base["power_avg"]        = summary.get("power_avg")
                    base["power_max"]        = summary.get("power_max")
                    log(f"    ✓ {len(splits)} splits vélo | D+{elevation.get('d_plus')}m")

    return base

# ─── BUILD NUIT ────────────────────────────────────────────────────────────────

def build_night(night, recharge_map):
    date = night.get("date","")[:10]
    rc   = recharge_map.get(date, {})

    def s2min(v):
        try: return round(float(v)/60) if v else None
        except: return None

    def calc_total():
        try:
            t0 = night.get("sleep_start_time","")
            t1 = night.get("sleep_end_time","")
            if t0 and t1:
                import re
                def pdt(s):
                    s = re.sub(r'([+-]\d{2}):(\d{2})$', r'+\1\2', s)
                    for fmt in ["%Y-%m-%dT%H:%M:%S.%f%z","%Y-%m-%dT%H:%M:%S%z"]:
                        try: return datetime.strptime(s, fmt)
                        except: pass
                    return None
                d0, d1 = pdt(t0), pdt(t1)
                if d0 and d1:
                    return (d1 - d0).total_seconds()
        except: pass
        phases_s = sum(filter(None, [
            night.get("light_sleep"), night.get("deep_sleep"),
            night.get("rem_sleep"), night.get("unrecognized_sleep_stage",0),
            night.get("total_interruption_duration",0)
        ]))
        return phases_s if phases_s > 0 else None

    hr_samples = night.get("heart_rate_samples") or {}
    hr_vals = [v for v in hr_samples.values() if v and v > 20]
    hr_avg_calc = round(sum(hr_vals)/len(hr_vals)) if hr_vals else None
    hr_min_calc = min(hr_vals) if hr_vals else None

    total_s = calc_total()

    return {
        "date":           date,
        "score":          night.get("sleep_score"),
        "duration":       fmt_hm(total_s),
        "total_min":      round(total_s/60) if total_s else None,
        "cycles":         night.get("sleep_cycles"),
        "phases": {
            "light_min":         s2min(night.get("light_sleep")),
            "deep_min":          s2min(night.get("deep_sleep")),
            "rem_min":           s2min(night.get("rem_sleep")),
            "interruptions_min": s2min(night.get("total_interruption_duration")),
        },
        "hr_avg":         hr_avg_calc or rc.get("heart_rate_avg"),
        "hr_min":         hr_min_calc or rc.get("heart_rate_min"),
        "breathing_avg":  rc.get("breathing_rate_avg"),
        "hrv_sdnn":       rc.get("hrv_sdnn"),
        "recharge_status":night.get("sleep_charge") or rc.get("nightly_recharge_status"),
        "recharge_score": rc.get("score"),
        "sleep_start_time": night.get("sleep_start_time"),
        "sleep_end_time":   night.get("sleep_end_time"),
    }

# ─── CHARGEMENT DONNÉES ────────────────────────────────────────────────────────

def load_week_data(week_key):
    d_start   = datetime.strptime(week_key, "%Y-%m-%d")
    d_end     = d_start + timedelta(days=7)
    start_str = d_start.strftime("%Y-%m-%d")
    end_str   = d_end.strftime("%Y-%m-%d")

    raw_by_slot = {}
    sl_seen  = set()
    sleep    = []
    recharge = {}

    # ── SOURCE 1 : sync_*.json (source historique)
    for f in sorted(DATA_DIR.glob("sync_*.json"), reverse=True):
        try:
            txt = f.read_text().strip()
            if not txt: continue
            d = json.loads(txt)
            for ex in (d.get("exercises") or d.get("new_exercises") or []):
                ex = normalize_ex(ex)
                st     = (ex.get("start_time") or "")
                st_day = st[:10]
                if not st_day or not (start_str <= st_day < end_str): continue
                sport  = ex.get("_sport","")
                slot   = (st[:16], sport)
                raw_by_slot.setdefault(slot, []).append(ex)
            for n in (d.get("sleep") or []):
                dt = n.get("date","")[:10]
                if not dt or not (start_str <= dt < end_str) or dt in sl_seen: continue
                sl_seen.add(dt); sleep.append(n)
            for r in (d.get("recharge") or d.get("nightly_recharge") or []):
                dt = r.get("date","")[:10]
                if dt and start_str <= dt < end_str and dt not in recharge:
                    recharge[dt] = r
        except Exception as e:
            log(f"  ⚠ {f.name}: {e}")

    # ── SOURCE 2 : week_current.json (FIX — évite la perte de données fin de semaine)
    wc_exercises = load_week_current_exercises()
    wc_sleep, wc_recharge = load_week_current_sleep(start_str, end_str)

    for slot, ex in wc_exercises.items():
        st_day = slot[0][:10]
        if not (start_str <= st_day < end_str): continue
        if slot not in raw_by_slot:
            # Données présentes dans week_current mais absentes des sync_*.json
            log(f"  🔄 Récupéré depuis week_current : {slot[0]} {slot[1]}")
            raw_by_slot[slot] = [ex]
        # Si déjà présent dans sync, week_current sert de fallback — on ne remplace pas

    for n in wc_sleep:
        dt = n.get("date","")[:10]
        if dt and dt not in sl_seen:
            log(f"  🔄 Nuit récupérée depuis week_current : {dt}")
            sl_seen.add(dt)
            sleep.append(n)

    for dt, r in wc_recharge.items():
        if dt not in recharge:
            recharge[dt] = r

    def best(cands):
        return max(cands, key=lambda e: (
            1 if e.get("_from_week_current") else 0,  # week_current prioritaire si seule source
            1 if e.get("_samples") else 0,
            1 if e.get("_splits_km") else 0,
            1 if not str(e.get("id","")).isdigit() else 0
        ))

    exercises = [best(v) for k,v in sorted(raw_by_slot.items())]
    sleep.sort(key=lambda n: n.get("date",""))
    return exercises, sleep, recharge

# ─── CONSOLIDATION ─────────────────────────────────────────────────────────────

def consolidate_week(week_key, force=False):
    out = WEEKS_DIR / f"week_{week_key}.json"
    if out.exists() and not force:
        log(f"⏭  {week_key} déjà consolidé (--force pour refaire)")
        return False

    log(f"\n{'='*52}\nCONSOLIDATION : {week_key}")
    ex_raw, sl_raw, rc_map = load_week_data(week_key)
    log(f"Données brutes : {len(ex_raw)} exercices | {len(sl_raw)} nuits")

    if not ex_raw and not sl_raw:
        log("⚠ Aucune donnée — semaine ignorée")
        return False

    exercises_out = []
    for ex in ex_raw:
        sport = ex.get("_sport","")
        st    = ex.get("start_time","")
        ex_id = ex.get("id","")
        log(f"  [{sport}] {st[:16]} {ex_id}")
        try:
            exercises_out.append(build_exercise(ex))
        except Exception as e:
            log(f"  ❌ {ex_id}: {e}")

    sleep_out = []
    for n in sl_raw:
        try:
            sleep_out.append(build_night(n, rc_map))
        except Exception as e:
            log(f"  ❌ nuit {n.get('date','')}: {e}")

    runs  = [e for e in exercises_out if "RUNNING" in (e.get("sport",""))]
    swims = [e for e in exercises_out if "SWIM"    in (e.get("sport",""))]
    bikes = [e for e in exercises_out if "CYCL"    in (e.get("sport",""))]
    km_r  = sum(e.get("distance_km",0) for e in runs)

    # Calculer sem_label depuis programme
    sem_label = ""
    try:
        prog_dir = Path("/root/polar/programme")
        if prog_dir.exists():
            for pf in prog_dir.glob("semaine_*.json"):
                pd = json.loads(pf.read_text())
                for s in pd.get("seances", []):
                    wk_s = week_monday(s.get("date",""))
                    if wk_s == week_key:
                        sn = pd.get("semaine", pf.stem)
                        try: sem_label = f"S{int(sn.strip().split()[-1])}"
                        except: sem_label = sn
                        break
                if sem_label: break
    except Exception as e:
        log(f"  sem_label erreur: {e}")

    week_data = {
        "week_key":     week_key,
        "sem_label":    sem_label or None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "nb_running": len(runs), "nb_swimming": len(swims),
            "nb_cycling": len(bikes), "nb_nights": len(sleep_out),
            "km_running": round(km_r, 2),
        },
        "exercises": exercises_out,
        "sleep":     sleep_out,
    }

    # ── F7 : Injection résumé nutritionnel ──────────────────────
    try:
        nutr_log_f = Path("/root/polar/nutrition_log.json")
        if nutr_log_f.exists():
            nutr_log = json.loads(nutr_log_f.read_text())
            d_start_dt = datetime.strptime(week_key, "%Y-%m-%d")
            d_end_dt   = d_start_dt + timedelta(days=7)
            week_entries = [
                e for e in nutr_log
                if start_str <= e.get("date","") < end_str
            ]
            if week_entries:
                dinners  = [e for e in week_entries if e.get("meal","dinner") == "dinner"]
                lunches  = [e for e in week_entries if e.get("meal") == "lunch"]
                all_days = dinners + lunches

                def safe_sum(lst, key):
                    return round(sum(float(e.get(key,0) or 0) for e in lst), 1)

                n_days = len({e["date"] for e in all_days})
                tot_k  = safe_sum(all_days, "kcal")
                tot_p  = safe_sum(all_days, "prot_g")
                tot_c  = safe_sum(all_days, "carb_g")
                tot_f  = safe_sum(all_days, "fat_g")

                week_data["nutrition"] = {
                    "jours_avec_data": n_days,
                    "kcal_total":  int(tot_k),
                    "kcal_moy_j":  round(tot_k / n_days) if n_days else 0,
                    "prot_total_g": tot_p,
                    "prot_moy_j":  round(tot_p / n_days, 1) if n_days else 0,
                    "carb_total_g": tot_c,
                    "carb_moy_j":  round(tot_c / n_days, 1) if n_days else 0,
                    "fat_total_g":  tot_f,
                    "fat_moy_j":   round(tot_f / n_days, 1) if n_days else 0,
                    "dejeuners": [
                        {"date": e["date"], "kcal": e.get("kcal",0),
                         "prot_g": e.get("prot_g",0), "carb_g": e.get("carb_g",0),
                         "fat_g": e.get("fat_g",0)}
                        for e in sorted(lunches, key=lambda x: x["date"])
                    ],
                    "diners": [
                        {"date": e["date"], "label": e.get("label",""), "kcal": e.get("kcal",0),
                         "prot_g": e.get("prot_g",0), "carb_g": e.get("carb_g",0),
                         "fat_g": e.get("fat_g",0)}
                        for e in sorted(dinners, key=lambda x: x["date"])
                    ],
                }
                log(f"  🥗 Nutrition injectée : {n_days} jours | {int(tot_k)} kcal total")
    except Exception as e:
        log(f"  ⚠ Nutrition non injectée : {e}")

    # ── Garde-fou renforcé : ne pas écraser si moins d'exercices ET moins de nuits
    if out.exists() and not force:
        try:
            existing = json.loads(out.read_text())
            ex_existing  = len(existing.get("exercises", []))
            sl_existing  = len(existing.get("sleep", []))
            ex_new       = len(exercises_out)
            sl_new       = len(sleep_out)
            if ex_existing > ex_new or sl_existing > sl_new:
                log(f"⚠ Garde-fou : existant={ex_existing}ex/{sl_existing}nuits vs nouveau={ex_new}ex/{sl_new}nuits")
                log(f"⚠ Fichier conservé tel quel. Utilise --force pour forcer.")
                return False
        except Exception:
            pass

    out.write_text(json.dumps(week_data, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"✅ {out.name} | 🏃{len(runs)}({km_r:.1f}km) 🏊{len(swims)} 🚴{len(bikes)} 🌙{len(sleep_out)}")
    return True

def purge_old_syncs(days=14):
    cutoff = datetime.now() - timedelta(days=days)
    consolidated = {f.stem.replace("week_","") for f in WEEKS_DIR.glob("week_*.json")}
    deleted = 0
    for f in DATA_DIR.glob("sync_*.json"):
        try:
            parts = f.stem.split("_")
            if len(parts) >= 2:
                file_date = datetime.strptime(parts[1], "%Y%m%d")
                if file_date >= cutoff:
                    continue
                week_key = week_monday(file_date.strftime("%Y-%m-%d"))
                if week_key in consolidated:
                    f.unlink()
                    deleted += 1
        except Exception:
            pass
    if deleted:
        log(f"🗑  {deleted} sync(s) supprimé(s) (> {days}j)")

# ─── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    log("POLAR CONSOLIDATE v2 — Consolidation hebdomadaire")
    if not TOKEN: log("⚠️  POLAR_ACCESS_TOKEN manquant → API samples désactivée")

    current_wk = week_monday(datetime.now().strftime("%Y-%m-%d"))

    # ── FIX 1 : Backup SYSTÉMATIQUE de week_current avant toute opération
    backup_week_current()

    if WEEK_ARG:
        consolidate_week(week_monday(WEEK_ARG) or WEEK_ARG, force=FORCE)
        return

    all_weeks = set()
    for f in DATA_DIR.glob("sync_*.json"):
        try:
            d = json.loads(f.read_text().strip() or "{}")
            for ex in (d.get("exercises") or d.get("new_exercises") or []):
                ex = normalize_ex(ex)
                wk = week_monday((ex.get("start_time") or "")[:10])
                if wk: all_weeks.add(wk)
            for n in (d.get("sleep") or []):
                wk = week_monday(n.get("date","")[:10])
                if wk: all_weeks.add(wk)
        except: pass

    # ── FIX 2 : Inclure aussi les semaines présentes dans week_current
    try:
        wc = json.loads((WEEKS_DIR / "week_current.json").read_text())
        for ex in wc.get("exercises", []):
            st = ex.get("start_time","")[:10]
            wk = week_monday(st)
            if wk: all_weeks.add(wk)
        for n in wc.get("sleep", []):
            wk = week_monday(n.get("date","")[:10])
            if wk: all_weeks.add(wk)
    except: pass

    if not DO_CURRENT: all_weeks.discard(current_wk)
    log(f"\n{len(all_weeks)} semaines à traiter" + (" (semaine courante exclue)" if not DO_CURRENT else ""))

    count = sum(1 for wk in sorted(all_weeks, reverse=True) if consolidate_week(wk, force=FORCE))
    log(f"\n✅ {count} semaine(s) consolidée(s)")
    if count == 0 and not FORCE:
        log("  → Toutes déjà consolidées. Utilise --force pour re-générer.")

    cleanup_splits_cache()


def cleanup_splits_cache(keep=30):
    """Supprime les fichiers {id}_splits.json les plus anciens, garde les {keep} derniers."""
    splits = sorted(DATA_DIR.glob("*_splits.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    to_delete = splits[keep:]
    if not to_delete:
        log(f"Cache splits : {len(splits)} fichier(s) — rien a supprimer")
        return
    for old_f in to_delete:
        old_f.unlink()
        log(f"  Cache splits supprime : {old_f.name}")
    log(f"Cache splits : {len(to_delete)} supprime(s), {min(len(splits), keep)} conserve(s)")

if __name__ == "__main__":
    main()
