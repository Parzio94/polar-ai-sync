#!/usr/bin/env python3
"""
xlsx_to_programme.py — Convertit Marathon_programme.xlsx → semaine_*.json
Usage : python3 xlsx_to_programme.py [chemin_excel]

Dépose les fichiers dans /root/polar/programme/
Le site se met à jour automatiquement au prochain rechargement.
"""

import json, sys, shutil
from pathlib import Path
from datetime import datetime, timedelta
import re

RE_SEMAINE = re.compile(r'^\s*(?:Semaine\s+(\d+)|S0?(\d+)\b)', re.IGNORECASE)

def is_ligne_titre_semaine(date):
    """Retourne le numero de semaine (int) si la cellule est un titre, sinon None."""
    if not isinstance(date, str):
        return None
    m = RE_SEMAINE.match(date.strip())
    if not m:
        return None
    return int(m.group(1) or m.group(2))

try:
    import openpyxl
except ImportError:
    print("Installation de openpyxl...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "openpyxl",
                    "--break-system-packages", "-q"])
    import openpyxl

# ─── CONFIG ───────────────────────────────────────────────────
EXCEL_PATH  = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/root/polar/Marathon_programme.xlsx")
OUTPUT_DIR  = Path("/root/polar/programme")

# Mapping discipline Excel → sport attendu par app.py
SPORT_MAP = {
    "Course":   "Course",
    "Natation": "Natation",
    "Vélo":     "Velo",
    "Velo":     "Velo",
    "Ski":      "Ski",
    "Renfo":    "Renfo",
}

# ─── PARSER ───────────────────────────────────────────────────
def parse_excel(path):
    wb = openpyxl.load_workbook(str(path), data_only=True)
    ws = wb.active

    semaines = {}       # "Semaine N" → {"num": N, "seances": [...]}
    current_sem = None
    orphan_processed = False  # les séances avant le 1er titre seront renumérotées

    for row in ws.iter_rows(values_only=True):
        if not any(c is not None for c in row):
            continue  # ligne vide

        # Excel: A=Date B=Jour C=Discipline D=Séance E=Durée F=Zones G=RPE H=Structure
        #        I=Distance Course(km)  J=Distance Vélo(km)  K=Distance Natation(m)
        date      = row[0]  if len(row) > 0  else None
        jour      = row[1]  if len(row) > 1  else None
        discipline= row[2]  if len(row) > 2  else None
        seance    = row[3]  if len(row) > 3  else None
        duree     = row[4]  if len(row) > 4  else None
        zones     = row[5]  if len(row) > 5  else None
        rpe       = row[6]  if len(row) > 6  else None
        structure = row[7]  if len(row) > 7  else None
        dist_course_km = row[8]  if len(row) > 8  else None   # col I
        dist_velo_km   = row[9]  if len(row) > 9  else None   # col J
        dist_nata_m    = row[10] if len(row) > 10 else None   # col K

        # ── Ligne de titre "Semaine N" ──────────────────────
        num_sem = is_ligne_titre_semaine(date)
        if num_sem is not None:
            current_sem = f"Semaine {num_sem}"
            if current_sem not in semaines:
                semaines[current_sem] = {"num": num_sem, "seances": []}
            continue

        # ── Ligne de séance valide ───────────────────────────
        if hasattr(date, "strftime") and discipline:
            # Si on arrive ici sans titre de semaine détecté encore
            # On ne sait pas encore quel numéro donner — on met '__orphan__' provisoirement
            if current_sem is None:
                current_sem = "__orphan__"
                semaines[current_sem] = {"num": 0, "seances": []}

            date_str = date.strftime("%Y-%m-%d")
            sport    = SPORT_MAP.get(str(discipline).strip(), str(discipline).strip())

            # Durée : formater en "Xmin" ou "Xh Ymin"
            duree_str = _fmt_duree(duree)

            # Distance selon la discipline
            # Course: col I (km), Vélo: col J (km), Natation: col K (m)
            if sport == "Course":
                dist_cible   = float(dist_course_km) if dist_course_km is not None else None
                dist_cible_m = None
            elif sport == "Velo":
                dist_cible   = float(dist_velo_km) if dist_velo_km is not None else None
                dist_cible_m = None
            elif sport == "Natation":
                dist_cible_m = int(dist_nata_m) if dist_nata_m is not None else None
                dist_cible   = None
            else:
                dist_cible   = float(dist_course_km) if dist_course_km is not None else None
                dist_cible_m = None

            seance_obj = {
                "date":      date_str,
                "jour":      str(jour).strip() if jour else "",
                "sport":     sport,
                "type":      str(seance).strip() if seance else "",
                "duree":     duree_str,
                "zone":      str(zones).strip() if zones else "",
                "rpe":       str(rpe).strip() if rpe else "",
                "structure": str(structure).strip() if structure else "",
            }
            if dist_cible   is not None: seance_obj["dist_cible"]   = dist_cible
            if dist_cible_m is not None: seance_obj["dist_cible_m"] = dist_cible_m

            semaines[current_sem]["seances"].append(seance_obj)

    # Post-traitement: renuméroter les séances orphelines (__orphan__)
    if "__orphan__" in semaines:
        explicit_nums = sorted(
            int(sn.split()[-1]) for sn in semaines
            if sn.startswith('Semaine ') and sn != '__orphan__'
            if sn.split()[-1].isdigit()
        )
        if explicit_nums:
            new_num = explicit_nums[0] - 1  # séances juste avant la 1ère semaine numérotée
            new_name = f'Semaine {new_num}'
            semaines[new_name] = {'num': new_num, 'seances': semaines.pop('__orphan__')['seances']}
        else:
            semaines['Semaine 1'] = {'num': 1, 'seances': semaines.pop('__orphan__')['seances']}
    return semaines


def _fmt_duree(val):
    """Convertit une durée (int minutes, ou None) en string lisible."""
    if val is None:
        return "—"
    try:
        mins = int(float(str(val)))
        if mins >= 60:
            h, m = divmod(mins, 60)
            return f"{h}h{m:02d}" if m else f"{h}h"
        return f"{mins}min"
    except Exception:
        return str(val)


# ─── ÉCRITURE JSON ────────────────────────────────────────────
def write_json(semaines, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Supprimer UNIQUEMENT les fichiers correspondant aux semaines du nouvel Excel
    # Les semaines absentes du nouvel Excel (ex: S1-S9 injectées manuellement) sont conservées
    nums_to_write = {sem_data["num"] for sem_data in semaines.values() if sem_data["seances"]}
    deleted = []
    for f in output_dir.glob("semaine_*.json"):
        try:
            num = int(f.stem.split("_")[1])
            if num in nums_to_write:
                f.unlink()
                deleted.append(f.name)
        except (ValueError, IndexError):
            pass
    if deleted:
        print(f"  🗑️  {len(deleted)} fichier(s) remplacé(s) : {', '.join(sorted(deleted))}")
    # Fichiers conservés (non touchés)
    kept = [f.name for f in output_dir.glob("semaine_*.json")]
    if kept:
        print(f"  📌 {len(kept)} fichier(s) conservé(s) : {', '.join(sorted(kept))}")

    written = 0
    for sem_name, sem_data in sorted(semaines.items(), key=lambda x: x[1]["num"]):
        if not sem_data["seances"]:
            continue

        # Nom de fichier : semaine_09.json, semaine_10.json, etc.
        num     = sem_data["num"]
        fname   = f"semaine_{num:02d}.json"
        # Calculer week_key (lundi de la première séance)
        first_date = sem_data["seances"][0]["date"] if sem_data["seances"] else None
        wk_key = ""
        if first_date:
            from datetime import date as _d
            try:
                fd = _d.fromisoformat(first_date)
                wk_key = (fd - timedelta(days=fd.weekday())).isoformat()
            except Exception:
                wk_key = first_date
        payload = {
            "semaine":   sem_name,
            "sem_label": f"S{num}",
            "week_key":  wk_key,
            "seances":   sem_data["seances"],
        }
        (output_dir / fname).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        nb_s = len(sem_data["seances"])
        dates = [s["date"] for s in sem_data["seances"]]
        print(f"  ✅ {fname} — {nb_s} séance(s) [{dates[0]} → {dates[-1]}]")
        written += 1

    return written


# ─── MAIN ─────────────────────────────────────────────────────
def main():
    print(f"\n📋 Lecture de : {EXCEL_PATH}")
    if not EXCEL_PATH.exists():
        print(f"❌ Fichier introuvable : {EXCEL_PATH}")
        print("   Usage : python3 xlsx_to_programme.py /chemin/vers/Marathon_programme.xlsx")
        sys.exit(1)

    semaines = parse_excel(EXCEL_PATH)
    total_seances = sum(len(v["seances"]) for v in semaines.values())
    print(f"   → {len(semaines)} semaine(s) trouvée(s), {total_seances} séance(s) au total\n")

    print(f"📁 Écriture dans : {OUTPUT_DIR}")
    written = write_json(semaines, OUTPUT_DIR)

    print(f"\n✅ {written} fichier(s) JSON généré(s) dans {OUTPUT_DIR}")
    print("   Le site se met à jour au prochain rechargement (ou restart : systemctl restart polar-app)\n")


if __name__ == "__main__":
    main()
