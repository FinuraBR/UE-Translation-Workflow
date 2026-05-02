import os
import json
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import *

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_INPUT_FILE = os.path.join(SCRIPT_DIR, 'csvjson.json')
OUTPUT_CHUNK_DIR = os.path.join(SCRIPT_DIR, '1_partes_para_traduzir')

def split_json_intelligently():
    if not os.path.exists(OUTPUT_CHUNK_DIR):
        os.makedirs(OUTPUT_CHUNK_DIR)

    print(f"Reading {ORIGINAL_INPUT_FILE}...")

    try:
        with open(ORIGINAL_INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ ERROR reading file: {e}")
        return

    if not isinstance(data, list):
        print("❌ ERROR: The JSON file must contain a LIST of objects at the top level.")
        return

    if not data:
        print("The file is empty!")
        return

    print(f"\n✅ Found {len(data)} records. Splitting by text size...")

    item_buffer = []
    current_buffer_size = 0
    file_counter = 1

    for item in data:
        item_string = json.dumps(item, ensure_ascii=False, indent=2)
        item_size = len(item_string)

        if (current_buffer_size + item_size) > MAX_CHARS_PER_CHUNK and item_buffer:
            save_json_chunk(item_buffer, file_counter)
            file_counter += 1
            item_buffer = []
            current_buffer_size = 0

        item_buffer.append(item)
        current_buffer_size += item_size + 2

    if item_buffer:
        save_json_chunk(item_buffer, file_counter)

    print(f"\n🚀 Success! {len(data)} entries divided into {file_counter} files.\n")
    print(f"Folder: {OUTPUT_CHUNK_DIR}")

def save_json_chunk(data_to_save: list, part_number: int):
    file_name = os.path.join(OUTPUT_CHUNK_DIR, f'part_{part_number:03d}.json')
    
    with open(file_name, 'w', encoding='utf-8') as f_out:
        json.dump(data_to_save, f_out, ensure_ascii=False, indent=2)
    
    print(f"  -> Generated: part_{part_number:03d}.json ({len(data_to_save)} entries)")

if __name__ == '__main__':
    split_json_intelligently()
