import os
import json

# --- CONFIGURAÇÕES ---
caminho_do_projeto = os.path.dirname(os.path.abspath(__file__))
# Nome do arquivo original (ajuste se necessário)
arquivo_original = os.path.join(caminho_do_projeto, 'csvjson.json')
pasta_saida = os.path.join(caminho_do_projeto, '1_partes_para_traduzir')

# LIMITE PARA IA (DeepSeek/Ollama/API Cloud)
# 8000 caracteres é uma margem segura para prompts
LIMITE_CARACTERES_POR_ARQUIVO = 8000

def dividir_json_inteligente():
    # Garante que a pasta de destino exista
    if not os.path.exists(pasta_saida):
        os.makedirs(pasta_saida)

    print(f"Lendo {arquivo_original}...")

    try:
        with open(arquivo_original, 'r', encoding='utf-8') as f:
            dados = json.load(f)
    except Exception as e:
        print(f"❌ ERRO ao ler arquivo: {e}")
        return

    # O script espera que o JSON seja uma lista de objetos: [{}, {}, {}]
    if not isinstance(dados, list):
        print("❌ ERRO: O arquivo JSON deve conter uma LISTA de objetos no nível superior.")
        return

    if not dados:
        print("O arquivo está vazio!")
        return

    print(f"\n✅ Encontrados {len(dados)} registros. Dividindo por tamanho de texto...")

    buffer_itens = []
    tamanho_atual_buffer = 0
    contador_arquivos = 1

    for item in dados:
        # Converte o item individual para string para medir seu tamanho real no JSON
        # ensure_ascii=False mantém acentos e caracteres especiais como 1 caractere
        item_string = json.dumps(item, ensure_ascii=False, indent=2)
        tamanho_item = len(item_string)

        # Lógica de agrupamento:
        # Se o item atual + o que já temos no buffer passar do limite, salvamos o buffer
        if (tamanho_atual_buffer + tamanho_item) > LIMITE_CARACTERES_POR_ARQUIVO and buffer_itens:
            salvar_parte_json(buffer_itens, contador_arquivos)
            contador_arquivos += 1
            buffer_itens = []
            tamanho_atual_buffer = 0

        buffer_itens.append(item)
        # Somamos o tamanho do item + 2 (margem para a vírgula e formatação de lista)
        tamanho_atual_buffer += tamanho_item + 2

    # Salva o restante
    if buffer_itens:
        salvar_parte_json(buffer_itens, contador_arquivos)

    print(f"\n🚀 Sucesso! {len(dados)} entradas divididas em {contador_arquivos} arquivos.\n")
    print(f"Pasta: {pasta_saida}")

def salvar_parte_json(dados, numero_parte):
    nome_arquivo = os.path.join(pasta_saida, f'parte_{numero_parte:03d}.json')
    
    with open(nome_arquivo, 'w', encoding='utf-8') as f_out:
        # Salvamos com indentação para facilitar a leitura da IA e do tradutor
        json.dump(dados, f_out, ensure_ascii=False, indent=2)
    
    print(f"  -> Gerado: parte_{numero_parte:03d}.json ({len(dados)} entradas)")

if __name__ == '__main__':
    dividir_json_inteligente()