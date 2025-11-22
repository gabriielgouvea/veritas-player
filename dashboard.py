# dashboard.py (Versão 10.6 - Fix Edição Completo)
import customtkinter as ctk
import os
import json
import time
from datetime import datetime, timedelta
from tkinter import filedialog
from config import *
from utils import ModernPopUp, ToolTip, carregar_db, salvar_db
from downloader import YoutubeDownloader

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
        self.editando_id = None; self.l_hours = []; self.l_dates = []; self.vid_path = ""

        # SIDEBAR
        self.sidebar = ctk.CTkFrame(self, width=260, corner_radius=0, fg_color="white")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        
        ctk.CTkLabel(self.sidebar, text="VERITAS\nPLAYER", font=("Arial Black", 24), text_color=VERITAS_BLUE).pack(pady=40)
        
        self.btn_dict = {}
        self.create_menu_btn("🏠  Configuração Inicial", "config")
        self.create_menu_btn("📋  Propagandas Ativas", "list")
        self.create_menu_btn("➕  Nova Propaganda", "create")
        
        ctk.CTkFrame(self.sidebar, height=2, fg_color="#F0F2F5").pack(fill="x", padx=20, pady=10)
        self.create_menu_btn("⬇️  Baixar do YouTube", "download")
        ctk.CTkFrame(self.sidebar, height=2, fg_color="#F0F2F5").pack(fill="x", padx=20, pady=10)
        
        ctk.CTkButton(self.sidebar, text="🔙  Voltar ao Player", command=self.destroy, 
                      fg_color="#FFF", text_color=VERITAS_BLUE, hover_color="#F0F2F5", 
                      font=("Segoe UI", 14, "bold"), height=50, anchor="w").pack(fill="x", padx=10)

        ctk.CTkLabel(self.sidebar, text="v10.6 - Fix Edição", text_color="#AAA", font=("Segoe UI", 10, "bold")).pack(side="bottom", pady=(0, 10))
        ctk.CTkLabel(self.sidebar, text="Desenvolvido por Gabriel Gouvêa", text_color="#CCC", font=("Segoe UI", 9)).pack(side="bottom", pady=5)

        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        self.show_view("config")

    def create_menu_btn(self, text, name):
        btn = ctk.CTkButton(self.sidebar, text=f"  {text}", command=lambda: self.show_view(name), fg_color="transparent", text_color="#555", anchor="w", font=("Segoe UI", 14, "bold"), height=50, hover_color="#F0F2F5")
        btn.pack(fill="x", padx=10, pady=2)
        self.btn_dict[name] = btn

    def show_view(self, view_name):
        if view_name == "download": YoutubeDownloader(self, self.player.pasta_treino); return
        for n, b in self.btn_dict.items(): 
            if n == view_name: b.configure(fg_color="#E3F2FD", text_color=VERITAS_BLUE)
            else: b.configure(fg_color="transparent", text_color="#555")
        for widget in self.main_area.winfo_children(): widget.destroy()
        if view_name == "config": self.render_config()
        elif view_name == "list": self.render_ad_list()
        elif view_name == "create": self.render_ad_create()

    # VIEW CONFIG
    def render_config(self):
        self.header("Configuração", "Gerencie as pastas e a playlist ativa.")
        card = ctk.CTkFrame(self.main_area, fg_color="white", corner_radius=10); card.pack(fill="x", pady=10, ipady=15)
        ctk.CTkLabel(card, text="Pasta Raiz (Mídia)", font=("Segoe UI", 14, "bold"), text_color=VERITAS_BLUE).pack(anchor="w", padx=25, pady=(15,5))
        fr = ctk.CTkFrame(card, fg_color="transparent"); fr.pack(fill="x", padx=25)
        self.lbl_path = ctk.CTkLabel(fr, text=self.player.pasta_treino or "...", font=("Consolas", 12), text_color="#555", fg_color="#F5F7FA", corner_radius=5, height=40, anchor="w"); self.lbl_path.pack(side="left", fill="x", expand=True, padx=(0,10))
        ctk.CTkButton(fr, text="Alterar", command=self.select_root, width=100, fg_color=VERITAS_BLUE).pack(side="right")
        card2 = ctk.CTkFrame(self.main_area, fg_color="white", corner_radius=10); card2.pack(fill="x", pady=10, ipady=15)
        ctk.CTkLabel(card2, text="Playlist Ativa", font=("Segoe UI", 14, "bold"), text_color=VERITAS_BLUE).pack(anchor="w", padx=25, pady=(15,5))
        self.combo_play = ctk.CTkComboBox(card2, values=[], width=300, height=40, state="readonly", command=self.change_playlist); self.combo_play.pack(anchor="w", padx=25)
        self.refresh_config_data()

    def select_root(self):
        p = filedialog.askdirectory(parent=self)
        if p:
            self.player.pasta_treino = p; 
            with open(LAST_PATHS_FILE, "w") as f: f.write(p)
            self.player.scan_folders(); self.refresh_config_data()
    def refresh_config_data(self):
        self.lbl_path.configure(text=self.player.pasta_treino or "Selecione...")
        pl = sorted(list(self.player.playlist_folders.keys()))
        if "TODOS" in pl: pl.remove("TODOS"); pl.insert(0,"TODOS")
        if pl: self.combo_play.configure(values=pl); self.combo_play.set(self.player.current_playlist_name)
        else: self.combo_play.configure(values=["Vazio"]); self.combo_play.set("Vazio")
    def change_playlist(self, c): 
        if c!="Vazio": self.player.change_playlist(c)

    # VIEW LISTA
    def render_ad_list(self):
        self.header("Propagandas Ativas", "Gerencie os contratos em vigência."); self.contratos = carregar_db()
        scroll = ctk.CTkScrollableFrame(self.main_area, fg_color="transparent"); scroll.pack(fill="both", expand=True, pady=10)
        if not self.contratos: ctk.CTkLabel(scroll, text="Nenhum contrato ativo.", text_color="#999", font=("Segoe UI", 16)).pack(pady=50); return
        for i, c in enumerate(self.contratos):
            card = ctk.CTkFrame(scroll, fg_color="white", corner_radius=8); card.pack(fill="x", pady=5)
            top = ctk.CTkFrame(card, fg_color="transparent"); top.pack(fill="x", padx=15, pady=10)
            ctk.CTkLabel(top, text=f"{'🟢' if c.get('ativo', True) else '🔴'} {c['nome']}", font=("Segoe UI", 16, "bold"), text_color="#333").pack(side="left")
            ctk.CTkButton(top, text="Excluir", width=80, fg_color="#FFEBEE", text_color=VERITAS_DANGER, hover_color="#FFCDD2", command=lambda x=i: self.excluir_ad(x)).pack(side="right")
            ctk.CTkButton(top, text="Editar", width=80, fg_color="#E3F2FD", text_color=VERITAS_BLUE, hover_color="#BBDEFB", command=lambda x=i: self.editar_ad(x)).pack(side="right", padx=10)
            det = ctk.CTkFrame(card, fg_color="#FAFAFA", corner_radius=6); det.pack(fill="x", padx=15, pady=(0,15))
            ctk.CTkLabel(det, text=f"👤 {c.get('autorizado','-')} | 📅 {c.get('inicio','-')} - {c.get('fim','-')}", text_color="#666").pack(anchor="w", padx=10, pady=5)

    def excluir_ad(self, idx):
        if ModernPopUp(self, "Excluir", "Tem certeza?", "yesno").resultado: del self.contratos[idx]; salvar_db(self.contratos); self.show_view("list")
    def editar_ad(self, idx): self.editando_id = self.contratos[idx]["id"]; self.show_view("create")

    # VIEW CREATE (CORRIGIDO)
    def render_ad_create(self):
        # Busca robusta: Converte ambos para string para garantir que ache o contrato
        d = {}
        if self.editando_id:
            d = next((c for c in self.contratos if str(c["id"]) == str(self.editando_id)), {})
        
        self.header("Editar Propaganda" if self.editando_id else "Nova Propaganda", "Preencha os dados.")
        f = ctk.CTkScrollableFrame(self.main_area, fg_color="transparent"); f.pack(fill="both", expand=True)
        
        self.card_form(f, "Dados Gerais")
        fr = ctk.CTkFrame(self.last_card, fg_color="transparent"); fr.pack(fill="x", padx=20, pady=10)
        
        self.inp_grid(fr, "Nome:", 0, 0)
        self.e_nome = ctk.CTkEntry(fr, height=40)
        self.e_nome.grid(row=1, column=0, sticky="ew", padx=(0,10))
        
        self.inp_grid(fr, "Autorizado:", 0, 1)
        self.e_autor = ctk.CTkComboBox(fr, values=["Basa","Juju","Betão","Fabi","Gerência"], height=40, button_color=VERITAS_BLUE)
        self.e_autor.grid(row=1, column=1, sticky="ew")
        
        fr.columnconfigure(0, weight=1); fr.columnconfigure(1, weight=1)
        
        ctk.CTkLabel(self.last_card, text="Arquivo de Vídeo:", text_color="#555").pack(anchor="w", padx=20, pady=(10,0))
        fv = ctk.CTkFrame(self.last_card, fg_color="#F5F7FA", height=50); fv.pack(fill="x", padx=20, pady=5)
        self.lbl_vid = ctk.CTkLabel(fv, text="Nenhum selecionado", text_color="#777"); self.lbl_vid.pack(side="left", padx=15)
        ctk.CTkButton(fv, text="Selecionar", command=self.sel_vid, fg_color=VERITAS_BLUE, width=100).pack(side="right", padx=10, pady=5)

        self.card_form(f, "Vigência")
        self.tabs = ctk.CTkTabview(self.last_card, height=250, fg_color="transparent", segmented_button_selected_color=VERITAS_BLUE)
        self.tabs.pack(fill="x", padx=10)
        self.tabs.add("PERÍODO"); self.tabs.add("DATA ÚNICA")
        
        t1 = self.tabs.tab("PERÍODO"); fd = ctk.CTkFrame(t1, fg_color="transparent"); fd.pack(fill="x", pady=10)
        ctk.CTkLabel(fd, text="Início:", text_color="#555").pack(side="left")
        self.e_ini = ctk.CTkEntry(fd, width=120, placeholder_text="DD/MM/AAAA"); self.e_ini.pack(side="left", padx=(5,20))
        self.e_ini.insert(0, datetime.now().strftime("%d/%m/%Y")); self.e_ini.bind("<KeyRelease>", self.smart_date)
        
        ctk.CTkLabel(fd, text="Fim:", text_color="#555").pack(side="left")
        self.e_fim = ctk.CTkEntry(fd, width=120, placeholder_text="DD/MM/AAAA"); self.e_fim.pack(side="left", padx=(5,20))
        self.e_fim.bind("<KeyRelease>", self.smart_date)
        
        self.e_dias = ctk.CTkEntry(fd, width=80, state="disabled", fg_color="#EEE", text_color="#333"); self.e_dias.pack(side="left")
        
        fc = ctk.CTkFrame(t1, fg_color="transparent"); fc.pack(fill="x", pady=5)
        self.v_indet = ctk.BooleanVar(); self.v_hoje = ctk.BooleanVar()
        self.chk_indet = ctk.CTkCheckBox(fc, text="Indeterminado", variable=self.v_indet, command=self.logic_indet, text_color="#333", checkmark_color=VERITAS_BLUE); self.chk_indet.pack(side="left", padx=20)
        self.chk_hoje = ctk.CTkCheckBox(fc, text="SOMENTE HOJE", variable=self.v_hoje, command=self.logic_hoje, text_color=VERITAS_DANGER, checkmark_color=VERITAS_DANGER); self.chk_hoje.pack(side="left")
        
        fs = ctk.CTkFrame(t1, fg_color="transparent"); fs.pack(fill="x"); self.d_vars = {}; self.chk_dias = []
        for d_name in ["seg","ter","qua","qui","sex","sab","dom"]: 
            v = ctk.BooleanVar(value=True); self.d_vars[d_name]=v
            c = ctk.CTkCheckBox(fs, text=d_name.upper(), variable=v, width=60, text_color="#555", checkmark_color=VERITAS_BLUE, command=self.logic_sem)
            c.pack(side="left", padx=5); self.chk_dias.append(c)
            
        t2 = self.tabs.tab("DATA ÚNICA"); fdt = ctk.CTkFrame(t2, fg_color="transparent"); fdt.pack(fill="x")
        self.e_dt = ctk.CTkEntry(fdt, placeholder_text="DD/MM/AAAA", width=150); self.e_dt.pack(side="left")
        self.e_dt.bind("<KeyRelease>", self.masc_dt); self.e_dt.bind("<Return>", self.add_dt)
        ctk.CTkButton(fdt, text="+", width=40, command=self.add_dt, fg_color=VERITAS_BLUE).pack(side="left", padx=5)
        self.fr_dt = ctk.CTkFrame(t2, fg_color="#F0F0F0"); self.fr_dt.pack(fill="both", expand=True, pady=10); self.l_dates = []

        self.card_form(f, "Horários")
        fh = ctk.CTkFrame(self.last_card, fg_color="transparent"); fh.pack(fill="x", padx=20, pady=10)
        self.e_hr = ctk.CTkEntry(fh, placeholder_text="HH:MM", width=100); self.e_hr.pack(side="left")
        self.e_hr.bind("<KeyRelease>", self.masc_hr); self.e_hr.bind("<Return>", self.add_hr)
        ctk.CTkButton(fh, text="+", width=40, command=self.add_hr, fg_color=VERITAS_BLUE).pack(side="left", padx=5)
        self.fr_hr = ctk.CTkFrame(self.last_card, fg_color="#F0F0F0", height=50); self.fr_hr.pack(fill="x", padx=20, pady=5); self.l_hours = []

        fb = ctk.CTkFrame(f, fg_color="transparent"); fb.pack(fill="x", pady=30)
        if self.editando_id: ctk.CTkButton(fb, text="CANCELAR", fg_color="#AAA", width=150, command=lambda: self.show_view("list")).pack(side="left")
        ctk.CTkButton(fb, text="SALVAR", fg_color=VERITAS_BLUE, width=200, height=50, font=("Segoe UI", 14, "bold"), command=self.salvar).pack(side="right")
        
        self.smart_date()
        if self.editando_id and d: self.preencher(d)

    def preencher(self, d):
        # NOME
        self.e_nome.delete(0, "end")
        self.e_nome.insert(0, d.get("nome",""))
        
        # AUTORIZADO
        self.e_autor.set(d.get("autorizado",""))
        
        # VIDEO
        self.vid_path = d.get("video","")
        if self.vid_path: 
            self.lbl_vid.configure(text=os.path.basename(self.vid_path))
        
        # HORARIOS
        self.l_hours = d.get("horarios",[])[:]
        self.render_tags(self.fr_hr, self.l_hours, self.rm_hr)
        
        # MODOS E DATAS
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
            ini = datetime.strptime(self.e_ini.get(), "%d/%m/%Y").date(); hoje = datetime.now().date()
            if ini > hoje: self.v_hoje.set(False); self.chk_hoje.configure(state="disabled")
            else: self.chk_hoje.configure(state="normal")
            if not self.v_indet.get():
                fim = datetime.strptime(self.e_fim.get(), "%d/%m/%Y").date()
                if fim < ini: self.e_dias.configure(state="normal"); self.e_dias.delete(0,"end"); self.e_dias.insert(0,"Erro"); self.e_dias.configure(state="disabled")
                else: self.e_dias.configure(state="normal"); self.e_dias.delete(0,"end"); self.e_dias.insert(0,f"{(fim-ini).days+1} Dias"); self.e_dias.configure(state="disabled")
        except: pass
    def logic_hoje(self):
        if self.v_hoje.get():
            h = datetime.now().strftime("%d/%m/%Y"); self.e_ini.delete(0,"end"); self.e_ini.insert(0,h); self.e_fim.delete(0,"end"); self.e_fim.insert(0,h); self.e_fim.configure(state="normal")
            self.v_indet.set(False); self.chk_indet.configure(state="normal"); self.smart_date()
        else: self.smart_date()
    def logic_indet(self):
        if self.v_indet.get(): self.e_fim.delete(0,"end"); self.e_fim.insert(0,"----------"); self.e_fim.configure(state="disabled", fg_color="#EEE"); self.v_hoje.set(False); self.chk_hoje.configure(state="disabled")
        else: self.e_fim.configure(state="normal", fg_color="white"); self.e_fim.delete(0,"end"); self.chk_hoje.configure(state="normal")
    def logic_sem(self):
        if self.v_hoje.get(): self.v_hoje.set(False); self.logic_hoje()
    
    def header(self, t, s): ctk.CTkLabel(self.main_area, text=t, font=("Segoe UI", 26, "bold"), text_color=VERITAS_TEXT).pack(anchor="w"); ctk.CTkLabel(self.main_area, text=s, font=("Segoe UI", 14), text_color="#777").pack(anchor="w", pady=(0,20))
    def card_form(self, p, t): self.last_card = ctk.CTkFrame(p, fg_color="white", corner_radius=10); self.last_card.pack(fill="x", pady=10); ctk.CTkLabel(self.last_card, text=t, font=("Segoe UI", 14, "bold"), text_color=VERITAS_BLUE).pack(anchor="w", padx=20, pady=(15,5)); ctk.CTkFrame(self.last_card, height=1, fg_color="#EEE").pack(fill="x", padx=20, pady=(0,10))
    def inp_grid(self, p, t, r, c): ctk.CTkLabel(p, text=t, text_color="#555").grid(row=r, column=c, sticky="w", padx=(0,10), pady=(0,5))
    def masc_dt(self, e): self._m(e.widget, 10)
    def masc_hr(self, e): self._m(e.widget, 5)
    def _m(self, w, l): 
        t=w.get().replace("/","").replace(":",""); 
        if not t.isdigit(): return
        w.delete(0,"end"); w.insert(0, (t[:2]+"/"+t[2:] if l==10 else t[:2]+":"+t[2:]) if len(t)>2 else t)
    def add_hr(self, e=None): self._tag(self.e_hr, self.l_hours, self.fr_hr, self.rm_hr, 5)
    def add_dt(self, e=None): self._tag(self.e_dt, self.l_dates, self.fr_dt, self.rm_dt, 10)
    def _tag(self, e, l, p, cb, ln):
        v = e.get()
        if len(v)==ln and v not in l: l.append(v); l.sort(); self.render_tags(p, l, cb); e.delete(0,"end")
    def rm_hr(self, v): self.l_hours.remove(v); self.render_tags(self.fr_hr, self.l_hours, self.rm_hr)
    def rm_dt(self, v): self.l_dates.remove(v); self.render_tags(self.fr_dt, self.l_dates, self.rm_dt)
    def render_tags(self, p, l, cb):
        for w in p.winfo_children(): w.destroy()
        for v in l: f=ctk.CTkFrame(p, fg_color="#E3F2FD", corner_radius=5); f.pack(side="left", padx=5, pady=5); ctk.CTkLabel(f, text=v, text_color=VERITAS_BLUE).pack(side="left", padx=5); ctk.CTkButton(f, text="x", width=15, fg_color="transparent", text_color="red", command=lambda x=v: cb(x)).pack(side="left")
    def sel_vid(self):
        p = filedialog.askopenfilename(parent=self, filetypes=[("Video", "*.mp4 *.mkv")])
        if p: self.vid_path=p; self.lbl_vid.configure(text=os.path.basename(p))
    
    def salvar(self):
        if not self.vid_path or not self.l_hours: ModernPopUp(self, "Erro", "Preencha vídeo e horários!"); return
        c = {
            "id": self.editando_id if self.editando_id else int(time.time()), "nome": self.e_nome.get() or "Sem Nome", "autorizado": self.e_autor.get(), "video": self.vid_path, "ativo": True,
            "modo": "DATAS ESPECÍFICAS" if self.tabs.get()=="DATA ÚNICA" else "POR PERÍODO", "horarios": self.l_hours, "inicio": self.e_ini.get(),
            "fim": "INDETERMINADO" if self.v_indet.get() else self.e_fim.get(), "dias": [d for d, v in self.d_vars.items() if v.get()],
            "somente_hoje": self.v_hoje.get(), "datas_especificas": self.l_dates, "execucoes_hoje": []
        }
        if self.editando_id:
            for i, x in enumerate(self.contratos):
                # Comparação segura aqui também
                if str(x["id"])==str(self.editando_id): c["execucoes_hoje"]=x.get("execucoes_hoje",[]); self.contratos[i]=c; break
        else: self.contratos.append(c)
        salvar_db(self.contratos); self.editando_id=None; self.show_view("list"); ModernPopUp(self, "Sucesso", "Salvo!")