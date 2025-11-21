import customtkinter as ctk

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

# Alias de compatibilidade
VERITAS_PRIMARY = VERITAS_BLUE 

# Arquivos
DB_FILE = "contratos_midia.json"
LAST_PATHS_FILE = "last_paths.txt"