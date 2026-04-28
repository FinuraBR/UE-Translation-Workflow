"""
Backup Restoration Script (.json.bak -> .json).
Objective: Recursively scans the source folder and renames all files
that have the '.json.bak' extension back to '.json', undoing security
changes or previous processing.
"""

import os
from config import ORIGINAL_JSON_DIR

def restore_backups():
    print(f"🔄 Looking for .bak files in {ORIGINAL_JSON_DIR}...")
    restored_count = 0
    
    for root, _, files in os.walk(ORIGINAL_JSON_DIR):
        for file_name in files:
            if file_name.endswith(".json.bak"):
                old_path = os.path.join(root, file_name)
                
                new_path = os.path.join(root, file_name.replace(".json.bak", ".json"))
                
                try:
                    os.rename(old_path, new_path)
                    print(f"✅ Restored: {file_name} -> {os.path.basename(new_path)}")
                    restored_count += 1
                except Exception as e:
                    print(f"❌ Error renaming {file_name}: {e}")
    
    if restored_count == 0:
        print("✨ No .bak files found.")
    else:
        print(f"\n🚀 Total files restored: {restored_count}")

if __name__ == '__main__':
    restore_backups()