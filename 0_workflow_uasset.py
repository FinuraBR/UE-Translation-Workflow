import sys
import mmap
import shutil
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import (
    UASSET_GUI_PATH, UE_VERSION, PASTA_RAW, 
    PASTA_FILTRADO, PASTA_JSON_ORIGINAL, KEYWORDS_BINARIAS
)

PATH_RAW = Path(PASTA_RAW)
PATH_FILTRADO = Path(PASTA_FILTRADO)
PATH_JSON = Path(PASTA_JSON_ORIGINAL)
UASSET_GUI_EXE = Path(UASSET_GUI_PATH)

# Pré-processa as keywords para bytes uma única vez
KW_BYTES =[kw if isinstance(kw, bytes) else kw.encode('utf-8') for kw in KEYWORDS_BINARIAS]

def validar_ambiente():
    if not PATH_RAW.exists():
        sys.exit(f"❌ Pasta RAW não encontrada: {PATH_RAW}")
    if not UASSET_GUI_EXE.exists():
        sys.exit(f"❌ UAssetGUI não encontrado em: {UASSET_GUI_EXE}")

def tem_texto(caminho: Path) -> bool:
    if caminho.stat().st_size == 0:
        return False
    try:
        with caminho.open('rb') as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            return any(mm.find(kw) != -1 for kw in KW_BYTES)
    except Exception:
        return False

def filtrar_arquivos() -> list[Path]:
    PATH_FILTRADO.mkdir(parents=True, exist_ok=True)
    arquivos_filtrados =[]

    for path_src in PATH_RAW.rglob("*.uasset"):
        if tem_texto(path_src):
            dest = PATH_FILTRADO / path_src.relative_to(PATH_RAW)
            dest.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(path_src, dest)
            uexp_src = path_src.with_suffix(".uexp")
            if uexp_src.exists():
                shutil.copy2(uexp_src, dest.with_suffix(".uexp"))
            
            arquivos_filtrados.append(dest)

    print(f"✅ Filtro concluído: {len(arquivos_filtrados)} arquivos contêm texto.\n")
    return arquivos_filtrados

def converter_arquivo(uasset_path: Path) -> tuple[Path, bool]:
    json_path = PATH_JSON / uasset_path.relative_to(PATH_FILTRADO).with_suffix(".json")
    
    # Pula se já existe e é válido
    if json_path.exists() and json_path.stat().st_size > 100:
        return uasset_path, True

    json_path.parent.mkdir(parents=True, exist_ok=True)
    
    cmd =[str(UASSET_GUI_EXE), "tojson", str(uasset_path), str(json_path), str(UE_VERSION)]
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    
    subprocess.run(cmd, capture_output=True, creationflags=flags)
    
    sucesso = json_path.exists() and json_path.stat().st_size > 100
    return uasset_path, sucesso

def converter_lote(arquivos: list[Path]):
    total = len(arquivos)
    print(f"🔧 Convertendo {total} arquivos para JSON")
    PATH_JSON.mkdir(parents=True, exist_ok=True)
    
    sucessos = 0
    
    # Usa as_completed para atualizar o print conforme os arquivos terminam paralelamente
    with ThreadPoolExecutor() as executor:
        futuros =[executor.submit(converter_arquivo, path) for path in arquivos]
        
        for i, futuro in enumerate(as_completed(futuros), 1):
            caminho, sucesso = futuro.result()
            nome_arquivo = caminho.name
            
            if sucesso:
                sucessos += 1
                status = "✅"
            else:
                status = "❌"
                
            # Print formatado do progresso
            print(f"[{i:03d}/{total}] {status} {nome_arquivo}")
        
    print(f"\n📊 RESUMO DA CONVERSÃO:\n   ✅ Sucesso: {sucessos}\n   ❌ Falhas: {total - sucessos}")

def main():
    validar_ambiente()
    
    arquivos_filtrados = filtrar_arquivos()
    if arquivos_filtrados:
        converter_lote(arquivos_filtrados)
        
    print("="*50 + f"\n🎉 CONCLUÍDO! JSONs em: {PATH_JSON}")

if __name__ == "__main__":
    main()