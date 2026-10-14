# -*- mode: python ; coding: utf-8 -*-
# The EXE's file properties (Details tab) carry BO2SP's version from porter/version.py.
import os,re
from PyInstaller.utils.win32.versioninfo import VSVersionInfo,FixedFileInfo,StringFileInfo,StringTable,StringStruct,VarFileInfo,VarStruct
VERSION=re.search(r"VERSION='([^']+)'",open(os.path.join(SPECPATH,'porter','version.py'),encoding='utf-8').read()).group(1)
numbers=tuple(int(x) for x in (VERSION.split('.')+['0']*4)[:4])
version_info=VSVersionInfo(ffi=FixedFileInfo(filevers=numbers,prodvers=numbers),kids=[
    StringFileInfo([StringTable('040904B0',[StringStruct('CompanyName','Yoroji & brokn'),StringStruct('FileDescription','BO2SP'),
        StringStruct('FileVersion',VERSION),StringStruct('InternalName','BO2SP'),StringStruct('LegalCopyright','GPL-3.0'),
        StringStruct('OriginalFilename','BO2SP.exe'),StringStruct('ProductName','BO2SP'),StringStruct('ProductVersion',VERSION)])]),
    VarFileInfo([VarStruct('Translation',[1033,1200])])])


a = Analysis(
    ['porter/bo2sp.py'],
    pathex=[],
    binaries=[],
    datas=[('porter/assets','assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BO2SP',
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
    icon='porter/assets/app.ico',
    version=version_info,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BO2SP',
)
