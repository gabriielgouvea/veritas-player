# player.py (Versão 19.1 - Stop Ready)
import customtkinter as ctk
import tkinter as tk
import vlc
import os
import time
import json
import random
import pyautogui
import sys 
from datetime import datetime
from config import *
from utils import ToolTip, carregar_db, salvar_db
from dashboard import DashboardWindow

# Fix para carregar DLLs do VLC localmente ou congelado
if os.name == 'nt':
    try:
        # Se estiver congelado (EXE), as DLLs estão em sys._MEIPASS ou na pasta local
        if hasattr(sys, '_MEIPASS'):
            os.add_dll_directory(sys._MEIPASS)
        else:
            os.add_dll_directory(os.getcwd())
    except:
        pass

class VisioDeckPlayer(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configuração da Janela Principal
        self.title("Veritas Player")
        self.configure(fg_color=VERITAS_PLAYER_BG)
        self.geometry("1200x800")
        
        # Maximiza após 100ms para evitar bugs visuais no Tkinter
        self.after(100, lambda: self.state("zoomed"))
        self.is_fullscreen = False
        
        # --- CONFIGURAÇÃO DOS PLAYERS (DUAL INSTANCE) ---
        
        # PLAYER 1: VÍDEO DE TREINO
        # Usa aceleração de hardware (avcodec-hw=none para segurança)
        self.vlc_video = vlc.Instance(
            "--no-xlib", 
            "--input-repeat=0", 
            "--disable-screensaver", 
            "--avcodec-hw=none"
        )
        self.player = self.vlc_video.media_player_new()
        
        # PLAYER 2: LOCUTOR / TTS
        # Força saída via DirectSound para evitar conflito com WASAPI
        self.vlc_audio = vlc.Instance("--aout=directsound") 
        self.tts_player = self.vlc_audio.media_player_new()
        
        # --- VARIÁVEIS DE ESTADO ---
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
        
        # Flags de Interrupção
        self.modo_ad = False       # True quando está passando vídeo comercial
        self.modo_tts = False      # True quando o locutor está falando
        
        # Memória de Reprodução
        self.mem_time = 0          # Guarda o tempo exato onde o vídeo parou
        self.video_atual = ""      # Guarda o caminho do vídeo atual
        self.saved_volume = 100    # Guarda o volume do vídeo antes do anúncio
        
        # Controle de Loops e Logs
        self.hist_minuto = [] 
        self.data_cache = datetime.now().strftime("%d/%m/%Y")
        
        # Controles do Usuário
        self.shuffle = False
        self.repeat_state = 0      # 0=Off, 1=Infinito (Loop Playlist), 2=Uma Vez (Loop 1x Video)
        self.repeat_one_done = False 
        
        self.muted = False
        self.last_vol = 100
        
        # Controle de Interface (Mouse e Ocultação)
        self.last_mouse = (0,0)
        self.controls_on = False
        self.hide_task = None
        self.last_ad_timestamp = 0

        # --- CONFIGURAÇÃO DO LAYOUT (GRID) ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Frame de Vídeo (Fundo)
        self.video_frame = tk.Frame(self, bg="black")
        self.video_frame.grid(row=0, column=0, sticky="nsew")
        
        # Canvas VLC (Onde o vídeo é desenhado)
        self.canvas = tk.Canvas(self.video_frame, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # --- BARRA DE CONTROLES FLUTUANTE ---
        self.controls = ctk.CTkFrame(
            self, 
            fg_color="#111", 
            height=150, 
            corner_radius=15, 
            border_width=1, 
            border_color="#333"
        )
        
        # 1. Slider de Progresso (Topo)
        self.slider = ctk.CTkSlider(
            self.controls, 
            from_=0, 
            to=1000, 
            command=self.seek, 
            progress_color=VERITAS_BLUE, 
            button_color=VERITAS_BLUE, 
            button_hover_color=VERITAS_BLUE_HOVER, 
            fg_color="#333", 
            height=16
        )
        self.slider.pack(fill="x", padx=30, pady=(15, 5))
        ToolTip(self.slider, "Progresso do Vídeo")
        
        # Container dos Botões
        bot_area = ctk.CTkFrame(self.controls, fg_color="transparent")
        bot_area.pack(fill="both", expand=True, padx=30, pady=(5, 15))
        
        # --- GRUPO ESQUERDA: Shuffle e Tempo ---
        left_c = ctk.CTkFrame(bot_area, fg_color="transparent")
        left_c.pack(side="left")
        
        self.btn_shuf = ctk.CTkButton(
            left_c, 
            text="🔀", 
            width=40, 
            height=40, 
            fg_color="transparent", 
            font=("Arial", 20), 
            command=self.toggle_shuffle, 
            hover_color="#333", 
            text_color="#777"
        )
        self.btn_shuf.pack(side="left", padx=(0,10))
        ToolTip(self.btn_shuf, "Vídeo Aleatório")
        
        self.lbl_time = ctk.CTkLabel(
            left_c, 
            text="00:00 / 00:00", 
            font=("Segoe UI", 12), 
            text_color="#AAA"
        )
        self.lbl_time.pack(side="left")

        # --- GRUPO CENTRO: Playback ---
        center_c = ctk.CTkFrame(bot_area, fg_color="transparent")
        center_c.place(relx=0.5, rely=0.5, anchor="center")
        
        # Estilo padrão dos botões médios
        btn_std = {
            "fg_color": "transparent", 
            "text_color": "#EEE", 
            "hover_color": "#333", 
            "width": 50, 
            "height": 50, 
            "font": ("Arial", 24)
        }
        
        # Botão Anterior
        self.btn_prev = ctk.CTkButton(center_c, text="⏮", command=self.prev, **btn_std)
        self.btn_prev.pack(side="left", padx=5)
        ToolTip(self.btn_prev, "Vídeo Anterior")
        
        # Botão Voltar 10s
        self.btn_rewind = ctk.CTkButton(
            center_c, 
            text="↺ 10", 
            command=lambda: self.skip_time(-10), 
            fg_color="transparent", 
            text_color="#DDD", 
            hover_color="#333", 
            width=50, 
            height=50, 
            font=("Segoe UI", 12, "bold")
        )
        self.btn_rewind.pack(side="left", padx=5)
        ToolTip(self.btn_rewind, "Voltar 10 Segundos")

        # Botão PLAY/PAUSE (Destaque)
        self.btn_play = ctk.CTkButton(
            center_c, 
            text="⏯", 
            command=self.play_pause, 
            width=70, 
            height=70, 
            corner_radius=35, 
            fg_color=VERITAS_BLUE, 
            hover_color=VERITAS_BLUE_HOVER, 
            font=("Arial", 30)
        )
        self.btn_play.pack(side="left", padx=15)
        ToolTip(self.btn_play, "Play / Pause")

        # Botão Avançar 10s
        self.btn_fwd = ctk.CTkButton(
            center_c, 
            text="↻ 10", 
            command=lambda: self.skip_time(10), 
            fg_color="transparent", 
            text_color="#DDD", 
            hover_color="#333", 
            width=50, 
            height=50, 
            font=("Segoe UI", 12, "bold")
        )
        self.btn_fwd.pack(side="left", padx=5)
        ToolTip(self.btn_fwd, "Adiantar 10 Segundos")

        # Botão Próximo
        self.btn_next = ctk.CTkButton(center_c, text="⏭", command=self.next, **btn_std)
        self.btn_next.pack(side="left", padx=5)
        ToolTip(self.btn_next, "Próximo Vídeo")
        
        # Botão Repeat (3 Estados)
        self.btn_rep = ctk.CTkButton(center_c, text="🔁", command=self.toggle_repeat, **btn_std)
        self.btn_rep.pack(side="left", padx=(15, 0))
        self.update_repeat_icon() # Configura ícone e tooltip iniciais

        # --- GRUPO DIREITA: Som e Janela ---
        right_c = ctk.CTkFrame(bot_area, fg_color="transparent")
        right_c.pack(side="right")

        self.btn_mute = ctk.CTkButton(
            right_c, 
            text="🔊", 
            width=40, 
            command=self.toggle_mute, 
            fg_color="transparent", 
            hover_color="#333", 
            font=("Arial", 20)
        )
        self.btn_mute.pack(side="left")
        ToolTip(self.btn_mute, "Mudo / Som")
        
        self.sl_vol = ctk.CTkSlider(
            right_c, 
            from_=0, 
            to=100, 
            width=100, 
            command=self.set_vol, 
            progress_color="white", 
            button_color="white", 
            button_hover_color="#DDD"
        )
        self.sl_vol.set(100)
        self.sl_vol.pack(side="left", padx=10)
        ToolTip(self.sl_vol, "Volume")
        
        self.btn_fs = ctk.CTkButton(
            right_c, 
            text="⛶", 
            width=40, 
            command=self.toggle_fs, 
            fg_color="transparent", 
            hover_color="#333", 
            font=("Arial", 20)
        )
        self.btn_fs.pack(side="left")
        ToolTip(self.btn_fs, "Tela Cheia / Janela")

        # --- INFO CENTRAL (Overlay) ---
        self.lbl_info = ctk.CTkLabel(
            self.canvas, 
            text="Clique em AJUSTES para selecionar a pasta...", 
            font=("Arial", 30), 
            text_color="#555", 
            bg_color="black"
        )
        self.lbl_info.place(relx=0.5, rely=0.5, anchor="center")

        # --- BOTÕES SUPERIORES (Config e Playlist) ---
        
        # Botão Ajustes
        self.btn_settings = ctk.CTkButton(
            self, 
            text="⚙️  AJUSTES", 
            command=self.open_dash, 
            width=130, 
            height=40, 
            fg_color="white", 
            text_color="black", 
            hover_color="#DDD", 
            font=("Segoe UI", 12, "bold"), 
            corner_radius=20, 
            bg_color="black"
        )
        self.btn_settings.place(relx=0.98, rely=0.03, anchor="ne")
        ToolTip(self.btn_settings, "Configurações e Uploads")

        # Menu de Playlist
        self.opt_playlist = ctk.CTkOptionMenu(
            self, 
            values=["TODOS"], 
            command=self.change_playlist, 
            width=200, 
            height=40, 
            fg_color="#333", 
            button_color="#444", 
            text_color="white", 
            button_hover_color="#555", 
            font=("Segoe UI", 12, "bold"), 
            dropdown_fg_color="#222", 
            dropdown_text_color="white", 
            bg_color="black"
        )
        self.opt_playlist.place(relx=0.88, rely=0.03, anchor="ne")
        self.opt_playlist.set("TODOS")
        ToolTip(self.opt_playlist, "Selecionar Playlist")

        # --- BINDINGS ---
        # Eventos de mouse e teclado
        self.bind_all("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.bind_all("<Escape>", self.toggle_fs)

        # --- INICIALIZAÇÃO DO SISTEMA ---
        self.check_mouse_polling()
        self.sys_loop()
        self.ui_loop()
        
        # Carrega playlist se houver pasta salva
        if self.pasta_treino: 
            self.scan_folders()
            
        self.show_controls()

    # Abre o Dashboard
    def open_dash(self):
        DashboardWindow(self, self)
    
    # --- FUNÇÃO CRÍTICA: LOCUTOR / TTS ---
    # Gerencia a pausa externa, pausa interna e volume boost
    def tocar_anuncio(self, arquivo_audio, volume_alvo=100):
        if not os.path.exists(arquivo_audio): return

        # 1. Controle Externo (DJ Mode)
        # Tenta pausar o Spotify/Chrome apertando a tecla Media Play/Pause
        try: 
            pyautogui.press("playpause")
        except: 
            print("Erro ao controlar mídia externa")
            
        # Delay para o som baixar
        time.sleep(0.5) 

        # 2. Controle Interno (Vídeo)
        # Pausa o vídeo e salva a posição
        if self.is_playing:
            self.player.pause()
            self.mem_time = self.player.get_time()
        
        # 3. Gestão de Volume Inteligente
        # Salva o volume atual do vídeo para restaurar depois
        try:
            self.saved_volume = self.player.audio_get_volume()
            if self.saved_volume == -1: self.saved_volume = 100
        except: 
            self.saved_volume = 100

        # 4. Configura Estado do Locutor
        self.modo_tts = True
        self.btn_play.configure(text="⏸") # Mostra ícone de pause
        
        # 5. Toca o Anúncio no Player Dedicado
        self.tts_player.set_media(self.vlc_audio.media_new(arquivo_audio))
        self.tts_player.audio_set_volume(int(volume_alvo)) # Aplica o boost
        self.tts_player.play()
        
        # 6. Oculta Interface (Modo Broadcast)
        self.controls.place_forget()
        self.configure(cursor="none")

    # NOVA FUNÇÃO: STOP TOTAL
    def parar_tts(self):
        # Para o player de voz imediatamente
        if self.tts_player.is_playing():
            self.tts_player.stop()
        
        self.modo_tts = False
        self.configure(cursor="arrow")
        
        # Tenta soltar o Play/Pause da música externa imediatamente
        try: 
            pyautogui.press("playpause") 
        except: pass

        # Se tiver um vídeo pausado, retoma ele
        if self.mem_time > 0:
            self.play_video(self.video_atual, resume=True)
            self.after(500, lambda: self.player.set_time(self.mem_time))

    # Troca de Playlist
    def change_playlist(self, name):
        if name in self.playlist_folders:
            self.current_playlist_name = name
            self.current_playlist = self.playlist_folders[name]
            
            self.opt_playlist.set(name)
            
            if self.current_playlist:
                self.play_video(0, start_paused=False)
            else:
                self.player.stop()

    # Escaneia Pastas
    def scan_folders(self):
        self.playlist_folders = {"TODOS": []}
        try:
            for root, dirs, files in os.walk(self.pasta_treino):
                folder = os.path.basename(root)
                if folder == os.path.basename(self.pasta_treino):
                    folder = "Geral"
                
                if folder not in self.playlist_folders:
                    self.playlist_folders[folder] = []
                
                for f in files:
                    if f.lower().endswith(('.mp4','.mkv','.avi')):
                        path = os.path.join(root, f)
                        self.playlist_folders["TODOS"].append(path)
                        self.playlist_folders[folder].append(path)
            
            # Remove vazias
            empty = [k for k,v in self.playlist_folders.items() if not v]
            for k in empty: del self.playlist_folders[k]
            
            # Atualiza menu
            pl_names = sorted(list(self.playlist_folders.keys()))
            if "TODOS" in pl_names: 
                pl_names.remove("TODOS")
                pl_names.insert(0, "TODOS")
            
            if pl_names:
                self.opt_playlist.configure(values=pl_names)
                self.opt_playlist.set(self.current_playlist_name)

            if self.playlist_folders["TODOS"]:
                self.lbl_info.place_forget()
                self.current_playlist = self.playlist_folders["TODOS"]
                self.play_video(0, start_paused=True)
            else:
                self.lbl_info.configure(text="Nenhum vídeo encontrado!")
        except: pass

    # --- LÓGICA DE REPRODUÇÃO DE VÍDEO ---
    def play_video(self, target, ad=False, resume=False, start_paused=False, keep_repeat=False):
        path = ""
        if ad:
            path = target 
        else:
            if not self.current_playlist: return
            
            if isinstance(target, int): 
                if target >= len(self.current_playlist): target = 0
                self.idx_video = target
                path = self.current_playlist[target]
            else:
                path = target
            
            self.video_atual = path 
            
            # Reset flag de repetição única se for troca manual/automática
            if not keep_repeat:
                self.repeat_one_done = False

        # Vincula ao Canvas (Visual)
        self.player.set_hwnd(self.canvas.winfo_id())
        self.player.set_media(self.vlc_video.media_new(path))
        
        # Restaura volume original se estiver voltando de um anúncio
        if resume:
            self.player.audio_set_volume(self.saved_volume)
        
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
            
            if resume:
                self.configure(cursor="none")
                self.controls.place_forget()
            else:
                self.show_controls()

    # --- CONTROLES DE TEMPO ---
    def skip_time(self, seconds):
        if not self.is_playing: return
        curr = self.player.get_time()
        length = self.player.get_length()
        new_time = curr + (seconds * 1000)
        
        if new_time < 0: new_time = 0
        if new_time > length: new_time = length - 1000
        
        self.player.set_time(int(new_time))
        self.slider.set(self.player.get_position() * 1000)

    # --- CONTROLES DE REPETIÇÃO ---
    def toggle_repeat(self):
        # Ciclo: 0 (Off) -> 1 (Infinito) -> 2 (Uma Vez) -> 0
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

    # --- CONTROLE ALEATÓRIO ---
    def toggle_shuffle(self): 
        self.shuffle = not self.shuffle
        if self.shuffle:
            self.btn_shuf.configure(text_color=VERITAS_BLUE)
            ToolTip(self.btn_shuf, "Aleatório: LIGADO")
        else:
            self.btn_shuf.configure(text_color="#777")
            ToolTip(self.btn_shuf, "Aleatório: DESLIGADO")

    # --- NAVEGAÇÃO ---
    def next(self):
        if not self.current_playlist: return
        if self.shuffle:
            nxt = random.randint(0, len(self.current_playlist)-1)
        else:
            nxt = (self.idx_video + 1) % len(self.current_playlist)
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

    def seek(self, v):
        self.player.set_position(float(v)/1000)

    def set_vol(self, v):
        self.player.audio_set_volume(int(v))

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
        
        # Reset Diário
        if hoje != self.data_cache:
            self.data_cache = hoje
            try:
                with open(DB_FILE,'r') as f: d = json.load(f)
                for c in d: c["execucoes_hoje"] = []
                with open(DB_FILE,'w') as f: json.dump(d,f,indent=4)
            except: pass
        
        agora_ts = time.time()
        
        # --- VERIFICAÇÃO DE ANÚNCIOS DE VÍDEO ---
        # Só verifica se não estiver rodando comercial ou locutor
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
                        
                        # Validação de Data
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
                        
                        # Validação de Hora e Execução
                        if hora in c["horarios"]:
                            if self.is_playing:
                                if hora not in c.get("execucoes_hoje", []):
                                    if "execucoes_hoje" not in c: c["execucoes_hoje"] = []
                                    c["execucoes_hoje"].append(hora)
                                    sv = True
                                    
                                    self.mem_time = self.player.get_time()
                                    self.play_video(c["video"], ad=True)
                                    break
                    if sv: 
                        with open(DB_FILE,'w') as f: json.dump(cons,f,indent=4)
                except: pass

        # --- VERIFICAÇÃO DE FIM DE MÍDIA ---
        
        # CASO 1: FIM DO LOCUTOR (TTS)
        if self.modo_tts:
            st = self.tts_player.get_state()
            if st == vlc.State.Ended or st == vlc.State.Error:
                self.modo_tts = False
                
                # SOLTA O PAUSE DA ACADEMIA (Retorna música externa)
                try: 
                    pyautogui.press("playpause") 
                except: pass
                
                # Volta o vídeo
                self.play_video(self.video_atual, resume=True)
                self.after(500, lambda: self.player.set_time(self.mem_time))
        
        # CASO 2: FIM DO VÍDEO (TREINO OU AD)
        elif self.is_playing:
            st = self.player.get_state()
            if st == vlc.State.Ended or st == vlc.State.Error:
                
                # Se acabou um anúncio de vídeo
                if self.modo_ad:
                    self.modo_ad = False
                    self.play_video(self.video_atual, resume=True)
                    self.after(500, lambda: self.player.set_time(self.mem_time))
                
                # Se acabou um vídeo de treino
                else:
                    if self.repeat_state == 1: 
                        # Loop Infinito
                        self.play_video(self.idx_video, keep_repeat=True)
                    
                    elif self.repeat_state == 2: 
                        # Loop 1x
                        if not self.repeat_one_done:
                            self.play_video(self.idx_video, keep_repeat=True)
                            self.repeat_one_done = True
                        else:
                            # Reset e Próximo
                            self.repeat_state = 0
                            self.update_repeat_icon()
                            self.next()
                    else:
                        # Normal
                        self.next()
                        
        self.after(1000, self.sys_loop)

    # --- LOOP DE UI ---
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

    # --- GESTÃO DE MOUSE ---
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