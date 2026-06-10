#!/usr/bin/env python3
"""
patch_natation.py — Corrige l'affichage des distances natation dans app.py

Fixes :
  1. parse_swim_distance : regex corrigé pour ne pas matcher "30min" comme "30m"
  2. dist_line natation : affiche "1600m · 30min" au lieu de "~0min"
  3. swim_time_estimate : n'est plus appelé si dist_cible_m vient du JSON (déjà fiable)

Usage : python3 patch_natation.py  (depuis /root/polar/)
"""
import sys
from pathlib import Path

SRC = Path("/root/polar/app.py")
if not SRC.exists():
    print("❌ app.py introuvable"); sys.exit(1)

content = SRC.read_text(encoding="utf-8")

# ── Fix 1 : parse_swim_distance — exclure "min" du match ──────────────────
OLD1 = "def parse_swim_distance(duree_str):\n    m=re.search(r'(\\d+)\\s*m',str(duree_str))\n    return int(m.group(1)) if m else 0"
NEW1 = "def parse_swim_distance(duree_str):\n    # (?!in) évite de matcher '30min' comme '30m'\n    m=re.search(r'(\\d+)\\s*m(?!in)',str(duree_str))\n    return int(m.group(1)) if m else 0"

if OLD1 in content:
    content = content.replace(OLD1, NEW1, 1)
    print("✅ Fix 1 appliqué : parse_swim_distance corrigé")
else:
    print("⚠️  Fix 1 : pattern introuvable (déjà corrigé ?)")

# ── Fix 2 : dist_line natation dans la carte Planning (ligne ~2102) ────────
# Avant : dm = dist_cible_m OR parse_swim_distance(duree) → renvoie 30 si duree="30min"
# Après : utilise dist_cible_m en priorité, parse seulement si vraiment absent
OLD2 = (
    '                dm=s.get("dist_cible_m") or parse_swim_distance(s.get("duree",""))\n'
    '                is_tech="technique" in s.get("type","").lower()\n'
    '                t_est=swim_time_estimate(dm,is_tech) if dm else ""\n'
    '                dist_line=f\'{dm}m{" · "+t_est if t_est else ""}\' if dm else ""'
)
NEW2 = (
    '                dm=s.get("dist_cible_m") or parse_swim_distance(s.get("duree",""))\n'
    '                _duree_str=s.get("duree","") or ""\n'
    '                if dm:\n'
    '                    dist_line=f\'{dm}m · {_duree_str}\' if _duree_str and _duree_str not in ("—","") else f\'{dm}m\'\n'
    '                else:\n'
    '                    dist_line=_duree_str'
)

if OLD2 in content:
    content = content.replace(OLD2, NEW2, 1)
    print("✅ Fix 2 appliqué : affichage dist_line natation corrigé")
else:
    print("⚠️  Fix 2 : pattern introuvable — vérification manuelle nécessaire")

# ── Fix 3 : même correction dans la section "done_html" (ligne ~2092) ─────
OLD3 = '                    pm=s.get("dist_cible_m") or parse_swim_distance(s.get("duree",""))\n                    done_html=f\'<div class="sdone">✅ {pm}m (prog.) · {fmt_dur(dur)}</div>\''
NEW3 = '                    pm=s.get("dist_cible_m") or parse_swim_distance(s.get("duree",""))\n                    _pm_str=f"{pm}m" if pm else "—"\n                    done_html=f\'<div class="sdone">✅ {_pm_str} (prog.) · {fmt_dur(dur)}</div>\''

if OLD3 in content:
    content = content.replace(OLD3, NEW3, 1)
    print("✅ Fix 3 appliqué : done_html natation corrigé")
else:
    print("⚠️  Fix 3 : pattern introuvable (optionnel)")

# ── Écriture ───────────────────────────────────────────────────────────────
SRC.write_text(content, encoding="utf-8")
print(f"\n✅ app.py mis à jour ({len(content)} chars)")
print("Redémarre avec : fuser -k 5000/tcp && systemctl restart polar-app")
