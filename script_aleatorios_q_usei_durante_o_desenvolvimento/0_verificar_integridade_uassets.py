"""
Script de Juiz Automático (QA).
Objetivo: Validar automaticamente cada arquivo convertido.
Fluxo: 
1. Converte JSON -> UAsset (usando UI Automation no UAssetGUI).
2. Empacota em um arquivo .pak (via batch).
3. Instala o mod no jogo.
4. Abre o jogo e monitora se ele entra em 'Crash' ou 'Não Respondendo'.
"""

import os
import subprocess
import shutil
import time
import pyautogui
import pyperclip
import psutil
from config import (
    UASSET_GUI_PATH, UE_VERSION, PASTA_JSON_ORIGINAL, 
    PASTA_MOD_FINAL
)

# --- CONFIGURAÇÕES DE TESTE ---
# Local onde o mod será colocado para o jogo carregar
PASTA_MODS_JOGO = r"D:\JOGOS\threeoutof10Ep1\ThreeTen\Content\Paks\~mods"
# Executável do jogo para monitoramento
GAME_EXE = r"D:\JOGOS\threeoutof10Ep1\ThreeTen.exe"
# Script de empacotamento (UnrealPak)
BATCH_PACOTE = r"D:\Ferramentas\Engine\Binaries\Win64\UnrealPak-Batch-With-Compression.bat"
# Tempo que o jogo deve rodar para ser considerado "saudável"
TEMPO_TESTE = 5  

# Logs para persistência: evita re-testar arquivos que já deram crash ou sucesso
LOG_BLACKLIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blacklist_crashes.txt") 
LOG_SUCESSO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testes_concluidos.txt")

def esperar_janela(titulos, timeout=0.5):
    """
    Função auxiliar para verificar se uma janela específica (Erro, Crash, etc)
    apareceu na tela. Útil para identificar falhas do UAssetGUI ou do jogo.
    """
    inicio = time.time()
    while time.time() - inicio < timeout:
        for t in titulos:
            janelas = pyautogui.getWindowsWithTitle(t)
            if janelas and janelas[0].visible: return janelas[0]
        time.sleep(0.1)
    return None

def converter_com_forca(uasset_path, json_path):
    """
    Esta é a parte mais crítica. Como o UAssetGUI não tem modo CLI para SALVAR,
    o script abre a UI e "clica" nos botões via atalhos de teclado (Ctrl+Shift+S).
    """
    proc = subprocess.Popen([UASSET_GUI_PATH, json_path, UE_VERSION])
    start_time = time.time()
    passos = {"SALVAR": False}
    
    # Loop de monitoramento da interface do UAssetGUI
    while proc.poll() is None:
        # Tenta fechar janelas de erro inesperadas do programa
        for titulo in ["Notice", "Uh oh!", "Error", "Warning"]:
            win_erro = esperar_janela([titulo], 0.2)
            if win_erro:
                try: win_erro.activate(); pyautogui.press('enter'); time.sleep(0.4)
                except: pass

        # Simula salvar o arquivo (Ctrl+Shift+S)
        if time.time() - start_time > 1 and not passos["SALVAR"]:
            win_main = esperar_janela(["UAssetGUI"], 1)
            if win_main:
                try: 
                    win_main.activate(); pyautogui.hotkey('ctrl', 'shift', 's'); time.sleep(0.4)
                    passos["SALVAR"] = True
                except: pass
        
        # Simula o preenchimento da janela "Salvar Como"
        if passos["SALVAR"]:
            win_save = esperar_janela(["Save As", "Salvar como"], 0.4)
            if win_save:
                try:
                    win_save.activate(); pyperclip.copy(uasset_path); pyautogui.hotkey('ctrl', 'v'); time.sleep(0.4); pyautogui.press('enter'); time.sleep(0.4); pyautogui.press('enter')
                except: pass

        # Verifica se o arquivo foi criado com sucesso
        if os.path.exists(uasset_path) and os.path.getsize(uasset_path) > 10:
            proc.terminate(); os.system("taskkill /f /im UAssetGUI.exe >nul 2>&1"); return True
            
        if time.time() - start_time > 35: break
        time.sleep(0.5)
    
    # Força encerramento se travar
    proc.terminate(); os.system("taskkill /f /im UAssetGUI.exe >nul 2>&1")
    return os.path.exists(uasset_path) and os.path.getsize(uasset_path) > 10

def processar_um_arquivo(json_path, rel_path, nome):
    """
    Orquestra o teste de um único arquivo: 
    Converte -> Empacota -> Instala -> Abre o Jogo -> Monitora.
    """
    pasta_raiz_teste = os.path.join(PASTA_MOD_FINAL, "Traducao_PTBR_P")
    
    # Limpa resíduos de testes anteriores para garantir isolamento
    if os.path.exists(pasta_raiz_teste):
        shutil.rmtree(pasta_raiz_teste)
    
    dest_folder = os.path.join(pasta_raiz_teste, rel_path)
    os.makedirs(dest_folder, exist_ok=True)
    uasset_final = os.path.join(dest_folder, f"{nome}.uasset")

    # Passo 1: Conversão (UI Automation)
    if not converter_com_forca(json_path=json_path, uasset_path=uasset_final):
        return False, "Conversao"

    # Passo 2: Empacotamento (.pak)
    subprocess.run(["cmd", "/c", BATCH_PACOTE, pasta_raiz_teste], stdout=subprocess.DEVNULL)
    
    # Passo 3: Instalação (Move o arquivo .pak para a pasta do jogo)
    pak_gerado = os.path.join(PASTA_MOD_FINAL, f"{os.path.basename(pasta_raiz_teste)}.pak")
    pak_destino = os.path.join(PASTA_MODS_JOGO, "Teste_Unico_P.pak")
    
    if not os.path.exists(pak_gerado): return False, "Pak nao gerado"
    if os.path.exists(pak_destino): os.remove(pak_destino)
    shutil.move(pak_gerado, pak_destino)

    # Passo 4: Execução e Juiz (Monitora o jogo rodando)
    proc_game = subprocess.Popen(GAME_EXE, cwd=os.path.dirname(GAME_EXE))
    
    try:
        process = psutil.Process(proc_game.pid)
    except psutil.NoSuchProcess:
        return False, "Jogo nao abriu"
    
    start_time = time.time()
    while time.time() - start_time < TEMPO_TESTE:
        # Se o jogo fechar antes do tempo, houve um crash
        if proc_game.poll() is not None:
            os.system("taskkill /f /im ThreeTen-Win64-Shipping.exe >nul 2>&1")
            proc_game.terminate()
            return False, "Crash (Fechou)"

        # Monitora o estado "Não Respondendo" do Windows
        janelas = pyautogui.getWindowsWithTitle("ThreeTen")
        if janelas:
            if "Não Respondendo" in janelas[0].title:
                os.system("taskkill /f /im ThreeTen-Win64-Shipping.exe >nul 2>&1")
                proc_game.terminate()
                return False, "Crash (Nao Respondendo)"
        
        # Monitora se janelas de erro Fatal aparecem
        for titulo in ["Error", "Crash", "Fatal Error!"]:
            win_erro = esperar_janela([titulo], 0.1)
            if win_erro:
                os.system("taskkill /f /im ThreeTen-Win64-Shipping.exe >nul 2>&1")
                proc_game.terminate()
                return False, f"Crash (Janela: {titulo})"
        
        time.sleep(0.5)
    
    # Se chegou aqui, o mod é considerado saudável
    os.system("taskkill /f /im ThreeTen-Win64-Shipping.exe >nul 2>&1")
    proc_game.terminate()
    shutil.rmtree(pasta_raiz_teste)

    return True, "Ok"

if __name__ == "__main__":
    print("--- INICIANDO JUIZ AUTOMÁTICO ---")
    
    # Carrega listas de histórico para não repetir testes
    blacklist = []; sucessos = []
    if os.path.exists(LOG_BLACKLIST):
        with open(LOG_BLACKLIST, "r") as f: blacklist = f.read().splitlines()
    if os.path.exists(LOG_SUCESSO):
        with open(LOG_SUCESSO, "r") as f: sucessos = f.read().splitlines()

    # Coleta arquivos candidatos
    arquivos_a_testar = []
    for root, _, files in os.walk(PASTA_JSON_ORIGINAL):
        for f in files:
            if f.endswith(".json"):
                nome = f.replace(".json", "")
                if nome not in blacklist and nome not in sucessos:
                    arquivos_a_testar.append((os.path.join(root, f), os.path.relpath(root, PASTA_JSON_ORIGINAL), nome))
    
    # Loop de execução
    for path, rel, nome in arquivos_a_testar:
        print(f"\n📦 Testando: {nome}...", end=" ", flush=True)
        sucesso, status = processar_um_arquivo(path, rel, nome)
        
        if status == "Ok":
            print(f"✅ SAUDÁVEL")
            with open(LOG_SUCESSO, "a") as f_log: f_log.write(f"{nome}\n")
        elif "Crash" in status:
            print(f"💀 {status} - Blacklist!")
            with open(LOG_BLACKLIST, "a") as f_log: f_log.write(f"{nome}\n")
        else:
            print(f"⚠️ FALHA TÉCNICA: {status}. Será tentado de novo na próxima vez.")

    print("\n🏁 TESTE CONCLUÍDO!")