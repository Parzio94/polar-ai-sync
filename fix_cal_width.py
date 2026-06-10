from pathlib import Path

SRC = Path('/root/polar/app.py')
content = SRC.read_text(encoding='utf-8')

# 1. Annuler le mauvais changement sur historique
bad  = "f'%%BAND%%<main style=\"max-width:960px\">{chart}{hist}</main>')"
good = "f'%%BAND%%<main>{chart}{hist}</main>')"
if bad in content:
    content = content.replace(bad, good, 1)
    print('OK annulé historique')
else:
    print('historique déjà propre')

# 2. Élargir uniquement le <main> de l'accueil
# La structure exacte est : f'%%BAND%%' suivi de f'<main>'
old = "f'%%BAND%%'\n             f'<main>'"
new = "f'%%BAND%%'\n             f'<main style=\"max-width:960px\">'"
if old in content:
    content = content.replace(old, new, 1)
    print('OK accueil -> 960px')
else:
    print('NOT FOUND - vérification...')
    # Chercher ce qui existe vraiment
    idx = content.find("f'%%BAND%%'")
    if idx >= 0:
        print('Contexte:', repr(content[idx:idx+80]))

SRC.write_text(content, encoding='utf-8')
print('Fichier sauvegardé')
