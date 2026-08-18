#!/usr/bin/env python3
import os
import time
import requests
from urllib.parse import quote
from image_processor import create_a5
from filemaker_service import filemaker_service
from search_operacrm_corrected import OperaCRMClient

# ================= CONFIG =================

FM_SERVER = "178.248.210.53"
DATABASE = "OperaGallery"
LAYOUT = "Artworks"

FM_IMAGE_DIR = "/app/photos/FM"
A5_DIR = "/app/photos/A5"

A5_PUBLIC_BASE = "https://images.operagallery.com/A5"

BATCH_SIZE = 100
START_OFFSET = 0   # ⬅️ yahin se resume karo
SLEEP_BETWEEN_BATCH = 1

ODOO_DB = "odoo_restore"
ODOO_USER = "frederic@faucouneau.fr"
ODOO_PASS = "ONc8VxiDFnSgCuwSkArqur3Sj1WFZhov"

# ==========================================

os.makedirs(A5_DIR, exist_ok=True)


def log(msg):
    print(time.strftime("[%H:%M:%S]"), msg, flush=True)


def fetch_records(offset):
    url = f"https://{FM_SERVER}/fmi/data/vLatest/databases/{DATABASE}/layouts/{LAYOUT}/records"
    params = {"_offset": offset, "_limit": BATCH_SIZE}

    resp = filemaker_service.session.get(url, params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()["response"]["data"]


def main():
    if not filemaker_service.connect():
        log("❌ FileMaker connect failed")
        return

    odoo = OperaCRMClient()
    if not odoo.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS):
        log("❌ Odoo auth failed")
        return

    offset = START_OFFSET

    while True:
        log(f"📦 Fetching records offset={offset}")
        try:
            records = fetch_records(offset)
        except Exception as e:
            log(f"⛔ Fetch error: {e}")
            time.sleep(10)
            continue

        if not records:
            log("✅ DONE — no more records")
            break

        for rec in records:
            fd = rec["fieldData"]
            record_id = rec["recordId"]

            artwork_id = fd.get("IdName")
            mainfm = fd.get("MAINFM")
            a5_existing = fd.get("UrlMainA5")

            if not artwork_id:
                continue

            if a5_existing:
                log(f"⏭️ {artwork_id} | A5 already exists")
                continue

            if not mainfm:
                log(f"⏭️ {artwork_id} | no MAINFM")
                continue

            fm_file = os.path.join(FM_IMAGE_DIR, os.path.basename(mainfm))
            if not os.path.exists(fm_file):
                log(f"❌ {artwork_id} | FM file missing")
                continue

            try:
                a5_name = f"{artwork_id}_A5.jpg"
                a5_path = os.path.join(A5_DIR, a5_name)

                if not os.path.exists(a5_path):
                    create_a5(fm_file, a5_path)

                a5_url = f"{A5_PUBLIC_BASE}/{quote(a5_name)}"

                # -------- FileMaker update --------
                filemaker_service.update_artwork(
                    record_id,
                    {"UrlMainA5": a5_url}
                )

                # -------- Odoo update --------
                recs = odoo.search_by_idname(artwork_id)
                if recs:
                    odoo.update_artwork_record(
                        recs[0]["id"],
                        {"main_a6_picture": a5_url}
                    )

                log(f"✅ {artwork_id} | A5 generated & synced")

            except Exception as e:
                log(f"❌ {artwork_id} | ERROR {e}")

        offset += BATCH_SIZE
        time.sleep(SLEEP_BETWEEN_BATCH)

    filemaker_service.disconnect()
    try:
        odoo.session.close()
    except:
        pass


if __name__ == "__main__":
    main()
