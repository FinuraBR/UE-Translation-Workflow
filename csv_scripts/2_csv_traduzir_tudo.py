import os
import re
import sys
import time
import json
import threading
from concurrent.futures import ThreadPoolExecutor # <--- Novo

# Ajusta o path do sistema
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- CONFIGURAÇÕES GLOBAIS ---
from config import (
    TIMEOUT_LIMITE,
    MAX_TENTATIVAS,
)

# Configuração de Paralelismo
MAX_WORKERS = 5  # Número de arquivos traduzidos ao mesmo tempo

# Validação de dependências
try:
    from openai import OpenAI  
except ImportError:
    print("❌ Erro: A biblioteca 'openai' não está instalada.")
    sys.exit(1)

# Configuração do Cliente
client = OpenAI(
    api_key="", # Lembre-se de não deixar exposta
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

DEFAULT_SYSTEM_PROMPT = """EN->PT-BR Game JSON Localizer. Raw JSON output only. No markdown.
1. Copy 'key' and 'source 'verbatim. NEVER alter paths.
2. Translate 'Translation' values only.""" 

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

def executar_chamada_ia(prompt_sistema, prompt_usuario, resultado_container):
    try:
        response = client.chat.completions.create(
            model="gemini-3.1-flash-lite-preview", # Ajustado para um modelo estável
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_usuario}
            ],
            temperature=1.0,
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
        resultado_container['res'] = response.choices[0].message.content
    except Exception as e:
        resultado_container['erro'] = e

def obter_traducao_com_timeout(json_content):
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        container = {'res': None, 'erro': None}
        t = threading.Thread(target=executar_chamada_ia, args=(DEFAULT_SYSTEM_PROMPT, json_content, container))
        t.daemon = True
        t.start()
        
        t.join(timeout=TIMEOUT_LIMITE)
        
        if t.is_alive():
            print(f"⏳ Timeout na tentativa {tentativa}")
            continue

        if container['erro']:
            print(f"❌ Erro na API: {container['erro']}")
            time.sleep(1) # Espera um pouco antes de tentar de novo em caso de erro de rate limit
            continue

        texto_final = container['res']
        resultado = limpar_resposta_ia(texto_final)
        
        if resultado:
            return resultado
    return None

def processar_arquivo(filename, input_folder, output_folder):
    """Função que será executada por cada thread"""
    input_path = os.path.join(input_folder, filename)
    output_path = os.path.join(output_folder, filename)

    print(f"🔄 Iniciando: {filename}")
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            conteudo = f.read()

        if not conteudo.strip():
            return f"⚠️ {filename} está vazio."

        traducao = obter_traducao_com_timeout(conteudo)

        if traducao:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(traducao)
            return f"✅ Salvo: {filename}"
        else:
            return f"❌ Falhou: {filename} após todas as tentativas."

    except Exception as e:
        return f"💥 Erro em {filename}: {e}"

def main():
    input_folder = r"D:\EP1\csv_scripts\1_partes_para_traduzir"
    output_folder = r"D:\EP1\csv_scripts\2_partes_traduzidas"

    if not os.path.exists(output_folder): os.makedirs(output_folder)

    todos_arquivos = sorted([f for f in os.listdir(input_folder) if f.endswith(".json")])
    arquivos_pendentes = [f for f in todos_arquivos if not os.path.exists(os.path.join(output_folder, f))]
    
    if not arquivos_pendentes:
        print("✨ Tudo pronto!")
        return

    print(f"\n🚀 Iniciando Tradução Paralela | {len(arquivos_pendentes)} arquivos | Threads: {MAX_WORKERS}\n")

    # O segredo do paralelismo está aqui
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Envia todas as tarefas para o pool
        futures = [executor.submit(processar_arquivo, f, input_folder, output_folder) for f in arquivos_pendentes]
        
        # Coleta e imprime os resultados conforme terminam
        for future in futures:
            print(future.result())

    print("\n🏁 Workflow de tradução encerrado.")

if __name__ == '__main__':
    main()