# config.py (Versão 19.22 - URL RAW Corrigida + AppData)
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

# --- DEFINIÇÃO DA PASTA DE DADOS (CORREÇÃO DE PERMISSÃO) ---
# Salva em C:\Users\Nome\AppData\Roaming\VeritasPlayer para não dar erro
try:
    app_data_dir = os.getenv('APPDATA')
    DATA_FOLDER = os.path.join(app_data_dir, "VeritasPlayer")
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
except Exception as e:
    DATA_FOLDER = os.getcwd()

# --- ARQUIVOS DE DADOS ---
DB_FILE = os.path.join(DATA_FOLDER, "contratos_midia.json")
LAST_PATHS_FILE = os.path.join(DATA_FOLDER, "last_paths.txt")
MSG_FILE = os.path.join(DATA_FOLDER, "mensagens_locutor.json")
CONFIG_LOCUTOR = os.path.join(DATA_FOLDER, "config_locutor.json")

# --- FUNÇÃO MÁGICA DE RECURSOS INTERNOS ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Caminhos das Ferramentas
FFMPEG_PATH = resource_path("ffmpeg.exe")
FFPROBE_PATH = resource_path("ffprobe.exe")

# --- ATUALIZAÇÕES ---
CURRENT_VERSION = "19.23"

# CORREÇÃO DO LINK: Mudou de 'blob' para 'raw'
UPDATE_JSON_URL = "https://raw.githubusercontent.com/gabriielgouvea/veritas-player/main/version.json"