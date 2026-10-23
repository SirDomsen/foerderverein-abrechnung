"""
Starter-Proxy für die Windows-Desktop-App.
Leitet direkt auf apps/windows/app_windows.py weiter.
"""
import sys
import os
import runpy

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

target = os.path.join(ROOT_DIR, "apps", "windows", "app_windows.py")
runpy.run_path(target, run_name="__main__")
