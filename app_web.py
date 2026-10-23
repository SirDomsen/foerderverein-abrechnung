"""
Starter-Proxy für die Web- und Smartphone-App.
Leitet direkt auf apps/web/app_web.py weiter.
"""
import sys
import os
import runpy

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

target = os.path.join(ROOT_DIR, "apps", "web", "app_web.py")
runpy.run_path(target, run_name="__main__")
