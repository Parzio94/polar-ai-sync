#!/usr/bin/env python3
"""
patch_fridge_qty.py
-------------------
Injecte les qty_count lus manuellement depuis le ticket Lidl du 17/03/2026
dans nutrition_fridge.json — sans appel API.

Utilisation :
    python3 /root/polar/patch_fridge_qty.py
"""

import json
from pathlib import Path

POLAR = Path("/root/polar")
FRIDGE_FILE = POLAR / "nutrition_fridge.json"

# Quantités lues directement sur le ticket
# banane  : 0,812 kg → 812g ÷ 120g/banane ≈ 7
# grenailles : 2,49 × 2 → 2 sachets
# oeuf    : ROBY OEUFS FRAIS LUX → boîte de 6
# skyr    : 1,35 × 2 → 2 pots
# avocat  : 1,39 × 4 → 4 avocats
QTY_COUNTS = {
    "banane":     7,
    "grenailles": 2,
    "oeuf":       6,
    "skyr":       2,
    "avocat":     4,
}

if not FRIDGE_FILE.exists():
    print("❌ nutrition_fridge.json introuvable dans", POLAR)
    exit(1)

fridge = json.loads(FRIDGE_FILE.read_text())
patched = 0

for item in fridge:
    fid = item.get("food_id")
    if fid in QTY_COUNTS:
        old = item.get("qty_count", "—")
        item["qty_count"] = QTY_COUNTS[fid]
        print(f"  ✅ {item.get('food_name', fid):25s} qty_count : {old} → {QTY_COUNTS[fid]}")
        patched += 1

if patched == 0:
    print("⚠️  Aucun aliment correspondant trouvé dans le frigo.")
    print("   Vérifie que le ticket a bien été importé au préalable.")
else:
    FRIDGE_FILE.write_text(json.dumps(fridge, ensure_ascii=False, indent=2))
    print(f"\n✅ {patched} article(s) mis à jour dans {FRIDGE_FILE}")
