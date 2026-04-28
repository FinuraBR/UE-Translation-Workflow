import json
import os
import shutil
import glob
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    MISSING_TRANSLATION_TAG,
    MAX_CHARS_PER_CHUNK,
    REPAIR_CHUNKS_DIR,
    MASTER_TRANSLATION_FILE
)

def process_dynamic_json_repair():
    if not os.path.exists(MASTER_TRANSLATION_FILE):
        print(f"❌ Error: '{MASTER_TRANSLATION_FILE}' not found.")
        return

    found_repair_files = glob.glob(os.path.join(REPAIR_CHUNKS_DIR, '*.json'))

    if os.path.exists(REPAIR_CHUNKS_DIR) and found_repair_files:
        print(f"🔄 Folder '{REPAIR_CHUNKS_DIR}' with files detected. Starting merge...")
        
        new_translations = {}
        
        for repair_file in found_repair_files:
            try:
                with open(repair_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        key = item.get('key')
                        translation_value = item.get('Translation') or item.get('translation')
                        translation_value = str(translation_value) if translation_value is not None else ""
                        
                        if key and translation_value and MISSING_TRANSLATION_TAG not in translation_value:
                            new_translations[key] = translation_value
            except Exception as e:
                print(f"⚠️ Error reading {os.path.basename(repair_file)}: {e}")

        try:
            with open(MASTER_TRANSLATION_FILE, 'r', encoding='utf-8') as f_master:
                master_data = json.load(f_master)
            
            update_count = 0
            for item in master_data:
                key = item.get('key')
                if key in new_translations:
                    item['Translation'] = new_translations[key]
                    update_count += 1

            with open(MASTER_TRANSLATION_FILE, 'w', encoding='utf-8') as f_out:
                json.dump(master_data, f_out, ensure_ascii=False, indent=2)

            print(f"✅ SUCCESS! {update_count} items corrected in the master file.")
            shutil.rmtree(REPAIR_CHUNKS_DIR)
            print(f"🗑️  Folder '{REPAIR_CHUNKS_DIR}' removed.")
        except Exception as e:
            print(f"💥 Error updating master file: {e}")

    else:
        print(f"🔍 Searching for failures to create JSON repair batches...")
        
        try:
            with open(MASTER_TRANSLATION_FILE, 'r', encoding='utf-8') as f:
                master_data = json.load(f)
        except Exception as e:
            print(f"❌ Error reading master file: {e}")
            return

        failed_items = []
        for item in master_data:
            raw_translation_value = item.get('Translation', '')
            translation_string = str(raw_translation_value) if raw_translation_value is not None else ""
            
            if MISSING_TRANSLATION_TAG in translation_string or not translation_string:
                failed_items.append({
                    'key': item.get('key'),
                    'source': item.get('source')
                })

        if not failed_items:
            print(f"✨ Nothing to fix in '{MASTER_TRANSLATION_FILE}'!")
            return

        if not os.path.exists(REPAIR_CHUNKS_DIR): os.makedirs(REPAIR_CHUNKS_DIR)

        current_block = []
        accumulated_size = 0
        part_number = 1

        for item in failed_items:
            item_string = json.dumps(item, ensure_ascii=False)
            item_size = len(item_string)

            if (accumulated_size + item_size > MAX_CHARS_PER_CHUNK) and current_block:
                output_filename = os.path.join(REPAIR_CHUNKS_DIR, f"repair_part_{part_number:03d}.json")
                with open(output_filename, 'w', encoding='utf-8') as f_out:
                    json.dump(current_block, f_out, ensure_ascii=False, indent=2)
                
                print(f"📦 Part {part_number:03d} created with {len(current_block)} items.")
                part_number += 1
                current_block = []
                accumulated_size = 0

            current_block.append(item)
            accumulated_size += item_size

        if current_block:
            output_filename = os.path.join(REPAIR_CHUNKS_DIR, f"repair_part_{part_number:03d}.json")
            with open(output_filename, 'w', encoding='utf-8') as f_out:
                json.dump(current_block, f_out, ensure_ascii=False, indent=2)
            print(f"📦 Part {part_number:03d} created with {len(current_block)} items.")

        print(f"\n🚀 Total of {len(failed_items)} failures divided into {part_number} files.")
        print(f"📂 Translate the files in '{REPAIR_CHUNKS_DIR}' and run this script again to apply.")

if __name__ == '__main__':
    process_dynamic_json_repair()