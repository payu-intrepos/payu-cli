# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — produces a single `payu` binary."""

import sys
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

hiddenimports = collect_submodules("payu_cli") + [
    "keyring.backends",
    "keyring.backends.macOS",
    "keyring.backends.SecretService",
    "keyring.backends.Windows",
    "keyring.backends.null",
]

a = Analysis(
    ["payu_cli/main.py"],
    pathex=["."],
    binaries=[],
    datas=[],
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
