#!/usr/bin/env python3
"""
daily_pv.py — Snapshot quotidien valeur portfolio + PV jour/mois
Cron : 0 2 * * * /root/venv/bin/python3 /root/polar/daily_pv.py
"""
import json, urllib.request
from pathlib import Path
from datetime import datetime, timedelta

POLAR = Path("/root/polar")
INV_FILE = POLAR / "finances" / "finances_investments.json"
SNAP_DIR = POLAR / "finances" / "snapshots" / "daily"
DATA_FILE = POLAR / "finances" / "finances_data.json"
SNAP_DIR.mkdir(parents=True, exist_ok=True)

def load(f): return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
def save(f, d): f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

inv = load(INV_FILE)
now = datetime.now()
ym = now.strftime("%Y-%m")
today = now.strftime("%Y-%m-%d")
yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
prev_ym = (datetime(now.year, now.month, 1) - timedelta(days=1)).strftime("%Y-%m")

USD_SYMS = ['MSFT','NVDA','BLK','MA','V','ORCL','AMD','CVX','XOM','IGLN.L','ISLN.L']

def get_price(sym):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1d"
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            d = json.loads(r.read())
        return d["chart"]["result"][0]["meta"].get("regularMarketPrice")
    except: return None

eurusd = get_price("EURUSD=X") or 1.15

def calc_valeur_portfolio(portfolio):
    total = 0
    detail = {}
    for sym, pos in portfolio.items():
        q = float(pos.get('qte', 0) or 0)
        pru = float(pos.get('pru', 0) or 0)
        if q == 0: continue
        prix = get_price(sym)
        if prix is None:
            detail[sym] = q * pru  # fallback PRU
        else:
            if sym in USD_SYMS: prix = prix / eurusd
            detail[sym] = q * prix
        total += detail[sym]
    return round(total), detail

def get_crypto_prices():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=eur"
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except: return {}

crypto_prices = get_crypto_prices()

def calc_valeur_crypto(portfolio):
    total = 0
    for cid, pos in portfolio.items():
        q = float(pos.get('qte', 0) or 0)
        pru = float(pos.get('pru', 0) or 0)
        prix = (crypto_prices.get(cid) or {}).get('eur')
        if prix: total += q * prix
        else: total += q * pru
    return round(total)

print(f"Calcul valeur {today}...")
val_pea, _ = calc_valeur_portfolio(inv.get('pea', {}))
val_cto, _ = calc_valeur_portfolio(inv.get('cto', {}))
val_crypto = calc_valeur_crypto(inv.get('crypto', {}))
val_total = val_pea + val_cto + val_crypto

# Charger fichier mensuel
snap_file = SNAP_DIR / f"pv_{ym}.json"
monthly = load(snap_file) if snap_file.exists() else {}

# PV jour = valeur aujourd'hui - valeur hier
yesterday_data = monthly.get(yesterday, {})
val_hier_pea = yesterday_data.get('val_pea', val_pea)
val_hier_cto = yesterday_data.get('val_cto', val_cto)
val_hier_crypto = yesterday_data.get('val_crypto', val_crypto)

pv_jour_pea = val_pea - val_hier_pea
pv_jour_cto = val_cto - val_hier_cto
pv_jour_crypto = val_crypto - val_hier_crypto
pv_jour_total = pv_jour_pea + pv_jour_cto + pv_jour_crypto

# PV mois = valeur aujourd'hui - valeur J1 du mois
first_day_data = monthly.get('_first_day', {})
val_first_pea = first_day_data.get('val_pea', val_pea)
val_first_cto = first_day_data.get('val_cto', val_cto)
val_first_crypto = first_day_data.get('val_crypto', val_crypto)

pv_mois_pea = val_pea - val_first_pea
pv_mois_cto = val_cto - val_first_cto
pv_mois_crypto = val_crypto - val_first_crypto
pv_mois_total = pv_mois_pea + pv_mois_cto + pv_mois_crypto

# Sauvegarder aujourd'hui
today_data = {
    'val_pea': val_pea,
    'val_cto': val_cto,
    'val_crypto': val_crypto,
    'val_total': val_total,
    'pv_jour': {'pea': pv_jour_pea, 'cto': pv_jour_cto, 'crypto': pv_jour_crypto, 'total': pv_jour_total},
    'pv_mois': {'pea': pv_mois_pea, 'cto': pv_mois_cto, 'crypto': pv_mois_crypto, 'total': pv_mois_total},
}
monthly[today] = today_data
monthly['_last'] = today_data
monthly['_ym'] = ym

# Premier jour du mois
if '_first_day' not in monthly:
    monthly['_first_day'] = {'val_pea': val_pea, 'val_cto': val_cto, 'val_crypto': val_crypto}

save(snap_file, monthly)
print(f"✅ PEA: {val_pea}€ | CTO: {val_cto}€ | Crypto: {val_crypto}€")
print(f"✅ PV jour: PEA {pv_jour_pea:+}€ | CTO {pv_jour_cto:+}€ | Crypto {pv_jour_crypto:+}€ | Total {pv_jour_total:+}€")
print(f"✅ PV mois: PEA {pv_mois_pea:+}€ | CTO {pv_mois_cto:+}€ | Crypto {pv_mois_crypto:+}€ | Total {pv_mois_total:+}€")

# Mettre à jour finances_data perf_snapshot avec PV mois
fd = load(DATA_FILE)
year = now.strftime("%Y")
if year not in fd: fd[year] = {}
if 'perf_snapshot' not in fd[year]: fd[year]['perf_snapshot'] = {}
fd[year]['perf_snapshot'][ym] = pv_mois_total
save(DATA_FILE, fd)
print(f"✅ perf_snapshot[{ym}] = {pv_mois_total}€")

# Sauvegarder pour WhatsApp
pv_file = POLAR / "data" / "pv_current.json"
save(pv_file, {
    'date': today,
    'pv_jour': {'pea': pv_jour_pea, 'cto': pv_jour_cto, 'crypto': pv_jour_crypto, 'total': pv_jour_total},
    'pv_mois': {'pea': pv_mois_pea, 'cto': pv_mois_cto, 'crypto': pv_mois_crypto, 'total': pv_mois_total},
})
