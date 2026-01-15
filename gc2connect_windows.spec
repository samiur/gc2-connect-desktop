# ABOUTME: PyInstaller spec file for building GC2 Connect as a Windows application.
# ABOUTME: Bundles NiceGUI static assets and creates a standalone .exe file.

# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path

block_cipher = None

# Get the path to nicegui package
import nicegui
nicegui_path = Path(nicegui.__file__).parent

# Get the path to our source
src_path = Path('src')

# Collect all necessary data files
datas = [
    # NiceGUI static files (CSS, JS, fonts, etc.)
    (str(nicegui_path / 'static'), 'nicegui/static'),
    # NiceGUI templates
    (str(nicegui_path / 'templates'), 'nicegui/templates'),
    # NiceGUI elements (some have their own static files)
    (str(nicegui_path / 'elements'), 'nicegui/elements'),
]

# Hidden imports that PyInstaller might miss
hiddenimports = [
    # NiceGUI core
    'nicegui',
    'nicegui.ui',
    'nicegui.app',
    'nicegui.elements',
    # NiceGUI dependencies
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'starlette',
    'starlette.routing',
    'starlette.middleware',
    'starlette.middleware.cors',
    'starlette.websockets',
    'fastapi',
    'fastapi.routing',
    'anyio',
    'anyio._backends',
    'anyio._backends._asyncio',
    'httptools',
    'watchfiles',
    'websockets',
    'python_multipart',
    'engineio',
    'socketio',
    # Native window (pywebview) - Windows backends
    'webview',
    'webview.platforms',
    'webview.platforms.mshtml',
    'webview.platforms.edgechromium',
    'webview.platforms.winforms',
    'bottle',
    'proxy_tools',
    # Windows-specific dependencies for pywebview
    'clr',
    'clr_loader',
    'pythonnet',
    # Pydantic
    'pydantic',
    'pydantic.fields',
    'pydantic_settings',
    # USB
    'usb',
    'usb.core',
    'usb.backend',
    'usb.backend.libusb1',
    # Our application modules
    'gc2_connect',
    'gc2_connect.main',
    'gc2_connect.models',
    'gc2_connect.ui',
    'gc2_connect.ui.app',
    'gc2_connect.ui.components',
    'gc2_connect.ui.components.mode_selector',
    'gc2_connect.ui.components.open_range_view',
    'gc2_connect.gc2',
    'gc2_connect.gc2.usb_reader',
    'gc2_connect.gspro',
    'gc2_connect.gspro.client',
    'gc2_connect.config',
    'gc2_connect.config.settings',
    'gc2_connect.services',
    'gc2_connect.services.history',
    'gc2_connect.services.export',
    'gc2_connect.services.shot_router',
    'gc2_connect.open_range',
    'gc2_connect.open_range.engine',
    'gc2_connect.open_range.models',
    'gc2_connect.open_range.physics',
    'gc2_connect.open_range.physics.engine',
    'gc2_connect.open_range.physics.trajectory',
    'gc2_connect.open_range.physics.aerodynamics',
    'gc2_connect.open_range.physics.ground',
    'gc2_connect.open_range.physics.constants',
    'gc2_connect.open_range.visualization',
    'gc2_connect.open_range.visualization.range_scene',
    'gc2_connect.open_range.visualization.ball_animation',
    'gc2_connect.utils',
    'gc2_connect.utils.reconnect',
]

a = Analysis(
    ['src/gc2_connect/main.py'],
    pathex=[str(src_path)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude test modules
        'pytest',
        'pytest_asyncio',
        'pytest_cov',
        'coverage',
        '_pytest',
        # Exclude dev tools
        'ruff',
        'mypy',
        'black',
        # Exclude macOS-specific modules
        'objc',
        'Foundation',
        'AppKit',
        'WebKit',
        'Cocoa',
        'Quartz',
        'Security',
        'PyObjCTools',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Single-file executable (onefile mode)
# All dependencies are bundled into one .exe file
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GC2Connect',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,  # Extract to temp dir at runtime
    console=True,  # Enable console to see errors (set to False for release)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/GC2Connect.ico',  # Windows icon
)
