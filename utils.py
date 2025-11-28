# utils.py
import customtkinter as ctk
import tkinter as tk
import json
import os
import base64
from config import *

# Dependências de Áudio do Windows
import comtypes
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# ... (As classes ToolTip, ModernPopUp, funções carregar_db, salvar_db e garantir_alerta_sonoro CONTINUAM IGUAIS) ...
# ... (Copie elas do código anterior se precisar, vou focar na correção do ControleVolume abaixo) ...

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
        self.geometry("400x200")
        self.title(titulo)
        self.attributes("-topmost", True)
        self.resizable(False, False)
        self.configure(fg_color="white")
        self.resultado = False
        
        try:
            self.geometry(f"+{parent.winfo_x()+300}+{parent.winfo_y()+300}")
        except: pass
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(self, text=titulo.upper(), font=("Segoe UI", 16, "bold"), text_color=VERITAS_BLUE).pack(pady=(25,5))
        ctk.CTkLabel(self, text=mensagem, font=("Segoe UI", 12), text_color="#555", wraplength=350).pack(pady=10)
        
        frame_btn = ctk.CTkFrame(self, fg_color="transparent")
        frame_btn.pack(pady=20)
        
        btn_s = {"font": ("Segoe UI", 12, "bold"), "height": 35, "corner_radius": 6}
        
        if tipo == "ok":
            ctk.CTkButton(frame_btn, text="OK", width=100, fg_color=VERITAS_BLUE, hover_color=VERITAS_BLUE_HOVER, command=self.destroy, **btn_s).pack()
        elif tipo == "yesno":
            ctk.CTkButton(frame_btn, text="SIM", width=100, fg_color=VERITAS_BLUE, hover_color=VERITAS_BLUE_HOVER, command=self.sim, **btn_s).pack(side="left", padx=10)
            ctk.CTkButton(frame_btn, text="NÃO", width=100, fg_color="#EEE", text_color="#333", hover_color="#DDD", command=self.destroy, **btn_s).pack(side="left", padx=10)
        
        self.transient(parent)
        self.grab_set()
        self.wait_window()

    def sim(self):
        self.resultado = True
        self.destroy()

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
            b64 = "SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4Ljc2LjEwMAAAAAAAAAAAAAAA//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAAAANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAAs8ANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAYx8ANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAcysANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAgzcANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAk0MANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAk0MANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAk0MANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq//NkxAk0MANIAAAAAExBTUUzLjEwMKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq"
            with open(path, "wb") as f:
                f.write(base64.b64decode(b64))
        except Exception as e:
            print(f"Erro ao criar alerta sonoro: {e}")
            return None 
            
    return path

# --- CONTROLE DE VOLUME DO WINDOWS (MASTER) - CORRIGIDO ---
class ControleVolume:
    @staticmethod
    def _get_interface():
        # Método interno para tentar pegar a interface de áudio de várias formas
        try:
            comtypes.CoInitialize()
            # Tenta pegar os falantes padrão
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            return cast(interface, POINTER(IAudioEndpointVolume))
        except:
            return None

    @staticmethod
    def get_volume():
        interface = ControleVolume._get_interface()
        if interface:
            try:
                return int(round(interface.GetMasterVolumeLevelScalar() * 100))
            except: pass
        return 50 # Fallback se falhar

    @staticmethod
    def set_volume(valor):
        interface = ControleVolume._get_interface()
        if interface:
            try:
                val = max(0, min(100, int(valor)))
                interface.SetMasterVolumeLevelScalar(val / 100, None)
            except: pass