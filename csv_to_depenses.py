#!/usr/bin/env python3
"""
csv_to_depenses.py — Convertit un export CSV Boursorama → depenses/mois_YYYY-MM.json
Usage : python3 csv_to_depenses.py [chemin_csv]

Dépose les fichiers dans /root/polar/depenses/
Dédoublonne automatiquement sur (date + libellé + montant + compte),
donc peut être relancé plusieurs fois avec des exports qui se chevauchent
sans créer de doublons.
"""

import csv, json, sys, hashlib
from pathlib import Path

# ─── CONFIG ───────────────────────────────────────────────────
CSV_PATH   = Path(sys.argv[1]) if len(sys.argv) > 1 else None
OUTPUT_DIR = Path("/root/polar/depenses")

# Catégories de mouvements internes (transferts entre comptes/cartes du même
# titulaire) : exclues du calcul des dépenses réelles, mais conservées à part
# pour transparence.
CATEGORIES_MOUVEMENTS_INTERNES = {
    "Virements émis",
    "Mouvements internes débiteurs",
}

# ─── HELPERS ──────────────────────────────────────────────────
def parse_montant_fr(raw):
    """Convertit '-2 660,00' ou '-37,70' en float -2660.0 / -37.7"""
    if raw is None:
        return 0.0
    s = str(raw).strip()
    s = s.replace("\xa0", "").replace(" ", "")  # espaces insécables / normales (séparateur de milliers)
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0

def fingerprint(dateOp, label, amount, accountNum):
    """Empreinte unique pour dédoublonnage : date + libellé + montant + compte."""
    raw = f"{dateOp}|{label.strip()}|{amount:.2f}|{accountNum.strip()}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

def month_key(date_str):
    """'2026-08-28' -> '2026-08'"""
    return date_str[:7]

# ─── PARSER ───────────────────────────────────────────────────
def parse_csv(path):
    """Retourne une liste d'opérations (dict) depuis le CSV Boursorama."""
    ops = []
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            date_op = (row.get("dateOp") or "").strip()
            date_val = (row.get("dateVal") or "").strip()
            label = (row.get("label") or "").strip()
            suggested = (row.get("suggestedLabel") or "").strip()
            category = (row.get("category") or "").strip()
            category_parent = (row.get("categoryParent") or "").strip()
            amount = parse_montant_fr(row.get("amount"))
            account_num = (row.get("accountNum") or "").strip()
            account_label = (row.get("accountLabel") or "").strip()
            balance = parse_montant_fr(row.get("accountbalance"))

            if not date_op:
                continue

            fp = fingerprint(date_op, label, amount, account_num)

            ops.append({
                "fingerprint": fp,
                "date": date_op,
                "date_val": date_val,
                "label": label,
                "suggested_label": suggested,
                "category": category,
                "category_parent": category_parent,
                "amount": amount,
                "account_num": account_num,
                "account_label": account_label,
                "balance_after": balance,
            })
    return ops

# ─── ÉCRITURE JSON (avec dédoublonnage) ───────────────────────
def write_json(ops, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Grouper les nouvelles opérations par mois
    by_month = {}
    for op in ops:
        mk = month_key(op["date"])
        by_month.setdefault(mk, []).append(op)

    total_new = 0
    total_skipped = 0
    written_months = []

    for mk, new_ops in sorted(by_month.items()):
        fpath = output_dir / f"mois_{mk}.json"

        # Charger l'existant si présent
        if fpath.exists():
            try:
                existing = json.loads(fpath.read_text(encoding="utf-8"))
                existing_ops = existing.get("operations", [])
            except Exception:
                existing_ops = []
        else:
            existing_ops = []

        existing_fps = {o["fingerprint"] for o in existing_ops}

        added = 0
        for op in new_ops:
            if op["fingerprint"] in existing_fps:
                total_skipped += 1
                continue
            existing_ops.append(op)
            existing_fps.add(op["fingerprint"])
            added += 1
            total_new += 1

        if added == 0 and fpath.exists():
            continue  # rien de nouveau pour ce mois, ne pas ré-écrire inutilement

        # Trier par date décroissante pour l'affichage
        existing_ops.sort(key=lambda o: o["date"], reverse=True)

        # Résumé par catégorie parente (pratique pour l'onglet Dépenses)
        # Les mouvements internes (virements entre comptes/cartes du même
        # titulaire) sont exclus du calcul des dépenses réelles, mais
        # conservés à part pour transparence.
        by_cat = {}
        total_depenses = 0.0
        total_revenus = 0.0
        total_mouvements_internes = 0.0
        for o in existing_ops:
            cat_parent = o["category_parent"] or "Autre"
            if cat_parent in CATEGORIES_MOUVEMENTS_INTERNES:
                total_mouvements_internes += abs(o["amount"])
                continue
            if o["amount"] < 0:
                by_cat[cat_parent] = by_cat.get(cat_parent, 0.0) + abs(o["amount"])
                total_depenses += abs(o["amount"])
            else:
                total_revenus += o["amount"]

        payload = {
            "mois": mk,
            "operations": existing_ops,
            "total_depenses": round(total_depenses, 2),
            "total_revenus": round(total_revenus, 2),
            "total_mouvements_internes": round(total_mouvements_internes, 2),
            "par_categorie": {k: round(v, 2) for k, v in sorted(by_cat.items(), key=lambda x: -x[1])},
        }

        fpath.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        written_months.append(mk)
        print(f"  ✅ mois_{mk}.json — {len(existing_ops)} opération(s) au total ({added} nouvelle(s)), "
              f"dépenses: {total_depenses:.2f}€")

    return total_new, total_skipped, written_months

# ─── MAIN ─────────────────────────────────────────────────────
def main():
    if CSV_PATH is None or not CSV_PATH.exists():
        print(f"❌ Fichier introuvable : {CSV_PATH}")
        print("   Usage : python3 csv_to_depenses.py /chemin/vers/export-operations-....csv")
        sys.exit(1)

    print(f"\n📋 Lecture de : {CSV_PATH}")
    ops = parse_csv(CSV_PATH)
    print(f"   → {len(ops)} opération(s) lue(s) dans le fichier\n")

    print(f"📁 Écriture dans : {OUTPUT_DIR}")
    total_new, total_skipped, months = write_json(ops, OUTPUT_DIR)

    print(f"\n✅ {total_new} nouvelle(s) opération(s) ajoutée(s), "
          f"{total_skipped} doublon(s) ignoré(s)")
    if months:
        print(f"   Mois mis à jour : {', '.join(months)}")
    else:
        print("   Aucun mois modifié (tout était déjà présent)")


if __name__ == "__main__":
    main()
