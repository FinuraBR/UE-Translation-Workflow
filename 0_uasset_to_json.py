import sys
import mmap
import shutil
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import (
    UASSET_GUI_PATH, UE_VERSION, RAW_ASSETS_PATH,
    FILTERED_ASSETS_PATH, ORIGINAL_JSON_DIR, BINARY_KEYWORDS
)

RAW_ASSETS_PATH_OBJ = Path(RAW_ASSETS_PATH)
FILTERED_ASSETS_PATH_OBJ = Path(FILTERED_ASSETS_PATH)
ORIGINAL_JSON_DIR_OBJ = Path(ORIGINAL_JSON_DIR)
UASSET_GUI_EXE_OBJ = Path(UASSET_GUI_PATH)

ENCODED_BINARY_KEYWORDS = [kw if isinstance(kw, bytes) else kw.encode('utf-8') for kw in BINARY_KEYWORDS]

def validate_environment():
    if not RAW_ASSETS_PATH_OBJ.exists():
        sys.exit(f"❌ Raw assets folder not found: {RAW_ASSETS_PATH_OBJ}")
    if not UASSET_GUI_EXE_OBJ.exists():
        sys.exit(f"❌ UAssetGUI not found at: {UASSET_GUI_EXE_OBJ}")

def contains_text(file_path: Path) -> bool:
    if file_path.stat().st_size == 0:
        return False
    try:
        with file_path.open('rb') as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            return any(mm.find(keyword) != -1 for keyword in ENCODED_BINARY_KEYWORDS)
    except Exception:
        return False

def filter_asset_files() -> list[Path]:
    FILTERED_ASSETS_PATH_OBJ.mkdir(parents=True, exist_ok=True)
    filtered_files = []

    for source_path in RAW_ASSETS_PATH_OBJ.rglob("*.uasset"):
        if contains_text(source_path):
            destination_path = FILTERED_ASSETS_PATH_OBJ / source_path.relative_to(RAW_ASSETS_PATH_OBJ)
            destination_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy2(source_path, destination_path)
            uexp_source_path = source_path.with_suffix(".uexp")
            if uexp_source_path.exists():
                shutil.copy2(uexp_source_path, destination_path.with_suffix(".uexp"))

            filtered_files.append(destination_path)

    print(f"✅ Filtering completed: {len(filtered_files)} files contain text.\n")
    return filtered_files

def convert_single_file(uasset_path: Path) -> tuple[Path, bool]:
    json_output_path = ORIGINAL_JSON_DIR_OBJ / uasset_path.relative_to(FILTERED_ASSETS_PATH_OBJ).with_suffix(".json")

    if json_output_path.exists() and json_output_path.stat().st_size > 100:
        return uasset_path, True

    json_output_path.parent.mkdir(parents=True, exist_ok=True)

    command = [str(UASSET_GUI_EXE_OBJ), "tojson", str(uasset_path), str(json_output_path), str(UE_VERSION)]
    creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

    subprocess.run(command, capture_output=True, creationflags=creation_flags)

    success = json_output_path.exists() and json_output_path.stat().st_size > 100
    return uasset_path, success

def convert_batch(files_to_convert: list[Path]):
    total_files = len(files_to_convert)
    print(f"🔧 Converting {total_files} files to JSON")
    ORIGINAL_JSON_DIR_OBJ.mkdir(parents=True, exist_ok=True)

    successful_conversions = 0

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(convert_single_file, path) for path in files_to_convert]

        for index, future in enumerate(as_completed(futures), 1):
            file_path, success = future.result()
            file_name = file_path.name

            if success:
                successful_conversions += 1
                status_indicator = "✅"
            else:
                status_indicator = "❌"

            print(f"[{index:03d}/{total_files}] {status_indicator} {file_name}")

    print(f"\n📊 CONVERSION SUMMARY:\n   ✅ Success: {successful_conversions}\n   ❌ Failures: {total_files - successful_conversions}")

def main():
    validate_environment()

    filtered_files = filter_asset_files()
    if filtered_files:
        convert_batch(filtered_files)

    print(f"\n🎉 COMPLETED! JSONs in: {ORIGINAL_JSON_DIR_OBJ}")

if __name__ == "__main__":
    main()