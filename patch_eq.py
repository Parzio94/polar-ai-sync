#!/usr/bin/env python3
"""
Colle ce fichier sur le VPS et exécute :
  python3 /root/polar/patch_eq.py
"""
import py_compile, shutil, sys

PATH = '/root/polar/app.py'
shutil.copy(PATH, PATH + '.bak_eq')

lines = open(PATH, encoding='utf-8').readlines()

# Vérifier que le fichier est bien l'original (non patché)
if 'display:flex;gap:6px;align-items:flex-start;margin-bottom:6px' not in lines[3387]:
    print("⚠️  Ligne 3388 ne correspond pas — fichier déjà patché ou version différente.")
    print(f"    Contenu L3388 : {lines[3387].strip()}")
    sys.exit(0)

NEW_HITEM  = '                   f\'<div class="hitem" style="margin-bottom:6px;{"position:relative;padding-right:118px" if _eq_card else ""}">\'\n'
NEW_EQCARD = '                   f\'{"<div style=\\\'position:absolute;top:9px;right:11px\\\'>"+_eq_card+"</div>" if _eq_card else ""}\'\n'

new_lines = []
for i, l in enumerate(lines):
    ln = i + 1
    if ln == 3388: continue                            # supprime outer flex
    if ln == 3389:                                     # remplace hitem
        new_lines.append(NEW_HITEM)
        new_lines.append(NEW_EQCARD)
        continue
    if ln in (3425, 3426, 3427, 3428): continue       # supprime extra closes + eq_card orpheline
    if ln == 3424:                                     # close hitem + ferme hist+=
        new_lines.append("                   f'</div>')\n")
        continue
    new_lines.append(l)

with open(PATH, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

try:
    py_compile.compile(PATH, doraise=True)
    print("✅ Patch appliqué — lance : systemctl restart polar-app")
except py_compile.PyCompileError as e:
    print(f"❌ Erreur : {e}")
    shutil.copy(PATH + '.bak_eq', PATH)
    print("Backup restauré.")
    sys.exit(1)
