"""
Script de Pré-verificação (Cleaner).
Objetivo: Varre a pasta original em busca de arquivos JSON.
1. Identifica arquivos que não possuem texto traduzível (baseado nas regras do config.py).
2. Renomeia esses arquivos inúteis para '.json.bak' para que o restante do 
   pipeline os ignore automaticamente.
3. Isso economiza muito tempo e custos de API, pois a IA não tentará traduzir 
   arquivos binários ou de metadados sem texto humano.
"""

import os
import json
import time

# --- IMPORTAÇÃO DE CONFIGURAÇÕES ---
# Importamos as regras de negócio para saber o que é "traduzível" ou não.
from config import (
    PASTA_JSON_ORIGINAL, 
    PASTA_MOD_FINAL, 
    REQUIRED_HISTORY_TYPE, 
    FORBIDDEN_FLAG, 
    WHITELIST_TYPES
)

def tem_texto_traduzivel(obj):
    """
    Função recursiva de busca. 
    Lógica de 'Avaliação de Curto-Circuito': assim que encontrar 1 item válido,
    ela retorna True e para de buscar imediatamente. Isso otimiza a performance.
    """
    if isinstance(obj, dict):
        # Verifica se o objeto atual atende às regras definidas no config.py
        history = obj.get("HistoryType", "")
        flags = str(obj.get("Flags", ""))

        # Filtro de regras: HistoryType deve ser permitido e não pode ser 'Immutable'
        if history in REQUIRED_HISTORY_TYPE and FORBIDDEN_FLAG not in flags:
            tipo = obj.get("Type", obj.get("$type", ""))
            # Se o tipo do objeto estiver na nossa lista permitida, é considerado útil
            if any(t in tipo for t in WHITELIST_TYPES):
                return True

        # Se não encontrou no nível atual, mergulha nos filhos (recursão)
        for v in obj.values():
            if tem_texto_traduzivel(v):
                return True
                
    elif isinstance(obj, list):
        # Se for uma lista, verifica cada item contido nela
        for item in obj:
            if tem_texto_traduzivel(item):
                return True
    
    return False

def iniciar_verificacao_segura():
    """
    Gerenciador da verificação.
    Percorre a pasta, analisa cada arquivo e limpa os 'inúteis'.
    """
    print(f"\n{'='*60}")
    print(f"🛡️  INICIANDO PRÉ-VERIFICAÇÃO JSON (MODO SEGURO)")
    print(f"Lendo e interpretando todos os arquivos da pasta 3_JSON_ORIGINAL...")
    print(f"{'='*60}\n")

    inicio = time.time()
    stats = {"total": 0, "prontos": 0, "inuteis": 0, "uteis": 0}

    # Coleta todos os arquivos válidos para processamento
    arquivos_para_ler = []
    for root, _, files in os.walk(PASTA_JSON_ORIGINAL):
        for f in files:
            # Ignora o que já foi marcado como backup anteriormente
            if f.endswith(".json") and not f.endswith(".bak"):
                arquivos_para_ler.append(os.path.join(root, f))

    total_fila = len(arquivos_para_ler)

    for i, caminho_completo in enumerate(arquivos_para_ler, 1):
        stats["total"] += 1
        nome_f = os.path.basename(caminho_completo)
        rel_path = os.path.relpath(caminho_completo, PASTA_JSON_ORIGINAL)
        
        # 1. Verificação de Otimização:
        # Se o arquivo já foi processado (existe um .uasset correspondente na pasta final),
        # pulamos ele para não reprocessar desnecessariamente.
        uasset_dest = os.path.join(PASTA_MOD_FINAL, rel_path.replace(".json", ".uasset"))
        if os.path.exists(uasset_dest):
            stats["prontos"] += 1
            continue

        # 2. Verificação de Conteúdo:
        try:
            with open(caminho_completo, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            
            # Se a função retornar True, o arquivo vale a pena ser traduzido
            if tem_texto_traduzivel(dados):
                stats["uteis"] += 1
                print(f"[{i}/{total_fila}] ✅ Útil: {nome_f}")
            else:
                # Se não tem nada traduzível, renomeamos para .bak (invisível para o pipeline)
                os.rename(caminho_completo, caminho_completo + ".bak")
                stats["inuteis"] += 1
                print(f"[{i}/{total_fila}] 📦 Ignorado (marcado como .bak): {nome_f}")

        except Exception as e:
            print(f"❌ Erro ao ler {nome_f}: {e}")

    # Relatório final de execução
    fim = time.time()
    
    print(f"\n{'='*60}")
    print(f"🏁 CONCLUÍDO EM: {fim - inicio:.2f} segundos")
    print(f"📊 Total analisado: {stats['total']}")
    print(f"💎 Arquivos Úteis (JSON): {stats['uteis']}")
    print(f"📦 Marcados como .bak (Inúteis): {stats['inuteis']}")
    print(f"⏩ Já traduzidos (.uasset): {stats['prontos']}")
    print(f"{'='*60}")

if __name__ == "__main__":
    iniciar_verificacao_segura()