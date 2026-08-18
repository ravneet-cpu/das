#!/usr/bin/env python3
"""
ODOO BACKFILL — FULL DATASET (37k SAFE)

RULES:
1) if main_super_picture_hd exists -> SKIP
2) else if main_picture_hd exists -> SKIP
3) else:
   - if frame_picture exists -> copy to main_picture_hd
   - else if other_url exists -> copy to main_picture_hd
"""

import time
import requests

ODOO_URL = "https://2.operacrm.com"
ODOO_DB = "odoo_restore"
ODOO_USER = "frederic@faucouneau.fr"
ODOO_PASS = "ONc8VxiDFnSgCuwSkArqur3Sj1WFZhov"

BATCH_SIZE = 200
SLEEP = 0.3   # safe for Odoo


def log(msg):
    print(time.strftime("[%H:%M:%S]"), msg, flush=True)


def login(session):
    r = session.post(f"{ODOO_URL}/web/session/authenticate", json={
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": ODOO_DB,
            "login": ODOO_USER,
            "password": ODOO_PASS
        },
        "id": 1
    })
    r.raise_for_status()
    if not r.json().get("result", {}).get("uid"):
        raise Exception("Login failed")
    log("✅ Odoo login OK")


def fetch_batch(session, offset):
    r = session.post(f"{ODOO_URL}/web/dataset/call_kw", json={
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": "product.template",
            "method": "search_read",
            "args": [],
            "kwargs": {
                "domain": [["active", "=", True]],
                "fields": [
                    "id",
                    "IdName",
                    "main_super_picture_hd",
                    "main_picture_hd",
                    "frame_picture",
                    "other_url"
                ],
                "limit": BATCH_SIZE,
                "offset": offset
            }
        },
        "id": 2
    })
    r.raise_for_status()
    return r.json().get("result", [])


def update_main(session, rec_id, url):
    session.post(f"{ODOO_URL}/web/dataset/call_kw", json={
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": "product.template",
            "method": "write",
            "args": [[rec_id], {
                "main_picture_hd": url,
                "image_url": url
            }]
        },
        "id": 3
    })


def main():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})

    login(session)

    offset = 0
    total_updated = 0

    while True:
        log(f"📦 Fetching artworks offset={offset}")
        artworks = fetch_batch(session, offset)

        if not artworks:
            log("🎉 DONE — reached end of dataset")
            break

        for art in artworks:
            if art.get("main_super_picture_hd") or art.get("main_picture_hd"):
                continue

            fallback = art.get("frame_picture") or art.get("other_url")
            if not fallback:
                continue

            update_main(session, art["id"], fallback)
            total_updated += 1
            log(f"✅ {art.get('IdName')} updated")

        offset += BATCH_SIZE
        time.sleep(SLEEP)

    log(f"🏁 FINISHED — total updated: {total_updated}")


if __name__ == "__main__":
    main()
