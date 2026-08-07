#!/usr/bin/env python3
"""
Migration script: Send old validated videos to HLS streaming server
and update local DB + FileMaker + Odoo with HLS URLs.

Run inside Docker:
  docker exec -it photo-validator python migrate_videos_to_hls.py

Or locally (set DB path manually):
  python3 migrate_videos_to_hls.py
"""

import sqlite3
import requests
import sys
import os
import time

# ── Config ──────────────────────────────────────────────────────────────────
DB_PATH = os.environ.get('DB_PATH', '/app/data/photo_validator.db')
if not os.path.exists(DB_PATH):
    DB_PATH = '/home/projet/photo-validator/data/photo_validator.db'

STREAMING_API = "https://video.operagallery.com/api/import"
IMAGES_BASE   = "https://images.operagallery.com/video"

_VIDEO_FIELD_MAP = {
    'VIDEO_PRESENTATION_1': 'VideoPresentationUrl1',
    'VIDEO_PRESENTATION_2': 'VideoPresentationUrl2',
    'VIDEO_DETAIL_1':       'VideoDetailUrl1',
    'VIDEO_DETAIL_2':       'VideoDetailUrl2',
    'VIDEO_INSTALLATION_1': 'VideoInstallationUrl1',
    'VIDEO_INSTALLATION_2': 'VideoInstallationUrl2',
    'VIDEO_TIMELAPSE_1':    'VideoTimelapseUrl1',
    'VIDEO_TIMELAPSE_2':    'VideoTimelapseUrl2',
    'VIDEO_DOCUMENTARY_1':  'VideoDocumentaryUrl1',
    'VIDEO_DOCUMENTARY_2':  'VideoDocumentaryUrl2',
    'VIDEO_INTERVIEW_1':    'VideoInterviewUrl1',
    'VIDEO_INTERVIEW_2':    'VideoInterviewUrl2',
}

# ── Helpers ──────────────────────────────────────────────────────────────────
def send_to_streaming(filename):
    """Send video to streaming server. Returns (hls_url, mp4_url) or (None, None)."""
    source_url = f"{IMAGES_BASE}/{filename}"
    mp4_url    = source_url
    try:
        resp = requests.post(
            STREAMING_API,
            json={"url": source_url, "title": filename},
            timeout=60
        )
        if resp.ok:
            vid_id  = resp.json().get("id")
            hls_url = f"https://video.operagallery.com/hls/{vid_id}/master.m3u8"
            print(f"  ✅ Streaming server OK — ID={vid_id}")
            return hls_url, mp4_url
        else:
            print(f"  ❌ Streaming server error {resp.status_code}: {resp.text[:200]}")
            return None, None
    except Exception as e:
        print(f"  ❌ Streaming server unreachable: {e}")
        return None, None


def update_filemaker(artwork_id, field, value):
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from filemaker_service import FileMakerService
        fm = FileMakerService()
        fm.update_specialized_field(artwork_id, field, value)
        print(f"  📁 FM updated: {field} = {value[:60]}...")
    except Exception as e:
        print(f"  ⚠️  FM update failed: {e}")


def update_odoo(artwork_id, classification, hls_url, mp4_url):
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from search_operacrm_corrected import OperaCRMClient
        opera = OperaCRMClient()
        if not opera.authenticate("odoo_15", "surafelwubshet7@gmail.com", "Surafell"):
            print("  ⚠️  Odoo auth failed")
            return

        records = opera.search_by_idname(artwork_id)
        if not records:
            print(f"  ⚠️  Odoo: artwork {artwork_id} not found")
            return

        r_id = records[0]["id"]
        odoo_field = _VIDEO_FIELD_MAP.get(classification)
        update_data = {}

        if odoo_field:
            update_data[odoo_field] = hls_url
            if mp4_url and odoo_field.endswith("Url1"):
                update_data[odoo_field[:-1] + "2"] = mp4_url

        if update_data:
            opera.update_artwork_record(r_id, update_data)
            print(f"  🟢 Odoo fields updated: {list(update_data.keys())}")

        # Add HLS media.bunny record (MP4 record should already exist)
        opera.create("product.media.bunny", {
            "product_id": r_id,
            "media_type": "video",
            "media_url":  hls_url,
            "media_name": artwork_id + " (HLS)",
            "is_uploaded": True
        })
        print(f"  🟢 Odoo media.bunny HLS record created")

    except Exception as e:
        print(f"  ⚠️  Odoo update failed: {e}")


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*60}")
    print(f"Video HLS Migration — DB: {DB_PATH}")
    print(f"{'='*60}\n")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    rows = cursor.execute("""
        SELECT id, photo_filename, artwork_id, classification
        FROM photo_validations
        WHERE status = 'validated'
          AND classification LIKE 'VIDEO_%'
          AND (streaming_url IS NULL OR streaming_url = '')
        ORDER BY id
    """).fetchall()

    print(f"Found {len(rows)} video(s) without HLS URL\n")

    if not rows:
        print("Nothing to migrate. ✅")
        conn.close()
        return

    success = 0
    failed  = 0

    for row_id, filename, artwork_id, classification in rows:
        print(f"[{artwork_id}] {filename}")

        hls_url, mp4_url = send_to_streaming(filename)

        if not hls_url:
            print(f"  ⏭️  Skipping (streaming server failed)\n")
            failed += 1
            continue

        # 1) Update local DB
        cursor.execute(
            "UPDATE photo_validations SET streaming_url = ? WHERE id = ?",
            (hls_url, row_id)
        )
        conn.commit()
        print(f"  💾 DB updated: streaming_url = {hls_url[:60]}...")

        # 2) Update FileMaker
        fm_field = _VIDEO_FIELD_MAP.get(classification)
        if fm_field:
            update_filemaker(artwork_id, fm_field, hls_url)
            if mp4_url and fm_field.endswith("Url1"):
                update_filemaker(artwork_id, fm_field[:-1] + "2", mp4_url)

        # 3) Update Odoo
        update_odoo(artwork_id, classification, hls_url, mp4_url)

        success += 1
        print()
        time.sleep(1)  # small pause between API calls

    conn.close()
    print(f"\n{'='*60}")
    print(f"Migration complete: {success} success, {failed} failed")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
