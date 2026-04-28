import os
import json
import time
import re
import subprocess
import threading
import sys 
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIGURAÇÕES GLOBAIS ---
from config import (
    PASTA_PARTES_1,
    PASTA_PARTES_3, 
    MODELO_IA,
    TIMEOUT_LIMITE,
    MAX_TENTATIVAS,
    API_KEY,
    TEMP_TRADUCAO
)

# Configuração de paralelismo (Quantos arquivos processar simultaneamente)
# Sugestão: 3 a 5 para não atingir o limite de quota da API muito rápido
MAX_WORKERS = 5

try:
    from openai import OpenAI  
except ImportError:
    print("❌ Erro: A biblioteca 'openai' não está instalada.")
    sys.exit(1)

# Gemini api (Google AI Studio)
client = OpenAI(
    api_key=API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

input_folder = PASTA_PARTES_1
output_folder = PASTA_PARTES_3

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# --- PROMPT REFINADO ---
prompt_sistema = """EN->PT-BR Game JSON Localizer. Raw JSON output only. No markdown.
1. Copy 'p' verbatim. NEVER alter paths.
2. Translate 't' values only."""

def validar_integridade_tags(original, traduzido):
    pattern = re.compile(r'\{.*?\}|<.*?>|%[sd]')
    tags_originais = pattern.findall(original)
    tags_traduzidas = pattern.findall(traduzido)
    return len(tags_originais) == len(tags_traduzidas)

def limpar_resposta_ia(texto_bruto):
    try:
        dados_brutos = json.loads(texto_bruto)
        if isinstance(dados_brutos, dict) and "data" in dados_brutos:
            lista_traduzida = dados_brutos["data"]
        elif isinstance(dados_brutos, list):
            lista_traduzida = dados_brutos
        else:
            return None
        return json.dumps(lista_traduzida, ensure_ascii=False, indent=2)
    except Exception as e:
        return None

# --- FUNÇÕES DE VERIFICAÇÃO ---

def verificar_status_final():
    arquivos_entrada = set([f for f in os.listdir(input_folder) if f.endswith('.json')])
    arquivos_saida = set([f for f in os.listdir(output_folder) if f.endswith('.json')])
    
    faltantes = arquivos_entrada - arquivos_saida
    if faltantes:
        print(f"\n❌ ERRO: Faltam {len(faltantes)} arquivos.")
        return False
    
    for f in arquivos_saida:
        path = os.path.join(output_folder, f)
        if os.path.getsize(path) < 10:
            print(f"❌ ERRO: O arquivo {f} está incompleto.")
            return False
    return True

# --- FUNÇÕES DE CHAMADA COM ISOLAMENTO ---

def chamada_ia_thread(texto, container):
    try:
        response = client.chat.completions.create(
            model=MODELO_IA,
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": texto}
            ],
            temperature=TEMP_TRADUCAO,
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
        texto_extraido = response.choices[0].message.content
        if texto_extraido:
            container['resultado'] = limpar_resposta_ia(texto_extraido)
        else:
            container['erro'] = "IA retornou uma resposta vazia."
    except Exception as e:
        container['erro'] = str(e)

def obter_traducao_segura(texto_original, nome_arquivo):
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        
        container = {'resultado': None, 'erro': None}
        t = threading.Thread(target=chamada_ia_thread, args=(texto_original, container))
        t.daemon = True
        t.start()
        
        t.join(timeout=TIMEOUT_LIMITE)
        
        if t.is_alive():
            print(f"⏳ [{nome_arquivo}] Tempo esgotado (Tentativa {tentativa})")
            continue
            
        if container['erro']:
            erro_msg = str(container['erro'])
            if "429" in erro_msg or "RESOURCE_EXHAUSTED" in erro_msg:
                print(f"⚠️ [{nome_arquivo}] Limite de taxa atingido. Aguardando 60s...")
                time.sleep(60)
            else:
                print(f"❌ [{nome_arquivo}] Erro: {erro_msg}")
            continue
            
        if container['resultado']:
            return container['resultado']
            
    return None

# --- PROCESSAMENTO PRINCIPAL ---

def processar_arquivo(nome_arquivo):
    caminho_in = os.path.join(input_folder, nome_arquivo)
    caminho_out = os.path.join(output_folder, nome_arquivo)
    
    if os.path.exists(caminho_out):
        return f"⏭️ {nome_arquivo} já existe."

    try:
        with open(caminho_in, 'r', encoding='utf-8') as f:
            dados_originais = json.load(f)
        
        qtd_esperada = len(dados_originais)
        print(f"🚀 Iniciando: {nome_arquivo} ({qtd_esperada} itens)")
        
        resposta_raw = obter_traducao_segura(json.dumps(dados_originais, ensure_ascii=False), nome_arquivo)
        
        if not resposta_raw: 
            return f"❌ Falha crítica em {nome_arquivo}: IA não retornou dados após tentativas."

        dados_traduzidos = json.loads(resposta_raw)
        
        # Normalização de lista
        if isinstance(dados_traduzidos, dict):
            for key in dados_traduzidos:
                if isinstance(dados_traduzidos[key], list):
                    dados_traduzidos = dados_traduzidos[key]
                    break

        if not isinstance(dados_traduzidos, list) or len(dados_traduzidos) != qtd_esperada:
            return f"❌ {nome_arquivo}: Contagem incorreta ({len(dados_traduzidos)}/{qtd_esperada})"

        for i in range(qtd_esperada):
            if not validar_integridade_tags(dados_originais[i]['t'], dados_traduzidos[i]['t']):
                return f"❌ {nome_arquivo}: Tags corrompidas no índice {i}"
            
        with open(caminho_out, 'w', encoding='utf-8') as f:
            json.dump(dados_traduzidos, f, indent=2, ensure_ascii=False)

        return f"✅ Finalizado: {nome_arquivo}"
    
    except Exception as e:
        return f"❌ Erro inesperado em {nome_arquivo}: {e}"

def executar_traducao_paralela():
    arquivos = sorted([f for f in os.listdir(input_folder) if f.endswith(".json")])
    arquivos_para_processar = [f for f in arquivos if not os.path.exists(os.path.join(output_folder, f))]
    
    if not arquivos_para_processar: 
        print("✅ Todos os arquivos já foram processados.")
        return
    
    total = len(arquivos_para_processar)
    print(f"🤖 [INICIANDO TRADUÇÃO PARALELA: {total} ARQUIVOS COM {MAX_WORKERS} WORKERS]\n")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for arq in arquivos_para_processar:
            future = executor.submit(processar_arquivo, arq)
            futures[future] = arq
            time.sleep(1)

        for future in as_completed(futures):
            try:
                resultado = future.result()
                print(resultado)
            except Exception as e:
                print(f"❌ Erro crítico na thread: {e}")

def main():
    
    executar_traducao_paralela()
    
    if verificar_status_final():
        print(f"\n🏁 Workflow finalizado com sucesso.")
    else:
        print("\n⚠️ O workflow terminou com pendências.")
        sys.exit(1)

if __name__ == '__main__':
    main()