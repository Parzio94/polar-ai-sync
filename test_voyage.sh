#!/bin/bash
# Test rapide à lancer sur le VPS
echo "=== Version du fichier ==="
md5sum /root/polar/app.py
echo ""
echo "=== Fonctions voyage dans app.py ==="
grep -c "voyOpenCreate\|voyConfirmDelete\|voySaveVoyage" /root/polar/app.py
echo ""
echo "=== Dernier démarrage service ==="
systemctl status polar-app | grep "Active:"
echo ""
echo "=== Test génération page voyages ==="
/root/venv/bin/python3 -c "
import sys; sys.path.insert(0, '/root/polar')
from app import app, _build_voyages_page, _voyages_script
l, d, m = _build_voyages_page(None)
scr = _voyages_script()
import re
btns = re.findall(r'onclick=\"([^\"]+)\"', l)
print('Boutons liste:', btns)
print('voyOpenCreate dans script:', 'voyOpenCreate' in scr)
print('voySaveVoyage dans script:', 'voySaveVoyage' in scr)
"
