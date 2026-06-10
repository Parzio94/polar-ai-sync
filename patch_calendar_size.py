#!/usr/bin/env python3
"""
Agrandit le calendrier de la page Accueil.
Lance : python3 patch_calendar_size.py
"""
from pathlib import Path

SRC = Path("/root/polar/app.py")
content = SRC.read_text(encoding="utf-8")

changes = [
    # Cellules plus hautes
    (".cal-cell{min-height:72px;",
     ".cal-cell{min-height:110px;"),

    # Numéro du jour plus visible
    (".cal-dn{font-size:.72rem;",
     ".cal-dn{font-size:.82rem;"),

    # Titres d'événements plus lisibles
    (".cal-ev-title{font-size:.56rem;",
     ".cal-ev-title{font-size:.64rem;"),

    # Gap entre cellules légèrement plus grand
    (".cal-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:2px;",
     ".cal-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:3px;"),
]

ok = 0
for old, new in changes:
    if old in content:
        content = content.replace(old, new, 1)
        print(f"✅ {old[:40]}...")
        ok += 1
    else:
        print(f"⚠️  Non trouvé : {old[:40]}...")

SRC.write_text(content, encoding="utf-8")
print(f"\n✅ {ok}/{len(changes)} modifications appliquées → {SRC}")
print("Redémarre le service : fuser -k 5000/tcp && systemctl restart polar-app")
