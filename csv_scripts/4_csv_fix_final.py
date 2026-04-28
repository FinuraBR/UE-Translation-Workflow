import json
import os
import shutil
import glob

# --- CONFIGURAÇÕES ---
caminho_do_projeto = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_MESTRE = os.path.join(caminho_do_projeto, 'traducao_PTBR.json')
PASTA_REPARO = os.path.join(caminho_do_projeto, 'TEMP_REPARO')
TAG_ERRO = "[FALTOU_TRADUCAO]"
LIMITE_CARACTERES_POR_PARTE = 8000

def processar_reparo_dinamico_json():
    if not os.path.exists(ARQUIVO_MESTRE):
        print(f"❌ Erro: '{ARQUIVO_MESTRE}' não encontrado.")
        return

    arquivos_reparo_encontrados = glob.glob(os.path.join(PASTA_REPARO, '*.json'))

    if os.path.exists(PASTA_REPARO) and arquivos_reparo_encontrados:
        # --- PARTE 2: INJEÇÃO EM MASSA ---
        print(f"🔄 Pasta '{PASTA_REPARO}' com arquivos detectada. Iniciando mesclagem...")
        
        novas_traducoes = {}
        
        for arq in arquivos_reparo_encontrados:
            try:
                with open(arq, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                    for item in dados:
                        key = item.get('key')
                        # Forçamos a tradução para string para evitar erros de tipo
                        trad = item.get('Translation') or item.get('translation')
                        trad = str(trad) if trad is not None else ""
                        
                        if key and trad and TAG_ERRO not in trad:
                            novas_traducoes[key] = trad
            except Exception as e:
                print(f"⚠️ Erro ao ler {os.path.basename(arq)}: {e}")

        try:
            with open(ARQUIVO_MESTRE, 'r', encoding='utf-8') as f_mestre:
                dados_mestre = json.load(f_mestre)
            
            contador = 0
            for item in dados_mestre:
                key = item.get('key')
                if key in novas_traducoes:
                    item['Translation'] = novas_traducoes[key]
                    contador += 1

            with open(ARQUIVO_MESTRE, 'w', encoding='utf-8') as f_out:
                json.dump(dados_mestre, f_out, ensure_ascii=False, indent=2)

            print(f"✅ SUCESSO! {contador} itens corrigidos no arquivo mestre.")
            shutil.rmtree(PASTA_REPARO)
            print(f"🗑️  Pasta '{PASTA_REPARO}' removida.")
        except Exception as e:
            print(f"💥 Erro ao atualizar mestre: {e}")

    else:
        # --- PARTE 1: EXTRAÇÃO DE FALHAS (SPLIT) ---
        print(f"🔍 Buscando falhas para criar lotes de reparo em JSON...")
        
        try:
            with open(ARQUIVO_MESTRE, 'r', encoding='utf-8') as f:
                dados_mestre = json.load(f)
        except Exception as e:
            print(f"❌ Erro ao ler mestre: {e}")
            return

        itens_falhos = []
        for item in dados_mestre:
            # CORREÇÃO AQUI: Convertendo para string antes de checar
            trad_raw = item.get('Translation', '')
            trad_str = str(trad_raw) if trad_raw is not None else ""
            
            if TAG_ERRO in trad_str or not trad_str:
                itens_falhos.append({
                    'key': item.get('key'),
                    'source': item.get('source')
                })

        if not itens_falhos:
            print(f"✨ Nada para consertar em '{ARQUIVO_MESTRE}'!")
            return

        if not os.path.exists(PASTA_REPARO): os.makedirs(PASTA_REPARO)

        bloco_atual = []
        tamanho_acumulado = 0
        num_parte = 1

        for item in itens_falhos:
            item_str = json.dumps(item, ensure_ascii=False)
            tamanho_item = len(item_str)

            if (tamanho_acumulado + tamanho_item > LIMITE_CARACTERES_POR_PARTE) and bloco_atual:
                nome_arq = os.path.join(PASTA_REPARO, f"reparo_parte_{num_parte:03d}.json")
                with open(nome_arq, 'w', encoding='utf-8') as f_out:
                    json.dump(bloco_atual, f_out, ensure_ascii=False, indent=2)
                
                print(f"📦 Parte {num_parte:03d} criada com {len(bloco_atual)} itens.")
                num_parte += 1
                bloco_atual = []
                tamanho_acumulado = 0

            bloco_atual.append(item)
            tamanho_acumulado += tamanho_item

        if bloco_atual:
            nome_arq = os.path.join(PASTA_REPARO, f"reparo_parte_{num_parte:03d}.json")
            with open(nome_arq, 'w', encoding='utf-8') as f_out:
                json.dump(bloco_atual, f_out, ensure_ascii=False, indent=2)
            print(f"📦 Parte {num_parte:03d} criada com {len(bloco_atual)} itens.")

        print(f"\n🚀 Total de {len(itens_falhos)} falhas divididas em {num_parte} arquivos.")
        print(f"📂 Traduza os arquivos em '{PASTA_REPARO}' e execute este script novamente para aplicar.")

if __name__ == '__main__':
    processar_reparo_dinamico_json()