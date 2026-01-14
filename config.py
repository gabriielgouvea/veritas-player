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

# --- DEFINIÇÃO DA PASTA DE DADOS (AppData) ---
try:
    app_data_dir = os.getenv('APPDATA')
    DATA_FOLDER = os.path.join(app_data_dir, "VeritasPlayer")
    
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
except Exception as e:
    # Fallback para pasta local se der erro
    DATA_FOLDER = os.getcwd()

# --- ARQUIVOS DE DADOS ---
DB_FILE = os.path.join(DATA_FOLDER, "contratos_midia.json")
LAST_PATHS_FILE = os.path.join(DATA_FOLDER, "last_paths.txt")
MSG_FILE = os.path.join(DATA_FOLDER, "mensagens_locutor.json")
CONFIG_LOCUTOR = os.path.join(DATA_FOLDER, "config_locutor.json")

# --- RECURSOS INTERNOS ---
def app_dir() -> str:
    """Diretório base do app (dev: cwd, empacotado: ao lado do .exe)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.abspath(".")

def resource_path(relative_path):
    """ Retorna caminho absoluto, funcionando para Dev e PyInstaller """
    candidates = []
    try:
        candidates.append(sys._MEIPASS)
    except Exception:
        pass
    candidates.append(app_dir())
    candidates.append(os.path.abspath("."))

    for base in candidates:
        p = os.path.join(base, relative_path)
        if os.path.exists(p):
            return p
    return os.path.join(candidates[0], relative_path)

# Caminhos das Ferramentas
FFMPEG_PATH = resource_path("ffmpeg.exe")
FFPROBE_PATH = resource_path("ffprobe.exe")

# --- NOVO: Caminho da Logo Marca D'água ---
# Certifique-se de ter o arquivo 'logo_watermark.png' na raiz do projeto
LOGO_PATH = resource_path("logo_watermark.png")

# --- ATUALIZAÇÕES ---
CURRENT_VERSION = "19.24" 
UPDATE_JSON_URL = "https://raw.githubusercontent.com/gabriielgouvea/veritas-player/main/version.json"