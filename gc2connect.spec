# ABOUTME: PyInstaller spec file for building GC2 Connect as a macOS application.
# ABOUTME: Bundles NiceGUI static assets and creates a standalone .app bundle.

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
    # Native window (pywebview)
    'webview',
    'webview.platforms',
    'webview.platforms.cocoa',
    'bottle',
    'proxy_tools',
    # PyObjC for macOS native window
    'objc',
    'Foundation',
    'AppKit',
    'WebKit',
    'Cocoa',
    'Quartz',
    'Security',
    'UniformTypeIdentifiers',
    'PyObjCTools',
    'PyObjCTools.Conversion',
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
    ],
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
    name='GC2Connect',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window on macOS
    disable_windowed_traceback=False,
    argv_emulation=True,  # Better macOS integration
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GC2Connect',
)

app = BUNDLE(
    coll,
    name='GC2Connect.app',
    icon='assets/GC2Connect.icns',
    bundle_identifier='com.gc2connect.app',
    info_plist={
        'CFBundleName': 'GC2 Connect',
        'CFBundleDisplayName': 'GC2 Connect',
        'CFBundleVersion': '1.1.0',
        'CFBundleShortVersionString': '1.1.0',
        'CFBundleIdentifier': 'com.gc2connect.app',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.15',
        'NSRequiresAquaSystemAppearance': False,  # Support dark mode
        'CFBundleDocumentTypes': [],
        'NSHumanReadableCopyright': 'Copyright © 2024-2025',
    },
)
