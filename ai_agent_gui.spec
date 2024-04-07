# -*- mode: python ; coding: utf-8 -*-

import sys ; sys.setrecursionlimit(sys.getrecursionlimit() * 5)

a = Analysis(
    ['ai_agent_gui.py'],
    pathex=[],
    binaries=[('/Users/anthonybliss/anaconda3/lib/libpython3.11.dylib', '.')],
    datas=[('ai_agent.png', '.')],
    hiddenimports=['PySide6', 'PySide6.QtWidgets', 'PySide6.QtCore', 'PySide6.QtGui', 'langchain_experimental.agents.agent_toolkit', 'langchain_openai', 'langchain.agents.agent_types', 'pandas', 'pinecone', 'dotenv', 'requests', 'os', 'uuid', 'sys', 'matplotlib', 'tabulate'],
    hookspath=["."],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ai_agent_gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['ai_agent.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ai_agent_gui',
)
app = BUNDLE(
    coll,
    name='ai_agent_gui.app',
    icon='ai_agent.icns',
    bundle_identifier=None,
)
