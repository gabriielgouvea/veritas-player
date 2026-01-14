# downloader.py
import customtkinter as ctk
import threading
import os
import time
import sys
import traceback
from datetime import datetime
from tkinter import filedialog
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
from config import *
from utils import ModernPopUp


class DownloadCancelled(Exception):
    pass

class YoutubeDownloader(ctk.CTkFrame): # <-- AGORA É UM FRAME, NÃO UMA JANELA
    def __init__(self, parent, pasta_padrao):
        super().__init__(parent, fg_color="transparent")
        
        self.pasta_padrao = pasta_padrao
        self.video_info = None
        self.grid_columnconfigure(0, weight=1)

        # HEADER
        ctk.CTkLabel(self, text="DOWNLOADER YOUTUBE", font=("Arial Black", 24), text_color=VERITAS_BLUE).pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(self, text="Baixe vídeos para suas playlists.", font=("Segoe UI", 14), text_color="#777").pack(anchor="w", pady=(0, 20))

        # CARD PRINCIPAL
        self.card = ctk.CTkFrame(self, fg_color="white", corner_radius=15)
        self.card.pack(fill="x", ipady=20)

        # --- INPUT + BOTÃO COLAR ---
        ctk.CTkLabel(self.card, text="Link do Vídeo:", font=("Segoe UI", 14, "bold"), text_color="#555").pack(anchor="w", padx=30, pady=(10,5))
        
        fr_input = ctk.CTkFrame(self.card, fg_color="transparent")
        fr_input.pack(fill="x", padx=30, pady=5)
        
        self.entry_link = ctk.CTkEntry(fr_input, placeholder_text="Cole o link aqui...", height=50, font=("Segoe UI", 14), border_color="#DDD")
        self.entry_link.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # Botão Colar
        self.btn_paste = ctk.CTkButton(fr_input, text="📋 COLAR", width=100, height=50, fg_color="#EEE", text_color="#333", hover_color="#DDD", command=self.colar_link)
        self.btn_paste.pack(side="right")
        # ---------------------------
        
        # Botão Analisar
        self.btn_analisar = ctk.CTkButton(self.card, text="🔍  ANALISAR VÍDEO", height=50, fg_color=VERITAS_BLUE, font=("Segoe UI", 14, "bold"), hover_color=VERITAS_BLUE_HOVER, command=self.analisar_link)
        self.btn_analisar.pack(fill="x", padx=30, pady=20)

        # OPÇÕES (Ocultas inicialmente)
        self.frame_options = ctk.CTkFrame(self.card, fg_color="transparent")
        
        ctk.CTkLabel(self.frame_options, text="Selecione a Qualidade (Estimativa de Tamanho):", font=("Segoe UI", 14, "bold"), text_color="#555").pack(anchor="w", pady=(10,5))
        
        # ComboBox agora começa vazio e será preenchido após análise
        self.combo_quality = ctk.CTkComboBox(self.frame_options, values=[], height=40, width=400, font=("Segoe UI", 14))
        self.combo_quality.pack(anchor="w", pady=5)
        
        ctk.CTkLabel(self.frame_options, text="Salvar em:", font=("Segoe UI", 14, "bold"), text_color="#555").pack(anchor="w", pady=(20,5))
        
        fr_path = ctk.CTkFrame(self.frame_options, fg_color="transparent")
        fr_path.pack(fill="x", pady=5)
        
        self.lbl_path = ctk.CTkLabel(fr_path, text=self.pasta_padrao or "Pasta Raiz", font=("Consolas", 12), text_color="#555", fg_color="#F5F7FA", corner_radius=5, height=40, anchor="w")
        self.lbl_path.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_change_path = ctk.CTkButton(fr_path, text="Alterar", width=80, height=40, fg_color=VERITAS_BLUE, command=self.alterar_pasta)
        self.btn_change_path.pack(side="right")

        # STATUS E PROGRESSO
        self.lbl_status = ctk.CTkLabel(self, text="", font=("Segoe UI", 14, "bold"), text_color=VERITAS_BLUE)
        self.lbl_status.pack(pady=(20,5))
        
        self.progress = ctk.CTkProgressBar(self, height=25, progress_color="#00C853")
        self.progress.set(0)
        
        self.btn_download = ctk.CTkButton(self, text="INICIAR DOWNLOAD", height=60, fg_color="#00C853", hover_color="#00A844", font=("Arial Black", 16), command=self.iniciar_download)

        # Botão de cancelar (só aparece durante o download)
        self._cancel_requested = False
        self._last_download_files = set()
        self.btn_cancel = ctk.CTkButton(
            self,
            text="PARAR DOWNLOAD",
            height=50,
            fg_color=VERITAS_DANGER,
            hover_color="#D32F2F",
            font=("Segoe UI", 14, "bold"),
            command=self.cancelar_download,
        )

    def _download_log_path(self) -> str:
        try:
            base = DATA_FOLDER
        except Exception:
            base = os.getcwd()
        return os.path.join(base, "youtube_download.log")

    def _log_download(self, message: str) -> None:
        try:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self._download_log_path(), "a", encoding="utf-8") as f:
                f.write(f"[{ts}] {message}\n")
        except Exception:
            pass

    def _get_ffmpeg_location(self) -> str | None:
        # No modo empacotado, o ffmpeg fica ao lado do .exe (não necessariamente em _MEIPASS).
        try:
            if getattr(sys, 'frozen', False):
                p = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "ffmpeg.exe")
                if os.path.exists(p):
                    return p
        except Exception:
            pass

        try:
            if os.path.exists(FFMPEG_PATH):
                return FFMPEG_PATH
        except Exception:
            pass

        p = os.path.join(os.getcwd(), "ffmpeg.exe")
        if os.path.exists(p):
            return p
        return None

    def colar_link(self):
        try:
            link = self.clipboard_get()
            self.entry_link.delete(0, "end")
            self.entry_link.insert(0, link)
        except: pass

    def alterar_pasta(self):
        p = filedialog.askdirectory(parent=self, title="Selecione onde salvar o vídeo")
        if p:
            self.pasta_padrao = p
            self.lbl_path.configure(text=p)

    def analisar_link(self):
        link = self.entry_link.get()
        if not link: return
        
        self.btn_analisar.configure(state="disabled", text="BUSCANDO INFORMAÇÕES E TAMANHOS...")
        self.lbl_status.configure(text="Conectando ao YouTube...", text_color="#555")
        
        threading.Thread(target=self.thread_analise, args=(link,), daemon=True).start()

    def format_bytes(self, size):
        # Converte bytes para MB ou GB
        if not size: return "?"
        power = 2**10
        n = 0
        power_labels = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
        while size > power:
            size /= power
            n += 1
        return f"{size:.1f} {power_labels[n]}B"

    def thread_analise(self, link):
        try:
            ydl_opts = {'quiet': True}
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=False)
                self.video_info = info
                
                # --- LÓGICA DE ESTIMATIVA DE TAMANHO ---
                formats = info.get('formats', [])
                
                # Helper para achar tamanho aproximado
                def get_size(height_target):
                    best_size = 0
                    for f in formats:
                        # Procura video mp4 com a altura desejada
                        if f.get('ext') == 'mp4' and f.get('height') == height_target:
                            # Pega filesize ou filesize_approx
                            s = f.get('filesize') or f.get('filesize_approx') or 0
                            if s > best_size: best_size = s
                    
                    # Adiciona uma estimativa de áudio (aprox 3MB por minuto) se achou video
                    duration = info.get('duration', 0)
                    if best_size > 0:
                        audio_est = (128 * 1024 / 8) * duration # 128kbps bitrate áudio
                        return best_size + audio_est
                    return 0

                size_1080 = get_size(1080)
                size_720 = get_size(720)
                size_480 = get_size(480)
                
                # Opções com tamanho
                self.opcoes_qualidade = [
                    f"Melhor (1080p+)   [~{self.format_bytes(size_1080)}]" if size_1080 else "Melhor (1080p+)",
                    f"Alta (720p)       [~{self.format_bytes(size_720)}]" if size_720 else "Alta (720p)",
                    f"Média (480p)      [~{self.format_bytes(size_480)}]" if size_480 else "Média (480p)",
                    "Áudio (MP3)"
                ]
                # ---------------------------------------

            self.after(0, self.show_options)
        except Exception as e:
            self.after(0, lambda: self.erro_analise(str(e)))

    def show_options(self):
        self.btn_analisar.pack_forget()
        
        # Atualiza a Combo com os tamanhos descobertos
        self.combo_quality.configure(values=self.opcoes_qualidade)
        self.combo_quality.set(self.opcoes_qualidade[0])
        
        self.frame_options.pack(fill="x", padx=30, pady=10)
        self.btn_download.pack(fill="x", padx=40, pady=20)
        
        titulo = self.video_info.get('title', 'Vídeo')
        self.lbl_status.configure(text=f"Vídeo Encontrado:\n{titulo[:50]}...", text_color=VERITAS_BLUE)

    def erro_analise(self, erro):
        self.btn_analisar.configure(state="normal", text="🔍  ANALISAR VÍDEO")
        self.lbl_status.configure(text="Erro ao buscar. Verifique o link.", text_color=VERITAS_DANGER)

    def iniciar_download(self):
        if not self.video_info:
            ModernPopUp(self, "Atenção", "Clique em ANALISAR VÍDEO antes de baixar.")
            return

        self._cancel_requested = False
        self._last_download_files = set()
        qualidade_str = self.combo_quality.get()
        base = self.pasta_padrao if self.pasta_padrao else os.getcwd()
        
        self.btn_download.configure(state="disabled", text="BAIXANDO...")
        self.progress.pack(fill="x", padx=40, pady=10)

        # Mostra o botão de cancelar apenas enquanto estiver baixando
        self.btn_cancel.configure(state="normal")
        self.btn_cancel.pack(fill="x", padx=40, pady=(0, 10))
        
        threading.Thread(target=self.thread_download, args=(self.video_info['webpage_url'], base, qualidade_str), daemon=True).start()

    def cancelar_download(self):
        # O cancelamento acontece na thread do yt-dlp via progress_hook
        self._cancel_requested = True
        try:
            self.btn_cancel.configure(state="disabled", text="CANCELANDO...")
        except Exception:
            pass
        try:
            self.lbl_status.configure(text="Cancelando download...", text_color=VERITAS_DANGER)
        except Exception:
            pass

    def thread_download(self, link, base, qualidade_str):
        try:
            save_path = base 
            if not os.path.exists(save_path): os.makedirs(save_path)

            ffmpeg_location = self._get_ffmpeg_location()
            if not ffmpeg_location:
                self._log_download("ffmpeg.exe não encontrado (nem ao lado do app, nem no cwd).")

            fmt = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            if "720p" in qualidade_str: fmt = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]'
            if "480p" in qualidade_str: fmt = 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]'
            if "Áudio" in qualidade_str: fmt = 'bestaudio/best'

            postprocessors = []
            merge_output_format = "mp4"
            if "Áudio" in qualidade_str:
                # Converte para MP3 (a UI promete MP3).
                merge_output_format = None
                postprocessors = [
                    {
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }
                ]

            ydl_opts = {
                'format': fmt,
                'outtmpl': os.path.join(save_path, '%(title).200s [%(id)s].%(ext)s'),
                'progress_hooks': [self.progress_hook],
                'noplaylist': True,
                'windowsfilenames': True,
                'restrictfilenames': False,
                'quiet': True,
                'no_warnings': True,
            }

            if ffmpeg_location:
                ydl_opts['ffmpeg_location'] = ffmpeg_location

            if merge_output_format:
                ydl_opts['merge_output_format'] = merge_output_format

            if postprocessors:
                ydl_opts['postprocessors'] = postprocessors

            self._log_download(f"Iniciando download: qualidade='{qualidade_str}', fmt='{fmt}', pasta='{save_path}', ffmpeg='{ffmpeg_location or 'N/A'}'")

            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([link])
            
            self.after(0, self.fim_sucesso)
            
        except DownloadCancelled:
            self.after(0, lambda: self.fim_cancelado(base))
        except DownloadError as e:
            self._log_download(f"DownloadError: {e}")
            self._log_download(traceback.format_exc())
            self.after(0, lambda: self.fim_erro(str(e)))
        except Exception as e:
            self._log_download(f"Erro inesperado: {e}")
            self._log_download(traceback.format_exc())
            self.after(0, lambda: self.fim_erro(str(e)))

    def progress_hook(self, d):
        # Interrompe assim que o usuário pedir cancelamento
        if self._cancel_requested:
            raise DownloadCancelled("Cancelado pelo usuário")

        if d['status'] == 'downloading':
            fn = d.get('filename')
            tmp = d.get('tmpfilename')
            if fn:
                self._last_download_files.add(fn)
            if tmp:
                self._last_download_files.add(tmp)

            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            eta = d.get('eta'); speed = d.get('speed')
            
            if total:
                percentage = downloaded / total
                self.after(0, lambda: self.update_bar(percentage, eta, speed))

    def update_bar(self, val, eta, speed):
        self.progress.set(val)
        perc_str = f"{int(val*100)}%"
        eta_str = "--:--"
        if eta: m, s = divmod(eta, 60); eta_str = f"{int(m):02d}:{int(s):02d}"
        speed_str = ""
        if speed: speed_mb = speed / 1024 / 1024; speed_str = f" • {speed_mb:.1f} MB/s"
        msg = f"Baixando: {perc_str}{speed_str} • ⏱ {eta_str} rest."
        self.lbl_status.configure(text=msg)
        self.update_idletasks()

    def fim_sucesso(self):
        self.progress.pack_forget()
        try:
            self.btn_cancel.pack_forget()
        except Exception:
            pass
        self.btn_download.configure(state="normal", text="BAIXAR OUTRO", fg_color=VERITAS_BLUE)
        self.lbl_status.configure(text="Download Concluído com Sucesso!", text_color="green")
        self.entry_link.delete(0, "end")
        ModernPopUp(self, "Sucesso", "Vídeo salvo!")

    def fim_cancelado(self, base_path):
        self.progress.pack_forget()
        try:
            self.btn_cancel.pack_forget()
        except Exception:
            pass
        self.btn_download.configure(state="normal", text="INICIAR DOWNLOAD", fg_color="#00C853")
        self.lbl_status.configure(text="Download cancelado.", text_color=VERITAS_DANGER)

        # Tenta remover arquivos parciais (.part/tmp) mais prováveis
        try:
            for p in list(self._last_download_files):
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass

            # Remove sobras comuns na pasta destino
            for fn in os.listdir(base_path):
                if fn.endswith('.part') or fn.endswith('.ytdl'):
                    try:
                        os.remove(os.path.join(base_path, fn))
                    except Exception:
                        pass
        except Exception:
            pass

        ModernPopUp(self, "Cancelado", "O download foi cancelado.")

    def fim_erro(self, msg):
        self.progress.pack_forget()
        try:
            self.btn_cancel.pack_forget()
        except Exception:
            pass
        self.btn_download.configure(state="normal", text="TENTAR NOVAMENTE")
        self.lbl_status.configure(text="Erro no Download", text_color=VERITAS_DANGER)
        resumo = (msg or "Erro desconhecido").strip()
        if len(resumo) > 800:
            resumo = resumo[:800] + "..."
        ModernPopUp(
            self,
            "Erro no Download",
            f"{resumo}\n\nDetalhes em: {self._download_log_path()}",
        )