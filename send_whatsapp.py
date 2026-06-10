#!/usr/bin/env python3
"""
send_whatsapp.py — Envoi quotidien du programme + calendrier sur WhatsApp
via CallMeBot (gratuit, 0 installation).

ACTIVATION (une seule fois) :
  1. Envoyer ce message WhatsApp au +34 644 60 29 88 :
     "I allow callmebot to send me messages"
  2. Vous recevrez votre apikey par WhatsApp
  3. Remplir .env : WHATSAPP_PHONE=+352XXXXXXXX  CALLMEBOT_APIKEY=XXXXXX

CRON (ajouter avec : crontab -e) :
  0 7 * * * /root/venv/bin/python3 /root/polar/send_whatsapp.py >> /root/polar/logs/whatsapp.log 2>&1
"""

import json, os, sys, urllib.request, urllib.parse
from pathlib import Path
from datetime import datetime, timezone, timedelta

# ── Config ────────────────────────────────────────────────────
POLAR     = Path("/root/polar")
DATA      = POLAR / "data"
PROG_DIR  = POLAR / "programme"

# Charger .env si présent
_env = POLAR / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

PHONE   = os.environ.get("WHATSAPP_PHONE", "")
API_KEY = os.environ.get("CALLMEBOT_APIKEY", "")

# ── Timezone ──────────────────────────────────────────────────
try:
    import zoneinfo
    TZ = zoneinfo.ZoneInfo("Europe/Luxembourg")
except ImportError:
    TZ = timezone(timedelta(hours=1))

def now_local():
    return datetime.now(TZ)

TODAY = now_local().strftime("%Y-%m-%d")
JOURS = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]
JOUR_NOM = JOURS[now_local().weekday()]
DATE_FR = now_local().strftime("%d/%m/%Y")

# ── Helpers ───────────────────────────────────────────────────
def load_json(path, default=None):
    try:
        p = Path(path)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except: pass
    return default

def get_sem_label():
    """Récupère le label de la semaine courante depuis week_current.json."""
    w = load_json(DATA / "weeks" / "week_current.json", {})
    return w.get("sem_label", "")

def get_today_seances():
    """Retourne les séances du jour depuis le programme."""
    sem = get_sem_label()
    seances = []
    # Chercher dans tous les fichiers semaine_*.json
    if PROG_DIR.exists():
        for f in sorted(PROG_DIR.glob("semaine_*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                for s in data.get("seances", []):
                    if s.get("date","") == TODAY:
                        seances.append(s)
            except: pass
    return seances

def get_today_cal_events():
    """Retourne les événements calendrier du jour."""
    events = load_json(POLAR / "calendar" / "calendar_events.json", [])
    today_ev = []
    for e in events:
        if e.get("date","") == TODAY or e.get("date","") == TODAY:
            today_ev.append(e)
    return today_ev

def get_hr_zones():
    """Retourne les zones FC."""
    zones = load_json(POLAR / "hr_zones.json", [])
    if not zones:
        # Zones par défaut Mattéo
        zones = [
            {"zone":"Z1","bpm_max":130,"pace_min":"6:00/km"},
            {"zone":"Z2","bpm_min":131,"bpm_max":145,"pace":"5:30-6:00/km"},
            {"zone":"Z3","bpm_min":146,"bpm_max":160,"pace":"4:55-5:25/km"},
            {"zone":"Z4","bpm_min":161,"bpm_max":172,"pace":"4:35-4:55/km"},
            {"zone":"Z5","bpm_min":173,"pace_max":"4:35/km"},
        ]
    return zones

SPORT_ICONS = {
    "Course":"🏃","RUNNING":"🏃",
    "Velo":"🚴","CYCLING":"🚴",
    "Natation":"🏊","SWIMMING":"🏊",
    "Renfo":"💪","OTHER":"🏅",
}

def fmt_seance(s):
    """Formate une séance en texte WhatsApp."""
    sport = s.get("sport","")
    ico   = SPORT_ICONS.get(sport, "🏅")
    typ   = s.get("type","")
    dur   = s.get("duree","")
    struct= s.get("structure","")
    dist  = s.get("dist_cible") or ""
    dist_m= s.get("dist_cible_m")
    dist_str = f"{dist}km" if dist else (f"{dist_m}m" if dist_m else "")

    lines = [f"{ico} *{typ}*"]
    if dist_str or dur:
        meta = " · ".join(filter(None,[dist_str, dur]))
        lines.append(meta)
    # Pas de zone — supprimé
    if struct:
        lines.append(struct)
    return "\n".join(lines)

def fmt_event(e):
    """Formate un événement calendrier."""
    title = e.get("title","Événement")
    h1 = e.get("start_time","")
    h2 = e.get("end_time","")
    if h1:
        def fh(t):
            if not t: return ""
            parts = t.split(":")
            return f"{int(parts[0])}h{parts[1] if len(parts)>1 and parts[1]!='00' else ''}"
        prefix = f"{fh(h1)}" + (f"→{fh(h2)}" if h2 else "") + " "
    else:
        prefix = ""
    return f"• {prefix}{title}"

def get_today_voyage_elements():
    """Retourne les éléments voyage du jour depuis voyages.json."""
    try:
        vdata = load_json(POLAR / "voyages.json", {})
        elements = []
        for v in vdata.get("voyages", []):
            d1 = v.get("date_debut","")
            d2 = v.get("date_fin","")
            if not (d1 <= TODAY <= d2): continue
            nom_voy = v.get("nom","Voyage")
            # Ville du jour si définie
            ville = v.get("villes_par_jour",{}).get(TODAY,"")
            if ville:
                elements.append(f"📍 {ville} ({nom_voy})")
            # Éléments du jour
            TYPE_ICO = {"transport":"🚆","hotel":"🏨","activite":"🎟️",
                        "nourriture":"🍽️","note":"📝"}
            for el in v.get("elements",[]):
                if el.get("date","") != TODAY: continue
                t = el.get("type","")
                ico = TYPE_ICO.get(t,"📌")
                h1 = el.get("heure","")
                h2 = el.get("heure_fin","")
                def fh(t2):
                    if not t2: return ""
                    h,_,m = str(t2).partition(":")
                    return f"{int(h)}h{m if m and m!='00' else ''}"
                heure = (f"{fh(h1)}→{fh(h2)} " if h1 and h2 else
                         f"{fh(h1)} " if h1 else "")
                if t == "transport":
                    def short(v2): return v2.split(",")[0].strip() if v2 else ""
                    nom = f"{short(el.get('ville_depart',''))} → {short(el.get('ville_arrivee',''))}"
                elif t == "note":
                    nom = el.get("titre","Note")
                else:
                    nom = el.get("nom","") or el.get("nom_etablissement","")
                elements.append(f"{ico} {heure}{nom}")
        return elements
    except: return []

# ── Construire le message ─────────────────────────────────────
def get_next_race():
    """Retourne la prochaine course la plus proche."""
    races = load_json(POLAR / "races.json", [])
    if not races: return None
    today = datetime.now(TZ).date()
    future = []
    for r in races:
        try:
            d = datetime.strptime(r["date"], "%Y-%m-%d").date()
            jx = (d - today).days
            if jx >= 0:
                future.append((jx, r))
        except: pass
    if not future: return None
    future.sort(key=lambda x: x[0])
    jx, r = future[0]
    return f"🏁 *{r.get('label','Course')}* — J-{jx}"

def get_debit_differe():
    """Retourne le débit différé du mois si on est le 1er."""
    if now_local().day != 1: return None
    try:
        data = load_json(POLAR / "finances" / "finances_data.json", {})
        ym = now_local().strftime("%Y-%m")
        year = str(now_local().year)
        dd = (data.get(year,{}).get("debit_differe",{}).get(ym,{}) or {}).get("montant",0)
        if dd > 0:
            return f"💳 Débit différé CB ce mois : *{dd:.0f}€*"
    except: pass
    return None

def get_pv_portfolio():
    """Retourne la PV du jour et du mois depuis pv_current.json."""
    pv_file = DATA / "pv_current.json"
    d = load_json(pv_file, {})
    if not d: return None
    pj = d.get("pv_jour", {})
    pm = d.get("pv_mois", {})
    def fmt(v):
        return ("+"+str(v) if v>=0 else str(v))+"€"
    parts = []
    if pj.get("pea") is not None: parts.append(f"PEA {fmt(pj['pea'])}")
    if pj.get("cto") is not None: parts.append(f"CTO {fmt(pj['cto'])}")
    if pj.get("crypto") is not None: parts.append(f"Crypto {fmt(pj['crypto'])}")
    if not parts: return None
    ligne_jour = " | ".join(parts) + f" | Total {fmt(pj.get('total',0))}"
    ligne_mois = f"Mois: {fmt(pm.get('total',0))}"
    return f"💹 PV hier: {ligne_jour}\n    {ligne_mois}"

def build_message():
    seances  = get_today_seances()
    events   = get_today_cal_events()
    voyage   = get_today_voyage_elements()
    next_race = get_next_race()
    debit = get_debit_differe()
    pv = get_pv_portfolio()

    parts = [f"🌅 Bonjour Mattéo ! *{JOUR_NOM} {DATE_FR}*"]
    if next_race:
        parts.append(next_race)
    if debit:
        parts.append(debit)
    if pv:
        parts.append(pv)
    parts.append("")

    if seances:
        parts.append("━━━ 📋 PROGRAMME DU JOUR ━━━")
        for s in seances:
            parts.append("")
            parts.append(fmt_seance(s))
    else:
        parts.append("🌿 _Pas de séance prévue aujourd'hui — récupération !_")

    if voyage:
        parts.append("")
        parts.append("━━━ ✈️ VOYAGE ━━━")
        for v in voyage:
            parts.append(v)

    if events:
        parts.append("")
        parts.append("━━━ 📅 AGENDA ━━━")
        for e in events:
            parts.append(fmt_event(e))

    return "\n".join(parts)

# ── Envoi ─────────────────────────────────────────────────────
def send_whatsapp(message):
    if not PHONE or not API_KEY:
        print("❌ WHATSAPP_PHONE ou CALLMEBOT_APIKEY manquant dans .env")
        print("   Ajoutez ces lignes dans /root/polar/.env :")
        print("   WHATSAPP_PHONE=+352XXXXXXXX")
        print("   CALLMEBOT_APIKEY=XXXXXX")
        return False

    encoded = urllib.parse.quote(message)
    url = f"https://api.callmebot.com/whatsapp.php?phone={PHONE}&text={encoded}&apikey={API_KEY}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent":"CoachIA/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = r.read().decode("utf-8", errors="replace")
            if "Message sent" in resp or "queued" in resp.lower():
                print(f"✅ Message envoyé à {PHONE}")
                return True
            else:
                print(f"⚠️  Réponse CallMeBot : {resp[:200]}")
                return False
    except Exception as e:
        print(f"❌ Erreur envoi : {e}")
        return False

# ── Main ──────────────────────────────────────────────────────
if __name__ == "__main__":
    msg = build_message()
    print("=" * 50)
    print(msg)
    print("=" * 50)

    if "--dry-run" in sys.argv or "--test" in sys.argv:
        print("\n[DRY RUN — pas d'envoi]")
    else:
        send_whatsapp(msg)
