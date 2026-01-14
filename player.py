import os
import sys
import ctypes
import vlc 
import customtkinter as ctk
import tkinter as tk
import time
import json
import random
import pyautogui
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from config import *
from utils import ToolTip, carregar_db, salvar_db
from dashboard import DashboardWindow

# Marca d'água (PNG) por cima do vídeo (VLC logo overlay)
WATERMARK_TEXT = "Gouvea Automações"
WATERMARK_FONT_SIZE = 18
WATERMARK_BG_ALPHA = 210  # 0..255 (fundo preto)
WATERMARK_TEXT_ALPHA = 255
WATERMARK_LOGO_OPACITY = 220  # 0..255 (opacidade geral do logo no VLC)
# Observação (VLC): se você define logo_x/logo_y, o logo_position é ignorado.
# Então usamos coordenadas absolutas para garantir que fique no rodapé.
WATERMARK_POSITION = vlc.Position.top_left.value
WATERMARK_MARGIN_X = 18
WATERMARK_MARGIN_Y = 14
WATERMARK_ALIGN = "left"  # "left" ou "right"

# O overlay do VLC posiciona relativo à área do vídeo (pode parecer "no meio" com letterbox).
# Para garantir que fique no canto da TELA, usamos overlay da UI.
WATERMARK_UI_ENABLED = True
WATERMARK_UI_FONT = ("Segoe UI", 16, "bold")
WATERMARK_UI_PAD_X = 12
WATERMARK_UI_PAD_Y = 6
WATERMARK_UI_CORNER_RADIUS = 12
WATERMARK_UI_BG = "black"
WATERMARK_UI_FG = "white"
WATERMARK_UI_IMAGE_MAX_HEIGHT = 34

def _find_watermark_ui_image_path() -> str | None:
    # Prioridade: override ao lado do .exe; fallback para recurso empacotado (resource_path)
    app_dir = _get_app_dir()
    for name in ("logo_watermark.png", "watermark.png"):
        # 1) Ao lado do executável (permite o usuário substituir fácil)
        p = os.path.join(app_dir, name)
        if os.path.exists(p):
            return p

        # 2) Dentro do pacote do PyInstaller (dist/_internal)
        try:
            rp = resource_path(name)
            if os.path.exists(rp):
                return rp
        except Exception:
            pass
    return None

def _get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.getcwd()

WATERMARK_IMAGE_PATH = os.path.join(_get_app_dir(), "watermark.png")

def _ensure_watermark_image(path: str) -> None:
    if os.path.exists(path):
        return

    text = WATERMARK_TEXT

    # Tenta usar fontes do Windows (mais bonitas). Cai para default se falhar.
    font = None
    for candidate in (
        r"C:\Windows\Fonts\segoeuib.ttf",   # Segoe UI Bold
        r"C:\Windows\Fonts\segoeuisb.ttf",  # Segoe UI Semibold
        r"C:\Windows\Fonts\segoeui.ttf",    # Segoe UI
        r"C:\Windows\Fonts\arialbd.ttf",    # Arial Bold
        r"C:\Windows\Fonts\arial.ttf",
    ):
        try:
            if os.path.exists(candidate):
                font = ImageFont.truetype(candidate, WATERMARK_FONT_SIZE)
                break
        except Exception:
            font = None

    if font is None:
        font = ImageFont.load_default()

    pad_x, pad_y = 12, 7
    radius = 10

    tmp = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tmp)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    w = text_w + pad_x * 2
    h = text_h + pad_y * 2

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Fundo preto (com cantos arredondados)
    draw.rounded_rectangle(
        (0, 0, w - 1, h - 1),
        radius=radius,
        fill=(0, 0, 0, WATERMARK_BG_ALPHA),
    )

    # Texto branco
    draw.text((pad_x, pad_y), text, font=font, fill=(255, 255, 255, WATERMARK_TEXT_ALPHA))
    img.save(path, format="PNG")

if os.name == 'nt':
    try:
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            app_dir = os.getcwd()

        # No PyInstaller (one-folder), os binários e plugins podem ficar em _internal.
        # Procura primeiro ao lado do .exe e depois em _internal.
        candidates = [app_dir, os.path.join(app_dir, "_internal")]
        vlc_base = None
        for base in candidates:
            if os.path.exists(os.path.join(base, 'libvlc.dll')):
                vlc_base = base
                break

        if not vlc_base:
            dll_vlc = os.path.join(app_dir, 'libvlc.dll')
            try:
                ctypes.windll.user32.MessageBoxW(0, f"ARQUIVO SUMIU!\nNão achei: {dll_vlc}\n\nDica: mantenha a pasta _internal junto do executável.", "Aviso", 0x30)
            except:
                pass
            vlc_base = app_dir

        dll_vlc = os.path.join(vlc_base, 'libvlc.dll')
        dll_core = os.path.join(vlc_base, 'libvlccore.dll')
        PLUGIN_PATH = os.path.join(vlc_base, "plugins")
        if not os.path.isdir(PLUGIN_PATH):
            PLUGIN_PATH = os.path.join(app_dir, "plugins")

        # Garante que o loader do Windows encontre as DLLs do VLC.
        try:
            os.add_dll_directory(vlc_base)
        except Exception:
            pass
        try:
            if vlc_base != app_dir:
                os.add_dll_directory(app_dir)
        except Exception:
            pass

        os.environ['PYTHON_VLC_MODULE_PATH'] = vlc_base
        os.environ['VLC_PLUGIN_PATH'] = PLUGIN_PATH
        try:
            ctypes.CDLL(dll_core)
            ctypes.CDLL(dll_vlc)
        except: pass
    except Exception as e: print(f"Erro VLC: {e}")

class VisioDeckPlayer(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"Veritas Player v{CURRENT_VERSION}")
        self.configure(fg_color=VERITAS_PLAYER_BG)
        self.geometry("1200x800")
        self.after(100, lambda: self.state("zoomed"))
        self.is_fullscreen = False
        
        self.vlc_video = vlc.Instance("--no-xlib", "--input-repeat=0", "--disable-screensaver", "--avcodec-hw=none", "--vout=direct3d9", "--quiet", "--verbose=-1")
        self.player = self.vlc_video.media_player_new()
        self.vlc_audio = vlc.Instance("--aout=directsound", "--quiet", "--verbose=-1") 
        self.tts_player = self.vlc_audio.media_player_new()
        
        self.pasta_treino = ""
        if os.path.exists(LAST_PATHS_FILE):
            try: 
                with open(LAST_PATHS_FILE, "r") as f: self.pasta_treino = f.read().strip()
            except: pass
        
        self.playlist_folders = {}
        self.current_playlist = []
        self.current_playlist_name = "TODOS"
        self.idx_video = 0
        self.is_playing = False
        self.modo_ad = False       
        self.modo_tts = False      
        self.mem_time = 0          
        self.video_atual = ""      
        self.hist_minuto = [] 
        self.data_cache = datetime.now().strftime("%d/%m/%Y")
        self.shuffle = False
        self.repeat_state = 0      
        self.repeat_one_done = False 
        self.muted = False
        self.last_vol = 100
        self.last_mouse = (0,0)
        self.controls_on = False
        self.hide_task = None
        self.last_ad_timestamp = 0

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.video_frame = tk.Frame(self, bg="black")
        self.video_frame.grid(row=0, column=0, sticky="nsew")
        self.canvas = tk.Canvas(self.video_frame, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        self.controls = ctk.CTkFrame(self, fg_color="#111", height=150, corner_radius=15, border_width=1, border_color="#333")
        self.slider = ctk.CTkSlider(self.controls, from_=0, to=1000, command=self.seek, progress_color=VERITAS_BLUE, button_color=VERITAS_BLUE, button_hover_color=VERITAS_BLUE_HOVER, fg_color="#333", height=16)
        self.slider.pack(fill="x", padx=30, pady=(15, 5))
        ToolTip(self.slider, "Progresso do Vídeo")
        
        bot_area = ctk.CTkFrame(self.controls, fg_color="transparent")
        bot_area.pack(fill="both", expand=True, padx=30, pady=(5, 15))
        
        left_c = ctk.CTkFrame(bot_area, fg_color="transparent"); left_c.pack(side="left")
        self.btn_shuf = ctk.CTkButton(left_c, text="🔀", width=40, height=40, fg_color="transparent", font=("Arial", 20), command=self.toggle_shuffle, hover_color="#333", text_color="#777"); self.btn_shuf.pack(side="left", padx=(0,10)); ToolTip(self.btn_shuf, "Vídeo Aleatório")
        self.lbl_time = ctk.CTkLabel(left_c, text="00:00 / 00:00", font=("Segoe UI", 12), text_color="#AAA"); self.lbl_time.pack(side="left")

        center_c = ctk.CTkFrame(bot_area, fg_color="transparent"); center_c.place(relx=0.5, rely=0.5, anchor="center")
        btn_std = {"fg_color": "transparent", "text_color": "#EEE", "hover_color": "#333", "width": 50, "height": 50, "font": ("Arial", 24)}
        self.btn_prev = ctk.CTkButton(center_c, text="⏮", command=self.prev, **btn_std); self.btn_prev.pack(side="left", padx=5)
        self.btn_rewind = ctk.CTkButton(center_c, text="↺ 10", command=lambda: self.skip_time(-10), fg_color="transparent", text_color="#DDD", hover_color="#333", width=50, height=50, font=("Segoe UI", 12, "bold")); self.btn_rewind.pack(side="left", padx=5)
        self.btn_play = ctk.CTkButton(center_c, text="⏯", command=self.play_pause, width=70, height=70, corner_radius=35, fg_color=VERITAS_BLUE, hover_color=VERITAS_BLUE_HOVER, font=("Arial", 30)); self.btn_play.pack(side="left", padx=15)
        self.btn_fwd = ctk.CTkButton(center_c, text="↻ 10", command=lambda: self.skip_time(10), fg_color="transparent", text_color="#DDD", hover_color="#333", width=50, height=50, font=("Segoe UI", 12, "bold")); self.btn_fwd.pack(side="left", padx=5)
        self.btn_next = ctk.CTkButton(center_c, text="⏭", command=self.next, **btn_std); self.btn_next.pack(side="left", padx=5)
        self.btn_rep = ctk.CTkButton(center_c, text="🔁", command=self.toggle_repeat, **btn_std); self.btn_rep.pack(side="left", padx=(15, 0)); self.update_repeat_icon() 

        right_c = ctk.CTkFrame(bot_area, fg_color="transparent"); right_c.pack(side="right")
        self.btn_mute = ctk.CTkButton(right_c, text="🔊", width=40, command=self.toggle_mute, fg_color="transparent", hover_color="#333", font=("Arial", 20)); self.btn_mute.pack(side="left")
        self.sl_vol = ctk.CTkSlider(right_c, from_=0, to=100, width=100, command=self.set_vol, progress_color="white", button_color="white", button_hover_color="#DDD"); self.sl_vol.set(100); self.sl_vol.pack(side="left", padx=10)
        self.btn_fs = ctk.CTkButton(right_c, text="⛶", width=40, command=self.toggle_fs, fg_color="transparent", hover_color="#333", font=("Arial", 20)); self.btn_fs.pack(side="left")

        # Watermark na UI (fica no canto da tela, acima do vídeo)
        self.watermark_label = None
        self.watermark_ui_image = None
        if WATERMARK_UI_ENABLED:
            self.watermark_label = ctk.CTkLabel(
                self,
                text="",
                font=WATERMARK_UI_FONT,
                text_color=WATERMARK_UI_FG,
                fg_color=WATERMARK_UI_BG,
                corner_radius=WATERMARK_UI_CORNER_RADIUS,
            )
            self._load_watermark_ui_asset()
            self.watermark_label.lift()

        self.lbl_info = ctk.CTkLabel(self.canvas, text="Clique em AJUSTES para selecionar a pasta...", font=("Arial", 30), text_color="#555", bg_color="black"); self.lbl_info.place(relx=0.5, rely=0.5, anchor="center")
        self.btn_settings = ctk.CTkButton(self, text="⚙️  AJUSTES", command=self.open_dash, width=130, height=40, fg_color="white", text_color="black", hover_color="#DDD", font=("Segoe UI", 12, "bold"), corner_radius=20, bg_color="black"); self.btn_settings.place(relx=0.98, rely=0.03, anchor="ne")
        self.opt_playlist = ctk.CTkOptionMenu(self, values=["TODOS"], command=self.change_playlist, width=200, height=40, fg_color="#333", button_color="#444", text_color="white", button_hover_color="#555", font=("Segoe UI", 12, "bold"), dropdown_fg_color="#222", dropdown_text_color="white", bg_color="black"); self.opt_playlist.place(relx=0.88, rely=0.03, anchor="ne"); self.opt_playlist.set("TODOS")

        self.bind_all("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.bind_all("<Escape>", self.toggle_fs)

        self.configurar_watermark()
        self.bind("<Configure>", lambda e: self._posicionar_watermark_ui())
        self.check_mouse_polling()
        self.sys_loop()
        self.ui_loop()
        if self.pasta_treino: self.scan_folders()
        self.show_controls()

    def open_dash(self): DashboardWindow(self, self)
    
    def configuring_watermark(self):
        self.configurar_watermark()

    def configurar_watermark(self):
        # 1) Watermark na UI (preferida: canto da tela)
        if WATERMARK_UI_ENABLED:
            self._load_watermark_ui_asset()
            self._posicionar_watermark_ui()

        # 2) Desativa overlay do VLC para não ficar "no meio" em vídeos com letterbox.
        try:
            self.player.video_set_logo_int(vlc.VideoLogoOption.logo_enable.value, 0)
        except Exception:
            pass

    def _posicionar_watermark_ui(self):
        if not WATERMARK_UI_ENABLED or not self.watermark_label:
            return

        # Usa posicionamento relativo para não depender do tamanho "reqwidth" (que pode mudar
        # depois que a imagem carrega ou ao alternar fullscreen/DPI). Isso evita ficar "cortado".
        controls_h = 150 if getattr(self, "controls_on", False) else 0

        align_right = str(WATERMARK_ALIGN).lower() == "right"
        relx = 1.0 if align_right else 0.0
        anchor = "se" if align_right else "sw"
        x = -int(WATERMARK_MARGIN_X) if align_right else int(WATERMARK_MARGIN_X)
        y = -int(WATERMARK_MARGIN_Y) - int(controls_h)

        self.watermark_label.place(relx=relx, rely=1.0, x=x, y=y, anchor=anchor)
        self.watermark_label.lift()

    def _load_watermark_ui_asset(self):
        if not WATERMARK_UI_ENABLED or not self.watermark_label:
            return

        img_path = _find_watermark_ui_image_path()
        if img_path:
            try:
                im = Image.open(img_path).convert("RGBA")
                w0, h0 = im.size
                if h0 > 0:
                    scale = min(1.0, float(WATERMARK_UI_IMAGE_MAX_HEIGHT) / float(h0))
                else:
                    scale = 1.0
                w = max(1, int(w0 * scale))
                h = max(1, int(h0 * scale))
                im = im.resize((w, h), Image.LANCZOS)
                self.watermark_ui_image = ctk.CTkImage(light_image=im, dark_image=im, size=(w, h))
                self.watermark_label.configure(
                    image=self.watermark_ui_image,
                    text="",
                    fg_color="transparent",
                )
                self.after_idle(self._posicionar_watermark_ui)
                return
            except Exception:
                # Cai para texto
                self.watermark_ui_image = None

        # Fallback: texto bonito com fundo
        self.watermark_ui_image = None
        self.watermark_label.configure(
            image=None,
            text=WATERMARK_TEXT,
            font=WATERMARK_UI_FONT,
            text_color=WATERMARK_UI_FG,
            fg_color=WATERMARK_UI_BG,
            corner_radius=WATERMARK_UI_CORNER_RADIUS,
        )
        self.after_idle(self._posicionar_watermark_ui)

    def tocar_audio_background(self, arquivo_audio):
        if not os.path.exists(arquivo_audio): return
        try: pyautogui.press("playpause")
        except: pass
        time.sleep(0.5)
        self.modo_tts = True; self.mem_time = 0 
        self.tts_player.set_media(self.vlc_audio.media_new(arquivo_audio))
        self.tts_player.audio_set_volume(100)
        self.tts_player.play()
        self.controls.place_forget(); self.configure(cursor="none")

    def tocar_anuncio(self, arquivo_audio, volume_alvo=100):
        if not os.path.exists(arquivo_audio): return
        try: pyautogui.press("playpause")
        except: pass
        time.sleep(0.5) 
        if self.is_playing: self.player.pause(); self.mem_time = self.player.get_time()
        self.modo_tts = True; self.btn_play.configure(text="⏸")
        self.tts_player.set_media(self.vlc_audio.media_new(arquivo_audio))
        self.tts_player.audio_set_volume(100); self.tts_player.play()
        self.controls.place_forget(); self.configure(cursor="none")

    def parar_tts(self):
        if self.tts_player.is_playing(): self.tts_player.stop()
        self._restaurar_estado_pos_tts()

    def _restaurar_estado_pos_tts(self):
        self.modo_tts = False; self.configure(cursor="arrow")
        try: pyautogui.press("playpause") 
        except: pass
        if self.mem_time > 0: self.play_video(self.video_atual, resume=True); self.after(500, lambda: self.player.set_time(self.mem_time))

    def get_tts_status(self):
        if not self.modo_tts: return False, 0, 0
        try:
            length = self.tts_player.get_length(); time_ms = self.tts_player.get_time()
            if length <= 0: return True, 0, 100 
            return True, time_ms, length
        except: return False, 0, 0

    def change_playlist(self, name):
        if name in self.playlist_folders:
            self.current_playlist_name = name; self.current_playlist = self.playlist_folders[name]
            self.opt_playlist.set(name)
            if self.current_playlist: self.play_video(0, start_paused=False)
            else: self.player.stop()

    def scan_folders(self):
        self.playlist_folders = {"TODOS": []}
        try:
            for root, dirs, files in os.walk(self.pasta_treino):
                folder = os.path.basename(root)
                if folder == os.path.basename(self.pasta_treino): folder = "Geral"
                if folder not in self.playlist_folders: self.playlist_folders[folder] = []
                for f in files:
                    if f.lower().endswith(('.mp4','.mkv','.avi')):
                        path = os.path.join(root, f)
                        self.playlist_folders["TODOS"].append(path)
                        self.playlist_folders[folder].append(path)
            empty = [k for k,v in self.playlist_folders.items() if not v]
            for k in empty: del self.playlist_folders[k]
            pl_names = sorted(list(self.playlist_folders.keys()))
            if "TODOS" in pl_names: pl_names.remove("TODOS"); pl_names.insert(0, "TODOS")
            if pl_names: self.opt_playlist.configure(values=pl_names); self.opt_playlist.set(self.current_playlist_name)
            if self.playlist_folders["TODOS"]: self.lbl_info.place_forget(); self.current_playlist = self.playlist_folders["TODOS"]; self.play_video(0, start_paused=True)
            else: self.lbl_info.configure(text="Nenhum vídeo encontrado!")
        except: pass

    def play_video(self, target, ad=False, resume=False, start_paused=False, keep_repeat=False):
        path = ""
        if ad: path = target 
        else:
            if not self.current_playlist: return
            if isinstance(target, int): 
                if target >= len(self.current_playlist): target = 0
                self.idx_video = target; path = self.current_playlist[target]
            else: path = target
            self.video_atual = path 
            if not keep_repeat: self.repeat_one_done = False
        self.player.set_hwnd(self.canvas.winfo_id())
        self.player.set_media(self.vlc_video.media_new(path))
        self.player.play()
        # Reaplica com um pequeno delay para garantir que a UI já foi dimensionada.
        self.after(200, self.configurar_watermark)
        if start_paused: self.after(100, lambda: self.player.pause()); self.is_playing = False; self.btn_play.configure(text="▶")
        else: self.is_playing = True; self.btn_play.configure(text="⏸")
        
        if ad: 
            self.modo_ad = True; self.controls.place_forget(); self.btn_settings.place_forget(); self.opt_playlist.place_forget(); self.configure(cursor="none"); self.last_ad_timestamp = time.time()
        else: 
            self.modo_ad = False; self.modo_tts = False 
            if not resume:
                if self.controls_on:
                    if self.hide_task: self.after_cancel(self.hide_task)
                    self.hide_task = self.after(3000, self.hide_controls)
                else: self.configure(cursor="none"); self.controls.place_forget()
            else: self.configure(cursor="none"); self.controls.place_forget()

    def skip_time(self, seconds):
        if not self.is_playing: return
        curr = self.player.get_time(); length = self.player.get_length(); new_time = curr + (seconds * 1000)
        if new_time < 0: new_time = 0
        if new_time > length: new_time = length - 1000
        self.player.set_time(int(new_time)); self.slider.set(self.player.get_position() * 1000)

    def toggle_repeat(self): self.repeat_state = (self.repeat_state + 1) % 3; self.update_repeat_icon()
    def update_repeat_icon(self):
        if self.repeat_state == 0: self.btn_rep.configure(text="🔁", text_color="#777"); ToolTip(self.btn_rep, "Repetição: DESATIVADA")
        elif self.repeat_state == 1: self.btn_rep.configure(text="🔁", text_color=VERITAS_BLUE); ToolTip(self.btn_rep, "Repetir Vídeo: INFINITO")
        elif self.repeat_state == 2: self.btn_rep.configure(text="🔂", text_color=VERITAS_BLUE); ToolTip(self.btn_rep, "Repetir Vídeo: 1 VEZ")

    def toggle_shuffle(self): 
        self.shuffle = not self.shuffle
        if self.shuffle: self.btn_shuf.configure(text_color=VERITAS_BLUE); ToolTip(self.btn_shuf, "Aleatório: LIGADO")
        else: self.btn_shuf.configure(text_color="#777"); ToolTip(self.btn_shuf, "Aleatório: DESLIGADO")

    def next(self):
        if not self.current_playlist: return
        if self.shuffle: nxt = random.randint(0, len(self.current_playlist)-1)
        else: nxt = (self.idx_video + 1) % len(self.current_playlist)
        self.play_video(nxt)

    def prev(self):
        if not self.current_playlist: return
        self.play_video((self.idx_video - 1) % len(self.current_playlist))

    def play_pause(self):
        if self.is_playing: self.player.pause(); self.is_playing=False; self.btn_play.configure(text="▶")
        else: self.player.play(); self.is_playing=True; self.btn_play.configure(text="⏸")

    def seek(self, v): self.player.set_position(float(v)/1000)
    def set_vol(self, v): self.player.audio_set_volume(int(v))

    def toggle_mute(self):
        if self.muted: self.muted=False; self.player.audio_set_mute(False); self.sl_vol.set(self.last_vol); self.btn_mute.configure(text="🔊")
        else: self.last_vol=self.sl_vol.get(); self.muted=True; self.player.audio_set_mute(True); self.sl_vol.set(0); self.btn_mute.configure(text="🔇")
    
    def sys_loop(self):
        hoje = datetime.now().strftime("%d/%m/%Y")
        if hoje != self.data_cache:
            self.data_cache = hoje
            try:
                with open(DB_FILE,'r') as f: d = json.load(f)
                for c in d: c["execucoes_hoje"] = []
                with open(DB_FILE,'w') as f: json.dump(d,f,indent=4)
            except: pass
        agora_ts = time.time()
        if not self.modo_ad and not self.modo_tts and (agora_ts - self.last_ad_timestamp) > 60:
            if os.path.exists(DB_FILE):
                now = datetime.now(); hora = now.strftime("%H:%M"); wd = ["seg","ter","qua","qui","sex","sab","dom"][now.weekday()]
                try:
                    with open(DB_FILE,'r') as f: cons = json.load(f)
                    sv = False
                    for c in cons:
                        if not c.get("ativo") or not c.get("inicio"): continue
                        if c.get("modo") == "DATAS ESPECÍFICAS":
                            if hoje not in c.get("datas_especificas", []): continue
                        else:
                            try:
                                ini = datetime.strptime(c["inicio"], "%d/%m/%Y")
                                if now.date() < ini.date(): continue
                                if c["fim"] != "INDETERMINADO":
                                    if now > datetime.strptime(c["fim"], "%d/%m/%Y").replace(hour=23,minute=59): continue
                            except: continue
                            if not c.get("somente_hoje") and wd not in c.get("dias", []): continue
                            if c.get("somente_hoje") and c["inicio"] != hoje: continue
                        if hora in c["horarios"]:
                            if self.is_playing:
                                if hora not in c.get("execucoes_hoje", []):
                                    if "execucoes_hoje" not in c: c["execucoes_hoje"] = []
                                    c["execucoes_hoje"].append(hora); sv = True
                                    tipo = c.get("tipo", "VIDEO")
                                    if tipo == "AUDIO": self.tocar_audio_background(c["video"])
                                    else: self.mem_time = self.player.get_time(); self.play_video(c["video"], ad=True)
                                    break
                    if sv:
                        with open(DB_FILE,'w') as f:
                            json.dump(cons,f,indent=4)
                except: pass
        if self.modo_tts:
            st = self.tts_player.get_state()
            if st == vlc.State.Ended or st == vlc.State.Error: self._restaurar_estado_pos_tts() 
        elif self.is_playing:
            st = self.player.get_state()
            if st == vlc.State.Ended or st == vlc.State.Error:
                if self.modo_ad: self.modo_ad = False; self.play_video(self.video_atual, resume=True); self.after(500, lambda: self.player.set_time(self.mem_time))
                else:
                    if self.repeat_state == 1: self.play_video(self.idx_video, keep_repeat=True)
                    elif self.repeat_state == 2: 
                        if not self.repeat_one_done: self.play_video(self.idx_video, keep_repeat=True); self.repeat_one_done = True
                        else: self.repeat_state = 0; self.update_repeat_icon(); self.next()
                    else: self.next()
        self.after(1000, self.sys_loop)

    def ui_loop(self):
        if self.is_playing and not self.modo_tts:
            try:
                c = self.player.get_time(); t = self.player.get_length()
                if t > 0: self.slider.set(self.player.get_position()*1000); self.lbl_time.configure(text=f"{time.strftime('%M:%S', time.gmtime(c//1000))} / {time.strftime('%M:%S', time.gmtime(t//1000))}")
            except: pass
        self.after(500, self.ui_loop)

    def check_mouse_polling(self):
        if not self.modo_ad and not self.modo_tts:
            try:
                x, y = self.winfo_pointerxy()
                if abs(x-self.last_mouse[0])>10 or abs(y-self.last_mouse[1])>10: self.last_mouse=(x,y); self.on_mouse_move(None)
            except: pass
        self.after(100, self.check_mouse_polling)

    def on_mouse_move(self, e):
        if self.modo_ad or self.modo_tts: return
        self.show_controls()
        if self.hide_task: self.after_cancel(self.hide_task)
        self.hide_task = self.after(3000, self.hide_controls)

    def show_controls(self):
        if not self.controls_on:
            self.configure(cursor="arrow")
            self.controls.place(relx=0.5, rely=0.85, relwidth=0.9, anchor="center")
            self.controls.lift(); self.controls_on=True
            if not self.is_fullscreen: self.btn_settings.place(relx=0.98, rely=0.03, anchor="ne"); self.opt_playlist.place(relx=0.88, rely=0.03, anchor="ne")
            self._posicionar_watermark_ui()

    def hide_controls(self):
        if self.is_playing and not self.modo_ad and not self.modo_tts:
            self.controls.place_forget(); self.configure(cursor="none"); self.controls_on = False
            if self.is_fullscreen: self.btn_settings.place_forget(); self.opt_playlist.place_forget()
            self._posicionar_watermark_ui()

    def toggle_fs(self, e=None):
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen: self.btn_settings.place_forget(); self.opt_playlist.place_forget(); self.attributes("-fullscreen", True)
        else: self.attributes("-fullscreen", False); self.state("zoomed"); self.btn_settings.place(relx=0.98, rely=0.03, anchor="ne"); self.opt_playlist.place(relx=0.88, rely=0.03, anchor="ne")
        self.show_controls()
        # Garante reposicionamento depois que o Windows aplicar o fullscreen
        self.after(60, self._posicionar_watermark_ui)
        if self.watermark_label:
            self.after(60, self.watermark_label.lift)

if __name__ == "__main__":
    app = VisioDeckPlayer()
    app.mainloop()