#!/usr/bin/env python3
"""Generuje katalog.json (format v2, per plytka) z plikow bin/<plytka>/*.bin i tabeli META.

Uzycie (z katalogu repo):  python3 tools/katalog.py
Rozmiary sa czytane z plikow; opisy/wersje z tabeli ponizej. Plik bez wpisu w META
dostaje nazwe z pliku i pusty opis (i ostrzezenie na stderr).
"""
import json, os, sys, hashlib

PLYTKI = [
    ("cyd24", 'CYD 2.4" (ESP32-2432S024)'),
    ("cyd28", 'CYD 2.8" (ESP32-2432S028R)'),
]
# (plytka, plik) albo plik -> (nazwa, opis, wersja); wpis z plytka ma pierwszenstwo.
META = {
    "marauder.bin":                ("Marauder",             "audyt WiFi / BLE (Fr4nkFletcher, profil CYD_24)", "1.4.3"),
    "radar-pion.bin":              ("Radar ADS-B (pion)",   "SkyCYD 4.4.1 pionowo 240x320",                   "4.4.1"),
    "radar-poziom.bin":            ("Radar ADS-B (poziom)", "SkyCYD 4.4.1 poziomo 320x240",                   "4.4.1"),
    "bruce.bin":                   ("Bruce (LITE)",         "eksperymentalny, NIETESTOWANY na sprzecie",      "lite"),
    "esp32div.bin":                ("ESP32-DIV",            "eksperymentalny, NIETESTOWANY na sprzecie",      "dev"),
    ("cyd28", "radar-pion.bin"):   ("Radar ADS-B (pion)",   "SkyCYD 4.4.1 pionowo; 2.8\" NIETESTOWANE",       "4.4.1"),
    ("cyd28", "radar-poziom.bin"): ("Radar ADS-B (poziom)", "SkyCYD 4.4.1 poziomo; 2.8\" NIETESTOWANE",       "4.4.1"),
}

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = {"sklep": "KORONA", "wersja": 2, "plytki": []}
for pid, pname in PLYTKI:
    d = os.path.join(root, "bin", pid)
    progs = []
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if not f.lower().endswith(".bin"): continue
            p = os.path.join(d, f)
            nazwa, opis, wersja = META.get((pid, f), META.get(f, (f[:-4], "", "")))
            if (pid, f) not in META and f not in META: print("UWAGA: brak META dla", pid, f, file=sys.stderr)
            with open(p, "rb") as fh: data = fh.read()
            if data[:1] != b"\xe9": print("UWAGA: zly magic (nie obraz ESP32):", p, file=sys.stderr)
            progs.append({"plik": f"bin/{pid}/{f}", "nazwa": nazwa, "opis": opis,
                          "rozmiar": len(data), "wersja": wersja,
                          "sha256": hashlib.sha256(data).hexdigest()})
    out["plytki"].append({"id": pid, "nazwa": pname, "programy": progs})

with open(os.path.join(root, "katalog.json"), "w") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=2); fh.write("\n")
print("katalog.json:", sum(len(p["programy"]) for p in out["plytki"]), "programow")
