import os
import subprocess
import sys
import time 

from config import (
    ORIGINAL_JSON_DIR,
    FINAL_MOD_DIR,
    CHUNK_DIR_1_TO_TRANSLATE,
    CHUNK_DIR_2_TRANSLATED
)

def clean_workflow_temp_dirs():
    temp_folders = {CHUNK_DIR_1_TO_TRANSLATE, CHUNK_DIR_2_TRANSLATED}
    for folder_path in temp_folders:
        if os.path.exists(folder_path):
            for file_in_dir in os.listdir(folder_path):
                full_file_path = os.path.join(folder_path, file_in_dir)
                try:
                    if os.path.isfile(full_file_path):
                        os.remove(full_file_path)
                except Exception as e:
                    print(f"⚠️ Could not delete {file_in_dir}: {e}")

def start_automation():
    try:
        target_files_list = []
        for root, _, files in os.walk(ORIGINAL_JSON_DIR):
            for f in files:
                if f.endswith(".json") and not f.endswith(".bak"):
                    target_files_list.append({
                        "name": f.replace(".json", ""),
                        "subpath": os.path.relpath(root, ORIGINAL_JSON_DIR)
                    })

        print(f"\n🚀 {len(target_files_list)} files in the verification queue.")

        for i, item in enumerate(target_files_list, 1):
            file_name = item["name"]
            subpath = item["subpath"]
            
            original_json_path = os.path.join(ORIGINAL_JSON_DIR, subpath, f"{file_name}.json")
            final_uasset_path = os.path.join(FINAL_MOD_DIR, subpath, f"{file_name}.uasset")
            backup_json_path = original_json_path + ".bak"

            if os.path.exists(final_uasset_path) or os.path.exists(backup_json_path):
                continue

            print(f"\n📦 [{i}/{len(target_files_list)}] PROCESSING: {file_name}\n📂 FOLDER: {subpath}\n")

            try:
                pause_for_blacklist_review = False

                divide_result = subprocess.run([sys.executable, "1_json_extract_and_chunk.py", file_name, subpath])

                if divide_result.returncode == 10:
                    if os.path.exists(original_json_path):
                        new_bak_name = original_json_path + ".bak"
                        if os.path.exists(new_bak_name): os.remove(new_bak_name)
                        os.rename(original_json_path, new_bak_name)
                    continue

                if divide_result.returncode != 0:
                    print(f"❌ Critical error in Step 1 for file {file_name}.")
                    break

                ai_translation_result = subprocess.run([sys.executable, "2_json_translate_chunks.py"])

                if ai_translation_result.returncode == 1:
                    break

                join_result = subprocess.run([sys.executable, "4_json_inject_translations.py", file_name, subpath])

                if join_result.returncode == 11:
                    pause_for_blacklist_review = True

                if join_result.returncode == 10:
                    print(f"✨ {file_name}: No changes necessary.")
                    clean_workflow_temp_dirs()
                    if os.path.exists(original_json_path):
                        new_bak_name = original_json_path + ".bak"
                        if os.path.exists(new_bak_name): os.remove(new_bak_name)
                        os.rename(original_json_path, new_bak_name)
                    continue

                if join_result.returncode != 0 and join_result.returncode != 11:
                    print(f"❌ Critical error in Step 4 for file {file_name}.")
                    break

                subprocess.run([sys.executable, "5_json_to_uasset_conversion.py", file_name, subpath], check=True)

                print(f"\n✅ SUCCESS: {file_name} finalized.")
                
                time.sleep(0.1)

                if pause_for_blacklist_review:
                    print("\n🛑 WORKFLOW PAUSED! New terms detected for Blacklist.")
                    break
                
            except subprocess.CalledProcessError as e:
                print(f"\n❌ ERROR in subprocess: {e}")
                break

    except Exception as e:
        print(f"\n⚠️ Unexpected error: {e}")

if __name__ == "__main__":
    start_automation()