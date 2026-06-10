#!/usr/bin/env python3
"""
monthly_snapshot.py — Snapshot mensuel patrimoine + intérêts
Exécuter le 1er de chaque mois via cron :
  0 8 1 * * /root/venv/bin/python3 /root/polar/monthly_snapshot.py
"""
import json, sys
from pathlib import Path
from datetime import datetime, timedelta

POLAR = Path("/root/polar")
FINANCES_DIR = POLAR / "finances"
INV_FILE = FINANCES_DIR / "finances_investments.json"
DATA_FILE = FINANCES_DIR / "finances_data.json"
SNAPSHOTS_DIR = FINANCES_DIR / "snapshots"
SNAPSHOTS_DIR.mkdir(exist_ok=True)

def load(f): return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
def save(f, d): f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

inv = load(INV_FILE)
fd = load(DATA_FILE)

# Mois précédent
now = datetime.now()
prev = datetime(now.year, now.month, 1) - timedelta(days=1)
ym = prev.strftime("%Y-%m")
year = prev.strftime("%Y")

print(f"Snapshot pour {ym}")

# 1. Intérêts livrets
int_livrets = 0
for lv in inv.get('livrets', {}).values():
    solde = float(lv.get('solde', 0) or 0)
    taux = float(lv.get('taux_actuel', 0) or 0)
    int_livrets += solde * taux / 100 / 12

# 2. Intérêts autres produits (AV, PER, CCB)
int_autres = 0
for ap in inv.get('autres_produits', {}).values():
    solde = float(ap.get('solde', 0) or 0)
    rdt = float(ap.get('rendement', 0) or ap.get('taux_actuel', 0) or 0)
    int_autres += solde * rdt / 100 / 12

# 3. Intérêts SCPI Bricks
int_scpi = 0
today = now.strftime("%Y-%m-%d")
for b in inv.get('scpi', {}).values():
    if not b.get('date_fin') or b['date_fin'] >= today:
        val = float(b.get('valeur', 0) or 0)
        rdt = float(b.get('rendement', 5.5) or 5.5)
        int_scpi += val * rdt / 100 / 12

total_interets = int_livrets + int_autres + int_scpi

# 4. Patrimoine par catégorie (PRU - pas de cours en temps réel ici)
livrets_total = sum(float(v.get('solde',0) or 0) for v in inv.get('livrets',{}).values())
autres_total = sum(float(v.get('solde',0) or 0) for v in inv.get('autres_produits',{}).values())
liq_pea = float(inv.get('liquidites',{}).get('montant',0) or 0)
liq_bricks = float(inv.get('liquidites_bricks',{}).get('montant',0) or 0)

pea_total = sum(float(v.get('qte',0) or 0)*float(v.get('pru',0) or 0) for v in inv.get('pea',{}).values()) + liq_pea
cto_total = sum(float(v.get('qte',0) or 0)*float(v.get('pru',0) or 0) for v in inv.get('cto',{}).values())
crypto_total = sum(float(v.get('qte',0) or 0)*float(v.get('pru',0) or 0) for v in inv.get('crypto',{}).values())
scpi_total = sum(float(b.get('valeur',0) or 0) for b in inv.get('scpi',{}).values()
                 if not b.get('date_fin') or b['date_fin'] >= today) + liq_bricks

patrimoine_total = livrets_total + autres_total + pea_total + cto_total + crypto_total + scpi_total

# 5. Sauvegarder snapshot mensuel
snapshot = {
    "ym": ym,
    "generated_at": now.isoformat(),
    "interets": {
        "livrets": round(int_livrets, 2),
        "autres_produits": round(int_autres, 2),
        "scpi": round(int_scpi, 2),
        "total": round(total_interets, 2),
    },
    "patrimoine": {
        "livrets": round(livrets_total, 2),
        "pea": round(pea_total, 2),
        "cto": round(cto_total, 2),
        "crypto": round(crypto_total, 2),
        "scpi": round(scpi_total, 2),
        "autres_produits": round(autres_total, 2),
        "total": round(patrimoine_total, 2),
    }
}

# Sauvegarder fichier mensuel
snap_file = SNAPSHOTS_DIR / f"snapshot_{ym}.json"
save(snap_file, snapshot)
print(f"✅ Snapshot sauvegardé : {snap_file}")
print(f"   Intérêts : {total_interets:.2f}€")
print(f"   Patrimoine : {patrimoine_total:.2f}€")

# Mettre à jour finances_data.json perf_snapshot
if year not in fd: fd[year] = {}
if 'perf_snapshot' not in fd[year]: fd[year]['perf_snapshot'] = {}
fd[year]['perf_snapshot'][ym] = round(total_interets)
save(DATA_FILE, fd)
print(f"✅ perf_snapshot mis à jour pour {ym}")
