# player.py (Versão 12.6 - Fix Mouse Hover & Tooltips)
import customtkinter as ctk
import tkinter as tk
import vlc
import os
import time
import json
import random
from datetime import datetime
from config import *
from utils import ToolTip, carregar_db, salvar_db
from dashboard import DashboardWindow

class VisioDeckPlayer(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Veritas Player")
        self.configure(fg_color=VERITAS_PLAYER_BG)
        
        # Janela
        self.geometry("1200x800")
        self.after(100, lambda: self.state("zoomed"))
        self.is_fullscreen = False
        
        # VLC
        self.vlc = vlc.Instance("--no-xlib", "--input-repeat=0", "--disable-screensaver", "--avcodec-hw=none")
        self.player = self.vlc.media_player_new()
        
        # Estado
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
        self.modo_ad = False
        self.mem_time = 0
        self.video_atual = "" 
        self.hist_minuto = [] 
        self.data_cache = datetime.now().strftime("%d/%m/%Y")
        
        # Estados de Controle
        self.shuffle = False
        self.repeat_state = 0 # 0=Off, 1=Infinito, 2=1x
        self.repeat_one_done = False 
        
        self.muted = False
        self.last_vol = 100
        self.last_mouse = (0,0)
        self.controls_on = False
        self.hide_task = None
        self.last_ad_timestamp = 0

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # VIDEO
        self.video_frame = tk.Frame(self, bg="black")
        self.video_frame.grid(row=0, column=0, sticky="nsew")
        self.canvas = tk.Canvas(self.video_frame, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # --- BARRA DE CONTROLE ---
        # Aumentei levemente a altura para garantir espaço
        self.controls = ctk.CTkFrame(self, fg_color="#111", height=150, corner_radius=15, border_width=1, border_color="#333")
        
        # Slider
        self.slider = ctk.CTkSlider(self.controls, from_=0, to=1000, command=self.seek, progress_color=VERITAS_BLUE, button_color=VERITAS_BLUE, button_hover_color=VERITAS_BLUE_HOVER, fg_color="#333", height=16)
        self.slider.pack(fill="x", padx=30, pady=(15, 5))
        ToolTip(self.slider, "Progresso do Vídeo")
        
        # Container Botoes
        # FIX AQUI: 'expand=True, fill="both"' garante que a área do mouse cubra os botões grandes
        bot_area = ctk.CTkFrame(self.controls, fg_color="transparent")
        bot_area.pack(fill="both", expand=True, padx=30, pady=(5, 15))
        
        # ESQUERDA
        left_c = ctk.CTkFrame(bot_area, fg_color="transparent")
        left_c.pack(side="left")
        
        self.btn_shuf = ctk.CTkButton(left_c, text="🔀", width=40, height=40, fg_color="transparent", font=("Arial", 20), command=self.toggle_shuffle, hover_color="#333", text_color="#777")
        self.btn_shuf.pack(side="left", padx=(0,10))
        ToolTip(self.btn_shuf, "Vídeo Aleatório") 
        
        self.lbl_time = ctk.CTkLabel(left_c, text="00:00 / 00:00", font=("Segoe UI", 12), text_color="#AAA")
        self.lbl_time.pack(side="left")

        # CENTRO
        center_c = ctk.CTkFrame(bot_area, fg_color="transparent")
        center_c.place(relx=0.5, rely=0.5, anchor="center")
        
        btn_std = {"fg_color": "transparent", "text_color": "#EEE", "hover_color": "#333", "width": 50, "height": 50, "font": ("Arial", 24)}
        
        self.btn_prev = ctk.CTkButton(center_c, text="⏮", command=self.prev, **btn_std)
        self.btn_prev.pack(side="left", padx=5)
        ToolTip(self.btn_prev, "Vídeo Anterior") 
        
        self.btn_rewind = ctk.CTkButton(center_c, text="↺ 10", command=lambda: self.skip_time(-10), fg_color="transparent", text_color="#DDD", hover_color="#333", width=50, height=50, font=("Segoe UI", 12, "bold"))
        self.btn_rewind.pack(side="left", padx=5)
        ToolTip(self.btn_rewind, "Voltar 10s") 

        self.btn_play = ctk.CTkButton(center_c, text="⏯", command=self.play_pause, width=70, height=70, corner_radius=35, fg_color=VERITAS_BLUE, hover_color=VERITAS_BLUE_HOVER, font=("Arial", 30))
        self.btn_play.pack(side="left", padx=15)
        ToolTip(self.btn_play, "Play / Pause") 

        self.btn_fwd = ctk.CTkButton(center_c, text="↻ 10", command=lambda: self.skip_time(10), fg_color="transparent", text_color="#DDD", hover_color="#333", width=50, height=50, font=("Segoe UI", 12, "bold"))
        self.btn_fwd.pack(side="left", padx=5)
        ToolTip(self.btn_fwd, "Adiantar 10s") 

        self.btn_next = ctk.CTkButton(center_c, text="⏭", command=self.next, **btn_std)
        self.btn_next.pack(side="left", padx=5)
        ToolTip(self.btn_next, "Próximo Vídeo") 
        
        self.btn_rep = ctk.CTkButton(center_c, text="🔁", command=self.toggle_repeat, **btn_std)
        self.btn_rep.pack(side="left", padx=(15, 0))
        self.update_repeat_icon() 

        # DIREITA
        right_c = ctk.CTkFrame(bot_area, fg_color="transparent")
        right_c.pack(side="right")

        self.btn_mute = ctk.CTkButton(right_c, text="🔊", width=40, command=self.toggle_mute, fg_color="transparent", hover_color="#333", font=("Arial", 20))
        self.btn_mute.pack(side="left")
        ToolTip(self.btn_mute, "Mudo") 
        
        self.sl_vol = ctk.CTkSlider(right_c, from_=0, to=100, width=100, command=self.set_vol, progress_color="white", button_color="white", button_hover_color="#DDD")
        self.sl_vol.set(100)
        self.sl_vol.pack(side="left", padx=10)
        ToolTip(self.sl_vol, "Volume") 
        
        self.btn_fs = ctk.CTkButton(right_c, text="⛶", width=40, command=self.toggle_fs, fg_color="transparent", hover_color="#333", font=("Arial", 20))
        self.btn_fs.pack(side="left")
        ToolTip(self.btn_fs, "Tela Cheia") 

        # AVISO CENTRAL
        self.lbl_info = ctk.CTkLabel(self.canvas, text="Clique em AJUSTES para selecionar a pasta...", font=("Arial", 30), text_color="#555", bg_color="black")
        self.lbl_info.place(relx=0.5, rely=0.5, anchor="center")

        # SUPERIORES
        self.btn_settings = ctk.CTkButton(self, text="⚙️  AJUSTES", command=self.open_dash, width=130, height=40, fg_color="white", text_color="black", hover_color="#DDD", font=("Segoe UI", 12, "bold"), corner_radius=20, bg_color="black")
        self.btn_settings.place(relx=0.98, rely=0.03, anchor="ne")
        ToolTip(self.btn_settings, "Configurações")

        self.opt_playlist = ctk.CTkOptionMenu(self, values=["TODOS"], command=self.change_playlist, width=200, height=40, fg_color="#333", button_color="#444", text_color="white", button_hover_color="#555", font=("Segoe UI", 12, "bold"), dropdown_fg_color="#222", dropdown_text_color="white", bg_color="black")
        self.opt_playlist.place(relx=0.88, rely=0.03, anchor="ne")
        self.opt_playlist.set("TODOS")
        ToolTip(self.opt_playlist, "Selecionar Playlist")

        self.bind_all("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.bind_all("<Escape>", self.toggle_fs)

        self.check_mouse_polling()
        self.sys_loop()
        self.ui_loop()
        
        if self.pasta_treino: self.scan_folders()
        self.show_controls()

    def open_dash(self): DashboardWindow(self, self)
    
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
            
            if not keep_repeat:
                self.repeat_one_done = False

        self.player.set_hwnd(self.canvas.winfo_id())
        self.player.set_media(self.vlc.media_new(path))
        self.player.play()
        
        if start_paused:
            self.after(100, lambda: self.player.pause())
            self.is_playing = False; self.btn_play.configure(text="▶")
        else:
            self.is_playing = True; self.btn_play.configure(text="⏸")
        
        if ad: 
            self.modo_ad=True; self.controls.place_forget(); self.btn_settings.place_forget(); self.opt_playlist.place_forget(); self.configure(cursor="none"); self.last_ad_timestamp = time.time()
        else: 
            self.modo_ad=False
            if resume: self.configure(cursor="none"); self.controls.place_forget()
            else: self.show_controls()

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
        if not self.modo_ad and (agora_ts - self.last_ad_timestamp) > 60:
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
                                    c["execucoes_hoje"].append(hora)
                                    sv = True; self.mem_time = self.player.get_time()
                                    self.play_video(c["video"], ad=True); break
                    if sv: 
                        with open(DB_FILE,'w') as f: json.dump(cons,f,indent=4)
                except: pass

        if self.is_playing:
            st = self.player.get_state()
            if st == vlc.State.Ended or st == vlc.State.Error:
                if self.modo_ad:
                    self.modo_ad = False
                    self.play_video(self.video_atual, resume=True)
                    self.after(500, lambda: self.player.set_time(self.mem_time))
                else:
                    if self.repeat_state == 1: # Infinito
                        self.play_video(self.idx_video, keep_repeat=True)
                    
                    elif self.repeat_state == 2: # Repetir 1x
                        if not self.repeat_one_done:
                            self.play_video(self.idx_video, keep_repeat=True)
                            self.repeat_one_done = True
                        else:
                            self.repeat_state = 0
                            self.update_repeat_icon()
                            self.next()
                    else:
                        self.next()
        self.after(1000, self.sys_loop)

    def ui_loop(self):
        if self.is_playing:
            try:
                c = self.player.get_time(); t = self.player.get_length()
                if t > 0:
                    self.slider.set(self.player.get_position()*1000)
                    self.lbl_time.configure(text=f"{time.strftime('%M:%S', time.gmtime(c//1000))} / {time.strftime('%M:%S', time.gmtime(t//1000))}")
            except: pass
        self.after(500, self.ui_loop)

    def check_mouse_polling(self):
        if not self.modo_ad:
            try:
                x, y = self.winfo_pointerxy()
                if abs(x-self.last_mouse[0])>10 or abs(y-self.last_mouse[1])>10: self.last_mouse=(x,y); self.on_mouse_move(None)
            except: pass
        self.after(100, self.check_mouse_polling)
    def on_mouse_move(self, e):
        if self.modo_ad: return
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
        if self.is_playing and not self.modo_ad:
            self.controls.place_forget()
            self.configure(cursor="none")
            self.controls_on = False
            if self.is_fullscreen: 
                self.btn_settings.place_forget()
                self.opt_playlist.place_forget()
    def toggle_fs(self, e=None):
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self.btn_settings.place_forget(); self.opt_playlist.place_forget()
            self.attributes("-fullscreen", True)
        else:
            self.attributes("-fullscreen", False); self.state("zoomed")
            self.btn_settings.place(relx=0.98, rely=0.03, anchor="ne"); self.opt_playlist.place(relx=0.88, rely=0.03, anchor="ne")
        self.show_controls()

if __name__ == "__main__":
    app = VisioDeckPlayer()
    app.mainloop()