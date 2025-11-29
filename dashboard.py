# dashboard.py (Versão 19.4 - Suporte a Audio Ads)
import customtkinter as ctk
import os
import time
import json
import threading
import asyncio
import edge_tts 
import subprocess 
from datetime import datetime
from tkinter import filedialog
from config import *
from utils import ModernPopUp, carregar_db, salvar_db, garantir_alerta_sonoro, ControleVolume
from downloader import YoutubeDownloader

MSG_FILE = "mensagens_locutor.json"
CONFIG_LOCUTOR = "config_locutor.json"

class DashboardWindow(ctk.CTkToplevel):
    def __init__(self, parent, player):
        super().__init__(parent)
        self.title("Veritas - Painel de Controle")
        self.configure(fg_color=VERITAS_BG_DASH)
        self.player = player
        
        self.geometry("1200x800")
        self.after(100, lambda: self.state("zoomed"))
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.contratos = carregar_db()
        self.msgs_prontas = self.carregar_msgs()
        self.alert_sound_path = self.carregar_config_locutor()
        
        self.editando_id = None
        self.l_hours = []
        self.l_dates = []
        self.vid_path = ""
        
        self.volume_antes_tts = 50 
        self.em_anuncio = False

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=260, corner_radius=0, fg_color="white")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        
        ctk.CTkLabel(self.sidebar, text="VERITAS\nPLAYER", font=("Arial Black", 24), text_color=VERITAS_BLUE).pack(pady=40)
        
        self.btn_dict = {}
        self.create_menu_btn("🏠  Configuração Inicial", "config")
        self.create_menu_btn("📋  Propagandas Ativas", "list")
        self.create_menu_btn("➕  Nova Propaganda", "create")
        self.create_menu_btn("📢  Locutor (TTS)", "locutor") 
        
        ctk.CTkFrame(self.sidebar, height=2, fg_color="#F0F2F5").pack(fill="x", padx=20, pady=10)
        self.create_menu_btn("⬇️  Baixar do YouTube", "download")
        self.create_menu_btn("☕  Apoiar Projeto", "donate") 
        ctk.CTkFrame(self.sidebar, height=2, fg_color="#F0F2F5").pack(fill="x", padx=20, pady=10)
        
        ctk.CTkButton(self.sidebar, text="🔙  Voltar ao Player", command=self.destroy, 
                      fg_color="#FFF", text_color=VERITAS_BLUE, hover_color="#F0F2F5", 
                      font=("Segoe UI", 14, "bold"), height=50, anchor="w").pack(fill="x", padx=10)

        ctk.CTkLabel(self.sidebar, text="v19.4 - Audio Ads", text_color="#AAA", font=("Segoe UI", 10, "bold")).pack(side="bottom", pady=(0, 10))
        ctk.CTkLabel(self.sidebar, text="Desenvolvido por Gabriel Gouvêa", text_color="#CCC", font=("Segoe UI", 9)).pack(side="bottom", pady=5)

        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        
        self.show_view("config")

    def create_menu_btn(self, text, name):
        btn = ctk.CTkButton(self.sidebar, text=f"  {text}", command=lambda: self.show_view(name), fg_color="transparent", text_color="#555", anchor="w", font=("Segoe UI", 14, "bold"), height=50, hover_color="#F0F2F5")
        btn.pack(fill="x", padx=10, pady=2)
        self.btn_dict[name] = btn

    def show_view(self, view_name):
        for n, b in self.btn_dict.items(): 
            if n == view_name: b.configure(fg_color="#E3F2FD", text_color=VERITAS_BLUE)
            else: b.configure(fg_color="transparent", text_color="#555")
        for widget in self.main_area.winfo_children(): widget.destroy()
        
        if view_name == "config": self.render_config()
        elif view_name == "list": self.render_ad_list()
        elif view_name == "create": self.render_ad_create()
        elif view_name == "locutor": self.render_locutor()
        elif view_name == "donate": self.render_donate()
        elif view_name == "download":
            self.header("Download Center", "Baixe vídeos do YouTube.")
            container = ctk.CTkFrame(self.main_area, fg_color="transparent")
            container.pack(fill="both", expand=True)
            YoutubeDownloader(container, self.player.pasta_treino).pack(fill="both", expand=True)

    # --- RENDER AD CREATE (ATUALIZADO COM SELETOR DE MÍDIA) ---
    def render_ad_create(self):
        d = {}
        if self.editando_id:
            d = next((c for c in self.contratos if str(c["id"]) == str(self.editando_id)), {})
        
        self.header("Editar Propaganda" if self.editando_id else "Nova Propaganda", "Preencha os dados.")
        f = ctk.CTkScrollableFrame(self.main_area, fg_color="transparent")
        f.pack(fill="both", expand=True)
        self.card_form(f, "Dados Gerais")
        fr = ctk.CTkFrame(self.last_card, fg_color="transparent")
        fr.pack(fill="x", padx=20, pady=10)
        
        # --- SELETOR DE TIPO ---
        ctk.CTkLabel(fr, text="Tipo de Mídia:", text_color="#555").grid(row=0, column=0, sticky="w", padx=(0,10), pady=(0,5))
        self.var_tipo = ctk.StringVar(value=d.get("tipo", "VIDEO"))
        self.seg_tipo = ctk.CTkSegmentedButton(fr, values=["VIDEO", "AUDIO"], variable=self.var_tipo, command=self.mudar_tipo_midia, selected_color=VERITAS_BLUE, selected_hover_color=VERITAS_BLUE_HOVER)
        self.seg_tipo.grid(row=1, column=0, sticky="ew", padx=(0,10))
        # -----------------------

        self.inp_grid(fr, "Nome:", 0, 1)
        self.e_nome = ctk.CTkEntry(fr, height=40)
        self.e_nome.grid(row=1, column=1, sticky="ew", padx=(0,10))
        
        self.inp_grid(fr, "Autorizado:", 0, 2)
        self.e_autor = ctk.CTkComboBox(fr, values=["Basa","Juju","Betão","Fabi","Gerência"], height=40, button_color=VERITAS_BLUE)
        self.e_autor.grid(row=1, column=2, sticky="ew")
        
        fr.columnconfigure(0, weight=1)
        fr.columnconfigure(1, weight=2)
        fr.columnconfigure(2, weight=1)
        
        self.lbl_arquivo_titulo = ctk.CTkLabel(self.last_card, text="Arquivo de Vídeo:", text_color="#555")
        self.lbl_arquivo_titulo.pack(anchor="w", padx=20, pady=(10,0))
        
        fv = ctk.CTkFrame(self.last_card, fg_color="#F5F7FA", height=50)
        fv.pack(fill="x", padx=20, pady=5)
        self.lbl_vid = ctk.CTkLabel(fv, text="Nenhum selecionado", text_color="#777")
        self.lbl_vid.pack(side="left", padx=15)
        ctk.CTkButton(fv, text="Selecionar", command=self.sel_vid, fg_color=VERITAS_BLUE, width=100).pack(side="right", padx=10, pady=5)

        self.card_form(f, "Vigência")
        self.tabs = ctk.CTkTabview(self.last_card, height=250, fg_color="transparent", segmented_button_selected_color=VERITAS_BLUE)
        self.tabs.pack(fill="x", padx=10)
        self.tabs.add("PERÍODO")
        self.tabs.add("DATA ÚNICA")
        t1 = self.tabs.tab("PERÍODO")
        fd = ctk.CTkFrame(t1, fg_color="transparent")
        fd.pack(fill="x", pady=10)
        ctk.CTkLabel(fd, text="Início:", text_color="#555").pack(side="left")
        self.e_ini = ctk.CTkEntry(fd, width=120, placeholder_text="DD/MM/AAAA")
        self.e_ini.pack(side="left", padx=(5,20))
        self.e_ini.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.e_ini.bind("<KeyRelease>", self.smart_date)
        ctk.CTkLabel(fd, text="Fim:", text_color="#555").pack(side="left")
        self.e_fim = ctk.CTkEntry(fd, width=120, placeholder_text="DD/MM/AAAA")
        self.e_fim.pack(side="left", padx=(5,20))
        self.e_fim.bind("<KeyRelease>", self.smart_date)
        self.e_dias = ctk.CTkEntry(fd, width=80, state="disabled", fg_color="#EEE", text_color="#333")
        self.e_dias.pack(side="left")
        
        fc = ctk.CTkFrame(t1, fg_color="transparent")
        fc.pack(fill="x", pady=5)
        self.v_indet = ctk.BooleanVar()
        self.v_hoje = ctk.BooleanVar()
        self.chk_indet = ctk.CTkCheckBox(fc, text="Indeterminado", variable=self.v_indet, command=self.logic_indet, text_color="#333", checkmark_color=VERITAS_BLUE)
        self.chk_indet.pack(side="left", padx=20)
        self.chk_hoje = ctk.CTkCheckBox(fc, text="SOMENTE HOJE", variable=self.v_hoje, command=self.logic_hoje, text_color=VERITAS_DANGER, checkmark_color=VERITAS_DANGER)
        self.chk_hoje.pack(side="left")
        
        fs = ctk.CTkFrame(t1, fg_color="transparent")
        fs.pack(fill="x")
        self.d_vars = {}
        self.chk_dias = []
        for d_name in ["seg","ter","qua","qui","sex","sab","dom"]: 
            v = ctk.BooleanVar(value=True)
            self.d_vars[d_name]=v
            c = ctk.CTkCheckBox(fs, text=d_name.upper(), variable=v, width=60, text_color="#555", checkmark_color=VERITAS_BLUE, command=self.logic_sem)
            c.pack(side="left", padx=5)
            self.chk_dias.append(c)
            
        t2 = self.tabs.tab("DATA ÚNICA")
        fdt = ctk.CTkFrame(t2, fg_color="transparent")
        fdt.pack(fill="x")
        self.e_dt = ctk.CTkEntry(fdt, placeholder_text="DD/MM/AAAA", width=150)
        self.e_dt.pack(side="left")
        self.e_dt.bind("<KeyRelease>", self.masc_dt)
        self.e_dt.bind("<Return>", self.add_dt)
        ctk.CTkButton(fdt, text="+", width=40, command=self.add_dt, fg_color=VERITAS_BLUE).pack(side="left", padx=5)
        self.fr_dt = ctk.CTkFrame(t2, fg_color="#F0F0F0")
        self.fr_dt.pack(fill="both", expand=True, pady=10)
        self.l_dates = []

        self.card_form(f, "Horários")
        fh = ctk.CTkFrame(self.last_card, fg_color="transparent")
        fh.pack(fill="x", padx=20, pady=10)
        self.e_hr = ctk.CTkEntry(fh, placeholder_text="HH:MM", width=100)
        self.e_hr.pack(side="left")
        self.e_hr.bind("<KeyRelease>", self.masc_hr)
        self.e_hr.bind("<Return>", self.add_hr)
        ctk.CTkButton(fh, text="+", width=40, command=self.add_hr, fg_color=VERITAS_BLUE).pack(side="left", padx=5)
        self.fr_hr = ctk.CTkFrame(self.last_card, fg_color="#F0F0F0", height=50)
        self.fr_hr.pack(fill="x", padx=20, pady=5)
        self.l_hours = []

        fb = ctk.CTkFrame(f, fg_color="transparent")
        fb.pack(fill="x", pady=30)
        if self.editando_id: 
            ctk.CTkButton(fb, text="CANCELAR", fg_color="#AAA", width=150, command=lambda: self.show_view("list")).pack(side="left")
        ctk.CTkButton(fb, text="SALVAR", fg_color=VERITAS_BLUE, width=200, height=50, font=("Segoe UI", 14, "bold"), command=self.salvar).pack(side="right")
        
        self.smart_date()
        if self.editando_id and d: self.preencher(d)
        self.mudar_tipo_midia() # Atualiza labels ao abrir

    def mudar_tipo_midia(self, v=None):
        t = self.var_tipo.get()
        if t == "AUDIO":
            self.lbl_arquivo_titulo.configure(text="Arquivo de Áudio (MP3/WAV):")
        else:
            self.lbl_arquivo_titulo.configure(text="Arquivo de Vídeo (MP4):")

    def sel_vid(self):
        t = self.var_tipo.get()
        ft = [("Video", "*.mp4 *.mkv")] if t == "VIDEO" else [("Audio", "*.mp3 *.wav")]
        p = filedialog.askopenfilename(parent=self, filetypes=ft)
        if p: 
            self.vid_path=p
            self.lbl_vid.configure(text=os.path.basename(p))

    def salvar(self):
        if not self.vid_path or not self.l_hours: 
            ModernPopUp(self, "Erro", "Preencha arquivo e horários!")
            return
            
        c = { 
            "id": self.editando_id if self.editando_id else int(time.time()), 
            "nome": self.e_nome.get() or "Sem Nome", 
            "tipo": self.var_tipo.get(), # SALVA O TIPO
            "autorizado": self.e_autor.get(), 
            "video": self.vid_path, 
            "ativo": True, 
            "modo": "DATAS ESPECÍFICAS" if self.tabs.get()=="DATA ÚNICA" else "POR PERÍODO", 
            "horarios": self.l_hours, 
            "inicio": self.e_ini.get(), 
            "fim": "INDETERMINADO" if self.v_indet.get() else self.e_fim.get(), 
            "dias": [d for d, v in self.d_vars.items() if v.get()], 
            "somente_hoje": self.v_hoje.get(), 
            "datas_especificas": self.l_dates, 
            "execucoes_hoje": [] 
        }
        
        if self.editando_id:
            for i, x in enumerate(self.contratos):
                if str(x["id"]) == str(self.editando_id): 
                    c["execucoes_hoje"] = x.get("execucoes_hoje",[])
                    self.contratos[i] = c
                    break
        else: 
            self.contratos.append(c)
            
        salvar_db(self.contratos)
        self.editando_id = None
        self.show_view("list")
        ModernPopUp(self, "Sucesso", "Salvo!")

    def preencher(self, d):
        self.e_nome.delete(0, "end")
        self.e_nome.insert(0, d.get("nome",""))
        self.e_autor.set(d.get("autorizado",""))
        self.var_tipo.set(d.get("tipo", "VIDEO")) # Carrega o tipo
        self.vid_path = d.get("video","")
        if self.vid_path: self.lbl_vid.configure(text=os.path.basename(self.vid_path))
        self.l_hours = d.get("horarios",[])[:]
        self.render_tags(self.fr_hr, self.l_hours, self.rm_hr)
        if d.get("modo") == "DATAS ESPECÍFICAS":
            self.tabs.set("DATA ÚNICA")
            self.l_dates = d.get("datas_especificas",[])[:]
            self.render_tags(self.fr_dt, self.l_dates, self.rm_dt)
        else:
            self.tabs.set("PERÍODO")
            self.e_ini.delete(0,"end")
            self.e_ini.insert(0, d.get("inicio", datetime.now().strftime("%d/%m/%Y")))
            if d.get("fim") == "INDETERMINADO": 
                self.v_indet.set(True)
                self.logic_indet()
            else: 
                self.e_fim.configure(state="normal", fg_color="white")
                self.e_fim.delete(0,"end")
                self.e_fim.insert(0, d.get("fim",""))
            self.v_hoje.set(d.get("somente_hoje", False))
            if self.v_hoje.get(): self.logic_hoje()
            dias_salvos = d.get("dias", [])
            for k,v in self.d_vars.items(): v.set(k in dias_salvos)
        self.smart_date()

    def smart_date(self, e=None):
        if e: self.masc_dt(e)
        try:
            ini = datetime.strptime(self.e_ini.get(), "%d/%m/%Y").date()
            hoje = datetime.now().date()
            if ini > hoje: 
                self.v_hoje.set(False)
                self.chk_hoje.configure(state="disabled")
            else: 
                self.chk_hoje.configure(state="normal")
            
            if not self.v_indet.get():
                fim = datetime.strptime(self.e_fim.get(), "%d/%m/%Y").date()
                if fim < ini: 
                    self.e_dias.configure(state="normal")
                    self.e_dias.delete(0,"end")
                    self.e_dias.insert(0,"Erro")
                    self.e_dias.configure(state="disabled")
                else: 
                    self.e_dias.configure(state="normal")
                    self.e_dias.delete(0,"end")
                    self.e_dias.insert(0,f"{(fim-ini).days+1} Dias")
                    self.e_dias.configure(state="disabled")
        except: pass
    
    def logic_hoje(self):
        if self.v_hoje.get(): 
            h = datetime.now().strftime("%d/%m/%Y")
            self.e_ini.delete(0,"end")
            self.e_ini.insert(0,h)
            self.e_fim.delete(0,"end")
            self.e_fim.insert(0,h)
            self.e_fim.configure(state="normal")
            self.v_indet.set(False)
            self.chk_indet.configure(state="normal")
            self.smart_date()
        else: self.smart_date()
    
    def logic_indet(self):
        if self.v_indet.get(): 
            self.e_fim.delete(0,"end")
            self.e_fim.insert(0,"----------")
            self.e_fim.configure(state="disabled", fg_color="#EEE")
            self.v_hoje.set(False)
            self.chk_hoje.configure(state="disabled")
        else: 
            self.e_fim.configure(state="normal", fg_color="white")
            self.e_fim.delete(0,"end")
            self.chk_hoje.configure(state="normal")
    
    def logic_sem(self):
        if self.v_hoje.get(): self.v_hoje.set(False); self.logic_hoje()

    def header(self, t, s): 
        ctk.CTkLabel(self.main_area, text=t, font=("Segoe UI", 26, "bold"), text_color=VERITAS_TEXT).pack(anchor="w")
        ctk.CTkLabel(self.main_area, text=s, font=("Segoe UI", 14), text_color="#777").pack(anchor="w", pady=(0,20))
    
    def card_form(self, p, t): 
        self.last_card = ctk.CTkFrame(p, fg_color="white", corner_radius=10)
        self.last_card.pack(fill="x", pady=10)
        ctk.CTkLabel(self.last_card, text=t, font=("Segoe UI", 14, "bold"), text_color=VERITAS_BLUE).pack(anchor="w", padx=20, pady=(15,5))
        ctk.CTkFrame(self.last_card, height=1, fg_color="#EEE").pack(fill="x", padx=20, pady=(0,10))
    
    def inp_grid(self, p, t, r, c): 
        ctk.CTkLabel(p, text=t, text_color="#555").grid(row=r, column=c, sticky="w", padx=(0,10), pady=(0,5))
    
    def masc_dt(self, e): self._m(e.widget, 10)
    def masc_hr(self, e): self._m(e.widget, 5)
    def _m(self, w, l): 
        t=w.get().replace("/","").replace(":","")
        if not t.isdigit(): return
        w.delete(0,"end")
        w.insert(0, (t[:2]+"/"+t[2:] if l==10 else t[:2]+":"+t[2:]) if len(t)>2 else t)
    
    def add_hr(self, e=None): self._tag(self.e_hr, self.l_hours, self.fr_hr, self.rm_hr, 5)
    def add_dt(self, e=None): self._tag(self.e_dt, self.l_dates, self.fr_dt, self.rm_dt, 10)
    
    def _tag(self, e, l, p, cb, ln): 
        v = e.get()
        if len(v)==ln and v not in l: 
            l.append(v)
            l.sort()
            self.render_tags(p, l, cb)
            e.delete(0,"end")
            
    def rm_hr(self, v): 
        self.l_hours.remove(v)
        self.render_tags(self.fr_hr, self.l_hours, self.rm_hr)
        
    def rm_dt(self, v): 
        self.l_dates.remove(v)
        self.render_tags(self.fr_dt, self.l_dates, self.rm_dt)
        
    def render_tags(self, p, l, cb):
        for w in p.winfo_children(): w.destroy()
        for v in l: 
            f=ctk.CTkFrame(p, fg_color="#E3F2FD", corner_radius=5)
            f.pack(side="left", padx=5, pady=5)
            ctk.CTkLabel(f, text=v, text_color=VERITAS_BLUE).pack(side="left", padx=5)
            ctk.CTkButton(f, text="x", width=15, fg_color="transparent", text_color="red", command=lambda x=v: cb(x)).pack(side="left")

    # --- RESTANTE DAS FUNÇÕES (LOCUTOR, DONATE, CONFIG, ETC) ---
    # (Elas permanecem inalteradas, mas como você pediu arquivo completo, vou manter as principais)
    # ... (Omitindo para economizar espaço e evitar duplicação desnecessária já que o foco é o Ad Create,
    # MAS como você pediu COMPLETO, vou colar o bloco do Locutor aqui também para garantir)

    def render_locutor(self):
        self.header("Locutor Virtual (IA)", "Digite uma mensagem ou selecione uma pronta.")
        left = ctk.CTkFrame(self.main_area, fg_color="white", corner_radius=10)
        left.pack(side="left", fill="both", expand=True, padx=(0,10), pady=10)
        
        fr_sound = ctk.CTkFrame(left, fg_color="#F5F7FA")
        fr_sound.pack(fill="x", padx=20, pady=(20,5))
        self.lbl_sound = ctk.CTkLabel(fr_sound, text=f"🎵 Alerta: {os.path.basename(self.alert_sound_path) if self.alert_sound_path else 'Padrão'}", text_color="#555", font=("Segoe UI", 12))
        self.lbl_sound.pack(side="left", padx=10, pady=5)
        ctk.CTkButton(fr_sound, text="🔔 Escolher Som", width=100, height=30, fg_color="#DDD", text_color="#333", hover_color="#CCC", command=self.selecionar_som_alerta).pack(side="right", padx=5, pady=5)

        ctk.CTkLabel(left, text="📢 Digite sua mensagem:", font=("Segoe UI", 14, "bold"), text_color="#333").pack(anchor="w", padx=20, pady=(10,5))
        self.txt_tts = ctk.CTkTextbox(left, height=150, font=("Segoe UI", 16), border_width=1, border_color="#DDD")
        self.txt_tts.pack(fill="x", padx=20, pady=5)
        
        ctrl_area = ctk.CTkFrame(left, fg_color="transparent")
        ctrl_area.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(ctrl_area, text="Volume PC (%):", font=("Segoe UI", 12, "bold"), text_color="#555").pack(side="left", padx=(0,5))
        self.e_vol = ctk.CTkEntry(ctrl_area, width=50, font=("Segoe UI", 12))
        self.e_vol.pack(side="left")
        self.e_vol.insert(0, "80") 
        
        self.btn_falar = ctk.CTkButton(ctrl_area, text="🔊 ANUNCIAR AGORA", height=50, fg_color=VERITAS_BLUE, font=("Segoe UI", 14, "bold"), command=self.falar_texto)
        self.btn_falar.pack(side="left", fill="x", expand=True, padx=(10,5))

        self.btn_stop = ctk.CTkButton(ctrl_area, text="⏹ PARAR", height=50, width=80, fg_color=VERITAS_DANGER, font=("Segoe UI", 12, "bold"), state="disabled", command=self.parar_fala)
        self.btn_stop.pack(side="right")
        
        self.progress_tts = ctk.CTkProgressBar(left, height=10, progress_color="#00C853")
        self.progress_tts.set(0)
        self.progress_tts.pack(fill="x", padx=20, pady=(0, 5))
        self.lbl_prog_tts = ctk.CTkLabel(left, text="Pronto para anunciar", font=("Segoe UI", 11), text_color="#777")
        self.lbl_prog_tts.pack(pady=(0, 10))

        ctk.CTkButton(left, text="💾 Salvar Frase", height=40, fg_color="#EEE", text_color="#333", hover_color="#DDD", command=self.salvar_frase).pack(fill="x", padx=20, pady=5)

        right = ctk.CTkFrame(self.main_area, fg_color="white", corner_radius=10)
        right.pack(side="right", fill="both", expand=True, padx=(10,0), pady=10)
        
        ctk.CTkLabel(right, text="📋 Mensagens Salvas", font=("Segoe UI", 14, "bold"), text_color="#333").pack(anchor="w", padx=20, pady=(20,10))
        self.scroll_msgs = ctk.CTkScrollableFrame(right, fg_color="transparent")
        self.scroll_msgs.pack(fill="both", expand=True, padx=10, pady=(0,20))
        self.atualizar_lista_msgs()

    def carregar_msgs(self):
        if os.path.exists(MSG_FILE):
            try: return json.load(open(MSG_FILE, 'r'))
            except: pass
        return []
    
    def carregar_config_locutor(self):
        if os.path.exists(CONFIG_LOCUTOR):
            try: 
                d = json.load(open(CONFIG_LOCUTOR, 'r'))
                return d.get("alert_sound", "")
            except: pass
        return ""

    def selecionar_som_alerta(self):
        p = filedialog.askopenfilename(parent=self, title="Selecione o som de alerta", filetypes=[("Audio", "*.mp3 *.wav")])
        if p:
            self.alert_sound_path = p
            self.lbl_sound.configure(text=f"🎵 Alerta: {os.path.basename(p)}")
            with open(CONFIG_LOCUTOR, 'w') as f:
                json.dump({"alert_sound": p}, f)

    def salvar_frase(self):
        txt = self.txt_tts.get("1.0", "end").strip()
        if not txt: return
        self.msgs_prontas.append(txt)
        with open(MSG_FILE, 'w') as f: json.dump(self.msgs_prontas, f)
        self.atualizar_lista_msgs()
        self.txt_tts.delete("1.0", "end")

    def atualizar_lista_msgs(self):
        for w in self.scroll_msgs.winfo_children(): w.destroy()
        for i, txt in enumerate(self.msgs_prontas):
            f = ctk.CTkFrame(self.scroll_msgs, fg_color="#F9F9F9", corner_radius=5)
            f.pack(fill="x", pady=5)
            lbl = ctk.CTkLabel(f, text=txt[:40] + ("..." if len(txt)>40 else ""), text_color="#555", anchor="w", font=("Segoe UI", 12))
            lbl.pack(side="left", padx=10, pady=10, fill="x", expand=True)
            ctk.CTkButton(f, text="▶", width=40, fg_color="#E3F2FD", text_color=VERITAS_BLUE, hover_color="#BBDEFB", command=lambda t=txt: self.falar_direto(t)).pack(side="right", padx=5)
            ctk.CTkButton(f, text="✏️", width=40, fg_color="transparent", text_color="#555", hover_color="#EEE", command=lambda t=txt: self.carregar_input(t)).pack(side="right")
            ctk.CTkButton(f, text="🗑", width=40, fg_color="transparent", text_color="red", hover_color="#FFEBEE", command=lambda x=i: self.deletar_msg(x)).pack(side="right")

    def carregar_input(self, txt):
        self.txt_tts.delete("1.0", "end")
        self.txt_tts.insert("1.0", txt)

    def deletar_msg(self, idx):
        del self.msgs_prontas[idx]
        with open(MSG_FILE, 'w') as f: json.dump(self.msgs_prontas, f)
        self.atualizar_lista_msgs()

    def falar_direto(self, txt):
        self.txt_tts.delete("1.0", "end")
        self.txt_tts.insert("1.0", txt)
        self.falar_texto()

    def falar_texto(self):
        txt = self.txt_tts.get("1.0", "end").strip()
        if not txt: return
        self.btn_falar.configure(state="disabled", text="GERANDO...")
        self.btn_stop.configure(state="normal")
        self.progress_tts.set(0)
        self.lbl_prog_tts.configure(text="Processando áudio...")
        try: self.volume_antes_tts = ControleVolume.get_volume()
        except: self.volume_antes_tts = 50
        try: vol_alvo = int(self.e_vol.get())
        except: vol_alvo = 80
        threading.Thread(target=self.thread_gerar_audio, args=(txt, vol_alvo), daemon=True).start()

    def thread_gerar_audio(self, texto, volume_windows):
        try:
            temp_voz = "temp_voz.mp3"
            arquivo_final = "anuncio_completo.mp3"
            ffmpeg_exe = FFMPEG_PATH
            if not os.path.exists(ffmpeg_exe): ffmpeg_exe = "ffmpeg"
            path_alerta = self.alert_sound_path if self.alert_sound_path and os.path.exists(self.alert_sound_path) else garantir_alerta_sonoro()
            VOZ = "pt-BR-FranciscaNeural" 
            async def _gen():
                comm = edge_tts.Communicate(texto, VOZ)
                await comm.save(temp_voz)
            asyncio.run(_gen())
            inputs = []
            filter_complex = ""
            idx = 0
            if path_alerta:
                inputs.extend(["-i", path_alerta])
                filter_complex += f"[{idx}:a]aformat=sample_rates=44100:channel_layouts=stereo,volume=0.3[alert];"
                idx += 1
            inputs.extend(["-i", temp_voz])
            filter_complex += f"[{idx}:a]aformat=sample_rates=44100:channel_layouts=stereo,volume=3.0[raw_voice];"
            idx += 1
            filter_complex += "[raw_voice]asplit=2[v1][v2];"
            if path_alerta: filter_complex += f"[alert][v1][v2]concat=n=3:v=0:a=1[out]"
            else: filter_complex += f"[v1][v2]concat=n=2:v=0:a=1[out]"
            cmd = [ffmpeg_exe, "-y"] + inputs + ["-filter_complex", filter_complex, "-map", "[out]", arquivo_final]
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(cmd, check=True, startupinfo=startupinfo, creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            try:
                dur_cmd = [ffmpeg_exe, "-i", arquivo_final, "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"]
                dur_res = subprocess.run(dur_cmd, capture_output=True, text=True, startupinfo=startupinfo, creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                duration = float(dur_res.stdout.strip())
            except: duration = 5.0
            self.after(0, lambda: self.iniciar_playback_com_progresso(arquivo_final, volume_windows, duration))
            try: os.remove(temp_voz)
            except: pass
        except Exception as e:
            print(f"Erro TTS: {e}")
            self.after(0, lambda: ModernPopUp(self, "Erro", f"Falha ao gerar áudio.\n{str(e)}"))
            self.after(0, self.reset_btn_falar)

    def iniciar_playback_com_progresso(self, arquivo, volume_windows, duration):
        ControleVolume.set_volume(volume_windows)
        self.player.tocar_anuncio(os.path.abspath(arquivo), 100)
        self.start_time = time.time()
        self.duration = duration
        self.em_anuncio = True
        self.update_progress()

    def update_progress(self):
        if not self.em_anuncio: return
        elapsed = time.time() - self.start_time
        if elapsed < self.duration:
            val = elapsed / self.duration
            self.progress_tts.set(val)
            self.lbl_prog_tts.configure(text=f"Tocando: {int(elapsed)}s / {int(self.duration)}s")
            self.after(100, self.update_progress)
        else:
            self.progress_tts.set(1.0)
            self.lbl_prog_tts.configure(text="Concluído")
            self.finalizar_anuncio()

    def parar_fala(self):
        if self.em_anuncio:
            self.em_anuncio = False
            self.player.parar_tts()
            self.lbl_prog_tts.configure(text="Interrompido pelo usuário")
            self.progress_tts.set(0)
            self.finalizar_anuncio()

    def finalizar_anuncio(self):
        ControleVolume.set_volume(self.volume_antes_tts)
        self.em_anuncio = False
        self.btn_falar.configure(state="normal", text="🔊 ANUNCIAR AGORA")
        self.btn_stop.configure(state="disabled")

    def render_donate(self):
        self.header("Apoie o Projeto", "Ajude a manter o Veritas Player gratuito e atualizado.")
        card = ctk.CTkFrame(self.main_area, fg_color="white", corner_radius=15)
        card.pack(fill="both", expand=True, padx=100, pady=20)
        ctk.CTkLabel(card, text="☕", font=("Arial", 60)).pack(pady=(40,10))
        ctk.CTkLabel(card, text="Gostou do Veritas Player?", font=("Segoe UI", 24, "bold"), text_color=VERITAS_BLUE).pack(pady=5)
        msg = ("Este software é desenvolvido por uma única pessoa (Gabriel Gouvêa). "
               "Se ele ajuda o seu negócio ou academia, considere fazer uma doação de qualquer valor. "
               "Isso ajuda a pagar o café e motiva novas atualizações com recursos como o Locutor AI!")
        ctk.CTkLabel(card, text=msg, font=("Segoe UI", 14), text_color="#555", wraplength=500, justify="center").pack(pady=20)
        box = ctk.CTkFrame(card, fg_color="#F5F7FA", corner_radius=10)
        box.pack(pady=20, padx=50, fill="x")
        ctk.CTkLabel(box, text="Chave PIX (E-mail):", font=("Segoe UI", 12, "bold"), text_color="#777").pack(pady=(15,5))
        self.pix_entry = ctk.CTkEntry(box, justify="center", font=("Consolas", 18, "bold"), width=300)
        self.pix_entry.pack(pady=5)
        self.pix_entry.insert(0, "gabriielgouvea@gmail.com")
        self.pix_entry.configure(state="readonly")
        ctk.CTkButton(box, text="Copiar Chave", fg_color=VERITAS_BLUE, command=self.copiar_pix).pack(pady=(5,15))
        ctk.CTkLabel(card, text="Muito obrigado pelo apoio! 💙", text_color="#AAA").pack(side="bottom", pady=20)

    def copiar_pix(self):
        self.clipboard_clear()
        self.clipboard_append("gabriielgouvea@gmail.com")
        ModernPopUp(self, "Copiado", "Chave PIX copiada para a área de transferência!")

    def render_config(self):
        self.header("Configuração", "Gerencie as pastas e a playlist ativa.")
        card = ctk.CTkFrame(self.main_area, fg_color="white", corner_radius=10)
        card.pack(fill="x", pady=10, ipady=15)
        ctk.CTkLabel(card, text="Pasta Raiz (Mídia)", font=("Segoe UI", 14, "bold"), text_color=VERITAS_BLUE).pack(anchor="w", padx=25, pady=(15,5))
        fr = ctk.CTkFrame(card, fg_color="transparent")
        fr.pack(fill="x", padx=25)
        self.lbl_path = ctk.CTkLabel(fr, text=self.player.pasta_treino or "...", font=("Consolas", 12), text_color="#555", fg_color="#F5F7FA", corner_radius=5, height=40, anchor="w")
        self.lbl_path.pack(side="left", fill="x", expand=True, padx=(0,10))
        ctk.CTkButton(fr, text="Alterar", command=self.select_root, width=100, fg_color=VERITAS_BLUE).pack(side="right")
        card2 = ctk.CTkFrame(self.main_area, fg_color="white", corner_radius=10)
        card2.pack(fill="x", pady=10, ipady=15)
        ctk.CTkLabel(card2, text="Playlist Ativa", font=("Segoe UI", 14, "bold"), text_color=VERITAS_BLUE).pack(anchor="w", padx=25, pady=(15,5))
        self.combo_play = ctk.CTkComboBox(card2, values=[], width=300, height=40, state="readonly", command=self.change_playlist)
        self.combo_play.pack(anchor="w", padx=25)
        self.refresh_config_data()

    def select_root(self):
        p = filedialog.askdirectory(parent=self)
        if p:
            self.player.pasta_treino = p
            with open(LAST_PATHS_FILE, "w") as f: f.write(p)
            self.player.scan_folders(); self.refresh_config_data()
            
    def refresh_config_data(self):
        self.lbl_path.configure(text=self.player.pasta_treino or "Selecione...")
        pl = sorted(list(self.player.playlist_folders.keys()))
        if "TODOS" in pl: pl.remove("TODOS"); pl.insert(0,"TODOS")
        if pl: 
            self.combo_play.configure(values=pl)
            self.combo_play.set(self.player.current_playlist_name)
        else: 
            self.combo_play.configure(values=["Vazio"])
            self.combo_play.set("Vazio")
            
    def change_playlist(self, c): 
        if c!="Vazio": self.player.change_playlist(c)

    def render_ad_list(self):
        self.header("Propagandas Ativas", "Gerencie os contratos em vigência.")
        self.contratos = carregar_db()
        scroll = ctk.CTkScrollableFrame(self.main_area, fg_color="transparent")
        scroll.pack(fill="both", expand=True, pady=10)
        if not self.contratos: 
            ctk.CTkLabel(scroll, text="Nenhum contrato ativo.", text_color="#999", font=("Segoe UI", 16)).pack(pady=50)
            return
        for i, c in enumerate(self.contratos):
            card = ctk.CTkFrame(scroll, fg_color="white", corner_radius=8)
            card.pack(fill="x", pady=5)
            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=15, pady=10)
            ctk.CTkLabel(top, text=f"{'🟢' if c.get('ativo', True) else '🔴'} {c['nome']}", font=("Segoe UI", 16, "bold"), text_color="#333").pack(side="left")
            ctk.CTkButton(top, text="Excluir", width=80, fg_color="#FFEBEE", text_color=VERITAS_DANGER, hover_color="#FFCDD2", command=lambda x=i: self.excluir_ad(x)).pack(side="right")
            ctk.CTkButton(top, text="Editar", width=80, fg_color="#E3F2FD", text_color=VERITAS_BLUE, hover_color="#BBDEFB", command=lambda x=i: self.editar_ad(x)).pack(side="right", padx=10)
            det = ctk.CTkFrame(card, fg_color="#FAFAFA", corner_radius=6)
            det.pack(fill="x", padx=15, pady=(0,15))
            ctk.CTkLabel(det, text=f"👤 {c.get('autorizado','-')} | 📅 {c.get('inicio','-')} - {c.get('fim','-')} | {c.get('tipo', 'VIDEO')}", text_color="#666").pack(anchor="w", padx=10, pady=5)

    def excluir_ad(self, idx):
        if ModernPopUp(self, "Excluir", "Tem certeza?", "yesno").resultado: 
            del self.contratos[idx]
            salvar_db(self.contratos)
            self.show_view("list")
            
    def editar_ad(self, idx): 
        self.editando_id = self.contratos[idx]["id"]
        self.show_view("create")