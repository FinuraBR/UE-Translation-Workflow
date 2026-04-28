"""
Script de Restauração de Backups (.json.bak -> .json).
Objetivo: Varre recursivamente a pasta de origem e renomeia todos os arquivos 
que possuem a extensão '.json.bak' de volta para '.json', desfazendo alterações 
de segurança ou processamentos anteriores.
"""

import os
from config import PASTA_JSON_ORIGINAL

def restaurar_bak():
    """
    Função principal de varredura e restauração.
    Percorre todas as subpastas em busca de backups e os renomeia.
    """
    print(f"🔄 Procurando arquivos .bak em {PASTA_JSON_ORIGINAL}...")
    count = 0
    
    # os.walk percorre a pasta base e todas as suas subpastas recursivamente
    for root, _, files in os.walk(PASTA_JSON_ORIGINAL):
        for file in files:
            # Verifica se o arquivo tem a extensão de backup definida
            if file.endswith(".json.bak"):
                old_path = os.path.join(root, file)
                
                # Cria o novo nome removendo o ".bak" do final da string
                new_path = os.path.join(root, file.replace(".json.bak", ".json"))
                
                try:
                    # Tenta realizar a renomeação (operação atômica no sistema de arquivos)
                    os.rename(old_path, new_path)
                    print(f"✅ Restaurado: {file} -> {os.path.basename(new_path)}")
                    count += 1
                except Exception as e:
                    # Caso o arquivo esteja bloqueado ou sem permissão, captura o erro sem parar o script
                    print(f"❌ Erro ao renomear {file}: {e}")
    
    # Resumo final da operação
    if count == 0:
        print("✨ Nenhum arquivo .bak encontrado.")
    else:
        print(f"\n🚀 Total de arquivos restaurados: {count}")

# Ponto de entrada do script
if __name__ == '__main__':
    restaurar_bak()