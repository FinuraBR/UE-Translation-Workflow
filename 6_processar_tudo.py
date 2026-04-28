import os
import subprocess
import sys
import time 

from config import (
    PASTA_JSON_ORIGINAL, 
    PASTA_MOD_FINAL, 
    PASTA_PARTES_1, 
    PASTA_PARTES_2, 
    PASTA_PARTES_3
)

def limpar_workflow():
    pastas = {PASTA_PARTES_1, PASTA_PARTES_2, PASTA_PARTES_3}
    for pasta in pastas:
        if os.path.exists(pasta):
            for arquivo in os.listdir(pasta):
                caminho_arquivo = os.path.join(pasta, arquivo)
                try:
                    # Remove apenas arquivos, mantendo a estrutura de pastas
                    if os.path.isfile(caminho_arquivo):
                        os.remove(caminho_arquivo)
                except Exception as e:
                    print(f"⚠️ Não foi possível deletar {arquivo}: {e}")

def iniciar_automacao():
    try:
        # 1. Monta a lista de todos os arquivos JSON para processar
        arquivos_alvo = []
        for root, _, files in os.walk(PASTA_JSON_ORIGINAL):
            for f in files:
                # Ignora arquivos de backup (.bak) e processa apenas .json
                if f.endswith(".json") and not f.endswith(".bak"):
                    arquivos_alvo.append({
                        "nome": f.replace(".json", ""),
                        "subpath": os.path.relpath(root, PASTA_JSON_ORIGINAL)
                    })

        print(f"\n🚀 {len(arquivos_alvo)} arquivos na fila de verificação.")

        # 2. Loop de processamento individual
        for i, item in enumerate(arquivos_alvo, 1):
            nome = item["nome"]
            subpath = item["subpath"]
            
            caminho_json_original = os.path.join(PASTA_JSON_ORIGINAL, subpath, f"{nome}.json")
            uasset_final = os.path.join(PASTA_MOD_FINAL, subpath, f"{nome}.uasset")
            arquivo_bak = caminho_json_original + ".bak"

            # --- VERIFICAÇÃO DE PULO (SKIP) ---
            # Se o arquivo já foi convertido (UAsset final existe) ou já foi marcado como 'sem texto'
            if os.path.exists(uasset_final) or os.path.exists(arquivo_bak):
                continue 

            # --- EXECUÇÃO DO PIPELINE ---
            print(f"\n📦 [{i}/{len(arquivos_alvo)}] PROCESSANDO: {nome}\n📂 PASTA: {subpath}\n")

            try:
                pausar_para_blacklist = False

                # PASSO 1: Dividir (Prepara o JSON em partes pequenas)
                # O script envia 'nome' e 'subpath' como argumentos.
                resultado_dividir = subprocess.run([sys.executable, "1_json_dividir.py", nome, subpath])

                # Retorno 10: Significa que o arquivo não tem texto traduzível. Marcamos como .bak e pulamos.
                if resultado_dividir.returncode == 10:
                    if os.path.exists(caminho_json_original):
                        novo_nome_bak = caminho_json_original + ".bak"
                        if os.path.exists(novo_nome_bak): os.remove(novo_nome_bak)
                        os.rename(caminho_json_original, novo_nome_bak)
                    continue 

                if resultado_dividir.returncode != 0:
                    print(f"❌ Erro crítico no Passo 1 para o arquivo {nome}.")
                    break

                # PASSO 2: Traduzir (O processamento pesado via IA)
                resultado_ia = subprocess.run([sys.executable, "2_json_traduzir_tudo.py"])

                # Retorno 1: Erro crítico (Saldo insuficiente ou falha de rede)
                if resultado_ia.returncode == 1:
                    break

                # PASSO 3: Juntar (Injetar a tradução no molde original)
                resultado_juntar = subprocess.run([sys.executable, "4_json_juntar.py", nome, subpath])

                # Retorno 11: Detectou novos termos técnicos (Blacklist precisa de atenção)
                if resultado_juntar.returncode == 11:
                    pausar_para_blacklist = True

                # Retorno 10: Sem alterações necessárias (já estava traduzido ou vazio)
                if resultado_juntar.returncode == 10:
                    print(f"✨ {nome}: Sem alterações necessárias.")
                    limpar_workflow()
                    if os.path.exists(caminho_json_original):
                        novo_nome_bak = caminho_json_original + ".bak"
                        if os.path.exists(novo_nome_bak): os.remove(novo_nome_bak)
                        os.rename(caminho_json_original, novo_nome_bak)
                    continue 

                if resultado_juntar.returncode != 0 and resultado_juntar.returncode != 11:
                    print(f"❌ Erro crítico no Passo 4 para o arquivo {nome}.")
                    break

                # PASSO 4: Finalizar (Converter JSON -> UAsset via CLI)
                subprocess.run([sys.executable, "5_json_corrigir_corrupcao.py", nome, subpath], check=True)

                print(f"\n✅ SUCESSO: {nome} finalizado.")
                
                # Pequena pausa para garantir que o Windows liberou os arquivos
                time.sleep(0.1)

                # Se detectou termos para blacklist, paramos a automação aqui para revisão humana
                if pausar_para_blacklist:
                    print("\n🛑 WORKFLOW PAUSADO! Novos termos detectados para Blacklist.")
                    break 
                
            except subprocess.CalledProcessError as e:
                print(f"\n❌ ERRO no subprocesso: {e}")
                break 

    except Exception as e:
        print(f"\n⚠️ Erro inesperado: {e}")

if __name__ == "__main__":
    iniciar_automacao()