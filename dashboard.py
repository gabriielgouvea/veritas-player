# dashboard.py
import customtkinter as ctk
import os
import json
import time  # <--- FALTAVA ISSO AQUI
from datetime import datetime, timedelta
from tkinter import filedialog
from config import *
from utils import ModernPopUp, ToolTip, carregar_db, salvar_db

class DashboardWindow(ctk.CTkToplevel):
    def __init__(self, parent, player):
        super().__init__(parent)
        self.title("Veritas - Painel de Controle")
        self.configure(fg_color=VERITAS_BG_DASH)
        self.player = player
        
        # Configuração Janela
        self.geometry("1200x800")
        self.after(100, lambda: self.state("zoomed"))
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- ESTADOS & DADOS ---
        self.contratos = carregar_db()
        self.editando_id = None
        self.l_hours = []
        self.l_dates = []
        self.vid_path = ""

        # --- SIDEBAR (MENU LATERAL) ---
        self.sidebar = ctk.CTkFrame(self, width=260, corner_radius=0, fg_color="white")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        
        # LOGO
        ctk.CTkLabel(self.sidebar, text="VERITAS\nPLAYER", font=("Arial Black", 24), text_color=VERITAS_BLUE).pack(pady=40)
        
        self.btn_dict = {}
        self.create_menu_btn("🏠  Configuração Inicial", "config")
        self.create_menu_btn("📋  Propagandas Ativas", "list")
        self.create_menu_btn("➕  Nova Propaganda", "create")
        
        ctk.CTkFrame(self.sidebar, height=2, fg_color="#F0F2F5").pack(fill="x", padx=20, pady=20)
        
        ctk.CTkButton(self.sidebar, text="🔙  Voltar ao Player", command=self.destroy, 
                      fg_color="#FFF", text_color=VERITAS_BLUE, hover_color="#F0F2F5", 
                      font=("Segoe UI", 14, "bold"), height=50, anchor="w").pack(fill="x", padx=10)

        ctk.CTkLabel(self.sidebar, text="v10.1 - Stable", text_color="#AAA", font=("Segoe UI", 10, "bold")).pack(side="bottom", pady=(0, 10))
        ctk.CTkLabel(self.sidebar, text="Desenvolvido por Gabriel Gouvêa\ne seus parceiros Gemini e Chat GPT", 
                     text_color="#CCC", font=("Segoe UI", 9), justify="center").pack(side="bottom", pady=10)

        # --- ÁREA PRINCIPAL ---
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        
        # Inicia na Home
        self.show_view("config")

    def create_menu_btn(self, text, name):
        btn = ctk.CTkButton(self.sidebar, text=f"  {text}", command=lambda: self.show_view(name),
                            fg_color="transparent", text_color="#555", anchor="w", 
                            font=("Segoe UI", 14, "bold"), height=50, hover_color="#F0F2F5")
        btn.pack(fill="x", padx=10, pady=2)
        self.btn_dict[name] = btn

    def show_view(self, view_name):
        # Reset Botoes
        for n, b in self.btn_dict.items():
            if n == view_name: b.configure(fg_color="#E3F2FD", text_color=VERITAS_BLUE)
            else: b.configure(fg_color="transparent", text_color="#555")

        # Limpa Area Principal
        for widget in self.main_area.winfo_children(): widget.destroy()

        if view_name == "config": self.render_config()
        elif view_name == "list": self.render_ad_list()
        elif view_name == "create": self.render_ad_create()

    # ==================================================
    # VIEW 1: CONFIGURAÇÃO
    # ==================================================
    def render_config(self):
        self.header("Configuração de Reprodução", "Gerencie as pastas e a playlist ativa.")
        
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
        if pl: self.combo_play.configure(values=pl); self.combo_play.set(self.player.current_playlist_name)
        else: self.combo_play.configure(values=["Vazio"]); self.combo_play.set("Vazio")

    def change_playlist(self, c): 
        if c!="Vazio": self.player.change_playlist(c)

    # ==================================================
    # VIEW 2: LISTA
    # ==================================================
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
            
            status_icon = "🟢" if c.get("ativo", True) else "🔴"
            ctk.CTkLabel(top, text=f"{status_icon} {c['nome']}", font=("Segoe UI", 16, "bold"), text_color="#333").pack(side="left")
            
            ctk.CTkButton(top, text="Excluir", width=80, fg_color="#FFEBEE", text_color=VERITAS_DANGER, hover_color="#FFCDD2", command=lambda x=i: self.excluir_ad(x)).pack(side="right")
            ctk.CTkButton(top, text="Editar", width=80, fg_color="#E3F2FD", text_color=VERITAS_BLUE, hover_color="#BBDEFB", command=lambda x=i: self.editar_ad(x)).pack(side="right", padx=10)

            det = ctk.CTkFrame(card, fg_color="#FAFAFA", corner_radius=6)
            det.pack(fill="x", padx=15, pady=(0,15))
            
            info_txt = f"👤 Autorizado: {c['autorizado']}   |   📅 Vigência: {c['inicio']} até {c['fim']}"
            if c.get("somente_hoje"): info_txt += "  (🚨 HOJE)"
            elif c.get("fim") == "INDETERMINADO": info_txt += "  (♾️ Indeterminado)"
            
            ctk.CTkLabel(det, text=info_txt, text_color="#666", font=("Segoe UI", 12)).pack(anchor="w", padx=10, pady=5)
            
            h_txt = "  ".join([f"⏰ {h}" for h in c["horarios"]])
            ctk.CTkLabel(det, text=f"Disparos: {h_txt}", text_color=VERITAS_BLUE, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=(0,5))

    def excluir_ad(self, idx):
        pop = ModernPopUp(self, "Excluir", "Tem certeza?", "yesno")
        if pop.resultado:
            del self.contratos[idx]
            salvar_db(self.contratos)
            self.show_view("list")

    def editar_ad(self, idx):
        self.editando_id = self.contratos[idx]["id"]
        self.show_view("create")

    # ==================================================
    # VIEW 3: NOVA PROPAGANDA
    # ==================================================
    def render_ad_create(self):
        dados = {}
        if self.editando_id:
            dados = next((c for c in self.contratos if c["id"] == self.editando_id), {})
            self.header("Editar Propaganda", f"Editando: {dados.get('nome')}")
        else:
            self.header("Nova Propaganda", "Cadastre um novo contrato de publicidade.")

        form_scroll = ctk.CTkScrollableFrame(self.main_area, fg_color="transparent")
        form_scroll.pack(fill="both", expand=True)

        # -- DADOS GERAIS --
        self.card_form(form_scroll, "Dados Gerais")
        
        fr_grid = ctk.CTkFrame(self.last_card, fg_color="transparent")
        fr_grid.pack(fill="x", padx=20, pady=10)
        
        self.inp_grid(fr_grid, "Nome da Campanha:", 0, 0)
        self.e_nome = ctk.CTkEntry(fr_grid, height=40); self.e_nome.grid(row=1, column=0, sticky="ew", padx=(0,10))
        
        self.inp_grid(fr_grid, "Autorizado por:", 0, 1)
        self.e_autor = ctk.CTkComboBox(fr_grid, values=["Basa","Juju","Betão","Fabi","Gerência"], height=40, button_color=VERITAS_BLUE)
        self.e_autor.grid(row=1, column=1, sticky="ew")
        fr_grid.columnconfigure(0, weight=1); fr_grid.columnconfigure(1, weight=1)

        ctk.CTkLabel(self.last_card, text="Arquivo de Vídeo:", text_color="#555").pack(anchor="w", padx=20, pady=(10,0))
        fr_vid = ctk.CTkFrame(self.last_card, fg_color="#F5F7FA", height=50)
        fr_vid.pack(fill="x", padx=20, pady=5)
        self.lbl_vid = ctk.CTkLabel(fr_vid, text="Nenhum selecionado", text_color="#777")
        self.lbl_vid.pack(side="left", padx=15)
        ctk.CTkButton(fr_vid, text="Selecionar Arquivo", command=self.sel_vid, fg_color=VERITAS_BLUE, width=150).pack(side="right", padx=10, pady=5)

        # -- VIGÊNCIA E REGRAS --
        self.card_form(form_scroll, "Vigência e Regras")
        
        self.tabs = ctk.CTkTabview(self.last_card, height=250, fg_color="transparent", text_color="#333", segmented_button_selected_color=VERITAS_BLUE)
        self.tabs.pack(fill="x", padx=10)
        self.tabs.add("PERÍODO"); self.tabs.add("DATA ÚNICA")
        
        # Aba Periodo
        t1 = self.tabs.tab("PERÍODO")
        fr_d = ctk.CTkFrame(t1, fg_color="transparent")
        fr_d.pack(fill="x", pady=10)
        
        ctk.CTkLabel(fr_d, text="Início:", text_color="#555").pack(side="left")
        self.e_ini = ctk.CTkEntry(fr_d, width=120, placeholder_text="DD/MM/AAAA"); self.e_ini.pack(side="left", padx=(5,20))
        self.e_ini.insert(0, datetime.now().strftime("%d/%m/%Y")); self.e_ini.bind("<KeyRelease>", self.smart_date_logic)
        
        ctk.CTkLabel(fr_d, text="Fim:", text_color="#555").pack(side="left")
        self.e_fim = ctk.CTkEntry(fr_d, width=120, placeholder_text="DD/MM/AAAA"); self.e_fim.pack(side="left", padx=(5,20))
        self.e_fim.bind("<KeyRelease>", self.smart_date_logic)

        ctk.CTkLabel(fr_d, text="Duração:", text_color="#777").pack(side="left")
        self.e_dias = ctk.CTkEntry(fr_d, width=80, state="disabled", fg_color="#EEE", text_color="#333"); self.e_dias.pack(side="left", padx=(5,0))
        
        # Checkboxes
        fr_chk = ctk.CTkFrame(t1, fg_color="transparent"); fr_chk.pack(fill="x", pady=5)
        self.v_indet = ctk.BooleanVar(value=False); self.v_hoje = ctk.BooleanVar(value=False)
        
        self.chk_indet = ctk.CTkCheckBox(fr_chk, text="Indeterminado (Sem fim)", variable=self.v_indet, command=self.logic_indet, text_color="#333", checkmark_color=VERITAS_BLUE)
        self.chk_indet.pack(side="left", padx=20)
        
        self.chk_hoje = ctk.CTkCheckBox(fr_chk, text="SOMENTE HOJE (Prioridade)", variable=self.v_hoje, command=self.logic_hoje, text_color=VERITAS_DANGER, checkmark_color=VERITAS_DANGER)
        self.chk_hoje.pack(side="left")
        
        ctk.CTkLabel(t1, text="Dias de Exibição:", text_color="#555", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=5, pady=(10,5))
        fr_sem = ctk.CTkFrame(t1, fg_color="transparent"); fr_sem.pack(fill="x")
        self.d_vars = {}; self.chk_dias_widgets = []
        for d in ["seg","ter","qua","qui","sex","sab","dom"]:
            v = ctk.BooleanVar(value=True); self.d_vars[d]=v
            chk = ctk.CTkCheckBox(fr_sem, text=d.upper(), variable=v, width=60, text_color="#555", checkmark_color=VERITAS_BLUE, command=self.logic_dias_semana)
            chk.pack(side="left", padx=5)
            self.chk_dias_widgets.append(chk)

        # Aba Data Unica
        t2 = self.tabs.tab("DATA ÚNICA")
        ctk.CTkLabel(t2, text="Adicionar Data Específica:", text_color="#555").pack(anchor="w", pady=5)
        fr_dt_inp = ctk.CTkFrame(t2, fg_color="transparent"); fr_dt_inp.pack(fill="x")
        self.e_dt_tag = ctk.CTkEntry(fr_dt_inp, placeholder_text="DD/MM/AAAA", width=150)
        self.e_dt_tag.pack(side="left"); self.e_dt_tag.bind("<KeyRelease>", self.mascara_data); self.e_dt_tag.bind("<Return>", self.add_dt)
        ctk.CTkButton(fr_dt_inp, text="+", width=40, command=self.add_dt, fg_color=VERITAS_BLUE).pack(side="left", padx=5)
        self.fr_tags_dt = ctk.CTkFrame(t2, fg_color="#F0F0F0"); self.fr_tags_dt.pack(fill="both", expand=True, pady=10)
        self.l_dates = []

        # -- HORÁRIOS --
        self.card_form(form_scroll, "Horários de Exibição")
        fr_h = ctk.CTkFrame(self.last_card, fg_color="transparent"); fr_h.pack(fill="x", padx=20, pady=10)
        self.e_hora = ctk.CTkEntry(fr_h, placeholder_text="HH:MM", width=100)
        self.e_hora.pack(side="left"); self.e_hora.bind("<KeyRelease>", self.mascara_hora); self.e_hora.bind("<Return>", self.add_hr)
        ctk.CTkButton(fr_h, text="Adicionar Horário", command=self.add_hr, fg_color=VERITAS_BLUE).pack(side="left", padx=10)
        self.fr_tags_hr = ctk.CTkFrame(self.last_card, fg_color="#F0F0F0", height=50); self.fr_tags_hr.pack(fill="x", padx=20, pady=5)
        self.l_hours = []

        # BOTÕES FINAIS
        fr_b = ctk.CTkFrame(form_scroll, fg_color="transparent"); fr_b.pack(fill="x", pady=30)
        if self.editando_id:
            ctk.CTkButton(fr_b, text="CANCELAR", fg_color="#AAA", hover_color="#999", width=150, command=lambda: self.show_view("list")).pack(side="left")
        ctk.CTkButton(fr_b, text="SALVAR E ATIVAR", fg_color=VERITAS_BLUE, width=200, height=50, font=("Segoe UI", 14, "bold"), command=self.salvar).pack(side="right")

        # INICIA LOGICA
        self.smart_date_logic() 
        if self.editando_id: self.preencher_form(dados)

    # --- LÓGICA INTELIGENTE DE DATAS ---
    def smart_date_logic(self, e=None):
        if e: self.mascara_data(e)
        hoje = datetime.now().date()
        
        try:
            ini = datetime.strptime(self.e_ini.get(), "%d/%m/%Y").date()
            if ini > hoje:
                self.v_hoje.set(False); self.chk_hoje.configure(state="disabled", text="Somente Hoje (Inválido)")
                for chk in self.chk_dias_widgets: chk.configure(state="normal")
            else:
                self.chk_hoje.configure(state="normal", text="SOMENTE HOJE (Prioridade)")

            if not self.v_indet.get():
                fim_txt = self.e_fim.get()
                if len(fim_txt) == 10:
                    fim = datetime.strptime(fim_txt, "%d/%m/%Y").date()
                    if fim < ini: self.set_dias("Erro")
                    else: self.set_dias(f"{(fim - ini).days + 1} Dias")
                else: self.set_dias("...")
        except: pass

    def set_dias(self, txt):
        self.e_dias.configure(state="normal"); self.e_dias.delete(0, "end"); self.e_dias.insert(0, txt); self.e_dias.configure(state="disabled")

    def logic_hoje(self):
        if self.v_hoje.get():
            hoje_str = datetime.now().strftime("%d/%m/%Y")
            self.e_ini.delete(0,"end"); self.e_ini.insert(0, hoje_str)
            self.e_fim.delete(0,"end"); self.e_fim.insert(0, hoje_str); self.e_fim.configure(state="normal")
            self.v_indet.set(False); self.chk_indet.configure(state="normal")
            for k in self.d_vars: self.d_vars[k].set(False)
            for chk in self.chk_dias_widgets: chk.configure(state="disabled", fg_color="#EEE")
            self.set_dias("1 Dia")
        else:
            for chk in self.chk_dias_widgets: chk.configure(state="normal", fg_color="white")
            for k in self.d_vars: self.d_vars[k].set(True)
            self.smart_date_logic()

    def logic_indet(self):
        if self.v_indet.get():
            self.e_fim.delete(0,"end"); self.e_fim.insert(0, "----------"); self.e_fim.configure(state="disabled", fg_color="#EEE")
            self.set_dias("∞")
            self.v_hoje.set(False); self.chk_hoje.configure(state="disabled")
            for chk in self.chk_dias_widgets: chk.configure(state="normal", fg_color="white")
        else:
            self.e_fim.configure(state="normal", fg_color="white"); self.e_fim.delete(0,"end")
            self.chk_hoje.configure(state="normal")
            self.smart_date_logic()

    def logic_dias_semana(self):
        if self.v_hoje.get():
            self.v_hoje.set(False); self.logic_hoje()

    # --- HELPERS ---
    def header(self, t, sub):
        ctk.CTkLabel(self.main_area, text=t, font=("Segoe UI", 26, "bold"), text_color=VERITAS_TEXT).pack(anchor="w")
        ctk.CTkLabel(self.main_area, text=sub, font=("Segoe UI", 14), text_color="#777").pack(anchor="w", pady=(0,20))

    def card_form(self, parent, title):
        self.last_card = ctk.CTkFrame(parent, fg_color="white", corner_radius=10)
        self.last_card.pack(fill="x", pady=10)
        ctk.CTkLabel(self.last_card, text=title, font=("Segoe UI", 14, "bold"), text_color=VERITAS_BLUE).pack(anchor="w", padx=20, pady=(15,5))
        ctk.CTkFrame(self.last_card, height=1, fg_color="#EEE").pack(fill="x", padx=20, pady=(0,10))

    def inp_grid(self, p, t, r, c): ctk.CTkLabel(p, text=t, text_color="#555").grid(row=r, column=c, sticky="w", padx=(0,10), pady=(0,5))

    def mascara_data(self, e): self._mascara(e.widget, 10)
    def mascara_hora(self, e): self._mascara(e.widget, 5)
    def _mascara(self, w, limit):
        t = w.get().replace("/","").replace(":","")
        if not t.isdigit(): return
        w.delete(0,"end"); w.insert(0, (t[:2]+"/"+t[2:] if limit==10 else t[:2]+":"+t[2:]) if len(t)>2 else t)

    def add_hr(self, e=None): self._add_tag(self.e_hora, self.l_hours, self.fr_tags_hr, self.rm_hr, 5)
    def add_dt(self, e=None): self._add_tag(self.e_dt_tag, self.l_dates, self.fr_tags_dt, self.rm_dt, 10)
    def _add_tag(self, entry, lista, parent, cb, ln):
        v = entry.get()
        if len(v)==ln and v not in lista: lista.append(v); lista.sort(); self.render_tags(parent, lista, cb); entry.delete(0,"end")

    def rm_hr(self, v): self.l_hours.remove(v); self.render_tags(self.fr_tags_hr, self.l_hours, self.rm_hr)
    def rm_dt(self, v): self.l_dates.remove(v); self.render_tags(self.fr_tags_dt, self.l_dates, self.rm_dt)
    
    def render_tags(self, parent, lista, cb):
        for w in parent.winfo_children(): w.destroy()
        for v in lista:
            f = ctk.CTkFrame(parent, fg_color="#E3F2FD", corner_radius=5)
            f.pack(side="left", padx=5, pady=5)
            ctk.CTkLabel(f, text=v, text_color=VERITAS_BLUE).pack(side="left", padx=5)
            ctk.CTkButton(f, text="x", width=15, fg_color="transparent", text_color="red", command=lambda x=v: cb(x)).pack(side="left")

    def sel_vid(self):
        p = filedialog.askopenfilename(parent=self, filetypes=[("Video", "*.mp4 *.mkv")])
        if p: self.vid_path=p; self.lbl_vid.configure(text=os.path.basename(p))

    def preencher_form(self, d):
        self.e_nome.insert(0, d["nome"]); self.e_autor.set(d["autorizado"])
        self.vid_path = d["video"]; self.lbl_vid.configure(text=os.path.basename(d["video"]))
        self.l_hours = d["horarios"][:]; self.render_tags(self.fr_tags_hr, self.l_hours, self.rm_hr)
        if d.get("modo")=="DATAS ESPECÍFICAS":
            self.tabs.set("DATA ÚNICA")
            self.l_dates = d.get("datas_especificas",[])[:]; self.render_tags(self.fr_tags_dt, self.l_dates, self.rm_dt)
        else:
            self.e_ini.delete(0,"end"); self.e_ini.insert(0, d["inicio"])
            if d["fim"]=="INDETERMINADO": self.v_indet.set(True); self.logic_indet()
            else: self.e_fim.delete(0,"end"); self.e_fim.insert(0, d["fim"])
            self.v_hoje.set(d.get("somente_hoje", False))
            if self.v_hoje.get(): self.logic_hoje()
            
            dias_salvos = d.get("dias", [])
            for k,v in self.d_vars.items(): v.set(k in dias_salvos)
        self.smart_date_logic()

    def salvar(self):
        if not self.vid_path or not self.l_hours: ModernPopUp(self, "Erro", "Preencha vídeo e horários!"); return
        
        # Gera ID apenas se não existir
        novo_id = self.editando_id if self.editando_id else int(time.time())

        c = {
            "id": novo_id,
            "nome": self.e_nome.get() or "Sem Nome",
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
                if x["id"] == self.editando_id: 
                    c["execucoes_hoje"] = x.get("execucoes_hoje", [])
                    self.contratos[i] = c; break
        else: self.contratos.append(c)
        
        salvar_db(self.contratos)
        self.editando_id = None
        self.show_view("list") 
        ModernPopUp(self, "Sucesso", "Propaganda Salva com Sucesso!")