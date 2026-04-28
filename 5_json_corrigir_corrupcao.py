import json
import os
import subprocess
import shutil
import time
import traceback
import sys

# --- IMPORTANDO CONFIGURAÇÕES DO CONFIG.PY ---
from config import (
    UASSET_GUI_PATH, UE_VERSION,
    PASTA_FILTRADO, PASTA_JSON_ORIGINAL, 
    PASTA_MOD_FINAL, ARQUIVO_STATUS, ARQUIVO_JSON_TRADUZIDO,
    PASTA_PARTES_1, PASTA_PARTES_2, PASTA_PARTES_3
)

def verificar_pre_requisitos(status) -> bool:
    problemas = []
    
    # Valida se o arquivo de controle de fluxo existe
    if not os.path.exists(ARQUIVO_STATUS):
        problemas.append("❌ Arquivo de status (projeto_status.json) não encontrado.")
    
    # Valida se a tradução final foi gerada
    if not os.path.exists(ARQUIVO_JSON_TRADUZIDO):
        problemas.append("❌ Arquivo JSON traduzido (json_PTBR.json) não encontrado. Execute o Passo 4 primeiro.")
    
    # Valida se o UAssetGUI (ferramenta externa) está no caminho configurado
    if not os.path.exists(UASSET_GUI_PATH):
        problemas.append(f"❌ UAssetGUI (CLI) não encontrado em: {UASSET_GUI_PATH}")
    
    # Valida o caminho do JSON original (usado como referência)
    orig_json_src = os.path.join(PASTA_JSON_ORIGINAL, status['subpath'], f'{status["nome"]}.json')
    if not os.path.exists(orig_json_src):
        problemas.append(f"❌ Arquivo JSON original não encontrado: {orig_json_src}")
    
    if problemas:
        print("\n❌ PROBLEMAS CRÍTICOS ENCONTRADOS:")
        for p in problemas: print(f"   {p}")
        return False
    return True

def executar_backup_seguro(status) -> bool:
    try:
        nome = status['nome']
        subpath = status['subpath']
        
        # Localiza o UAsset que será substituído
        original_uasset_src = os.path.join(PASTA_FILTRADO, subpath, f'{nome}.uasset')
        original_uexp_src = original_uasset_src.replace(".uasset", ".uexp")
        
        # Backup do arquivo principal
        backup_uasset_path = original_uasset_src + ".bak"
        if os.path.exists(original_uasset_src):
            shutil.copy2(original_uasset_src, backup_uasset_path)
        else:
            print(f"⚠️ UAsset original não encontrado em '{original_uasset_src}' para backup.")
        
        # Backup do arquivo de dados associado (uexp), comum em Unreal Engine 4.25+
        backup_uexp_path = original_uexp_src + ".bak"
        if os.path.exists(original_uexp_src):
            shutil.copy2(original_uexp_src, backup_uexp_path)
        
        return True
        
    except Exception as e:
        print(f"❌ Erro durante backup: {e}")
        return False

def limpar_arquivos_temporarios(status) -> bool:
    try:
        # Arquivos globais de controle
        arquivos_para_remover = [ARQUIVO_JSON_TRADUZIDO, ARQUIVO_STATUS]
        
        # Pastas de processamento
        pastas_para_limpar = [PASTA_PARTES_1, PASTA_PARTES_2, PASTA_PARTES_3]
        
        # Esvazia as pastas de trabalho
        for pasta in pastas_para_limpar:
            if os.path.exists(pasta):
                for arquivo in os.listdir(pasta):
                    caminho_arquivo = os.path.join(pasta, arquivo)
                    try:
                        if os.path.isfile(caminho_arquivo):
                            os.remove(caminho_arquivo)
                    except Exception: 
                        pass # Silencia erros caso o arquivo esteja bloqueado
        
        # Remove arquivos de controle
        for arquivo in arquivos_para_remover:
            if os.path.exists(arquivo):
                try:
                    os.remove(arquivo)
                except Exception: 
                    pass
        return True
        
    except Exception as e:
        print(f"❌ Erro durante limpeza: {e}")
        return False

def executar_conversao_json_para_uasset_cli(status) -> bool:
    nome = status['nome']
    subpath = status['subpath']
    
    # Define o arquivo de entrada (JSON final) e o de saída (UAsset)
    input_json_path = os.path.abspath(ARQUIVO_JSON_TRADUZIDO)
    dest_folder = os.path.join(PASTA_MOD_FINAL, subpath)
    os.makedirs(dest_folder, exist_ok=True) 
    output_uasset_path = os.path.abspath(os.path.join(dest_folder, f'{nome}.uasset'))
    print(f"📍 UAsset de saída: {output_uasset_path}\n")
    
    try:
        # Monta o comando CLI: UAssetGUI fromjson [origem] [destino] [versao_ue]
        comando = [
            str(UASSET_GUI_PATH), 
            "fromjson", 
            str(input_json_path), 
            str(output_uasset_path), 
            str(UE_VERSION)
        ]
        
        # Configuração para não abrir uma janela do console (execução silenciosa)
        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        
        # Executa e aguarda o término
        resultado = subprocess.run(
            comando, 
            capture_output=True, 
            text=True, 
            check=False, 
            creationflags=creation_flags
        )

        # Validação do sucesso da operação baseada no código de retorno e existência do arquivo
        if resultado.returncode == 0:
            if os.path.exists(output_uasset_path) and os.path.getsize(output_uasset_path) > 100:
                return True
            else:
                print("❌ Conversão via CLI falhou: arquivo de saída não gerado ou vazio.")
                print(f"Saída: {resultado.stdout}")
                return False
        else:
            print(f"❌ UAssetGUI CLI retornou erro {resultado.returncode}.")
            print(f"Erros: {resultado.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao executar UAssetGUI CLI: {e}")
        traceback.print_exc()
        return False

def main() -> bool:
    try:
        # Carrega o estado atual (qual arquivo estamos processando)
        if not os.path.exists(ARQUIVO_STATUS):
            print("❌ Arquivo de status (projeto_status.json) não encontrado. Rode o Gerente.")
            return False
        
        with open(ARQUIVO_STATUS, 'r', encoding='utf-8') as f:
            status = json.load(f)
        
        print(f"📦 Processando: {status['nome']}\n")
        
        # 1. Checagem inicial
        if not verificar_pre_requisitos(status): 
            return False
        
        # 2. Conversão propriamente dita
        sucesso_conversao = executar_conversao_json_para_uasset_cli(status)
        
        # 3. Pós-processamento apenas se a conversão funcionou
        if sucesso_conversao:
            executar_backup_seguro(status)
            limpar_arquivos_temporarios(status)
            return True
        else:
            print(f"\n❌ Falha na conversão do arquivo {status['nome']} para UAsset.")
            return False
            
    except Exception as e:
        print(f"💥 Erro crítico no script: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Execução e controle de código de saída (1 para erro, nada/0 para sucesso)
    resultado_sucesso = main()
    
    if not resultado_sucesso:
        sys.exit(1)