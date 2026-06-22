# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['menu.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('steps', 'steps'),
        ('steps_en', 'steps_en'),
        ('i18n', 'i18n'),
        ('assets/style_presets_classified.json', 'assets'),
        ('assets/style_presets_classified_en.json', 'assets'),
        ('.menu_config.json', '.'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='woke-menu',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\logo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='woke-menu',
)
