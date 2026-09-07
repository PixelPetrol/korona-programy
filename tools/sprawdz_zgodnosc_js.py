#!/usr/bin/env python3
"""sprawdz_zgodnosc_js.py - czy walidator w przegladarce nie rozjechal sie ze skryptami.

Strona portal/zglos.html sprawdza .bin u uzytkownika w przegladarce, bo GitHub Pages nie ma
serwera, ktory mialby co przyjac. Reguly musialy wiec zostac PRZEPISANE do JavaScriptu -
i to jest druga kopia tych samych liczb. Ten skrypt pilnuje, zeby obie kopie mowily to samo.

Zrodlo prawdy: tools/sprawdz_bin.py (format .bin) i tools/sprawdz_zgloszenie.py (meta.json).
Kopia:         portal/zglos.js, blok "POCZATEK REGUL ... KONIEC REGUL".

Uzycie:
  python3 tools/sprawdz_zgodnosc_js.py            porownaj i wypisz roznice
  python3 tools/sprawdz_zgodnosc_js.py <sciezka>  porownaj z innym zglos.js (np. zrodlem portalu
                                                  sprzed rsync-a)
Kod wyjscia: 0 = zgodne, 1 = rozjazd, 2 = nie ma czego porownac (brak portal/zglos.js).

Gdy zmieniasz limit, offset albo regule w skryptach - popraw tez blok REGULY w zglos.js
i uruchom to ponownie.
"""
import sys, os, re, json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
JS = os.path.join(ROOT, "portal", "zglos.js")
sys.path.insert(0, HERE)
import sprawdz_bin as SB            # noqa: E402
import sprawdz_zgloszenie as SZ     # noqa: E402


def czytaj_js(tekst):
    """Wyciaga blok REGULY z zglos.js jako slownik nazwa -> liczba / tekst / lista."""
    m = re.search(r"POCZATEK REGUL.*?\n(.*?)/\* =+ KONIEC REGUL", tekst, re.S)
    if not m:
        raise SystemExit("zglos.js: nie znalazlem bloku 'POCZATEK REGUL ... KONIEC REGUL'")
    out = {}
    for linia in m.group(1).splitlines():
        linia = re.sub(r"//.*$", "", linia).strip().rstrip(",")
        k = re.match(r"^(\w+)\s*:\s*(.+)$", linia)
        if not k:
            continue
        nazwa, sur = k.group(1), k.group(2).strip()
        if re.fullmatch(r"0[xX][0-9a-fA-F]+|\d+", sur):
            out[nazwa] = int(sur, 0)
        elif sur.startswith("[") or sur.startswith('"'):
            try:
                out[nazwa] = json.loads(sur)
            except ValueError:
                out[nazwa] = sur
    return out


def main(argv):
    js_path = argv[0] if argv else JS
    if not os.path.isfile(js_path):
        print(f"nie ma {js_path} - nie ma czego porownywac")
        return 2
    tekst = open(js_path, encoding="utf-8").read()
    js = czytaj_js(tekst)

    ma_byc = {
        "OTA0_SIZE": SB.OTA0_SIZE,
        "OFF_BOOT": SB.OFF_BOOT,
        "OFF_PART": SB.OFF_PART,
        "OFF_APP": SB.OFF_APP,
        "ESP_MAGIC": SB.ESP_MAGIC,
        "APP_DESC_MAGIC": SB.APP_DESC_MAGIC,
        "ID_RE_SRC": SZ.ID_RE.pattern,
        "PLYTKI": list(SZ.PLYTKI),
        "ORIENT": list(SZ.ORIENT),
        "WYMAGANE": list(SZ.WYMAGANE),
    }
    for k, v in SZ.LIMITY.items():
        ma_byc["LIM_" + k] = v

    rozjazdy = []
    for k, v in sorted(ma_byc.items()):
        if k not in js:
            rozjazdy.append(f"{k}: brak w zglos.js (w skryptach: {v!r})")
        elif js[k] != v:
            rozjazdy.append(f"{k}: zglos.js ma {js[k]!r}, skrypty maja {v!r}")
    nadmiar = [k for k in js if k not in ma_byc]
    if nadmiar:
        rozjazdy.append("w zglos.js sa reguly, ktorych nie ma w skryptach: " + ", ".join(sorted(nadmiar)))

    # PART_MAGIC i tablica ukladow leza poza blokiem REGULY - sprawdzane osobno
    m = re.search(r"var PART_MAGIC\s*=\s*\[([^\]]*)\]", tekst)
    if not m:
        rozjazdy.append("PART_MAGIC: nie znalazlem w zglos.js")
    else:
        js_pm = bytes(int(x, 0) for x in m.group(1).split(","))
        if js_pm != SB.PART_MAGIC:
            rozjazdy.append(f"PART_MAGIC: zglos.js ma {js_pm!r}, sprawdz_bin.py ma {SB.PART_MAGIC!r}")

    m = re.search(r"var CHIPS\s*=\s*\{(.*?)\};", tekst, re.S)
    if not m:
        rozjazdy.append("CHIPS: nie znalazlem w zglos.js")
    else:
        js_chips = {int(a, 0): b for a, b in re.findall(r"(0x[0-9a-fA-F]+)\s*:\s*\"([^\"]+)\"", m.group(1))}
        if js_chips != SB.CHIPS:
            rozjazdy.append(f"CHIPS: zglos.js ma {js_chips}, sprawdz_bin.py ma {SB.CHIPS}")

    if rozjazdy:
        print("ROZJAZD portal/zglos.js <-> tools/sprawdz_bin.py|sprawdz_zgloszenie.py:")
        for x in rozjazdy:
            print("  -", x)
        print("\nPopraw blok REGULY w portal/zglos.js (kopia w tym repo powstaje przez rsync).")
        return 1
    print(f"zglos.js zgodny ze skryptami ({len(ma_byc) + 2} regul sprawdzonych)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
