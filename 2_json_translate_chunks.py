import os
import json
import time
import re
import threading
import sys
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from rich.live import Live
from rich.console import Group
from rich.text import Text
from rich.rule import Rule
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn

from config import *

console = Console()

try:
    from openai import OpenAI
    from openai import APIStatusError
except ImportError:
    console.print("❌ [bold red]Error: The 'openai' library is not installed. Please run 'pip install openai'.[/]")
    sys.exit(1)

client = OpenAI(
    api_key=API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

input_folder = CHUNK_DIR_1_TO_TRANSLATE
output_folder = CHUNK_DIR_2_TRANSLATED

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

SYSTEM_PROMPT = """EN->PT-BR Game JSON Localizer. Raw JSON output only. No markdown.
1. Copy 'p' verbatim. NEVER alter paths.
2. Translate 't' values only."""

translation_lock = threading.Lock()
translation_successes = 0
translation_failures = 0
current_translation_file = "Waiting..."

def get_dynamic_workers(total_files):
    return min(os.cpu_count(), total_files)

def generate_translation_layout(total_files, workers, progress_bar):
    return Group(
        Text(f"🤖 Translating {total_files} chunks with {workers} threads...", style="bold magenta"),
        Text(f"📁 File: {current_translation_file}", style="blue", overflow="ellipsis"),
        Text(f"✅ Success: {translation_successes} | ❌ Failures: {translation_failures}", style="white"),
        Rule(characters="="),
        progress_bar
    )

def validate_tag_integrity(original_text: str, translated_text: str) -> bool:
    pattern = re.compile(r'\{.*?\}|<.*?>|%[sd]')
    original_tags = pattern.findall(original_text)
    translated_tags = pattern.findall(translated_text)
    return len(original_tags) == len(translated_tags)

def clean_ai_response(raw_text_response: str):
    try:
        raw_data = json.loads(raw_text_response)
        if isinstance(raw_data, dict) and "data" in raw_data:
            translated_list = raw_data["data"]
        elif isinstance(raw_data, list):
            translated_list = raw_data
        else:
            return None
        return json.dumps(translated_list, ensure_ascii=False, indent=2)
    except Exception as e:
        return None

def check_final_status() -> bool:
    input_files = set([f for f in os.listdir(input_folder) if f.endswith('.json')])
    output_files = set([f for f in os.listdir(output_folder) if f.endswith('.json')])
    
    missing_files = input_files - output_files
    if missing_files:
        console.print(f"\n❌ [bold red]ERROR: {len(missing_files)} files are missing from output:[/]")
        for f_name in missing_files:
            console.print(f"  - [red]{f_name}[/]")
        return False
    
    for f in output_files:
        path = os.path.join(output_folder, f)
        if os.path.getsize(path) < 10:
            console.print(f"❌ [bold red]ERROR: Output file {f} is incomplete or empty.[/]")
            return False
    return True

def ai_call_thread(text_to_translate: str, result_container: dict):
    try:
        response = client.chat.completions.create(
            model=AI_MODEL_NAME,
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text_to_translate}
            ],
            temperature=AI_TEMPERATURE,
            extra_body={
                'extra_body': {
                    "google": {
                    "thinking_config": {
                        "thinking_level": "high"
                    }
                    }
                }
            }
        )
        extracted_text = response.choices[0].message.content
        if extracted_text:
            result_container['result'] = clean_ai_response(extracted_text)
        else:
            result_container['error'] = "AI returned an empty response."
    except Exception as e:
        result_container['error'] = str(e)

def get_safe_translation(original_text_json: str, file_name: str, live) -> str | None:
    for attempt in range(1, AI_MAX_RETRIES + 1):
        
        container = {'result': None, 'error': None}
        thread = threading.Thread(target=ai_call_thread, args=(original_text_json, container))
        thread.daemon = True
        thread.start()
        
        thread.join(timeout=AI_TIMEOUT_SECONDS)
        
        if thread.is_alive():
            live.console.print(f"⏳ [yellow][{file_name}] Timeout (Attempt {attempt})[/]")
            continue
            
        if container['error']:
            error_message = str(container['error'])
            if "429" in error_message or "RESOURCE_EXHAUSTED" in error_message:
                wait_time = (60) + random.uniform(0, 1)
                live.console.print(f"⚠️ [yellow][{file_name}] Rate limit hit. Waiting {wait_time:.2f}s... (Attempt {attempt})[/]")
                time.sleep(wait_time)
            else:
                live.console.print(f"❌ [bold red][{file_name}] Error: {error_message} (Attempt {attempt})[/]")
            continue
            
        if container['result']:
            return container['result']
            
    return None

def process_single_file_task(file_name: str, progress, task_id, live, total_files, workers):
    global translation_successes, translation_failures, current_translation_file
    
    with translation_lock:
        current_translation_file = file_name

    input_path = os.path.join(input_folder, file_name)
    output_path = os.path.join(output_folder, file_name)
    
    if os.path.exists(output_path):
        with translation_lock:
            translation_successes += 1
        progress.advance(task_id)
        live.update(generate_translation_layout(total_files, workers, progress))
        return

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        
        expected_item_count = len(original_data)
        
        raw_ai_response = get_safe_translation(json.dumps(original_data, ensure_ascii=False), file_name, live)
        
        if not raw_ai_response: 
            with translation_lock:
                translation_failures += 1
            live.console.print(f"❌ [bold red]Critical failure in {file_name}: AI returned no data after multiple attempts.[/]")
            progress.advance(task_id)
            live.update(generate_translation_layout(total_files, workers, progress))
            return

        translated_data = json.loads(raw_ai_response)
        
        if isinstance(translated_data, dict):
            for key in translated_data:
                if isinstance(translated_data[key], list):
                    translated_data = translated_data[key]
                    break

        if not isinstance(translated_data, list) or len(translated_data) != expected_item_count:
            with translation_lock:
                translation_failures += 1
            live.console.print(f"❌ [bold red]{file_name}: Incorrect item count ({len(translated_data)}/{expected_item_count}) from AI response.[/]")
            progress.advance(task_id)
            live.update(generate_translation_layout(total_files, workers, progress))
            return

        for i in range(expected_item_count):
            if not validate_tag_integrity(original_data[i]['t'], translated_data[i]['t']):
                with translation_lock:
                    translation_failures += 1
                live.console.print(f"❌ [bold red]{file_name}: Corrupted tags at index {i} in AI response.[/]")
                progress.advance(task_id)
                live.update(generate_translation_layout(total_files, workers, progress))
                return
            
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(translated_data, f, indent=2, ensure_ascii=False)

        with translation_lock:
            translation_successes += 1
        
    except Exception as e:
        with translation_lock:
            translation_failures += 1
        live.console.print(f"❌ [bold red]Unexpected error in {file_name}: {e}[/]")
    finally:
        progress.advance(task_id)
        live.update(generate_translation_layout(total_files, workers, progress))

def execute_parallel_translation():
    all_files = sorted([f for f in os.listdir(input_folder) if f.endswith(".json")])
    
    if not all_files:
        console.print("[bold blue]No JSON chunks found to translate.[/]")
        return
    
    total_to_process = len(all_files)
    workers = get_dynamic_workers(total_to_process)
    
    global translation_successes, translation_failures, current_translation_file
    translation_successes = 0
    translation_failures = 0
    current_translation_file = "Waiting..."

    progress = Progress(TextColumn("[bold blue]{task.description}"), BarColumn(), TimeElapsedColumn())
    task = progress.add_task("Translating Chunks", total=total_to_process)
    
    with Live(generate_translation_layout(total_to_process, workers, progress), refresh_per_second=10) as live:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(process_single_file_task, file_name, progress, task, live, total_to_process, workers) for file_name in all_files]
            
    if translation_failures > 0:
        console.print(f"\n⚠️ [bold yellow]The workflow finished with {translation_failures} pending issues.[/]")
        sys.exit(1)
    else:
        console.print(f"\n🏁 [bold green]Translation workflow successfully completed.[/]")

def main():
    execute_parallel_translation()

    if check_final_status():
        console.print(f"✅ [bold green]Final output directories are complete and valid.[/]")
    else:
        console.print(f"❌ [bold red]There are issues with the final output directories.[/]")
        sys.exit(1)

if __name__ == '__main__':
    main()
