"""Удаляет из среды Python для Windows всё, что не нужно приложению (тесты, tkinter, лишние модули Qt).
Запуск: python prune.py <папка среды>"""
import os
import re
import shutil
import sys

E = sys.argv[1]


def rm(p):
    p = os.path.join(E, p)
    if os.path.isdir(p):
        shutil.rmtree(p)
    elif os.path.exists(p):
        os.remove(p)


for p in ["Library/lib", "Library/include", "Library/share", "Tools", "include", "Scripts", "lib", "libs", "bin",
          "share", "etc", "conda-meta", "Lib/idlelib", "Lib/tkinter", "Lib/ensurepip", "Lib/lib2to3",
          "Lib/pydoc_data", "Lib/test", "Lib/turtledemo", "Lib/site-packages/bin", "Lib/site-packages/README.txt"]:
    rm(p)
for f in os.listdir(os.path.join(E, "DLLs")):
    if f.startswith(("_tkinter", "_test", "xxlimited", "_ctypes_test")):
        rm(os.path.join("DLLs", f))
lb = os.path.join(E, "Library", "bin")
for f in os.listdir(lb):
    if re.match(r"(tcl|tk|tclsh|wish|openssl\.exe|c_rehash)", f) or f.endswith(".pdb"):
        os.remove(os.path.join(lb, f))
# библиотеки, которые нужны модулям Python, кладём рядом с ними
for f in ["sqlite3.dll", "ffi-8.dll", "libbz2.dll", "liblzma.dll", "libssl-3-x64.dll", "libcrypto-3-x64.dll",
          "libexpat.dll", "zlib.dll", "zlib1.dll"]:
    if os.path.exists(os.path.join(lb, f)):
        shutil.copy(os.path.join(lb, f), os.path.join(E, "DLLs", f))

P = os.path.join(E, "Lib", "site-packages", "PySide6")
keep_dll = {"Qt6Core.dll", "Qt6Gui.dll", "Qt6Widgets.dll", "pyside6.abi3.dll"}
for f in os.listdir(P):
    p = os.path.join(P, f)
    if os.path.isdir(p):
        if f not in ("plugins", "translations", "support"):
            shutil.rmtree(p)
    elif f.endswith(".dll"):
        if f not in keep_dll and not re.match(r"(msvcp|vcruntime|concrt|vcomp|vccorlib)", f):
            os.remove(p)
    elif f.endswith(".pyd"):
        if f not in ("QtCore.pyd", "QtGui.pyd", "QtWidgets.pyd"):
            os.remove(p)
    elif f.endswith((".exe", ".pyi", ".lib", ".json")) or f == "py.typed":
        os.remove(p)
keep_pl = {"platforms": ["qwindows.dll"], "imageformats": ["qjpeg.dll", "qico.dll", "qwebp.dll", "qgif.dll"],
           "styles": ["qmodernwindowsstyle.dll"]}
for d in os.listdir(os.path.join(P, "plugins")):
    dp = os.path.join(P, "plugins", d)
    if d not in keep_pl:
        shutil.rmtree(dp)
        continue
    for f in os.listdir(dp):
        if f not in keep_pl[d]:
            os.remove(os.path.join(dp, f))
for f in os.listdir(os.path.join(P, "translations")):
    if f not in ("qtbase_ru.qm", "qt_ru.qm"):
        rm(os.path.join("Lib", "site-packages", "PySide6", "translations", f))
for root, dirs, files in os.walk(E):
    for d in list(dirs):
        if d == "__pycache__":
            shutil.rmtree(os.path.join(root, d))
            dirs.remove(d)
    for f in files:
        if f.endswith(".pdb"):
            os.remove(os.path.join(root, f))
print("лишнее удалено")
