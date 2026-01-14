import customtkinter as ctk
import tkinter as tk
import json
import os
import base64
import urllib.request
import webbrowser
import time
import random
from datetime import datetime
from config import *

# --- FERRAMENTAS DE INTERFACE ---
class ToolTip(object):
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.showtip)

    def unschedule(self):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None

    def showtip(self, event=None):
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = ctk.CTkLabel(tw, text=self.text, fg_color="#333", text_color="white", corner_radius=6, font=("Segoe UI", 11), height=25)
        label.pack(ipadx=8, ipady=4)

    def hidetip(self):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None

class ModernPopUp(ctk.CTkToplevel):
    def __init__(self, parent, titulo, mensagem, tipo="ok"):
        super().__init__(parent)
        
        # --- AJUSTE VISUAL: Aumentei para caber o texto de update ---
        w = 500
        h = 300
        self.geometry(f"{w}x{h}")
        self.title(titulo)
        self.attributes("-topmost", True)
        self.resizable(False, False)
        self.configure(fg_color="white")
        self.resultado = False
        
        # --- CENTRALIZAÇÃO MELHORADA ---
        try:
            # Tenta centralizar exatamente no meio da janela pai
            px = parent.winfo_x()
            py = parent.winfo_y()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            
            x = px + (pw // 2) - (w // 2)
            y = py + (ph // 2) - (h // 2)
            self.geometry(f"+{x}+{y}")
        except:
            pass # Se falhar, usa o padrão do Windows
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(self, text=titulo.upper(), font=("Segoe UI", 18, "bold"), text_color=VERITAS_BLUE).pack(pady=(30,10))
        
        # Aumentei o wraplength para usar melhor a largura nova
        ctk.CTkLabel(self, text=mensagem, font=("Segoe UI", 13), text_color="#555", wraplength=450).pack(pady=10)
        
        frame_btn = ctk.CTkFrame(self, fg_color="transparent")
        frame_btn.pack(side="bottom", pady=30)
        
        btn_s = {"font": ("Segoe UI", 12, "bold"), "height": 40, "corner_radius": 6}
        
        if tipo == "ok":
            ctk.CTkButton(frame_btn, text="OK", width=120, fg_color=VERITAS_BLUE, hover_color=VERITAS_BLUE_HOVER, command=self.destroy, **btn_s).pack()
        elif tipo == "yesno":
            ctk.CTkButton(frame_btn, text="SIM, ATUALIZAR", width=140, fg_color=VERITAS_BLUE, hover_color=VERITAS_BLUE_HOVER, command=self.sim, **btn_s).pack(side="left", padx=15)
            ctk.CTkButton(frame_btn, text="AGORA NÃO", width=120, fg_color="#EEE", text_color="#333", hover_color="#DDD", command=self.destroy, **btn_s).pack(side="left", padx=15)
        
        self.transient(parent)
        self.grab_set()
        self.wait_window()

    def sim(self):
        self.resultado = True
        self.destroy()

# --- PERSISTÊNCIA DE DADOS ---
def carregar_db():
    if os.path.exists(DB_FILE):
        try:
            return json.load(open(DB_FILE, 'r'))
        except: pass
    return []

def salvar_db(dados):
    with open(DB_FILE, 'w') as f:
        json.dump(dados, f, indent=4)

def garantir_alerta_sonoro():
    path = "ding.mp3"
    if not os.path.exists(path):
        try:
            b64 = "SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4Ljc2LjEwMAAAAAAAAAAAAAAA//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAs8ANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAYx8ANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAcysANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAgzcANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAk0MANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAk0MANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAk0MANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAk0MANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq"
            with open(path, "wb") as f:
                f.write(base64.b64decode(b64))
        except Exception as e:
            print(f"Erro ao criar alerta sonoro: {e}")
            return None 
    return path

# --- SISTEMA DE ATUALIZAÇÃO (COM DEBUG E ANTI-CACHE) ---
def verificar_updates(url_json, versao_atual):
    print(f"\n--- INICIANDO VERIFICAÇÃO DE UPDATE ---")
    print(f"Versão Local: {versao_atual}")
    
    # Adiciona parametro aleatório para evitar Cache do GitHub
    url_final = f"{url_json}?t={int(time.time())}{random.randint(1,999)}"
    print(f"Consultando URL: {url_final}")

    try:
        req = urllib.request.Request(
            url_final, 
            headers={'User-Agent': 'Mozilla/5.0'} # Finge ser um navegador
        )
        
        with urllib.request.urlopen(req, timeout=5) as response:
            conteudo = response.read().decode('utf-8')
            print(f"Conteúdo baixado do GitHub:\n{conteudo}")
            
            data = json.loads(conteudo)
            remote_ver = data.get("version", "0.0")
            
            print(f"Versão Remota Encontrada: {remote_ver}")
            
            if remote_ver != versao_atual:
                print(">> ATUALIZAÇÃO DISPONÍVEL! <<")
                return True, data
            else:
                print(">> JÁ ESTÁ ATUALIZADO <<")
            
    except Exception as e:
        print(f"ERRO ao verificar update: {e}")
        return False, None
    
    return False, None

def abrir_link_download(url):
    print(f"Abrindo link: {url}")
    if url:
        webbrowser.open(url)


def _parse_iso_datetime(s: str) -> datetime:
    # Suporta 'Z' e offsets. Ex.: 2026-01-14T16:58:26.123456-03:00
    s = (s or "").strip()
    if not s:
        raise ValueError("datetime vazio")
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def obter_horario_brasilia(timeout: int = 4) -> datetime:
    """Retorna um datetime (timezone-aware) do horário de Brasília.

    Usa APIs públicas com fallback. Lança exceção se não conseguir.
    """
    urls = [
        "http://worldtimeapi.org/api/timezone/America/Sao_Paulo",
        "https://timeapi.io/api/Time/current/zone?timeZone=America/Sao_Paulo",
    ]

    last_err = None
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
            data = json.loads(raw)

            # worldtimeapi
            if isinstance(data, dict) and data.get("datetime"):
                return _parse_iso_datetime(data["datetime"])

            # timeapi.io
            if isinstance(data, dict) and data.get("dateTime"):
                return _parse_iso_datetime(data["dateTime"])

            raise ValueError("Resposta inesperada")
        except Exception as e:
            last_err = e

    raise RuntimeError(f"Falha ao obter horário de Brasília: {last_err}")


# --- PREFERÊNCIAS DO APP (AppData) ---
def carregar_app_settings():
    """Carrega preferências do app (AppData). Retorna dict vazio se não existir."""
    try:
        if os.path.exists(APP_SETTINGS_FILE):
            with open(APP_SETTINGS_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                return d if isinstance(d, dict) else {}
    except Exception:
        pass
    return {}


def salvar_app_settings(dados: dict) -> None:
    """Salva preferências do app (AppData)."""
    try:
        os.makedirs(os.path.dirname(APP_SETTINGS_FILE), exist_ok=True)
    except Exception:
        pass
    with open(APP_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)


def get_app_setting(chave: str, padrao=None):
    d = carregar_app_settings()
    return d.get(chave, padrao)


def set_app_setting(chave: str, valor) -> dict:
    d = carregar_app_settings()
    d[chave] = valor
    salvar_app_settings(d)
    return d