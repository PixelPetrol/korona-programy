#!/usr/bin/env python3
"""Wstawia do portal/README.md tabele rozmiarow obrazow - GENEROWANA z obrazy/SUMY.txt.

Po co: tabela byla wpisana w README recznie i zostala przy K-OS 0.3.6, podczas gdy
SUMY.txt jechalo dalej z kazdym biegiem zbuduj-obrazy.sh. Kto sprawdzal pobrany plik
wzgledem README, widzial inny rozmiar niz ma na dysku i mysial, ze ma uszkodzone
pobranie. Jedno zrodlo prawdy to obrazy/SUMY.txt (pisze je zbuduj-obrazy.sh z plikow,
ktore naprawde wytworzyl) - README ma tylko je pokazywac.

Uzycie:
    python3 portal/tabela-rozmiarow.py            # obok skryptu: obrazy/SUMY.txt, README.md
    python3 portal/tabela-rozmiarow.py <SUMY.txt> <README.md>

Wolane na koncu zbuduj-obrazy.sh, po zapisaniu SUMY.txt. Kod wyjscia 1 = nie zapisano
(brak SUMY.txt, brak znacznikow w README, zly format) - z komunikatem, co zrobic.
"""
import os
import re
import sys

ZNACZNIK_OD = "<!--TABELA-ROZMIAROW-->"
ZNACZNIK_DO = "<!--/TABELA-ROZMIAROW-->"


def blad(*a):
    print("BLAD:", *a, file=sys.stderr)
    sys.exit(1)


def liczba(n):
    """1415328 -> '1 415 328' (spacja jako separator tysiecy, tak jak w reszcie README)."""
    return "{:,}".format(n).replace(",", " ")


def czytaj_sumy(sciezka):
    """Zwraca (naglowek, factory_size, [(plik, rozmiar, sha), ...])."""
    with open(sciezka, encoding="utf-8") as fh:
        linie = fh.read().splitlines()
    naglowek, factory, wiersze = "", None, []
    for w in linie:
        if w.startswith("# K-OS "):
            # "# K-OS 0.7.0 - obrazy portalu, 2026-09-08 16:18" -> "K-OS 0.7.0, 2026-09-08 16:18"
            m = re.match(r"#\s*(K-OS \S+)\s*-\s*obrazy portalu,\s*(.+)$", w)
            naglowek = "%s, %s" % (m.group(1), m.group(2)) if m else w[2:].strip()
        elif w.startswith("# partycja factory:"):
            m = re.search(r"(\d+)", w)
            if m:
                factory = int(m.group(1))
        elif w and not w.startswith("#"):
            czesci = w.split()
            if len(czesci) != 3:
                blad("nie rozumiem wiersza w %s: %r" % (sciezka, w))
            wiersze.append((czesci[0], int(czesci[1]), czesci[2]))
    if not wiersze:
        blad("%s nie ma ani jednego wiersza z plikiem - uruchom najpierw ./zbuduj-obrazy.sh" % sciezka)
    if factory is None:
        blad("%s nie ma naglowka '# partycja factory: <N> B'" % sciezka)
    return naglowek, factory, wiersze


def zbuduj_tabele(naglowek, factory, wiersze):
    out = []
    out.append("### Zmierzone — %s" % (naglowek or "obrazy portalu"))
    out.append("")
    out.append("**Tabela jest generowana** z `obrazy/SUMY.txt` przez `zbuduj-obrazy.sh`\n"
               "(`tabela-rozmiarow.py`) — nie poprawiaj jej ręcznie, następny bieg skryptu i tak ją\n"
               "nadpisze. Rozbieżność między tą tabelą a pobranym plikiem oznacza uszkodzone\n"
               "pobranie, a nie nieaktualną dokumentację.")
    out.append("")
    out.append("| plik | rozmiar | zapas w `factory` (%s B) | SHA-256 |" % liczba(factory))
    out.append("|---|---|---|---|")
    najmniejszy = None
    for plik, rozmiar, sha in wiersze:
        if plik.endswith("/loader.bin"):
            zapas = factory - rozmiar
            proc = 100.0 * zapas / factory
            kol = "%s B (%s %%)" % (liczba(zapas), ("%.1f" % proc).replace(".", ","))
            if najmniejszy is None or zapas < najmniejszy[1]:
                najmniejszy = (plik, zapas, proc)
        else:
            kol = "—"
        out.append("| `%s` | %s B | %s | `%s` |" % (plik, liczba(rozmiar), kol, sha))
    out.append("")
    if najmniejszy:
        out.append("Najciaśniej jest w `%s`: zapas %s B (%s %%) w partycji `factory`."
                   % (najmniejszy[0], liczba(najmniejszy[1]),
                      ("%.1f" % najmniejszy[2]).replace(".", ",")))
    return "\n".join(out)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    if len(sys.argv) == 3:
        sumy, readme = sys.argv[1], sys.argv[2]
    elif len(sys.argv) == 1:
        sumy = os.path.join(here, "obrazy", "SUMY.txt")
        readme = os.path.join(here, "README.md")
    else:
        blad("uzycie: tabela-rozmiarow.py [<SUMY.txt> <README.md>]")
    if not os.path.isfile(sumy):
        blad("nie ma %s - uruchom najpierw ./zbuduj-obrazy.sh" % sumy)
    if not os.path.isfile(readme):
        blad("nie ma %s" % readme)

    tabela = zbuduj_tabele(*czytaj_sumy(sumy))

    with open(readme, encoding="utf-8") as fh:
        tekst = orig = fh.read()
    wzor = re.compile(re.escape(ZNACZNIK_OD) + ".*?" + re.escape(ZNACZNIK_DO), re.S)
    nowy = "%s\n%s\n%s" % (ZNACZNIK_OD, tabela, ZNACZNIK_DO)
    tekst, ile = wzor.subn(lambda _m: nowy, tekst)
    if ile == 0:
        blad("%s nie ma znacznikow %s ... %s - tabeli nie wstawiono.\n"
             "       Wstaw je tam, gdzie ma byc tabela rozmiarow." % (readme, ZNACZNIK_OD, ZNACZNIK_DO))
    if tekst == orig:
        print("  README.md: tabela rozmiarow bez zmian")
        return
    with open(readme, "w", encoding="utf-8") as fh:
        fh.write(tekst)
    print("  README.md -> tabela rozmiarow z obrazy/SUMY.txt")


if __name__ == "__main__":
    main()
