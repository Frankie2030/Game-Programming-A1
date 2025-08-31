# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Include all necessary pygame and sound dependencies
hidden_imports = [
    'pygame',
    'pygame._sdl2.audio',  # Important for sound
    'pygame.mixer',
    'pygame.mixer_music',
    'numpy',  # Often needed by pygame
    'pygame._sdl2.audio',
    'pygame._sdl2.mixer'
]

# Include all assets and any sound libraries
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/', 'assets/'),  # Include assets folder
        # Include any sound fonts or additional files
    ],
    hiddenimports=hidden_imports,
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
    name='WhackZombies',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True during development for debugging
    icon='assets/icon.ico' if os.path.exists('assets/icon.ico') else None,
)