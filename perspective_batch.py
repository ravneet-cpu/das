import os
from search_operacrm_corrected import OperaCRMClient

PERS_DIR = "/app/photos/Perspective"

print("🗑️ Starting FULL Perspective Cleanup...")

# ---------- Odoo Login ----------
opera = OperaCRMClient()
if not opera.authenticate("odoo_restore", "frederic@faucouneau.fr", "ONc8VxiDFnSgCuwSkArqur3Sj1WFZhov"):
    print("❌ ODOO LOGIN FAILED")
    exit()

print("✅ Logged in to Odoo")

deleted_files = 0
odoo_cleaned = 0

# Delete all perspective images
for file in os.listdir(PERS_DIR):
    if file.lower().endswith(".jpg") and "_PERS" in file:
        file_path = os.path.join(PERS_DIR, file)

        try:
            os.remove(file_path)
            deleted_files += 1
            print(f"🗑️ Deleted file: {file_path}")
        except Exception as e:
            print(f"❌ Error deleting {file}: {e}")

        # Extract ID from filename
        record_id_part = file.split("_")[0]
        try:
            records = opera.search_by_idname(record_id_part)
            if records:
                record_id = records[0]["id"]
                opera.update_artwork_record(record_id, {"perspective_url": False})
                print(f"🧼 Odoo cleaned: {record_id_part}")
                odoo_cleaned += 1
        except Exception as e:
            print(f"❌ Odoo update failed for {file}: {e}")

# Summary
print("\n===== DONE =====")
print(f"🗑️ Files deleted: {deleted_files}")
print(f"🧼 Odoo records cleaned: {odoo_cleaned}")
print("🎉 Cleanup Completed Successfully!")
