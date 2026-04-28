import json
import os
import sys

# --- CONFIGURAÇÕES GLOBAIS ---
# Importa regras externas para permitir fácil manutenção sem alterar a lógica
from config import (
    REQUIRED_HISTORY_TYPE,
    FORBIDDEN_FLAG,
    WHITELIST_TYPES,
    BLACKLIST_CONTEUDO,
    BLACKLIST_NOMES_VARIAVEL,
    REGEX
)

# ==============================================================================
#                            LÓGICA DE FILTRAGEM
# ==============================================================================

def eh_texto_valido(obj, texto):
# Verifica se o texto é nulo, vazio ou não é uma string
    if not texto or not isinstance(texto, str) or not texto.strip():
        return False
    
    t_limpo = texto.strip()
    t_lower = t_limpo.lower()

    # 1. Verifica Blacklist de Conteúdo: Filtra textos que já sabemos que não traduzem
    if t_lower in BLACKLIST_CONTEUDO:
        return False

    # 2. Verifica Nome da Variável: Filtra campos específicos que não devem ser traduzidos
    nome_var = str(obj.get("Name", "")).lower()
    if nome_var in BLACKLIST_NOMES_VARIAVEL:
        return False
    
    # 3. Ignora se o texto for um padrão técnico identificado via Regex (ex: caminhos, IDs)
    if REGEX.match(t_limpo):
        return False
    
    # 4. Heurística para IDs internos: Se não tem espaços e contém underline, 
    # geralmente é um identificador de código, não conteúdo traduzível.
    if " " not in t_limpo and "_" in t_limpo:
        return False

    return True

def extrair_recursivo(obj, lista, path=""):
    if isinstance(obj, dict):
        # --- VERIFICAÇÃO DAS REGRAS ESTRITAS ---
        # Apenas extraímos se o HistoryType for permitido e não tiver a flag 'Immutable'
        history = obj.get("HistoryType", "")
        flags = str(obj.get("Flags", ""))

        # Verifica se o objeto atual atende aos critérios de 'translatabilidade'
        if history in REQUIRED_HISTORY_TYPE and FORBIDDEN_FLAG not in flags:
            
            # Verifica se o tipo do objeto está na lista permitida (ex: 'Text', 'StringTable')
            tipo = obj.get("Type", obj.get("$type", ""))
            if any(t in tipo for t in WHITELIST_TYPES):
                
                # Procura por chaves específicas que contêm o texto real
                for key in ["LocalizedString", "SourceString", "CultureInvariantString", "DisplayString"]:
                    if key in obj:
                        valor = obj.get(key)
                        # Valida o texto antes de adicionar à lista final
                        if eh_texto_valido(obj, valor):
                            lista.append({
                                "p": f"{path}.{key}" if path else key, # Caminho para referência futura
                                "t": valor                             # O texto extraído
                            })
                            return 

        # Continua navegando no JSON (Recursão)
        for k, v in obj.items():
            # Pula chaves que são apenas metadados técnicos, não precisam ser analisadas
            if k in ["Namespace", "Key", "Guid", "Type", "$type", "Flags", "Class", "Outer"]:
                continue
            # Chama a função recursivamente para o próximo nível do JSON
            extrair_recursivo(v, lista, f"{path}.{k}" if path else k)
                
    elif isinstance(obj, list):
        # Se for uma lista, itera sobre os itens mantendo o índice no caminho (path)
        for i, item in enumerate(obj):
            extrair_recursivo(item, lista, f"{path}[{i}]")

# ==============================================================================
#                        EXECUÇÃO E EXPORTAÇÃO
# ==============================================================================

from config import PASTA_JSON_ORIGINAL, PASTA_PARTES_1, ARQUIVO_STATUS, LIMITE_CARACTERES_POR_PARTE

def main():
    # --- LÓGICA DE ARGUMENTOS ---
    # Este script pode ser chamado por um "Gerente" que passa o arquivo alvo via argumento
    if len(sys.argv) >= 3:
        nome_arquivo = sys.argv[1]
        subpath_arquivo = sys.argv[2]
        alvo = {"nome": nome_arquivo, "subpath": subpath_arquivo}
    else:
        # Se rodado manualmente, procura o primeiro arquivo .json disponível
        alvo = None
        for root, _, files in os.walk(PASTA_JSON_ORIGINAL):
            for f in files:
                if f.endswith(".json") and not f.endswith(".bak"):
                    alvo = {
                        "nome": f.replace(".json", ""), 
                        "subpath": os.path.relpath(root, PASTA_JSON_ORIGINAL)
                    }
                    break
            if alvo: break
    
    # Caso não ache nada, finaliza o script
    if not alvo: 
        return

    # Define caminho completo do arquivo
    arquivo_path = os.path.join(PASTA_JSON_ORIGINAL, alvo['subpath'], alvo['nome'] + ".json")
    
    if not os.path.exists(arquivo_path):
        print(f"❌ Erro: Arquivo não encontrado em {arquivo_path}")
        sys.exit(1)

    # Carrega os dados JSON
    with open(arquivo_path, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    
    # Salva estado atual para o "Gerente" saber em qual arquivo estamos trabalhando
    with open(ARQUIVO_STATUS, 'w', encoding='utf-8') as f: 
        json.dump(alvo, f, indent=2)

    # Inicia a extração recursiva
    lista_final = []
    extrair_recursivo(dados, lista_final)
    
    # Se nada foi extraído, aborta (geralmente usado para pular arquivos vazios)
    if not lista_final:
        sys.exit(10) 

    # --- DIVISÃO PARA IA ---
    # Limita o tamanho do arquivo final para que a IA não sofra com limite de tokens
    os.makedirs(PASTA_PARTES_1, exist_ok=True)
    
    # Limpa arquivos de partes antigas para evitar mistura de dados
    for f in os.listdir(PASTA_PARTES_1):
        os.remove(os.path.join(PASTA_PARTES_1, f))

    # Agrupa os itens em blocos de tamanho definido (configurável)
    partes, bloco, count = [], [], 0
    for item in lista_final:
        tamanho = len(json.dumps(item, ensure_ascii=False))
        if (count + tamanho) > LIMITE_CARACTERES_POR_PARTE and bloco:
            partes.append(bloco)
            bloco, count = [], 0
        bloco.append(item)
        count += tamanho
    if bloco: partes.append(bloco)

    # Salva os arquivos de partes
    for idx, conteudo in enumerate(partes):
        with open(os.path.join(PASTA_PARTES_1, f'parte_{idx+1:03d}.json'), 'w', encoding='utf-8') as f:
            json.dump(conteudo, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Extraídos {len(lista_final)} itens em {len(partes)} partes.")
    sys.exit(0) # Sucesso

if __name__ == '__main__':
    main()