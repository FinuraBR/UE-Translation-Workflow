import sys
import mmap
import shutil
import subprocess
import os
import threading
import signal
import logging
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from rich.live import Live
from rich.console import Group
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule
from rich.progress import Progress, BarColumn, TimeElapsedColumn

from config import (
    UASSET_GUI_PATH, UE_VERSION, RAW_ASSETS_PATH,
    FILTERED_ASSETS_PATH, ORIGINAL_JSON_DIR, BINARY_KEYWORDS
)

RAW_ASSETS_PATH_OBJ = Path(RAW_ASSETS_PATH)
FILTERED_ASSETS_PATH_OBJ = Path(FILTERED_ASSETS_PATH)
ORIGINAL_JSON_DIR_OBJ = Path(ORIGINAL_JSON_DIR)
UASSET_GUI_EXE_OBJ = Path(UASSET_GUI_PATH)

ENCODED_BINARY_KEYWORDS = [kw if isinstance(kw, bytes) else kw.encode('utf-8') for kw in BINARY_KEYWORDS]

progress_lock = threading.Lock()
shutdown_flag = threading.Event()
accepted_count = 0
rejected_count = 0
current_file_name = "Starting..."

conv_start_time = 0
conv_current_file = "Starting..."
conv_successes = 0

logging.basicConfig(
    filename='workflow_errors.log', 
    level=logging.ERROR, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

def signal_handler(sig, frame):
    print("\n🛑 Interrupt detected! Safely terminating threads...")
    shutdown_flag.set()

signal.signal(signal.SIGINT, signal_handler)

def get_dynamic_workers(total_files):
    return min(os.cpu_count(), total_files)

def validate_environment():
    if not RAW_ASSETS_PATH_OBJ.exists():
        print(f"⚠️ Raw assets folder not found at: {RAW_ASSETS_PATH_OBJ}")
        RAW_ASSETS_PATH_OBJ.mkdir(parents=True, exist_ok=True)
        sys.exit(0)
    FILTERED_ASSETS_PATH_OBJ.mkdir(parents=True, exist_ok=True)
    ORIGINAL_JSON_DIR_OBJ.mkdir(parents=True, exist_ok=True)

def generate_filter_layout(total_files, progress_bar):
    return Panel(
        Group(
            Text(f"📁 File: {current_file_name}", style="yellow", overflow="ellipsis"),
            Text(f"✅ Accepted: {accepted_count} | ❌ Rejected: {rejected_count} | Total: {total_files}", style="green"),
            Rule(style="dim white"),
            progress_bar
        ),
        title="[bold blue]Asset Pre-Processing",
        border_style="blue",
        padding=(0, 0)
    )

def generate_conv_layout(total_files, progress_bar):
    elapsed = time.time() - conv_start_time
    speed = conv_successes / elapsed if elapsed > 0 else 0
    return Panel(
        Group(
            Text(f"📁 File: {conv_current_file}", style="cyan", overflow="ellipsis"),
            Text(f"✅ Converted: {conv_successes}/{total_files} | ⚡ Speed: {speed:.1f} files/s", style="green"),
            Rule(style="dim white"),
            progress_bar
        ),
        title="[bold green]JSON Conversion",
        border_style="green",
        padding=(0, 0)
    )

def contains_text(file_path: Path) -> bool:
    if file_path.stat().st_size == 0: return False
    try:
        with file_path.open('rb') as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            return any(mm.find(kw) != -1 for kw in ENCODED_BINARY_KEYWORDS)
    except Exception: return False

def process_filter_task(source_path: Path, progress, task_id, live, total_files):
    if shutdown_flag.is_set(): return

    global accepted_count, rejected_count, current_file_name
    
    with progress_lock:
        current_file_name = source_path.name
    
    if contains_text(source_path):
        dest = FILTERED_ASSETS_PATH_OBJ / source_path.relative_to(RAW_ASSETS_PATH_OBJ)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, dest)
        uexp = source_path.with_suffix(".uexp")
        if uexp.exists(): shutil.copy2(uexp, dest.with_suffix(".uexp"))
        
        with progress_lock:
            accepted_count += 1
    else:
        with progress_lock:
            rejected_count += 1
            
    progress.advance(task_id)
    live.update(generate_filter_layout(total_files, progress))

def filter_asset_files_parallel():
    all_files = list(RAW_ASSETS_PATH_OBJ.rglob("*.uasset"))
    total = len(all_files)
    workers = get_dynamic_workers(total)
    
    progress = Progress(BarColumn(), TimeElapsedColumn())
    task = progress.add_task("Filtering...", total=total)
    
    with Live(generate_filter_layout(total, progress), refresh_per_second=10) as live:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            [executor.submit(process_filter_task, path, progress, task, live, total) for path in all_files]

    return list(FILTERED_ASSETS_PATH_OBJ.rglob("*.uasset"))

def convert_single_file(uasset_path: Path) -> bool:
    json_path = ORIGINAL_JSON_DIR_OBJ / uasset_path.relative_to(FILTERED_ASSETS_PATH_OBJ).with_suffix(".json")
    if json_path.exists() and json_path.stat().st_size > 100: return True

    json_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(UASSET_GUI_EXE_OBJ), "tojson", str(uasset_path), str(json_path), str(UE_VERSION)]
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    
    res = subprocess.run(cmd, capture_output=True, text=True, creationflags=flags)
    
    if res.returncode != 0:
        logging.error(f"UAssetGUI failed on {uasset_path.name}: {res.stderr}")
        return False
    
    return json_path.exists() and json_path.stat().st_size > 100

def convert_batch_parallel(files_to_convert: list[Path]):
    global conv_current_file, conv_successes, conv_start_time
    total = len(files_to_convert)
    workers = get_dynamic_workers(total)
    lock = threading.Lock()
    
    progress = Progress(BarColumn(), TimeElapsedColumn())
    task = progress.add_task("Converting...", total=total)
    conv_start_time = time.time()
    
    with Live(generate_conv_layout(total, progress), refresh_per_second=10) as live:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            def worker(path):
                if shutdown_flag.is_set(): return
                
                global conv_current_file, conv_successes
                with lock:
                    conv_current_file = path.name
                
                if convert_single_file(path):
                    with lock: conv_successes += 1
                
                progress.advance(task)
                live.update(generate_conv_layout(total, progress))
            
            [executor.submit(worker, path) for path in files_to_convert]
    
    print(f"📊 Summary: {conv_successes} Success, {total - conv_successes} Failures.")

def main():
    validate_environment()
    filtered = filter_asset_files_parallel()
    if filtered:
        convert_batch_parallel(filtered)
    print(f"\n🎉 Completed!")

if __name__ == "__main__":
    main()
