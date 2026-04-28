import os
import glob
import json
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    MISSING_TRANSLATION_TAG,
    FINAL_TRANSLATION_FILE,
    TRANSLATED_CHUNKS_DIR,
    ORIGINAL_CHUNKS_DIR
)

def join_and_correct_json():
    original_chunk_files = sorted(glob.glob(os.path.join(ORIGINAL_CHUNKS_DIR, '*.json')))
    translated_chunk_files = sorted(glob.glob(os.path.join(TRANSLATED_CHUNKS_DIR, '*.json')))

    if not original_chunk_files:
        print(f"❌ No original files found in: {ORIGINAL_CHUNKS_DIR}")
        return

    print(f"--- STARTING SMART MERGE OF {len(original_chunk_files)} JSON FILES ---")

    ai_translations = {}
    for translated_file in translated_chunk_files:
        try:
            with open(translated_file, 'r', encoding='utf-8') as f_translated:
                translated_data_chunks = json.load(f_translated)
                
                for item in translated_data_chunks:
                    key = item.get('key')
                    translation_value = item.get('Translation') or item.get('translation')
                    
                    if key and translation_value is not None:
                        ai_translations[key] = translation_value
        except Exception as e:
            print(f"⚠️ Error reading translated part {os.path.basename(translated_file)}: {e}")

    final_list = []
    missing_lines = 0
    original_keys = set()

    for original_file in original_chunk_files:
        try:
            with open(original_file, 'r', encoding='utf-8') as f_original:
                original_data_chunks = json.load(f_original)
                
                for item in original_data_chunks:
                    key = item.get('key')
                    source = item.get('source')
                    original_keys.add(key)
                    
                    raw_translation = ai_translations.get(key, "")
                    
                    if isinstance(raw_translation, list):
                        processed_translation = " ".join(str(x) for x in raw_translation).strip()
                    elif raw_translation is None:
                        processed_translation = ""
                    else:
                        processed_translation = str(raw_translation).strip()

                    if not processed_translation or processed_translation == "None":
                        processed_translation = MISSING_TRANSLATION_TAG
                        missing_lines += 1
                    
                    new_item = item.copy()
                    new_item['Translation'] = processed_translation
                    final_list.append(new_item)
                    
        except Exception as e:
            print(f"💥 Critical error reading original {os.path.basename(original_file)}: {e}")

    try:
        with open(FINAL_TRANSLATION_FILE, 'w', encoding='utf-8') as f_out:
            json.dump(final_list, f_out, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Error saving final file: {e}")
        return

    translated_keys = set(ai_translations.keys())
    invented_keys_count = len(translated_keys - original_keys)

    print("-" * 50)
    print(f"🚀 SUCCESS! Final file generated: {os.path.basename(FINAL_TRANSLATION_FILE)}")
    print(f"📊 Total processed objects: {len(final_list)}")
    
    if missing_lines > 0 or invented_keys_count > 0:
        print("\n⚠️ SYNCHRONIZATION REPORT:")
        if invented_keys_count > 0:
            print(f"   Ghost Keys: {invented_keys_count} invented entries by AI were discarded.")
        if missing_lines > 0:
            print(f"   Missing: {missing_lines} unfound entries received the tag {MISSING_TRANSLATION_TAG}.")
    else:
        print("\n✅ Perfect synchronization! All fields translated.")
    print("-" * 50)

if __name__ == '__main__':
    join_and_correct_json()