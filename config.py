# config.py (Versão Final - Portable Ready)
import customtkinter as ctk
import os
import sys

# --- TEMA E CORES ---
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

# Paleta Veritas Blue
VERITAS_BLUE = "#2196F3"        
VERITAS_BLUE_HOVER = "#1976D2"
VERITAS_BG_DASH = "#F5F7FA"     
VERITAS_WHITE = "#FFFFFF"
VERITAS_TEXT = "#333333"
VERITAS_DANGER = "#F44336"
VERITAS_PLAYER_BG = "black"
VERITAS_PRIMARY = VERITAS_BLUE 

# --- ARQUIVOS DE DADOS (Ficam na pasta do usuário, não dentro do EXE) ---
# Usamos os.getcwd() para que os dados fiquem na mesma pasta do executável
DB_FILE = os.path.join(os.getcwd(), "contratos_midia.json")
LAST_PATHS_FILE = os.path.join(os.getcwd(), "last_paths.txt")
MSG_FILE = os.path.join(os.getcwd(), "mensagens_locutor.json")
CONFIG_LOCUTOR = os.path.join(os.getcwd(), "config_locutor.json")

# --- FUNÇÃO MÁGICA DE RECURSOS INTERNOS ---
# Essa função encontra arquivos (imagens, ffmpeg, vlc) se estiver compilado ou não
def resource_path(relative_path):
    """ Obtém o caminho absoluto para recursos, funciona para dev e para PyInstaller """
    try:
        # PyInstaller cria uma pasta temporária em _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Caminhos das Ferramentas (Binários)
# O sistema vai procurar esses arquivos JUNTOS do executável
FFMPEG_PATH = resource_path("ffmpeg.exe")
FFPROBE_PATH = resource_path("ffprobe.exe")