import os
from api.storage import list_images
from api.db import supabase
from dotenv import load_dotenv

load_dotenv()

user_id = "a383e13f-38f2-40fc-8b50-c0e461320c31"
vault_id = "7445abb6-9ff8-4fcd-9923-a4073a3e283d"

print(f"--- Verification (Real Mode) ---")
images_real = list_images(user_id=user_id, vault_id=vault_id)
print(f"Total images found in real mode: {len(images_real)}")
for img in images_real[:3]:
    print(f" - {img['id']}: {img['filename']} (Hidden: {img['has_hidden_data']})")

print(f"\n--- Verification (Panic Mode) ---")
# In panic mode, we look for vault_id == user_id (the decoy vault)
# and we filter for has_hidden_data == False
images_panic = list_images(user_id=user_id, vault_id=user_id, has_hidden_data=False)
print(f"Total images found in panic mode: {len(images_panic)}")
