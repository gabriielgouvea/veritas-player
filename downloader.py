# downloader.py
import customtkinter as ctk
import threading
import os
import time
from tkinter import filedialog
from yt_dlp import YoutubeDL
from config import *
from utils import ModernPopUp

class YoutubeDownloader(ctk.CTkToplevel):
    def __init__(self, parent, pasta_padrao):
        super().__init__(parent)
        self.title("Veritas - Download Center")
        self.configure(fg_color=VERITAS_BG_DASH)
        self.geometry("700x700")
        self.attributes("-topmost", True) 
        self.resizable(True, True)
        
        try: self.geometry(f"+{parent.winfo_x()+50}+{parent.winfo_y()+50}")
        except: pass
        
        self.pasta_padrao = pasta_padrao
        self.video_info = None
        
        self.grid_columnconfigure(0, weight=1)

        # HEADER
        ctk.CTkLabel(self, text="DOWNLOADER YOUTUBE", font=("Arial Black", 24), text_color=VERITAS_BLUE).pack(pady=(30, 5))
        ctk.CTkLabel(self, text="Baixe vídeos para suas playlists.", font=("Segoe UI", 14), text_color="#777").pack(pady=(0, 20))

        # CARD
        self.card = ctk.CTkFrame(self, fg_color="white", corner_radius=15)
        self.card.pack(fill="x", padx=40, pady=10, ipady=20)

        # Input
        ctk.CTkLabel(self.card, text="Link do Vídeo:", font=("Segoe UI", 14, "bold"), text_color="#555").pack(anchor="w", padx=30, pady=(10,5))
        self.entry_link = ctk.CTkEntry(self.card, placeholder_text="Cole o link aqui...", height=50, font=("Segoe UI", 14), border_color="#DDD")
        self.entry_link.pack(fill="x", padx=30, pady=5)
        
        # Botão Analisar
        self.btn_analisar = ctk.CTkButton(self.card, text="🔍  ANALISAR VÍDEO", height=50, fg_color=VERITAS_BLUE, font=("Segoe UI", 14, "bold"), hover_color=VERITAS_BLUE_HOVER, command=self.analisar_link)
        self.btn_analisar.pack(fill="x", padx=30, pady=20)

        # OPÇÕES (Ocultas)
        self.frame_options = ctk.CTkFrame(self.card, fg_color="transparent")
        
        ctk.CTkLabel(self.frame_options, text="Selecione a Qualidade:", font=("Segoe UI", 14, "bold"), text_color="#555").pack(anchor="w", pady=(10,5))
        self.combo_quality = ctk.CTkComboBox(self.frame_options, values=["Melhor (1080p+)", "Alta (720p)", "Média (480p)", "Áudio (MP3)"], height=40, width=300, font=("Segoe UI", 14))
        self.combo_quality.pack(anchor="w", pady=5)
        
        ctk.CTkLabel(self.frame_options, text="Salvar em:", font=("Segoe UI", 14, "bold"), text_color="#555").pack(anchor="w", pady=(20,5))
        
        # --- CONTAINER DE CAMINHO + BOTÃO ALTERAR ---
        fr_path = ctk.CTkFrame(self.frame_options, fg_color="transparent")
        fr_path.pack(fill="x", pady=5)
        
        self.lbl_path = ctk.CTkLabel(fr_path, text=self.pasta_padrao or "Pasta Raiz", font=("Consolas", 12), text_color="#555", fg_color="#F5F7FA", corner_radius=5, height=40, anchor="w")
        self.lbl_path.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_change_path = ctk.CTkButton(fr_path, text="Alterar", width=80, height=40, fg_color=VERITAS_BLUE, command=self.alterar_pasta)
        self.btn_change_path.pack(side="right")
        # ---------------------------------------------

        # STATUS
        self.lbl_status = ctk.CTkLabel(self, text="", font=("Segoe UI", 14, "bold"), text_color=VERITAS_BLUE)
        self.lbl_status.pack(pady=(20,5))
        
        self.progress = ctk.CTkProgressBar(self, height=25, progress_color="#00C853")
        self.progress.set(0)
        
        self.btn_download = ctk.CTkButton(self, text="INICIAR DOWNLOAD", height=60, fg_color="#00C853", hover_color="#00A844", font=("Arial Black", 16), command=self.iniciar_download)

    def alterar_pasta(self):
        p = filedialog.askdirectory(parent=self, title="Selecione onde salvar o vídeo")
        if p:
            self.pasta_padrao = p
            self.lbl_path.configure(text=p)

    def analisar_link(self):
        link = self.entry_link.get()
        if not link: return
        
        self.btn_analisar.configure(state="disabled", text="BUSCANDO INFORMAÇÕES...")
        self.lbl_status.configure(text="Conectando ao YouTube...", text_color="#555")
        
        threading.Thread(target=self.thread_analise, args=(link,), daemon=True).start()

    def thread_analise(self, link):
        try:
            ydl_opts = {'quiet': True}
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=False)
                self.video_info = info
            self.after(0, self.show_options)
        except Exception as e:
            self.after(0, lambda: self.erro_analise(str(e)))

    def show_options(self):
        self.btn_analisar.pack_forget()
        self.frame_options.pack(fill="x", padx=30, pady=10)
        self.btn_download.pack(fill="x", padx=40, pady=20)
        
        titulo = self.video_info.get('title', 'Vídeo')
        self.lbl_status.configure(text=f"Vídeo Encontrado:\n{titulo[:50]}...", text_color=VERITAS_BLUE)

    def erro_analise(self, erro):
        self.btn_analisar.configure(state="normal", text="🔍  ANALISAR VÍDEO")
        self.lbl_status.configure(text="Erro ao buscar. Verifique o link.", text_color=VERITAS_DANGER)

    def iniciar_download(self):
        qualidade = self.combo_quality.get()
        # FIX: Usa diretamente a pasta selecionada, sem criar subpastas
        base = self.pasta_padrao if self.pasta_padrao else os.getcwd()
        
        self.btn_download.configure(state="disabled", text="BAIXANDO...")
        self.progress.pack(fill="x", padx=40, pady=10)
        
        threading.Thread(target=self.thread_download, args=(self.video_info['webpage_url'], base, qualidade), daemon=True).start()

    def thread_download(self, link, base, qualidade):
        try:
            # FIX: save_path agora é direto na base, sem folder "Downloads_Youtube"
            save_path = base 
            if not os.path.exists(save_path): os.makedirs(save_path)

            fmt = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            if "720p" in qualidade: fmt = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]'
            if "480p" in qualidade: fmt = 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]'
            if "Áudio" in qualidade: fmt = 'bestaudio/best'

            ydl_opts = {
                'format': fmt,
                'outtmpl': f'{save_path}/%(title)s.%(ext)s',
                'progress_hooks': [self.progress_hook],
                'noplaylist': True,
            }

            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([link])
            
            self.after(0, self.fim_sucesso)
            
        except Exception as e:
            self.after(0, lambda: self.fim_erro(str(e)))

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            
            # Dados Extras
            eta = d.get('eta') # Segundos restantes
            speed = d.get('speed') # Bytes por segundo
            
            if total:
                percentage = downloaded / total
                self.after(0, lambda: self.update_bar(percentage, eta, speed))

    def update_bar(self, val, eta, speed):
        self.progress.set(val)
        
        # Formatação bonita
        perc_str = f"{int(val*100)}%"
        
        eta_str = "--:--"
        if eta:
            m, s = divmod(eta, 60)
            eta_str = f"{int(m):02d}:{int(s):02d}"
            
        speed_str = ""
        if speed:
            speed_mb = speed / 1024 / 1024
            speed_str = f" • {speed_mb:.1f} MB/s"

        # Texto Final: 35% • 2.5 MB/s • 00:45 restante
        msg = f"Baixando: {perc_str}{speed_str} • ⏱ {eta_str} rest."
        self.lbl_status.configure(text=msg)
        self.update_idletasks()

    def fim_sucesso(self):
        self.progress.pack_forget()
        self.btn_download.configure(state="normal", text="BAIXAR OUTRO", fg_color=VERITAS_BLUE)
        self.lbl_status.configure(text="Download Concluído com Sucesso!", text_color="green")
        self.entry_link.delete(0, "end")
        ModernPopUp(self, "Sucesso", "Vídeo salvo na pasta selecionada!")

    def fim_erro(self, msg):
        self.progress.pack_forget()
        self.btn_download.configure(state="normal", text="TENTAR NOVAMENTE")
        self.lbl_status.configure(text="Erro no Download", text_color=VERITAS_DANGER)
        print(msg)