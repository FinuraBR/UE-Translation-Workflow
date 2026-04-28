import os
import glob
import json

# --- CONFIGURAÇÕES GLOBAIS ---
caminho_do_projeto = os.path.dirname(os.path.abspath(__file__))

# Pastas e arquivos
pasta_originais = os.path.join(caminho_do_projeto, '1_partes_para_traduzir')
pasta_traduzidos = os.path.join(caminho_do_projeto, '2_partes_traduzidas')
arquivo_final = os.path.join(caminho_do_projeto, 'traducao_PTBR.json')

TAG_MARCADOR = "[FALTOU_TRADUCAO]"

def juntar_e_corrigir_json():
    arquivos_originais = sorted(glob.glob(os.path.join(pasta_originais, '*.json')))
    arquivos_traduzidos = sorted(glob.glob(os.path.join(pasta_traduzidos, '*.json')))

    if not arquivos_originais:
        print(f"❌ Nenhum arquivo original encontrado em: {pasta_originais}")
        return

    print(f"--- INICIANDO UNIÃO INTELIGENTE DE {len(arquivos_originais)} ARQUIVOS JSON ---")

    traducoes_ia = {}
    for arq_trad in arquivos_traduzidos:
        try:
            with open(arq_trad, 'r', encoding='utf-8') as f_trad:
                dados_traduzidos = json.load(f_trad)
                
                for item in dados_traduzidos:
                    key = item.get('key')
                    traducao = item.get('Translation') or item.get('translation')
                    
                    if key and traducao is not None: # Aceita 0 ou listas, trata depois
                        traducoes_ia[key] = traducao
        except Exception as e:
            print(f"⚠️ Erro ao ler a parte traduzida {os.path.basename(arq_trad)}: {e}")

    lista_final = []
    linhas_faltantes = 0
    chaves_originais = set()

    for arq_orig in arquivos_originais:
        try:
            with open(arq_orig, 'r', encoding='utf-8') as f_orig:
                dados_originais = json.load(f_orig)
                
                for item in dados_originais:
                    key = item.get('key')
                    source = item.get('source')
                    chaves_originais.add(key)
                    
                    # --- INÍCIO DA CORREÇÃO ---
                    traducao_bruta = traducoes_ia.get(key, "")
                    
                    if isinstance(traducao_bruta, list):
                        # Se for lista, junta os itens (ex: ["Texto"] vira "Texto")
                        traducao = " ".join(str(x) for x in traducao_bruta).strip()
                    elif traducao_bruta is None:
                        traducao = ""
                    else:
                        # Converte números ou outros tipos para string antes do strip
                        traducao = str(traducao_bruta).strip()
                    # --- FIM DA CORREÇÃO ---

                    if not traducao or traducao == "None":
                        traducao = f"{TAG_MARCADOR}"
                        linhas_faltantes += 1
                    
                    novo_item = item.copy()
                    novo_item['Translation'] = traducao
                    lista_final.append(novo_item)
                    
        except Exception as e:
            print(f"💥 Erro crítico ao ler original {os.path.basename(arq_orig)}: {e}")

    try:
        with open(arquivo_final, 'w', encoding='utf-8') as f_out:
            json.dump(lista_final, f_out, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Erro ao salvar arquivo final: {e}")
        return

    chaves_traduzidas = set(traducoes_ia.keys())
    inventadas = len(chaves_traduzidas - chaves_originais)

    print("-" * 50)
    print(f"🚀 SUCESSO! Arquivo final gerado: {os.path.basename(arquivo_final)}")
    print(f"📊 Total de objetos processados: {len(lista_final)}")
    
    if linhas_faltantes > 0 or inventadas > 0:
        print("\n⚠️ RELATÓRIO DE SINCRONIZAÇÃO:")
        if inventadas > 0:
            print(f"   Ghost Keys: {inventadas} entradas inventadas pela IA foram descartadas.")
        if linhas_faltantes > 0:
            print(f"   Missing: {linhas_faltantes} entradas não encontradas receberam a tag {TAG_MARCADOR}.")
    else:
        print("\n✅ Sincronização perfeita! Todos os campos foram traduzidos.")
    print("-" * 50)

if __name__ == '__main__':
    juntar_e_corrigir_json()