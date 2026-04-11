"""
Pre-loaded HTML pages — loaded once at startup, used by routes/*.py
"""

import os

BASE_DIR = os.path.dirname(__file__)


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


page_not_found_html = _read(os.path.join(BASE_DIR, "sites/pagenotfound/404.html"))
root_html = _read(os.path.join(BASE_DIR, "sites/root/index.html"))
login_html = _read(os.path.join(BASE_DIR, "sites/login/index.html"))
register_html = _read(os.path.join(BASE_DIR, "sites/register/index.html"))
dashboard_html = _read(os.path.join(BASE_DIR, "sites/dashboard/index.html"))
