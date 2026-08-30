#!/usr/bin/env python3
"""
refresh_quotes.py — Rafraîchit le cache de cours boursiers/crypto.
Lit dynamiquement les positions PEA/CTO/Crypto actuelles, interroge
Yahoo Finance et CoinGecko, écrit le résultat dans data/quotes_cache.json.

CRON (toutes les 30 min) :
  */30 * * * * /root/venv/bin/python3 /root/polar/refresh_quotes.py >> /root/polar/logs/quotes.log 2>&1
"""

import json, sys, time
import urllib.request as _ur
from pathlib import Path
from datetime import datetime, timezone

POLAR = Path("/root/polar")
INV_FILE = POLAR / "finances" / "finances_investments.json"
CACHE_FILE = POLAR / "data" / "quotes_cache.json"

USD_SYMS = {"MSFT", "NVDA", "BLK", "MA", "V", "ORCL", "AMD", "CVX", "XOM", "IGLN.L", "ISLN.L"}
KRW_SYMS = {"005930.KS"}


def load_symbols():
    """Lit dynamiquement les symboles PEA/CTO actuels depuis finances_investments.json."""
    if not INV_FILE.exists():
        return [], []
    try:
        inv = json.loads(INV_FILE.read_text(encoding="utf-8"))
    except Exception:
        return [], []

    symbols = []
    for section in ("pea", "cto"):
        for key, pos in (inv.get(section) or {}).items():
            sym = pos.get("symbol") or key
            if sym and sym not in symbols:
                symbols.append(sym)

    crypto_ids = list((inv.get("crypto") or {}).keys())
    return symbols, crypto_ids


def fetch_yahoo(symbol, timeout=5):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
        req = _ur.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with _ur.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read())
        return d["chart"]["result"][0]["meta"].get("regularMarketPrice")
    except Exception:
        return None


def fetch_quotes(symbols):
    result = {}
    eurusd = fetch_yahoo("EURUSD=X") or 1.0
    eurgbp = fetch_yahoo("EURGBP=X") or 1.15

    for sym in symbols[:40]:
        result[sym] = fetch_yahoo(sym)
        time.sleep(0.15)  # éviter de bombarder Yahoo trop vite

    result["__eurusd"] = eurusd
    result["__eurgbp"] = eurgbp
    return result


def fetch_crypto(ids):
    if not ids:
        return {}
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(ids)}&vs_currencies=eur"
        req = _ur.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with _ur.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception:
        return {}


def main():
    print(f"\n📈 Rafraîchissement des cours — {datetime.now(timezone.utc).isoformat()}")

    symbols, crypto_ids = load_symbols()
    print(f"   Symboles actions/PEA/CTO : {len(symbols)} ({', '.join(symbols)})")
    print(f"   IDs crypto : {', '.join(crypto_ids) if crypto_ids else 'aucun'}")

    quotes = fetch_quotes(symbols)
    crypto = fetch_crypto(crypto_ids)

    ok_quotes = sum(1 for k, v in quotes.items() if not k.startswith("__") and v is not None)
    ok_crypto = sum(1 for v in crypto.values() if v and v.get("eur") is not None)

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "quotes": quotes,
        "crypto": crypto,
    }

    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"   ✅ {ok_quotes}/{len(symbols)} cours actions récupérés, "
          f"{ok_crypto}/{len(crypto_ids)} cours crypto récupérés")
    print(f"   📁 Écrit dans {CACHE_FILE}")


if __name__ == "__main__":
    main()
