# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
import os
import sys

block_cipher = None

# --- COLETA AUTOMÁTICA DE DEPENDÊNCIAS ---
# Coleta tudo do CustomTkinter e EdgeTTS para evitar erros de importação
datas = []
binaries = []
hiddenimports = [
    'customtkinter', 
    'edge_tts', 
    'vlc', 
    'pycaw', 
    'comtypes', 
    'PIL._tkinter_finder'
]

# Adiciona bibliotecas que o PyInstaller as vezes esquece
tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

tmp_ret = collect_all('edge_tts')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# --- ASSETS DO PROJETO ---
# (Esses arquivos são acessados via resource_path / arquivos locais)
for asset in ("logo_watermark.png", "watermark.png"):
    if os.path.exists(asset):
        datas.append((asset, "."))

# --- VLC PLUGINS ---
# Necessário para o libVLC funcionar quando empacotado.
if os.path.isdir("plugins"):
    for root, _dirs, files in os.walk("plugins"):
        rel_dir = os.path.relpath(root, "plugins")
        dest_dir = "plugins" if rel_dir == "." else os.path.join("plugins", rel_dir)
        for fn in files:
            src = os.path.join(root, fn)
            datas.append((src, dest_dir))

# --- INCLUSÃO MANUAL DE BINÁRIOS (FFMPEG E VLC) ---
# (Arquivo Origem, Pasta Destino no EXE)
added_files = [
    ('ffmpeg.exe', '.'),
    ('ffprobe.exe', '.'),
    ('libvlc.dll', '.'),
    ('libvlccore.dll', '.'),
]

# --- RUNTIME VC++ (Python 3.11) ---
# Em algumas máquinas sem Python instalado, o python311.dll depende de VCRUNTIME140_1.dll.
try:
    vcr_1 = os.path.join(sys.base_prefix, 'vcruntime140_1.dll')
    if os.path.exists(vcr_1):
        added_files.append((vcr_1, '.'))
except Exception:
    pass

# Adiciona os binários à lista
for src, dest in added_files:
    binaries.append((src, dest))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VeritasPlayer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # FALSE para não abrir a tela preta (terminal) junto
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None, # Se tiver icone, coloque 'icone.ico' aqui
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VeritasPlayer',
)