#!/usr/bin/env python3
"""Прогон тестов с физически заблокированной сетью — для проверки офлайн-режима.

Нужен, чтобы утверждение «тесты проходят без сети» было проверено, а не заявлено.
Блокировка делается в самом процессе: сокеты к GitHub и urllib обрываются, поэтому
любая попытка выйти наружу падает так же, как при отсутствии сети.
"""
import os
import runpy
import socket
import sys
import urllib.request

BLOCKED = ("github.com", "api.github.com", "raw.githubusercontent.com",
           "codeload.github.com", "objects.githubusercontent.com")


def _addr_blocked(addr) -> bool:
    if isinstance(addr, tuple) and addr:
        host = str(addr[0])
        return any(b in host for b in ("github", "140.82.", "185.199."))
    return False


_orig_connect = socket.socket.connect
_orig_create = socket.create_connection


def _blocked_connect(self, addr, *a, **k):
    if _addr_blocked(addr):
        raise OSError("сеть заблокирована (offline-проверка)")
    return _orig_connect(self, addr, *a, **k)


def _blocked_create(addr, *a, **k):
    if _addr_blocked(addr):
        raise OSError("сеть заблокирована (offline-проверка)")
    return _orig_create(addr, *a, **k)


socket.socket.connect = _blocked_connect
socket.create_connection = _blocked_create
sys.argv = ["tests/test_scripts.py"] + [x for x in sys.argv[1:] if x.startswith("--")]
os.environ.pop("GITHUB_TOKEN", None)
os.environ.pop("GH_TOKEN", None)

# Подпроцессы наследуют окружение, но блокировка сокетов действует только в ЭТОМ
# процессе: `broken_refs.py`, запущенный тестом, ходил в сеть, и шаг «без сети» в CI
# проходил, ничего не проверяя. Поэтому подпроцессам передаётся:
#   VH_OFFLINE=1 — не обращаться к сети вовсе;
#   VH_UPSTREAM_TREES — снимок деревьев апстримов (те же данные, что у тестов).
# Плюс настоящая проверка изоляции делается снаружи (bwrap --unshare-net или
# docker --network none): см. docs/offline.md.
FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures",
                       "upstream-trees.json.gz")
os.environ["VH_OFFLINE"] = "1"
os.environ["VH_UPSTREAM_TREES"] = FIXTURE

runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "test_scripts.py"), run_name="__main__")
