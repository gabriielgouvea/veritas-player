import os
import sys
import ctypes

# --- FIX "NUCLEAR" PARA VLC (CRÍTICO: DEVE VIR PRIMEIRO) ---
if os.name == 'nt':
    try:
        # 1. Descobrir onde estamos (Path Real)
        if getattr(sys, 'frozen', False):
            # Se for EXE, pega a pasta do executável
            app_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            # Se for Terminal, pega o diretório atual
            app_dir = os.getcwd()

        # 2. Definir caminhos críticos
        dll_vlc = os.path.join(app_dir, 'libvlc.dll')
        dll_core = os.path.join(app_dir, 'libvlccore.dll')
        PLUGIN_PATH = os.path.join(app_dir, "plugins")

        # 3. DEBUG VISUAL (Segurança: avisa se faltar arquivo vital)
        if not os.path.exists(dll_vlc):
            try:
                ctypes.windll.user32.MessageBoxW(0, f"ARQUIVO SUMIU!\nNão achei: {dll_vlc}", "Erro Fatal", 0x10)
            except:
                print(f"ERRO CRÍTICO: DLL não encontrada em {dll_vlc}")

        # 4. Adicionar ao Path do Windows para carregamento
        os.add_dll_directory(app_dir)
        
        # 5. Configurar Variáveis de Ambiente
        os.environ['PYTHON_VLC_MODULE_PATH'] = app_dir
        os.environ['VLC_PLUGIN_PATH'] = PLUGIN_PATH

        # 6. CARREGAMENTO FORÇADO VIA CTYPES
        try:
            ctypes.CDLL(dll_core)
            ctypes.CDLL(dll_vlc)
        except Exception as e:
            # Se falhar aqui mas carregar depois, tudo bem.
            pass
        
    except Exception as e:
        print(f"Erro ao configurar ambiente VLC: {e}")

# --- AGORA SIM IMPORTAMOS O RESTO ---
import vlc 
import customtkinter as ctk
import tkinter as tk
import time
import json
import random
import pyautogui
from datetime import datetime
from config import *
from utils import ToolTip, carregar_db, salvar_db
from dashboard import DashboardWindow

class VisioDeckPlayer(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configuração da Janela Principal
        self.title(f"Veritas Player v{CURRENT_VERSION}")
        self.configure(fg_color=VERITAS_PLAYER_BG)
        self.geometry("1200x800")
        
        self.after(100, lambda: self.state("zoomed"))
        self.is_fullscreen = False
        
        # --- CONFIGURAÇÃO DOS PLAYERS ---
        
        # PLAYER 1: VÍDEO 
        # --quiet e --verbose=-1 limpam o terminal de erros D3D11
        # --avcodec-hw=none evita travamentos com Intel UHD
        self.vlc_video = vlc.Instance(
            "--no-xlib", 
            "--input-repeat=0", 
            "--disable-screensaver", 
            "--avcodec-hw=none",
            "--vout=direct3d9",
            "--quiet",
            "--verbose=-1"
        )
        self.player = self.vlc_video.media_player_new()
        
        # PLAYER 2: ÁUDIO/TTS (DirectSound para mixagem independente)
        self.vlc_audio = vlc.Instance("--aout=directsound", "--quiet", "--verbose=-1") 
        self.tts_player = self.vlc_audio.media_player_new()
        
        # --- ESTADO E VARIÁVEIS ---
        self.pasta_treino = ""
        if os.path.exists(LAST_PATHS_FILE):
            try: 
                with open(LAST_PATHS_FILE, "r") as f:
                    self.pasta_treino = f.read().strip()
            except: pass
        
        self.playlist_folders = {}
        self.current_playlist = []
        self.current_playlist_name = "TODOS"
        self.idx_video = 0
        self.is_playing = False
        
        # Flags de Estado
        self.modo_ad = False       
        self.modo_tts = False      
        
        # Memória de Reprodução
        self.mem_time = 0          
        self.video_atual = ""      
        
        self.hist_minuto = [] 
        self.data_cache = datetime.now().strftime("%d/%m/%Y")
        
        # Controles
        self.shuffle = False
        self.repeat_state = 0      
        self.repeat_one_done = False 
        self.muted = False
        self.last_vol = 100
        
        # Mouse e UI
        self.last_mouse = (0,0)
        self.controls_on = False
        self.hide_task = None
        self.last_ad_timestamp = 0

        # --- LAYOUT GUI ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.video_frame = tk.Frame(self, bg="black")
        self.video_frame.grid(row=0, column=0, sticky="nsew")
        self.canvas = tk.Canvas(self.video_frame, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # --- BARRA DE CONTROLES ---
        self.controls = ctk.CTkFrame(self, fg_color="#111", height=150, corner_radius=15, border_width=1, border_color="#333")
        
        self.slider = ctk.CTkSlider(self.controls, from_=0, to=1000, command=self.seek, progress_color=VERITAS_BLUE, button_color=VERITAS_BLUE, button_hover_color=VERITAS_BLUE_HOVER, fg_color="#333", height=16)
        self.slider.pack(fill="x", padx=30, pady=(15, 5))
        ToolTip(self.slider, "Progresso do Vídeo")
        
        bot_area = ctk.CTkFrame(self.controls, fg_color="transparent")
        bot_area.pack(fill="both", expand=True, padx=30, pady=(5, 15))
        
        # Esquerda (Shuffle e Tempo)
        left_c = ctk.CTkFrame(bot_area, fg_color="transparent")
        left_c.pack(side="left")
        self.btn_shuf = ctk.CTkButton(left_c, text="🔀", width=40, height=40, fg_color="transparent", font=("Arial", 20), command=self.toggle_shuffle, hover_color="#333", text_color="#777")
        self.btn_shuf.pack(side="left", padx=(0,10))
        ToolTip(self.btn_shuf, "Vídeo Aleatório")
        self.lbl_time = ctk.CTkLabel(left_c, text="00:00 / 00:00", font=("Segoe UI", 12), text_color="#AAA")
        self.lbl_time.pack(side="left")

        # Centro (Play, Pause, Skip)
        center_c = ctk.CTkFrame(bot_area, fg_color="transparent")
        center_c.place(relx=0.5, rely=0.5, anchor="center")
        btn_std = {"fg_color": "transparent", "text_color": "#EEE", "hover_color": "#333", "width": 50, "height": 50, "font": ("Arial", 24)}
        
        self.btn_prev = ctk.CTkButton(center_c, text="⏮", command=self.prev, **btn_std)
        self.btn_prev.pack(side="left", padx=5)
        self.btn_rewind = ctk.CTkButton(center_c, text="↺ 10", command=lambda: self.skip_time(-10), fg_color="transparent", text_color="#DDD", hover_color="#333", width=50, height=50, font=("Segoe UI", 12, "bold"))
        self.btn_rewind.pack(side="left", padx=5)
        self.btn_play = ctk.CTkButton(center_c, text="⏯", command=self.play_pause, width=70, height=70, corner_radius=35, fg_color=VERITAS_BLUE, hover_color=VERITAS_BLUE_HOVER, font=("Arial", 30))
        self.btn_play.pack(side="left", padx=15)
        self.btn_fwd = ctk.CTkButton(center_c, text="↻ 10", command=lambda: self.skip_time(10), fg_color="transparent", text_color="#DDD", hover_color="#333", width=50, height=50, font=("Segoe UI", 12, "bold"))
        self.btn_fwd.pack(side="left", padx=5)
        self.btn_next = ctk.CTkButton(center_c, text="⏭", command=self.next, **btn_std)
        self.btn_next.pack(side="left", padx=5)
        self.btn_rep = ctk.CTkButton(center_c, text="🔁", command=self.toggle_repeat, **btn_std)
        self.btn_rep.pack(side="left", padx=(15, 0))
        self.update_repeat_icon() 

        # Direita (Volume e Fullscreen)
        right_c = ctk.CTkFrame(bot_area, fg_color="transparent")
        right_c.pack(side="right")
        self.btn_mute = ctk.CTkButton(right_c, text="🔊", width=40, command=self.toggle_mute, fg_color="transparent", hover_color="#333", font=("Arial", 20))
        self.btn_mute.pack(side="left")
        self.sl_vol = ctk.CTkSlider(right_c, from_=0, to=100, width=100, command=self.set_vol, progress_color="white", button_color="white", button_hover_color="#DDD")
        self.sl_vol.set(100)
        self.sl_vol.pack(side="left", padx=10)
        self.btn_fs = ctk.CTkButton(right_c, text="⛶", width=40, command=self.toggle_fs, fg_color="transparent", hover_color="#333", font=("Arial", 20))
        self.btn_fs.pack(side="left")

        # Info e Botões Superiores
        self.lbl_info = ctk.CTkLabel(self.canvas, text="Clique em AJUSTES para selecionar a pasta...", font=("Arial", 30), text_color="#555", bg_color="black")
        self.lbl_info.place(relx=0.5, rely=0.5, anchor="center")

        self.btn_settings = ctk.CTkButton(self, text="⚙️  AJUSTES", command=self.open_dash, width=130, height=40, fg_color="white", text_color="black", hover_color="#DDD", font=("Segoe UI", 12, "bold"), corner_radius=20, bg_color="black")
        self.btn_settings.place(relx=0.98, rely=0.03, anchor="ne")

        self.opt_playlist = ctk.CTkOptionMenu(self, values=["TODOS"], command=self.change_playlist, width=200, height=40, fg_color="#333", button_color="#444", text_color="white", button_hover_color="#555", font=("Segoe UI", 12, "bold"), dropdown_fg_color="#222", dropdown_text_color="white", bg_color="black")
        self.opt_playlist.place(relx=0.88, rely=0.03, anchor="ne")
        self.opt_playlist.set("TODOS")

        self.bind_all("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.bind_all("<Escape>", self.toggle_fs)

        # --- NOVO: Configurar Marca D'água (Logo) ---
        self.configurar_watermark()

        # Início dos Loops
        self.check_mouse_polling()
        self.sys_loop()
        self.ui_loop()
        
        if self.pasta_treino: self.scan_folders()
        self.show_controls()

    def open_dash(self):
        DashboardWindow(self, self)
    
    # --- NOVO MÉTODO: CONFIGURAR MARCA D'ÁGUA ---
    def configurar_watermark(self):
        """ Configura a logo da Gouvea Automações no canto inferior esquerdo """
        if not os.path.exists(LOGO_PATH):
            print(f"Aviso: Logo não encontrada em {LOGO_PATH}")
            return

        try:
            # 1. Habilita o filtro de logo (1 = ligado)
            self.player.video_set_logo_int(vlc.VideoLogoOption.enable, 1)
            
            # 2. Define o arquivo da imagem (IMPORTANTE: O VLC as vezes pede bytes)
            path_bytes = LOGO_PATH.encode('utf-8')
            self.player.video_set_logo_string(vlc.VideoLogoOption.file, path_bytes)
            
            # 3. Define a posição: BottomLeft (Inferior Esquerdo = 6)
            self.player.video_set_logo_int(vlc.VideoLogoOption.position, 6)

            # 4. Define a transparência (0-255). 180 = Meio transparente
            self.player.video_set_logo_int(vlc.VideoLogoOption.opacity, 180)
            
            # 5. Margem (Padding) das bordas
            self.player.video_set_logo_int(vlc.VideoLogoOption.x, 30)
            self.player.video_set_logo_int(vlc.VideoLogoOption.y, 30)
            
            print("Marca d'água configurada com sucesso.")
        except Exception as e:
            print(f"Erro ao configurar marca d'água: {e}")

    # --- MÉTODOS DE ÁUDIO (MANUAL - SEM AUTOMAÇÃO DE VOLUME) ---
    def tocar_audio_background(self, arquivo_audio):
        """ Toca áudio sem parar vídeo, e SEM baixar volume do vídeo """
        if not os.path.exists(arquivo_audio): return
        
        # 1. Pausa som externo (Spotify) via Media Keys
        try: pyautogui.press("playpause")
        except: pass
        time.sleep(0.5)

        # 2. Toca Anúncio
        self.modo_tts = True
        self.mem_time = 0 
        
        self.tts_player.set_media(self.vlc_audio.media_new(arquivo_audio))
        self.tts_player.audio_set_volume(100)
        self.tts_player.play()
        
        self.controls.place_forget()
        self.configure(cursor="none")

    def tocar_anuncio(self, arquivo_audio, volume_alvo=100):
        """ Toca anúncio pausando vídeo (Modo Locutor) """
        if not os.path.exists(arquivo_audio): return
        
        try: pyautogui.press("playpause")
        except: pass
        time.sleep(0.5) 

        if self.is_playing:
            self.player.pause()
            self.mem_time = self.player.get_time()
        
        self.modo_tts = True
        self.btn_play.configure(text="⏸")
        
        self.tts_player.set_media(self.vlc_audio.media_new(arquivo_audio))
        self.tts_player.audio_set_volume(100) 
        self.tts_player.play()
        
        self.controls.place_forget()
        self.configure(cursor="none")

    def parar_tts(self):
        if self.tts_player.is_playing(): self.tts_player.stop()
        self._restaurar_estado_pos_tts()

    def _restaurar_estado_pos_tts(self):
        # Restaura estado interno do Player
        self.modo_tts = False
        self.configure(cursor="arrow")
        
        # 1. Solta Play Externo (Spotify)
        try: pyautogui.press("playpause") 
        except: pass

        # 2. Retoma Vídeo (apenas Play, sem mexer no volume)
        if self.mem_time > 0:
            self.play_video(self.video_atual, resume=True)
            self.after(500, lambda: self.player.set_time(self.mem_time))

    # --- CONSULTA DE STATUS (USADO PELO DASHBOARD) ---
    def get_tts_status(self):
        if not self.modo_tts:
            return False, 0, 0
        try:
            length = self.tts_player.get_length()
            time_ms = self.tts_player.get_time()
            if length <= 0: return True, 0, 100 
            return True, time_ms, length
        except:
            return False, 0, 0

    # --- NAVEGAÇÃO E GERENCIAMENTO DE PLAYLIST ---
    def change_playlist(self, name):
        if name in self.playlist_folders:
            self.current_playlist_name = name
            self.current_playlist = self.playlist_folders[name]
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
            if pl_names:
                self.opt_playlist.configure(values=pl_names)
                self.opt_playlist.set(self.current_playlist_name)
            if self.playlist_folders["TODOS"]:
                self.lbl_info.place_forget()
                self.current_playlist = self.playlist_folders["TODOS"]
                self.play_video(0, start_paused=True)
            else: self.lbl_info.configure(text="Nenhum vídeo encontrado!")
        except: pass

    # --- CONTROLE DE VÍDEO E TRANSIÇÃO LIMPA ---
    def play_video(self, target, ad=False, resume=False, start_paused=False, keep_repeat=False):
        path = ""
        if ad: path = target 
        else:
            if not self.current_playlist: return
            if isinstance(target, int): 
                if target >= len(self.current_playlist): target = 0
                self.idx_video = target
                path = self.current_playlist[target]
            else: path = target
            self.video_atual = path 
            if not keep_repeat: self.repeat_one_done = False

        self.player.set_hwnd(self.canvas.winfo_id())
        self.player.set_media(self.vlc_video.media_new(path))
        self.player.play()
        if start_paused:
            self.after(100, lambda: self.player.pause())
            self.is_playing = False
            self.btn_play.configure(text="▶")
        else:
            self.is_playing = True
            self.btn_play.configure(text="⏸")
        
        if ad: 
            self.modo_ad = True
            self.controls.place_forget()
            self.btn_settings.place_forget()
            self.opt_playlist.place_forget()
            self.configure(cursor="none")
            self.last_ad_timestamp = time.time()
        else: 
            self.modo_ad = False
            self.modo_tts = False 
            
            # --- FIX DA BARRA PRESA (TRANSICAO LIMPA) ---
            # Se for troca automática (sem resume), esconde a barra
            if not resume:
                if self.controls_on:
                    # Se estava visível (usuario mexendo), garante que some em 3s
                    if self.hide_task: self.after_cancel(self.hide_task)
                    self.hide_task = self.after(3000, self.hide_controls)
                else:
                    # Transição limpa: esconde cursor e barra
                    self.configure(cursor="none")
                    self.controls.place_forget()
            else:
                # Resume (pós-anuncio): esconde tudo
                self.configure(cursor="none")
                self.controls.place_forget()

    def skip_time(self, seconds):
        if not self.is_playing: return
        curr = self.player.get_time()
        length = self.player.get_length()
        new_time = curr + (seconds * 1000)
        if new_time < 0: new_time = 0
        if new_time > length: new_time = length - 1000
        self.player.set_time(int(new_time))
        self.slider.set(self.player.get_position() * 1000)

    def toggle_repeat(self):
        self.repeat_state = (self.repeat_state + 1) % 3
        self.update_repeat_icon()

    def update_repeat_icon(self):
        if self.repeat_state == 0:
            self.btn_rep.configure(text="🔁", text_color="#777") 
            ToolTip(self.btn_rep, "Repetição: DESATIVADA")
        elif self.repeat_state == 1:
            self.btn_rep.configure(text="🔁", text_color=VERITAS_BLUE)
            ToolTip(self.btn_rep, "Repetir Vídeo: INFINITO")
        elif self.repeat_state == 2:
            self.btn_rep.configure(text="🔂", text_color=VERITAS_BLUE) 
            ToolTip(self.btn_rep, "Repetir Vídeo: 1 VEZ")

    def toggle_shuffle(self): 
        self.shuffle = not self.shuffle
        if self.shuffle:
            self.btn_shuf.configure(text_color=VERITAS_BLUE)
            ToolTip(self.btn_shuf, "Aleatório: LIGADO")
        else:
            self.btn_shuf.configure(text_color="#777")
            ToolTip(self.btn_shuf, "Aleatório: DESLIGADO")

    def next(self):
        if not self.current_playlist: return
        if self.shuffle: nxt = random.randint(0, len(self.current_playlist)-1)
        else: nxt = (self.idx_video + 1) % len(self.current_playlist)
        self.play_video(nxt)

    def prev(self):
        if not self.current_playlist: return
        self.play_video((self.idx_video - 1) % len(self.current_playlist))

    def play_pause(self):
        if self.is_playing:
            self.player.pause()
            self.is_playing=False
            self.btn_play.configure(text="▶")
        else:
            self.player.play()
            self.is_playing=True
            self.btn_play.configure(text="⏸")

    def seek(self, v): self.player.set_position(float(v)/1000)
    def set_vol(self, v): self.player.audio_set_volume(int(v))

    def toggle_mute(self):
        if self.muted:
            self.muted=False
            self.player.audio_set_mute(False)
            self.sl_vol.set(self.last_vol)
            self.btn_mute.configure(text="🔊")
        else:
            self.last_vol=self.sl_vol.get()
            self.muted=True
            self.player.audio_set_mute(True)
            self.sl_vol.set(0)
            self.btn_mute.configure(text="🔇")
    
    # --- LOOP DE SISTEMA (CORE) ---
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
        
        # Verificação de Anúncios Agendados
        if not self.modo_ad and not self.modo_tts and (agora_ts - self.last_ad_timestamp) > 60:
            if os.path.exists(DB_FILE):
                now = datetime.now()
                hora = now.strftime("%H:%M")
                wd = ["seg","ter","qua","qui","sex","sab","dom"][now.weekday()]
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
                                    c["execucoes_hoje"].append(hora)
                                    sv = True
                                    
                                    tipo = c.get("tipo", "VIDEO")
                                    if tipo == "AUDIO":
                                        self.tocar_audio_background(c["video"])
                                    else:
                                        self.mem_time = self.player.get_time()
                                        self.play_video(c["video"], ad=True)
                                    break
                    if sv: 
                        with open(DB_FILE,'w') as f: json.dump(cons,f,indent=4)
                except: pass

        # Verificação de Fim de Mídia
        if self.modo_tts:
            st = self.tts_player.get_state()
            if st == vlc.State.Ended or st == vlc.State.Error:
                self._restaurar_estado_pos_tts() 
        
        elif self.is_playing:
            st = self.player.get_state()
            if st == vlc.State.Ended or st == vlc.State.Error:
                if self.modo_ad:
                    self.modo_ad = False
                    self.play_video(self.video_atual, resume=True)
                    self.after(500, lambda: self.player.set_time(self.mem_time))
                else:
                    if self.repeat_state == 1: self.play_video(self.idx_video, keep_repeat=True)
                    elif self.repeat_state == 2: 
                        if not self.repeat_one_done:
                            self.play_video(self.idx_video, keep_repeat=True)
                            self.repeat_one_done = True
                        else:
                            self.repeat_state = 0
                            self.update_repeat_icon()
                            self.next()
                    else: self.next()
        
        self.after(1000, self.sys_loop)

    def ui_loop(self):
        if self.is_playing and not self.modo_tts:
            try:
                c = self.player.get_time()
                t = self.player.get_length()
                if t > 0:
                    self.slider.set(self.player.get_position()*1000)
                    self.lbl_time.configure(text=f"{time.strftime('%M:%S', time.gmtime(c//1000))} / {time.strftime('%M:%S', time.gmtime(t//1000))}")
            except: pass
        self.after(500, self.ui_loop)

    def check_mouse_polling(self):
        if not self.modo_ad and not self.modo_tts:
            try:
                x, y = self.winfo_pointerxy()
                if abs(x-self.last_mouse[0])>10 or abs(y-self.last_mouse[1])>10:
                    self.last_mouse=(x,y)
                    self.on_mouse_move(None)
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
            self.controls.lift()
            self.controls_on=True
            if not self.is_fullscreen:
                self.btn_settings.place(relx=0.98, rely=0.03, anchor="ne")
                self.opt_playlist.place(relx=0.88, rely=0.03, anchor="ne")

    def hide_controls(self):
        if self.is_playing and not self.modo_ad and not self.modo_tts:
            self.controls.place_forget()
            self.configure(cursor="none")
            self.controls_on = False
            if self.is_fullscreen:
                self.btn_settings.place_forget()
                self.opt_playlist.place_forget()

    def toggle_fs(self, e=None):
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self.btn_settings.place_forget()
            self.opt_playlist.place_forget()
            self.attributes("-fullscreen", True)
        else:
            self.attributes("-fullscreen", False)
            self.state("zoomed")
            self.btn_settings.place(relx=0.98, rely=0.03, anchor="ne")
            self.opt_playlist.place(relx=0.88, rely=0.03, anchor="ne")
        self.show_controls()

if __name__ == "__main__":
    app = VisioDeckPlayer()
    app.mainloop()