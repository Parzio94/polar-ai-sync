#!/usr/bin/env python3
"""
ticket_email_importer.py — Import automatique des tickets de caisse par email

Cron : tous les jours à 21h00
Lance : /root/venv/bin/python3 /root/polar/ticket_email_importer.py

Config dans /root/polar/.env :
  TICKET_EMAIL_HOST=imap.gmail.com
  TICKET_EMAIL_PORT=993
  TICKET_EMAIL_USER=tickets@tondomaine.fr
  TICKET_EMAIL_PASS=motdepasse_app
  TICKET_EMAIL_FOLDER=INBOX
  TICKET_EMAIL_PROCESSED_FOLDER=Processed
  FLASK_LOCAL_URL=http://127.0.0.1:5000
  ANTHROPIC_API_KEY=sk-ant-...
"""

import imaplib
import email
import json
import base64
import hashlib
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from email.header import decode_header

try:
    from dotenv import load_dotenv
    load_dotenv("/root/polar/.env")
except ImportError:
    pass

# ─── CONFIG ────────────────────────────────────────────────────

POLAR            = Path("/root/polar")
HASHES_FILE      = POLAR / "ticket_hashes.json"
LOG_DIR          = POLAR / "logs"
LOG_DIR.mkdir(exist_ok=True)

IMAP_HOST        = os.getenv("TICKET_EMAIL_HOST", "imap.gmail.com")
IMAP_PORT        = int(os.getenv("TICKET_EMAIL_PORT", "993"))
IMAP_USER        = os.getenv("TICKET_EMAIL_USER", "")
IMAP_PASS        = os.getenv("TICKET_EMAIL_PASS", "")
IMAP_FOLDER      = os.getenv("TICKET_EMAIL_FOLDER", "INBOX")
IMAP_PROCESSED   = os.getenv("TICKET_EMAIL_PROCESSED_FOLDER", "Processed")
FLASK_URL        = os.getenv("FLASK_LOCAL_URL", "http://127.0.0.1:5000")
API_KEY          = os.getenv("ANTHROPIC_API_KEY", "")

KNOWN_IDS = (
    "poulet_filet,boeuf,porc,saumon_fume,dinde,oeuf,"
    "fromage_chevre,skyr,camembert,brie,comte,emmental,mozzarella,"
    "pates_cuites,riz_cuit,pain,banane,chocolat_noir,avocat,tomate,"
    "fraises,epinards,grenailles,miel,citron"
)

NUTRI_REF = (
    "VALEURS NUTRI (pour 100g sauf mention) :\n"
    "PROTEINES : poulet_filet 165kcal P31 G0 L3.6 | boeuf 217kcal P26 G0 L12 | porc 143kcal P21.5 G0 L6\n"
    "saumon_fume 172kcal P25.4 G0 L7.5 | dinde 109kcal P23 G0 L1.5\n"
    "UNITES : oeuf(1=60g) 86kcal P7.5 G0.6 L5.9\n"
    "LAITAGES : fromage_chevre 250kcal P17 G0.5 L20 | camembert 299kcal P19.8 G0.5 L24.7\n"
    "brie 334kcal P20.7 G0.5 L27.7 | comte 413kcal P29.2 G0.4 L32.4 | emmental 370kcal P28.5 G0.5 L28\n"
    "mozzarella 280kcal P17.5 G3.1 L22 | skyr(pot=500g) 63kcal/100g P11 G4 L0.3\n"
    "FECULENTS (cuits) : pates_cuites 131kcal P5 G25 L1.1 | riz_cuit 130kcal P2.7 G28.2 L0.3\n"
    "grenailles(sachet=500g) 77kcal P2 G17 L0.1 | pain 265kcal P9 G49 L3\n"
    "FRUITS/LEGUMES : banane(1=120g) 107kcal P1.3 G27 L0.4 | avocat(1=160g) 256kcal P3.2 G3.4 L24\n"
    "tomate 18kcal | fraises 32kcal | epinards 23kcal\n"
    "AUTRES : chocolat_noir 598kcal P7.8 G44 L42 | miel 304kcal P0.3 G82.4 L0\n"
)

# ─── HELPERS ───────────────────────────────────────────────────

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)

def load_hashes():
    if HASHES_FILE.exists():
        try:
            return json.loads(HASHES_FILE.read_text())
        except Exception:
            pass
    return []

def save_hashes(hashes):
    HASHES_FILE.write_text(json.dumps(hashes, ensure_ascii=False, indent=2))

def image_hash(image_bytes):
    return hashlib.sha256(image_bytes[:4096]).hexdigest()

def decode_str(s):
    """Décoder les headers email encodés."""
    if not s:
        return ""
    parts = decode_header(s)
    out = []
    for raw, enc in parts:
        if isinstance(raw, bytes):
            out.append(raw.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(raw)
    return "".join(out)

# ─── SCAN API ──────────────────────────────────────────────────

def call_scan_api(image_b64, media_type="image/jpeg"):
    """Appel direct à l'API Anthropic pour analyser un ticket."""
    if not API_KEY:
        log("⚠ ANTHROPIC_API_KEY manquante — scan ignoré")
        return []

    prompt_text = (
        "Analyse ce ticket de caisse. Extrait UNIQUEMENT les aliments "
        "(ignore produits ménagers, alcool, hygiène, non-alimentaires).\n\n"
        "RÈGLES QUANTITÉ :\n"
        "1. 'X,XXX kg × Y €/kg' → qty_g = arrondi(X×1000), qty_count=null\n"
        "2. 'N × Y €' à l'unité → qty_count=N, qty_g=N×poids_unitaire : "
        "avocat=160g, banane=120g, oeuf=60g, skyr=500g, sachet grenailles=500g, citron=100g\n"
        "3. Boîte œufs → qty_count=nb_oeufs, qty_g=nb×60\n"
        "4. Prix fixe sans quantité → estimer : poulet=600g, saumon=200g, fromage=150g, "
        "mozzarella=125g, pâtes=500g (×2.5 cuits), riz=1kg (×2 cuit), pain=400g, fraises=500g\n\n"
        f"{NUTRI_REF}\n"
        "Réponds UNIQUEMENT en JSON valide, sans markdown.\n"
        'Format : [{"food_name":"Poulet filet","qty_g":600,"qty_count":null,'
        '"food_id":"poulet_filet","category":"proteine","detail":"1 barquette ~600g"}]\n'
        f"food_id parmi : {KNOWN_IDS}\n"
        "food_id='autre' si inconnu."
    )

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1200,
        "messages": [{"role": "user", "content": [
            {"type": "image", "source": {
                "type": "base64", "media_type": media_type, "data": image_b64}},
            {"type": "text", "text": prompt_text}
        ]}]
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        raw = result["content"][0]["text"].strip()
        raw = raw.lstrip("```json").lstrip("```").rstrip("```").strip()
        articles = json.loads(raw)
        return [a for a in articles if a.get("food_id") != "autre"]
    except Exception as e:
        log(f"  ⚠ Erreur API Anthropic : {e}")
        return []

def call_fridge_import(articles):
    """POST /api/nutrition/fridge/import via l'API locale Flask."""
    if not articles:
        return False
    payload = json.dumps({"items": [
        {
            "food_id":   a["food_id"],
            "food_name": a.get("food_name", a["food_id"]),
            "stock_g":   float(a.get("qty_g", 0)),
            "qty_count": a.get("qty_count"),
        }
        for a in articles
    ]}).encode()
    req = urllib.request.Request(
        f"{FLASK_URL}/api/nutrition/fridge/import",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            d = json.loads(resp.read())
            return d.get("ok", False)
    except Exception as e:
        log(f"  ⚠ Erreur import frigo : {e}")
        return False

# ─── IMAP ──────────────────────────────────────────────────────

def ensure_folder(imap, folder):
    """Créer le dossier IMAP s'il n'existe pas."""
    try:
        status, _ = imap.select(folder)
        if status == "OK":
            return True
    except Exception:
        pass
    try:
        imap.create(folder)
        log(f"  📁 Dossier IMAP créé : {folder}")
        return True
    except Exception as e:
        log(f"  ⚠ Impossible de créer {folder} : {e}")
        return False

def get_image_attachments(msg):
    """Extraire toutes les pièces jointes image d'un email."""
    images = []
    for part in msg.walk():
        ct = part.get_content_type()
        disp = str(part.get("Content-Disposition", ""))
        if ct.startswith("image/") or "attachment" in disp:
            payload = part.get_payload(decode=True)
            if payload and len(payload) > 1000:
                # Détecter le type MIME depuis les magic bytes
                if payload[:8] == b'\x89PNG\r\n\x1a\n':
                    media_type = "image/png"
                elif payload[:3] == b'\xff\xd8\xff':
                    media_type = "image/jpeg"
                elif payload[:4] == b'GIF8':
                    media_type = "image/gif"
                else:
                    media_type = ct if ct.startswith("image/") else "image/jpeg"
                images.append({
                    "bytes":      payload,
                    "b64":        base64.b64encode(payload).decode(),
                    "media_type": media_type,
                })
    return images

# ─── MAIN ──────────────────────────────────────────────────────

def run():
    if not IMAP_USER or not IMAP_PASS:
        log("⚠ TICKET_EMAIL_USER / TICKET_EMAIL_PASS non configurés dans .env — abandon")
        sys.exit(0)

    log(f"📬 Connexion IMAP {IMAP_HOST}:{IMAP_PORT} en tant que {IMAP_USER}")
    hashes = load_hashes()
    hash_set = {h["hash"] for h in hashes}
    processed = 0
    skipped_dup = 0
    errors = 0

    try:
        imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        imap.login(IMAP_USER, IMAP_PASS)
        log(f"  ✅ Connecté")

        # Sélectionner dossier source
        status, _ = imap.select(IMAP_FOLDER)
        if status != "OK":
            log(f"  ❌ Dossier {IMAP_FOLDER} introuvable")
            imap.logout()
            return

        # Chercher les emails non lus
        status, msg_ids = imap.search(None, "UNSEEN")
        if status != "OK" or not msg_ids[0]:
            log("  📭 Aucun email non lu — rien à traiter")
            imap.logout()
            return

        ids = msg_ids[0].split()
        log(f"  📩 {len(ids)} email(s) non lu(s) à traiter")

        # S'assurer que le dossier Processed existe
        ensure_folder(imap, IMAP_PROCESSED)
        imap.select(IMAP_FOLDER)

        for msg_id in ids:
            try:
                status, data = imap.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue

                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)
                subject = decode_str(msg.get("Subject", ""))
                sender  = decode_str(msg.get("From", ""))
                log(f"\n  📧 Email de {sender} — Objet : {subject[:60]}")

                images = get_image_attachments(msg)
                if not images:
                    log(f"  ⏭  Aucune image attachée — email ignoré")
                    # Marquer comme lu quand même
                    imap.store(msg_id, "+FLAGS", "\\Seen")
                    continue

                log(f"  🖼  {len(images)} image(s) détectée(s)")
                email_imported = False

                for i, img in enumerate(images):
                    h = image_hash(img["bytes"])

                    if h in hash_set:
                        log(f"    [{i+1}] ⏭  Doublon (déjà scanné) — ignoré")
                        skipped_dup += 1
                        continue

                    log(f"    [{i+1}] 🔍 Analyse en cours via Claude Haiku...")
                    articles = call_scan_api(img["b64"], img["media_type"])

                    if not articles:
                        log(f"    [{i+1}] ⚠ Aucun aliment détecté")
                        continue

                    log(f"    [{i+1}] ✅ {len(articles)} aliment(s) détecté(s) : "
                        f"{', '.join(a['food_name'] for a in articles[:5])}")

                    ok = call_fridge_import(articles)
                    if ok:
                        log(f"    [{i+1}] ✅ Frigo mis à jour")
                        # Enregistrer le hash
                        hashes.append({
                            "hash":   h,
                            "date":   datetime.now().strftime("%Y-%m-%d"),
                            "source": "email",
                            "from":   sender[:80],
                            "items":  len(articles),
                        })
                        hash_set.add(h)
                        email_imported = True
                        processed += 1
                    else:
                        log(f"    [{i+1}] ❌ Erreur import frigo")
                        errors += 1

                # Déplacer l'email vers Processed
                imap.store(msg_id, "+FLAGS", "\\Seen")
                try:
                    imap.copy(msg_id, IMAP_PROCESSED)
                    imap.store(msg_id, "+FLAGS", "\\Deleted")
                    imap.expunge()
                    log(f"  📁 Email déplacé vers {IMAP_PROCESSED}")
                except Exception as mv_err:
                    log(f"  ⚠ Impossible de déplacer l'email : {mv_err}")

            except Exception as e:
                log(f"  ❌ Erreur traitement email {msg_id} : {e}")
                errors += 1

        imap.logout()

    except imaplib.IMAP4.error as e:
        log(f"❌ Erreur IMAP : {e}")
        sys.exit(1)
    except Exception as e:
        log(f"❌ Erreur inattendue : {e}")
        sys.exit(1)
    finally:
        save_hashes(hashes)

    log(f"\n{'='*50}")
    log(f"✅ Terminé — {processed} importé(s) | {skipped_dup} doublon(s) | {errors} erreur(s)")

if __name__ == "__main__":
    run()
