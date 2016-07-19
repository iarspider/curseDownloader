#!python3

import sys
from cx_Freeze import setup, Executable

base = None
targetName = "cursePackDownloader"
if sys.platform == "win32":
    base = "Win32GUI"
    targetName = "cursePackDownloader.exe"

setup(
    name="cursePackDownloader",
    version="0.2",
    description="Download extra mods from Curse-hosted Minecraft modpacks",
    executables=[Executable("downloader.py", targetName=targetName)],
    install_requires=[
        'appdirs',
        'requests',
        'tk', 'simplejson', 'win_unicode_console'
    ]
)
