# Prepended by run.sh. Helpers such as list_tabs, close_tab, new_tab, js, wait_for_load are provided by browser-harness.
import json, re, time, random

_before = {t['targetId'] for t in list_tabs()}     # the user's tabs at the start: reported at the end, never closed
_mine = set()                                       # tabs this job opened: the only ones cleanup_tabs may close
_orig_new_tab = new_tab


def new_tab(url="about:blank"):
    tid = _orig_new_tab(url)
    if tid and tid not in _before:                  # new_tab can reuse a blank tab the user already had: never claim that one
        _mine.add(tid)
    return tid


def cleanup_tabs():
    for tid in list(_mine):
        try:
            close_tab(tid)
        except Exception:
            pass
    _mine.clear()


def human(a=3, b=6):
    time.sleep(random.uniform(a, b))
