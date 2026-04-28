import json
import os
import glob
import re
import sys
from config import PASTA_JSON_ORIGINAL, PASTA_PARTES_3, ARQUIVO_JSON_TRADUZIDO, ARQUIVO_STATUS, BASE_DIR, CHAVES_DE_TEXTO

def registrar_sugestao_blacklist(texto):
    caminho_log = os.path.join(BASE_DIR, "sugestoes_blacklist.txt")
    texto_limpo = texto.strip().replace('"', '').lower()
    
    # Filtros de segurança: não registrar textos muito longos ou vazios
    if not texto_limpo or len(texto_limpo) > 25:
        return False

    # Carrega log existente para evitar duplicatas
    existentes = set()
    if os.path.exists(caminho_log):
        with open(caminho_log, "r", encoding="utf-8") as f:
            conteudo = f.read()
            # Extrai termos entre aspas do arquivo de log
            existentes = set(re.findall(r'"(.*?)"', conteudo.lower()))

    # Se o texto ainda não está na lista, adiciona ao log
    if texto_limpo not in existentes:
        with open(caminho_log, "a", encoding="utf-8") as f:
            f.write(f'"{texto_limpo}", ')
        return True
    return False

def navegar_e_injetar(obj, path, texto_vindo_da_traducao):
    try:
        if texto_vindo_da_traducao is None:
            return False, False

        # Converte o caminho string em uma lista de chaves/índices
        # Ex: "Root.Items[0].Name" -> ["Root", "Items", "0", "Name"]
        partes = re.findall(r'([^.\[\]]+)', path)
        caminho_pai = partes[:-1] # Todos menos o último (o local onde vamos injetar)
        chave_original_alvo = partes[-1] 
        
        # Navega até o objeto pai
        atual = obj
        for parte in caminho_pai:
            if parte.isdigit():
                atual = atual[int(parte)] # Se for dígito, é índice de lista
            else:
                atual = atual[parte]      # Caso contrário, é chave de dicionário

        # --- LÓGICA DE APRENDIZADO (Detecção de falhas) ---
        # Tenta pegar o valor original para comparar com o traduzido
        referencia_original = atual.get("SourceString") or atual.get("CultureInvariantString") or atual.get(chave_original_alvo)
        
        # Se a IA manteve o texto idêntico ao original, sugere para a blacklist
        item_novo_blacklist = False
        if str(referencia_original).strip() == texto_vindo_da_traducao.strip():
            item_novo_blacklist = registrar_sugestao_blacklist(texto_vindo_da_traducao)

        # --- INJEÇÃO DA TRADUÇÃO ---
        mudou_algo = False
        # Percorre as chaves possíveis configuradas (ex: SourceString, DisplayString)
        for chave in CHAVES_DE_TEXTO:
            if chave in atual:
                valor_antigo = atual.get(chave)
                if valor_antigo != texto_vindo_da_traducao:
                    atual[chave] = texto_vindo_da_traducao
                    mudou_algo = True
        
        # Fallback: Se a chave não existia explicitamente, cria ou atualiza
        if chave_original_alvo not in atual:
            atual[chave_original_alvo] = texto_vindo_da_traducao
            mudou_algo = True

        return mudou_algo, item_novo_blacklist

    except Exception:
        # Em caso de caminho corrompido, apenas ignora e segue o fluxo
        return False, False

def main():
    # 1. Carrega as informações do arquivo que está sendo processado
    if not os.path.exists(ARQUIVO_STATUS): 
        sys.exit(1)
    
    with open(ARQUIVO_STATUS, 'r', encoding='utf-8') as f: 
        status = json.load(f)

    nome_arquivo = status['nome']
    molde_path = os.path.join(PASTA_JSON_ORIGINAL, status['subpath'], status['nome'] + ".json")
    
    if not os.path.exists(molde_path):
        print(f"❌ Molde não encontrado: {molde_path}")
        sys.exit(1)

    # 2. Abre o arquivo original (mestre)
    with open(molde_path, 'r', encoding='utf-8') as f: 
        dados_originais = json.load(f)
    
    # 3. Localiza todas as "partes" traduzidas pela IA
    arquivos_partes = sorted(glob.glob(os.path.join(PASTA_PARTES_3, 'parte_*.json')))
    if not arquivos_partes:
        print("⚠️ Nenhuma parte traduzida encontrada.")
        sys.exit(1)

    total_injetado = 0
    detectou_novos_termos_tecnicos = False

    # 4. Itera sobre cada parte e aplica as traduções no molde original
    for arq in arquivos_partes:
        with open(arq, 'r', encoding='utf-8') as f: 
            try:
                lista_traducao = json.load(f)
            except json.JSONDecodeError:
                continue

            for item in lista_traducao:
                path = item.get('p')
                t = item.get('t')
                
                if path and t is not None:
                    # Injeta a tradução no objeto em memória
                    mudou, novo_termo = navegar_e_injetar(dados_originais, path, t)
                    if mudou:
                        total_injetado += 1
                    if novo_termo:
                        detectou_novos_termos_tecnicos = True

    # 5. Salva o arquivo final com as traduções integradas
    os.makedirs(os.path.dirname(ARQUIVO_JSON_TRADUZIDO), exist_ok=True)
    with open(ARQUIVO_JSON_TRADUZIDO, 'w', encoding='utf-8') as f:
        json.dump(dados_originais, f, indent=2, ensure_ascii=False)
    
    # 6. Códigos de Saída para o Gerenciador (Orquestrador)
    
    # Caso não tenha ocorrido tradução nenhuma
    if total_injetado == 0:
        print(f"ℹ️ {status['nome']}: Nenhuma alteração necessária.")
        # Limpa lixo da pasta
        arquivos_para_limpar = [
            os.path.join(BASE_DIR, f"{nome_arquivo}_SEGURO.json"),
            os.path.join(BASE_DIR, "json_PTBR.json")
        ]
        for caminho in arquivos_para_limpar:
            if os.path.exists(caminho):
                try:
                    os.remove(caminho)
                except: pass
        
        # Código 11 (Técnico encontrado) tem prioridade sobre o 10 (Nada feito)
        if detectou_novos_termos_tecnicos:
            print("📢 Novos itens técnicos detectados mesmo sem tradução aplicada.")
            sys.exit(11)
        
        sys.exit(10) # Código 10 diz ao gerente: arquivo pronto, pode pular
    
    print(f"✅ Sucesso: {total_injetado} blocos sincronizados em {status['nome']}.")
    
    sys.exit(0) # Sucesso total

if __name__ == '__main__': 
    main()