import json
import os
import sys
import re

from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TaskProgressColumn
from rich.text import Text
from rich.panel import Panel

from config import *

console = Console()

def is_valid_text(obj: dict, text: str) -> bool:
    if not text or not isinstance(text, str) or not text.strip():
        return False
    
    cleaned_text = text.strip()
    lower_text = cleaned_text.lower()

    if lower_text in CONTENT_BLACKLIST:
        return False

    variable_name = str(obj.get("Name", "")).lower()
    if variable_name in VARIABLE_NAME_BLACKLIST:
        return False
    
    if TEXT_FILTER_REGEX.match(cleaned_text):
        return False
    
    if " " not in cleaned_text and "_" in cleaned_text:
        return False

    return True

def extract_recursively(obj: dict | list, extracted_list: list):
    path_stack = []

    def _extract(current_obj, current_path=""):
        nonlocal extracted_list

        if isinstance(current_obj, dict):
            history_type = current_obj.get("HistoryType", "")
            flags = str(current_obj.get("Flags", ""))

            if history_type in REQUIRED_HISTORY_TYPE and FORBIDDEN_FLAG not in flags:
                obj_type = current_obj.get("Type", current_obj.get("$type", ""))
                if WHITELIST_TYPES_REGEX.search(obj_type):
                    for key_name in ["LocalizedString", "SourceString", "CultureInvariantString", "DisplayString"]:
                        if key_name in current_obj:
                            value = current_obj.get(key_name)
                            if is_valid_text(current_obj, value):
                                extracted_list.append({
                                    "p": f"{current_path}.{key_name}" if current_path else key_name,
                                    "t": value
                                })
                                return

            for k, v in current_obj.items():
                if k in ["Namespace", "Key", "Guid", "Type", "$type", "Flags", "Class", "Outer"]:
                    continue
                _extract(v, f"{current_path}.{k}" if current_path else k)
                    
        elif isinstance(current_obj, list):
            for i, item in enumerate(current_obj):
                _extract(item, f"{current_path}[{i}]")
    
    _extract(obj)


def main():
    if len(sys.argv) >= 3:
        file_name = sys.argv[1]
        file_subpath = sys.argv[2]
        target_file_info = {"name": file_name, "subpath": file_subpath}
    else:
        target_file_info = None
        for root, _, files in os.walk(ORIGINAL_JSON_DIR):
            for f in files:
                if f.endswith(".json") and not f.endswith(".bak"):
                    target_file_info = {
                        "name": f.replace(".json", ""),
                        "subpath": os.path.relpath(root, ORIGINAL_JSON_DIR)
                    }
                    break
            if target_file_info: break
    
    if not target_file_info:
        console.print(f"[bold blue]No .json files found in '{ORIGINAL_JSON_DIR}' (or all are .bak) to process. Exiting.[/]")
        sys.exit(0)

    json_file_path = os.path.join(ORIGINAL_JSON_DIR, target_file_info['subpath'], target_file_info['name'] + ".json")
    
    if not os.path.exists(json_file_path):
        console.print(f"❌ [bold red]Error: File not found at {json_file_path}[/]")
        sys.exit(1)

    console.print(f"📁 [bold white]File: [yellow]{target_file_info['name']}.json[/]")

    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    except json.JSONDecodeError as e:
        console.print(f"❌ [bold red]Error decoding JSON from {json_file_path}: {e}[/]")
        sys.exit(1)
    
    with open(PROJECT_STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump(target_file_info, f, indent=2)

    final_extracted_list = []

    with console.status("[bold green]Extracting translatable text...") as status:
        extract_recursively(json_data, final_extracted_list)
        status.update("[bold green]Text extraction completed.[/]")
    
    if not final_extracted_list:
        console.print(f"[bold blue]No translatable text found in {target_file_info['name']}.json. Skipping.[/]")
        sys.exit(10)

    os.makedirs(CHUNK_DIR_1_TO_TRANSLATE, exist_ok=True)
    
    for f in os.listdir(CHUNK_DIR_1_TO_TRANSLATE):
        try:
            os.remove(os.path.join(CHUNK_DIR_1_TO_TRANSLATE, f))
        except OSError as e:
            console.print(f"[bold red]Could not remove old chunk file {f}: {e}[/]")

    chunks, current_block, current_block_size = [], [], 0
    
    with Progress(BarColumn(), TextColumn("{task.completed}/{task.total}"), TimeElapsedColumn(),
                  TextColumn("[bold magenta]{task.description}")) as progress:
        chunk_task = progress.add_task(total=len(final_extracted_list))

        for item in final_extracted_list:
            item_size = len(json.dumps(item, ensure_ascii=False))

            if (current_block_size + item_size) > MAX_CHARS_PER_CHUNK and current_block:
                chunks.append(current_block)
                current_block, current_block_size = [], 0
            current_block.append(item)
            current_block_size += item_size
            progress.advance(chunk_task)
        if current_block: chunks.append(current_block)
    
    for idx, content in enumerate(chunks):
        with open(os.path.join(CHUNK_DIR_1_TO_TRANSLATE, f'part_{idx+1:03d}.json'), 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
    
    console.print(f"✅ [bold green]Extracted {len(final_extracted_list)} items into {len(chunks)} parts.[/]")
    sys.exit(0)

if __name__ == '__main__':
    main()
