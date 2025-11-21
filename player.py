# player.py
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
        self.video_atual = "" # Variável Crítica
        self.hist_minuto = [] 
        self.data_cache = datetime.now().strftime("%d/%m/%Y")
        self.shuffle = False
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
        
        # CONTROLES
        self.controls = ctk.CTkFrame(self, fg_color="black", height=120, corner_radius=0)
        self.slider = ctk.CTkSlider(self.controls, from_=0, to=1000, command=self.seek, progress_color="red", button_color="red", button_hover_color="#B71C1C", fg_color="#333", height=20)
        self.slider.pack(fill="x", padx=40, pady=(20,10))

        btns = ctk.CTkFrame(self.controls, fg_color="transparent")
        btns.pack(fill="x", padx=40, pady=(0,20))
        sb = {"fg_color": "transparent", "text_color": "white", "hover_color": "#222", "width": 60, "height": 60, "font": ("Arial", 24)}
        
        self.btn_prev = ctk.CTkButton(btns, text="⏮", command=self.prev, **sb); self.btn_prev.pack(side="left")
        self.btn_play = ctk.CTkButton(btns, text="⏯", command=self.play_pause, **sb); self.btn_play.pack(side="left", padx=10)
        self.btn_next = ctk.CTkButton(btns, text="⏭", command=self.next, **sb); self.btn_next.pack(side="left")
        self.lbl_time = ctk.CTkLabel(btns, text="00:00", font=("Arial", 16), text_color="#DDD"); self.lbl_time.pack(side="left", padx=20)

        self.btn_fs = ctk.CTkButton(btns, text="⛶", command=self.toggle_fs, **sb); self.btn_fs.pack(side="right", padx=5)
        self.sl_vol = ctk.CTkSlider(btns, from_=0, to=100, width=120, command=self.set_vol, progress_color="white", button_color="white", button_hover_color="#EEE"); self.sl_vol.set(100); self.sl_vol.pack(side="right", padx=15)
        self.btn_mute = ctk.CTkButton(btns, text="🔊", command=self.toggle_mute, **sb); self.btn_mute.pack(side="right")
        self.btn_shuf = ctk.CTkButton(btns, text="🔀", command=self.toggle_shuffle, **sb); self.btn_shuf.pack(side="right", padx=10)

        self.lbl_info = ctk.CTkLabel(self.canvas, text="Clique em AJUSTES para selecionar a pasta...", font=("Arial", 30), text_color="#555", bg_color="black")
        self.lbl_info.place(relx=0.5, rely=0.5, anchor="center")

        self.btn_settings = ctk.CTkButton(self, text="⚙️  AJUSTES", command=self.open_dash, width=130, height=40, fg_color="white", text_color="black", hover_color="#DDD", font=("Segoe UI", 12, "bold"), corner_radius=20, bg_color="black")
        self.btn_settings.place(relx=0.98, rely=0.03, anchor="ne")

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
            if self.current_playlist: self.play_video(0, start_paused=False)
            else: self.player.stop()

    def scan_folders(self):
        self.playlist_folders = {"TODOS": []}
        self.all_videos = []
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
            
            if self.playlist_folders["TODOS"]:
                self.lbl_info.place_forget()
                self.current_playlist = self.playlist_folders["TODOS"]
                self.play_video(0, start_paused=True)
            else: self.lbl_info.configure(text="Nenhum vídeo encontrado!")
        except: pass

    def play_video(self, target, ad=False, resume=False, start_paused=False):
        path = ""
        
        # --- CORREÇÃO DA LÓGICA DE PATH E MEMÓRIA ---
        if ad:
            path = target # Se for AD, o caminho vem direto
            # IMPORTANTE: NÃO ATUALIZAMOS self.video_atual AQUI
        else:
            # Se for vídeo normal
            if not self.current_playlist: return
            
            if isinstance(target, int): 
                if target >= len(self.current_playlist): target = 0
                self.idx_video = target
                path = self.current_playlist[target]
            else:
                path = target
            
            # ATUALIZA O VÍDEO ATUAL APENAS SE NÃO FOR AD
            self.video_atual = path 
        # ----------------------------------------------

        self.player.set_hwnd(self.canvas.winfo_id())
        self.player.set_media(self.vlc.media_new(path))
        self.player.play()
        
        if start_paused:
            self.after(100, lambda: self.player.pause())
            self.is_playing = False; self.btn_play.configure(text="▶")
        else:
            self.is_playing = True; self.btn_play.configure(text="⏸")
        
        if ad: 
            self.modo_ad=True
            self.controls.place_forget()
            self.btn_settings.place_forget()
            self.configure(cursor="none")
            self.last_ad_timestamp = time.time()
        else: 
            self.modo_ad=False
            if resume: 
                self.configure(cursor="none")
                self.controls.place_forget()
            else: self.show_controls()

    def sys_loop(self):
        hoje = datetime.now().strftime("%d/%m/%Y")
        
        if hoje != self.data_cache:
            self.data_cache = hoje
            try:
                with open(DB_FILE,'r') as f:
                    d = json.load(f)
                for c in d: c["execucoes_hoje"] = []
                with open(DB_FILE,'w') as f:
                    json.dump(d,f,indent=4)
            except: pass
        
        agora_ts = time.time()
        # Só checa se não estiver em AD e se passou 60s do ultimo
        if not self.modo_ad and (agora_ts - self.last_ad_timestamp) > 60:
            if os.path.exists(DB_FILE):
                now = datetime.now()
                hora = now.strftime("%H:%M")
                wd = ["seg","ter","qua","qui","sex","sab","dom"][now.weekday()]
                try:
                    with open(DB_FILE,'r') as f:
                        cons = json.load(f)
                    
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
                                    
                                    # SALVA O TEMPO DO VÍDEO DE TREINO ATUAL
                                    self.mem_time = self.player.get_time()
                                    
                                    self.play_video(c["video"], ad=True)
                                    break
                    if sv: 
                        with open(DB_FILE,'w') as f:
                            json.dump(cons,f,indent=4)
                except: pass

        if self.is_playing:
            st = self.player.get_state()
            if st == vlc.State.Ended or st == vlc.State.Error:
                if self.modo_ad:
                    # FIM DO AD -> VOLTA PRO TREINO (usando video_atual preservado)
                    self.modo_ad = False
                    self.play_video(self.video_atual, resume=True)
                    # Atraso maior para garantir seek
                    self.after(500, lambda: self.player.set_time(self.mem_time))
                else: 
                    self.next()
        
        self.after(1000, self.sys_loop)

    def ui_loop(self):
        if self.is_playing:
            try:
                c = self.player.get_time()
                t = self.player.get_length()
                if t > 0:
                    self.slider.set(self.player.get_position()*1000)
                    self.lbl_time.configure(text=f"{time.strftime('%M:%S', time.gmtime(c//1000))} / {time.strftime('%M:%S', time.gmtime(t//1000))}")
            except: pass
        self.after(500, self.ui_loop)

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
    def toggle_shuffle(self): self.shuffle=not self.shuffle; self.btn_shuf.configure(text_color=VERITAS_PRIMARY if self.shuffle else "#AAA")
    
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
            self.configure(cursor="arrow"); self.controls.place(relx=0.5, rely=0.85, relwidth=0.9, anchor="center"); self.controls.lift(); self.controls_on=True
            if not self.is_fullscreen: self.btn_settings.place(relx=0.98, rely=0.03, anchor="ne")
    def hide_controls(self):
        if self.is_playing and not self.modo_ad:
            self.controls.place_forget()
            self.configure(cursor="none")
            self.controls_on = False
            if self.is_fullscreen: self.btn_settings.place_forget()
    def toggle_fs(self, e=None):
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self.btn_settings.place_forget()
            self.attributes("-fullscreen", True)
        else:
            self.attributes("-fullscreen", False)
            self.state("zoomed")
            self.btn_settings.place(relx=0.98, rely=0.03, anchor="ne") #nada#
        self.show_controls()

if __name__ == "__main__":
    app = VisioDeckPlayer()
    app.mainloop()