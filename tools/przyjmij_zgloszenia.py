#!/usr/bin/env python3
"""przyjmij_zgloszenia.py - przenosi poprawne zgloszenia z zgloszenia/<id>/ do sklepu.

Dla kazdego katalogu zgloszenia/<id>/ (po merge do main; uruchamia GitHub Action, mozna tez recznie):
  1. tools/sprawdz_zgloszenie.py - jesli odrzucone, katalog zostaje (raport na stderr, kod wyjscia 1);
  2. obraz aplikacji (czysty, albo wyciety ze scalonego)  ->  bin/<plytka>/uzytkownicy/<id>.bin
  3. meta.json + kategoria "uzytkownicy" + data + sha256 zgloszenia  ->  bin/<plytka>/uzytkownicy/<id>.meta.json
  4. usuwa zgloszenia/<id>/
  5. na koncu tools/katalog.py (katalog.json).

Uzycie:  python3 tools/przyjmij_zgloszenia.py [--na-sucho]
Kod wyjscia: 0 = wszystkie zgloszenia przyjete (albo brak), 1 = ktores odrzucone (zostaje w zgloszenia/).
"""
import sys, os, json, shutil, datetime, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sprawdz_zgloszenie, sprawdz_bin  # noqa: E402

DO_KATALOGU = ("nazwa", "opis", "wersja", "autor", "licencja", "zrodlo", "plytka", "orientacja", "model_b", "info", "zglaszajacy")


def main(argv):
    na_sucho = "--na-sucho" in argv
    zd = os.path.join(ROOT, "zgloszenia")
    ids = sorted(d for d in os.listdir(zd) if os.path.isdir(os.path.join(zd, d)) and not d.startswith(".")) if os.path.isdir(zd) else []
    if not ids:
        print("brak zgloszen"); return 0
    zle = 0; przyjete = []
    for zid in ids:
        src = os.path.join(zd, zid)
        r = sprawdz_zgloszenie.sprawdz(src)
        print(sprawdz_zgloszenie.raport_txt(r))
        if not r["ok"]:
            zle += 1; print(f"-> {zid}: ODRZUCONE, zostaje w zgloszenia/\n", file=sys.stderr); continue
        meta = r["meta"]; plytka = meta["plytka"]
        dst_dir = os.path.join(ROOT, "bin", plytka, "uzytkownicy")
        dst_bin = os.path.join(dst_dir, f"{zid}.bin")
        dst_meta = os.path.join(dst_dir, f"{zid}.meta.json")
        _rb, img = sprawdz_bin.analyze(os.path.join(src, f"{zid}.bin"))
        out_meta = {k: meta[k] for k in DO_KATALOGU if k in meta}
        out_meta["kategoria"] = "uzytkownicy"
        out_meta["zgloszono"] = datetime.date.today().isoformat()
        out_meta["sha256_zgloszenia"] = r["bin"]["sha256_pliku"]
        if r["bin"].get("rodzaj") == "scalony":
            out_meta["wycieto_ze_scalonego"] = True
        print(f"-> {zid}: {'[na sucho] ' if na_sucho else ''}{os.path.relpath(dst_bin, ROOT)} ({len(img)} B) + {os.path.basename(dst_meta)}"
              + (" (aktualizacja)" if r["aktualizacja"] else "") + "\n")
        if na_sucho: continue
        os.makedirs(dst_dir, exist_ok=True)
        with open(dst_bin, "wb") as fh: fh.write(img)
        with open(dst_meta, "w", encoding="utf-8") as fh:
            json.dump(out_meta, fh, ensure_ascii=False, indent=2); fh.write("\n")
        shutil.rmtree(src)
        przyjete.append(zid)
    if przyjete:
        subprocess.run([sys.executable, os.path.join(HERE, "katalog.py")], check=True)
        print("przyjete:", ", ".join(przyjete))
        # dla GitHub Action (lista do komunikatu commita)
        gh = os.environ.get("GITHUB_OUTPUT")
        if gh:
            with open(gh, "a") as fh: fh.write("przyjete=" + " ".join(przyjete) + "\n")
    return 1 if zle else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
