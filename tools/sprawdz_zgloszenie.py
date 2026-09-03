#!/usr/bin/env python3
"""sprawdz_zgloszenie.py - walidator zgloszenia programu uzytkownika do sklepu KORONA.

Zgloszenie = katalog  zgloszenia/<id>/  z dwoma plikami:
    <id>.bin      obraz aplikacji ESP32 (czysty; scalony tez przejdzie - zostanie wyciety przy przyjeciu)
    meta.json     opis (pola nizej)

Uzycie:
  python3 tools/sprawdz_zgloszenie.py zgloszenia/moj-program        raport tekstowy
  python3 tools/sprawdz_zgloszenie.py --wszystkie                     wszystkie katalogi w zgloszenia/
  ... --md                                                           raport w Markdown (komentarz do PR)
  ... --json                                                         wynik JSON
Kod wyjscia: 0 = wszystko OK, 1 = co najmniej jedno zgloszenie odrzucone.

meta.json - pola wymagane:
  nazwa       nazwa wyswietlana w menu (<= 40 znakow; ladowarka nie ma polskich znakow w czcionce -> ASCII)
  opis        jedna linia (<= 60)
  wersja      np. "1.2.0" (<= 16)
  autor       autor PROGRAMU (jesli to port cudzego projektu - oryginalny autor, nie osoba zglaszajaca)
  licencja    np. "MIT", "GPL-3.0", "Apache-2.0" (<= 40)
  zrodlo      URL do zrodel (http/https) - przy GPL obowiazkowe, przy innych mocno pozadane
  plytka      "cyd24" albo "cyd28"
  orientacja  "pion" albo "poziom"
  model_b     true  - oswiadczenie autora: program kasuje otadata na poczatku setup() (albo ma
              verifyRollbackLater()), czyli RST wraca do menu KORONY. Automat tego NIE sprawdzi.
  info        dluzszy opis widoczny w karcie programu (<= 600; pierwszy start, AP, haslo, sterowanie)
pola opcjonalne:
  zglaszajacy  kto zglasza (nick GitHub), gdy to nie autor
  uwagi        cokolwiek dla przegladajacego PR (nie trafia do katalogu)

<id> (nazwa katalogu i pliku .bin): 2-32 znaki, male litery, cyfry, '-' i '_'. To jest klucz
migawki ustawien na karcie - po publikacji nazwy sie nie zmienia.
"""
import sys, os, re, json, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sprawdz_bin  # noqa: E402

ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,31}$")
PLYTKI = ("cyd24", "cyd28")
ORIENT = ("pion", "poziom")
WYMAGANE = ("nazwa", "opis", "wersja", "autor", "licencja", "zrodlo", "plytka", "orientacja", "model_b", "info")
LIMITY = {"nazwa": 40, "opis": 60, "wersja": 16, "autor": 60, "licencja": 40, "zrodlo": 200, "info": 600, "zglaszajacy": 60}
OPCJONALNE = ("zglaszajacy", "uwagi")
GPL_RE = re.compile(r"GPL|AGPL|LGPL", re.I)


def sprawdz(dir_path):
    """Zwraca dict: id, ok, bledy[], ostrzezenia[], meta, bin (raport sprawdz_bin), aktualizacja."""
    dir_path = os.path.abspath(dir_path.rstrip("/"))
    zid = os.path.basename(dir_path)
    r = {"id": zid, "katalog": os.path.relpath(dir_path, ROOT), "ok": False, "bledy": [], "ostrzezenia": [],
         "meta": None, "bin": None, "aktualizacja": False}
    E, W = r["bledy"].append, r["ostrzezenia"].append

    if not os.path.isdir(dir_path):
        E(f"nie ma katalogu {dir_path}"); return r
    if not ID_RE.match(zid):
        E(f"zla nazwa katalogu '{zid}': 2-32 znaki, male litery a-z, cyfry, '-' i '_' (to bedzie nazwa pliku .bin i klucz ustawien na karcie)")

    files = sorted(os.listdir(dir_path))
    bins = [f for f in files if f.lower().endswith(".bin")]
    bin_path = os.path.join(dir_path, f"{zid}.bin")
    if f"{zid}.bin" not in files:
        E(f"brak pliku {zid}.bin (plik .bin musi nazywac sie tak jak katalog)" + (f"; znalazlem: {', '.join(bins)}" if bins else ""))
    if len(bins) > 1:
        E(f"w zgloszeniu ma byc JEDEN plik .bin, jest {len(bins)}: {', '.join(bins)}")
    extra = [f for f in files if f not in (f"{zid}.bin", "meta.json") and not f.startswith(".")]
    if extra:
        W(f"dodatkowe pliki (nie trafia do sklepu): {', '.join(extra)}")

    # --- meta.json ---
    meta_path = os.path.join(dir_path, "meta.json")
    meta = None
    if "meta.json" not in files:
        E("brak meta.json")
    else:
        try:
            with open(meta_path, encoding="utf-8") as fh:
                meta = json.load(fh)
            if not isinstance(meta, dict):
                E("meta.json: ma byc obiekt JSON {...}"); meta = None
        except ValueError as e:
            E(f"meta.json: niepoprawny JSON: {e}")
        except OSError as e:
            E(f"meta.json: {e}")
    if meta is not None:
        r["meta"] = meta
        for k in WYMAGANE:
            if k not in meta:
                E(f"meta.json: brak pola '{k}'")
        for k, v in meta.items():
            if k not in WYMAGANE and k not in OPCJONALNE:
                W(f"meta.json: nieznane pole '{k}' (zignorowane)")
        for k, lim in LIMITY.items():
            v = meta.get(k)
            if v is None: continue
            if not isinstance(v, str):
                E(f"meta.json: '{k}' ma byc tekstem"); continue
            if not v.strip() and k in WYMAGANE:
                E(f"meta.json: '{k}' jest puste")
            if len(v) > lim:
                E(f"meta.json: '{k}' za dlugie ({len(v)} > {lim} znakow)")
            if k in ("nazwa", "opis", "info", "autor") and any(ord(c) > 126 for c in v):
                W(f"meta.json: '{k}' ma znaki poza ASCII - czcionka ladowarki ich nie narysuje (zamien np. 'ł' -> 'l')")
            if "\n" in v and k != "info":
                E(f"meta.json: '{k}' ma byc jedna linia")
        if meta.get("plytka") not in PLYTKI:
            E(f"meta.json: 'plytka' musi byc jedna z {PLYTKI} (jest {meta.get('plytka')!r})")
        if meta.get("orientacja") not in ORIENT:
            E(f"meta.json: 'orientacja' musi byc jedna z {ORIENT} (jest {meta.get('orientacja')!r})")
        if meta.get("model_b") is not True:
            E("meta.json: 'model_b' musi byc true - oswiadczenie, ze program kasuje otadata w setup() (albo ma verifyRollbackLater()). "
              "Bez tego RST nie wraca do menu i plytke odzyskuje sie tylko po USB. Patrz portal/programy.html")
        z = meta.get("zrodlo")
        if isinstance(z, str) and z and not re.match(r"^https?://[^\s]+$", z):
            E(f"meta.json: 'zrodlo' ma byc adresem http(s) (jest {z!r})")
        lic = meta.get("licencja", "")
        if isinstance(lic, str) and GPL_RE.search(lic) and not (isinstance(z, str) and z.startswith("http")):
            E("meta.json: licencja GPL wymaga podania 'zrodlo' (URL do zrodel tej wlasnie wersji)")
        if isinstance(meta.get("nazwa"), str) and meta["nazwa"].strip().lower() in ("test", "program", "app"):
            W("meta.json: 'nazwa' bardzo ogolna - w menu widac tylko ja")

    # --- kolizje nazw ---
    plytka = meta.get("plytka") if isinstance(meta, dict) else None
    if plytka in PLYTKI:
        if os.path.exists(os.path.join(ROOT, "bin", plytka, f"{zid}.bin")):
            E(f"nazwa '{zid}' jest zajeta przez program sklepu (bin/{plytka}/{zid}.bin) - wybierz inna")
        if os.path.exists(os.path.join(ROOT, "bin", plytka, "uzytkownicy", f"{zid}.bin")):
            r["aktualizacja"] = True
            W(f"'{zid}' juz jest w bin/{plytka}/uzytkownicy/ - to AKTUALIZACJA istniejacego programu (nadpisze bin i meta)")
            try:
                with open(os.path.join(ROOT, "bin", plytka, "uzytkownicy", f"{zid}.meta.json"), encoding="utf-8") as fh:
                    stare = json.load(fh)
                if isinstance(meta, dict) and stare.get("wersja") == meta.get("wersja"):
                    W(f"aktualizacja z ta sama 'wersja' ({meta.get('wersja')!r}) - podnies numer wersji")
                if isinstance(meta, dict) and stare.get("autor") != meta.get("autor"):
                    W(f"aktualizacja zmienia autora: {stare.get('autor')!r} -> {meta.get('autor')!r}")
            except (OSError, ValueError):
                pass

    # --- .bin ---
    if os.path.isfile(bin_path):
        rb, img = sprawdz_bin.analyze(bin_path)
        r["bin"] = rb
        for b in rb["bledy"]:
            E(f"{zid}.bin: {b}")
        for w in rb["ostrzezenia"]:
            W(f"{zid}.bin: {w}")
        if rb.get("rodzaj") == "scalony":
            W(f"{zid}.bin to SCALONY obraz flasha - do sklepu trafi wycieta aplikacja "
              f"({rb.get('rozmiar')} B, sha256 {rb.get('sha256', '')[:16]}...). Lepiej zglaszaj czysty obraz aplikacji.")
        d = rb.get("app_desc") or {}
        if isinstance(meta, dict) and d.get("project_name") and d["project_name"] != "arduino-lib-builder":
            r["app_desc_nazwa"] = d["project_name"]

    r["ok"] = not r["bledy"]
    return r


def raport_txt(r):
    L = [f"== zgloszenie {r['id']}  ({r['katalog']}) ==", "WYNIK: " + ("OK - do przyjecia (Model B do sprawdzenia recznie)" if r["ok"] else "ODRZUCONE")]
    m = r.get("meta") or {}
    if m:
        L.append(f"  {m.get('nazwa', '?')} {m.get('wersja', '')} | {m.get('plytka', '?')} {m.get('orientacja', '?')} | autor: {m.get('autor', '?')} | lic.: {m.get('licencja', '?')}")
        if m.get("zrodlo"): L.append(f"  zrodlo: {m['zrodlo']}")
    b = r.get("bin")
    if b and "rozmiar" in b:
        L.append(f"  bin: {b['rodzaj']}, {b['rozmiar']} B (zapas {b.get('zapas', '-')} B), {b['chip']}, sha256 {b['sha256']}")
        d = b.get("app_desc")
        if d: L.append(f"  app_desc: {d['project_name']} {d['version']} idf {d['idf_ver']} ({d['date']})")
    for x in r["bledy"]: L.append(f"  BLAD:  {x}")
    for x in r["ostrzezenia"]: L.append(f"  UWAGA: {x}")
    if r.get("aktualizacja"): L.append("  (aktualizacja istniejacego programu)")
    L.append("  Model B: NIE DA SIE SPRAWDZIC AUTOMATEM - przegladajacy: uruchom pod KORONA, nacisnij RST, ma wrocic menu.")
    return "\n".join(L)


def raport_md(wyniki):
    L = ["## KORONA - sprawdzenie zgloszenia", ""]
    for r in wyniki:
        m = r.get("meta") or {}
        L.append(f"### {'✅' if r['ok'] else '❌'} `{r['id']}`" + (f" — {m.get('nazwa', '')} {m.get('wersja', '')}" if m else ""))
        L.append("")
        if m:
            L.append(f"- płytka: `{m.get('plytka', '?')}`, orientacja: `{m.get('orientacja', '?')}`, autor: {m.get('autor', '?')}, licencja: `{m.get('licencja', '?')}`"
                     + (f", [źródło]({m['zrodlo']})" if isinstance(m.get('zrodlo'), str) and m['zrodlo'].startswith('http') else ""))
        b = r.get("bin")
        if b and "rozmiar" in b:
            n = lambda x: f"{x:,}".replace(",", " ")
            L.append(f"- bin: **{b['rodzaj']}**, {n(b['rozmiar'])} B z {n(b['limit_ota0'])} B (zapas {n(b.get('zapas', 0))} B), układ {b['chip']}, sha256 `{b['sha256']}`")
            d = b.get("app_desc")
            if d: L.append(f"- app_desc: `{d['project_name']}` `{d['version']}` idf `{d['idf_ver']}` ({d['date']} {d['time']})")
        if r.get("aktualizacja"): L.append("- **aktualizacja** istniejącego programu")
        for x in r["bledy"]: L.append(f"- ❌ **BŁĄD:** {x}")
        for x in r["ostrzezenia"]: L.append(f"- ⚠️ {x}")
        L.append("")
    L.append("> **Model B** (reset wraca do menu) nie da się sprawdzić automatem — to kod, nie tekst. "
             "Przeglądający: wgraj `.bin` na kartę do `/programy/<płytka>/`, uruchom, naciśnij RST — musi wrócić menu KORONY. "
             "Bez tego płytkę odzyskuje się tylko po USB.")
    L.append("")
    L.append(f"_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · tools/sprawdz_zgloszenie.py_")
    return "\n".join(L)


def main(argv):
    flags = {a for a in argv if a.startswith("--")}
    args = [a for a in argv if not a.startswith("--")]
    if "--wszystkie" in flags:
        zd = os.path.join(ROOT, "zgloszenia")
        args += sorted(os.path.join(zd, d) for d in os.listdir(zd) if os.path.isdir(os.path.join(zd, d)) and not d.startswith(".")) if os.path.isdir(zd) else []
    if not args:
        if "--wszystkie" in flags:
            print("brak zgloszen w zgloszenia/"); return 0
        print(__doc__); return 2
    wyniki = [sprawdz(a) for a in args]
    if "--json" in flags:
        print(json.dumps(wyniki, ensure_ascii=False, indent=2))
    elif "--md" in flags:
        print(raport_md(wyniki))
    else:
        print("\n\n".join(raport_txt(r) for r in wyniki))
    return 0 if all(r["ok"] for r in wyniki) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
