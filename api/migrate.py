import json
import os
import uuid
from pathlib import Path
from api.db import supabase
from api.config import settings

def migrate():
    metadata_path = Path("storage/metadata.json")
    if not metadata_path.exists():
        print("No metadata.json found in storage/.")
        return

    with open(metadata_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    images = data.get("images", {})
    print(f"Found {len(images)} images to migrate.")

    if not supabase:
        print("Supabase client not initialized. Cannot migrate.")
        return

    # Set legacy identifiers from discovered real IDs in the DB
    legacy_user_id = "a383e13f-38f2-40fc-8b50-c0e461320c31"
    legacy_vault_id = "7445abb6-9ff8-4fcd-9923-a4073a3e283d"
    
    try:
        user_exists = supabase.table("users").select("id").eq("id", legacy_user_id).execute()
        if not user_exists.data:
            print(f"Creating legacy user record {legacy_user_id}...")
            supabase.table("users").insert({
                "id": legacy_user_id,
                "checkin_password_hash": settings.GALLERY_PASSWORD,
                "email": "legacy@stego.cloud"
            }).execute()
    except Exception as e:
        print(f"Warning: Could not ensure legacy user exists: {e}")

    success_count = 0
    fail_count = 0

    for img_id, entry in images.items():
        try:
            # Prepare entry for Supabase
            db_entry = entry.copy()
            
            # Use valid UUIDs for legacy identifiers
            if "user_id" not in db_entry or db_entry["user_id"] == "legacy_user":
                db_entry["user_id"] = legacy_user_id
            if "vault_id" not in db_entry or db_entry["vault_id"] == "legacy_vault":
                db_entry["vault_id"] = legacy_vault_id
            
            # Check if image already exists to avoid duplicates
            existing = supabase.table("images").select("id").eq("id", img_id).execute()
            if existing.data:
                print(f"Image {img_id} already exists in DB. Skipping.")
                continue

            # Insert into Supabase
            supabase.table("images").insert(db_entry).execute()
            print(f"Migrated image {img_id}: {entry.get('filename')}")
            success_count += 1
        except Exception as e:
            print(f"Failed to migrate {img_id}: {e}")
            fail_count += 1

    print(f"\nMigration complete!")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")

    if success_count > 0:
        # Rename the file instead of deleting it
        backup_path = metadata_path.with_suffix(".json.bak")
        try:
            metadata_path.rename(backup_path)
            print(f"Renamed {metadata_path.name} to {backup_path.name}")
        except Exception as e:
            print(f"Failed to rename metadata.json: {e}")

if __name__ == "__main__":
    migrate()
