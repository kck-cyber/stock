# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=['src'],
    binaries=[('C:\\Users\\kck28\\AppData\\Local\\Programs\\Python\\Python312\\DLLs\\_tkinter.pyd', '.'), ('C:\\Users\\kck28\\AppData\\Local\\Programs\\Python\\Python312\\DLLs\\tcl86t.dll', '.'), ('C:\\Users\\kck28\\AppData\\Local\\Programs\\Python\\Python312\\DLLs\\tk86t.dll', '.')],
    datas=[('C:\\Users\\kck28\\AppData\\Local\\Programs\\Python\\Python312\\Lib\\tkinter', 'tkinter'), ('C:\\Users\\kck28\\AppData\\Local\\Programs\\Python\\Python312\\tcl', 'tcl'), ('src\\morning_stock_assistant\\collectors\\market\\us_stock_list.json', 'morning_stock_assistant\\collectors\\market'), ('cache\\krx_list.csv', 'cache')],
    hiddenimports=[
        'tkinter',
        'matplotlib.backends.backend_tkagg',
    ],
    hookspath=[],
    hooksconfig={
        'matplotlib': {
            'backends': ['TkAgg'],
        },
    },
    runtime_hooks=['pyinstaller_tk_runtime_hook.py'],
    excludes=[
        'PySide6',
        'PySide2',
        'PyQt6',
        'PyQt5',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MorningStockAssistantPro',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MorningStockAssistantPro',
)
