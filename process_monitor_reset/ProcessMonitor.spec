a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('icon.ico', '.'),
        ('app_icon.png', '.')
    ],
    hiddenimports=[
        'core',
        'core.app_controller',
        'core.config',
        'core.hotkey_manager',
        'core.http_api',
        'core.icon_cache',
        'core.logger',
        'core.monitor_thread',
        'core.process_utils',
        'core.system_utils',
        'core.window_manager',
        'core.window_utils',
        'ui',
        'ui.main_window',
        'ui.process_tree',
        'ui.monitor_tree',
        'ui.debug_window',
        'ui.device_discovery',
        'ui.dialogs'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ProcessMonitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico'
)