# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — produces a single `payu` binary."""

import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_all

block_cipher = None

# Collect everything for packages that PyInstaller struggles with
all_datas = []
all_binaries = []
all_hiddenimports = []

for pkg in ["click", "typer", "rich", "httpx", "httpcore", "anyio", "sniffio", "certifi", "h11", "idna"]:
    try:
        datas, binaries, hiddenimports = collect_all(pkg)
        all_datas += datas
        all_binaries += binaries
        all_hiddenimports += hiddenimports
    except Exception:
        pass

all_hiddenimports += collect_submodules("payu_cli") + [
    "click",
    "click.core",
    "click.decorators",
    "click.types",
    "click.utils",
    "click.exceptions",
    "click.formatting",
    "click.parser",
    "click.termui",
    "click.testing",
    "click._compat",
    "typer",
    "typer.core",
    "typer.main",
    "keyring.backends",
    "keyring.backends.macOS",
    "keyring.backends.SecretService",
    "keyring.backends.Windows",
    "keyring.backends.null",
]

a = Analysis(
    ["payu_cli/main.py"],
    pathex=["."],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hiddenimports,
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="payu",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    console=True,
    target_arch=None,
)
