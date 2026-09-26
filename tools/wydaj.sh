#!/bin/bash
# K-OS - LISTA KONTROLNA WYDANIA JAKO SKRYPT (D5 z PROPOZYCJE-2026-09-24.md).
#
# TEN SKRYPT NICZEGO NIE PUBLIKUJE. Nie robi git push, nie robi rsync do repo sklepu, nie wgrywa
# plytki i nie wdraza Workera. Buduje, sprawdza i NA KONCU WYPISUJE komendy do wykonania recznie.
#
#   tools/wydaj.sh                    pelny bieg: testy hostowe, 3 profile K-OS w loader/,
#                                     kontrola binarek, obrazy portalu (portal/zbuduj-obrazy.sh),
#                                     rozmiar katalogu v2 - i komendy publikacji
#   tools/wydaj.sh --bez-budowania    to samo na binarkach, ktore JUZ leza w loader/.build-*;
#                                     nic nie buduje i NIE rusza portal/ (obrazow nie sklada)
#   tools/wydaj.sh --napis "tekst"    dodatkowy napis, ktory MUSI byc w kazdej binarce (mozna
#                                     powtarzac); np. wiersz logu, o ktory robiony jest build
#   tools/wydaj.sh po-pushu           PO wypchnieciu repo sklepu: czeka, az GitHub Pages zbuduje
#                                     TEN commit, i sprawdza, co strona NAPRAWDE serwuje (tylko czyta)
#
# KOD WYJSCIA: 0 = gotowe (ostrzezenia dozwolone), 1 = sa bledy - NIE publikowac, 2 = zle uzycie.
# SPRAWDZAJAC WYNIK NIGDY `tools/wydaj.sh | grep ...` - potok maskuje kod wyjscia (pulapka nr 2
# z SPEC-K-OS). Prawidlowo:  tools/wydaj.sh > log 2>&1; echo $?
#
# CO LAPIE - kazda pozycja juz raz kosztowala (SPEC-K-OS, "PULAPKI, KTORE JUZ NAS KOSZTOWALY"):
#   1. NIEPODBITY NUMER WERSJI: FW_VERSION z loader/loader/version.h musi byc WIEKSZY niz wersja
#      w opublikowanym manifescie (GitHub Pages; bez sieci - kopia w repo sklepu). Rowny = stara
#      i nowa binarka twierdzilyby, ze sa tym samym (tak wpadl tester przy rozmiarach w README).
#   2. NAPISY W BINARCE: kazda z 3 binarek musi zawierac FW_VERSION, baner "K-OS READY" (czekaja
#      na niego narzedzia), znacznik KORONA-LOADER-OBRAZ-1 (bez niego samoaktualizacja na plytkach
#      odrzuci obraz) i kazdy napis z --napis. Build diagnostyczny SkyCYD wyszedl bez obiecanego
#      wiersza, bo byl w RAPORCIE agenta, a nie w zrodle (zgloszenie #3).
#   3. ZAPAS W factory: partycja z loader/partitions_loader.csv minus rozmiar obrazu; ponizej
#      ZAPAS_MIN (10 000 B, podloga z SPEC) = blad, ponizej ZAPAS_OSTRZ (12 kB) = ostrzezenie.
#   4. ROZMIAR KATALOGU v2: tools/katalog.py --sprawdz; ponad 26 000 B generator nie zapisuje
#      NICZEGO, a nieaktualne katalogi opublikowalyby sie tym samym pushem.
#   5. KOD WYJSCIA MASKOWANY POTOKIEM: kazdy krok idzie do pliku logu, a kod wyjscia jest
#      sprawdzany wprost (set -o pipefail, zero potokow za budowaniem). Do tego binarka musi byc
#      NOWSZA niz start budowania - "build padl, a stary .bin zostal" nie przejdzie jako sukces.
#   Przy okazji: obrazy portalu z tej samej wersji, SUMY.txt i manifesty < 4096 B (tyle czyta
#   samoaktualizacja), zgodnosc portal/ z kopia w repo sklepu, a w "po-pushu" - GitHub Pages
#   zbudowane dla TEGO commita (status "built" bywa prawda takze dla poprzedniego).
#
# Wgrywanie do testu wypisuje jako ./flash.sh - NIGDY ./build.sh upload (wgrywa tablice partycji
# huge_app bez knvs i plytka wstaje "pusta").
#
# Uklad katalogow bierze sie z polozenia skryptu: <KORZEN>/korona-programy/tools/wydaj.sh,
# obok korona-programy leza loader/ (K-OS), portal/ (zrodlo strony) i k-os-stat/ (Worker).
# Bash 3.2 z macOS wystarcza (bez tablic asocjacyjnych). Potrzebne: git, python3, curl,
# arduino-cli (pelny bieg), gh (opcjonalnie: stan GitHub Pages).

set -euo pipefail
export PATH="/opt/homebrew/bin:$PATH"

TOOLS="$(cd "$(dirname "$0")" && pwd)"
SKLEP="$(dirname "$TOOLS")"
KORZEN="$(dirname "$SKLEP")"
LOADER="$KORZEN/loader"
PORTAL="$KORZEN/portal"
STRONA="https://pixelpetrol.github.io/korona-programy/portal"
REPO_GH="PixelPetrol/korona-programy"
ZAPAS_MIN="${ZAPAS_MIN:-10000}"
ZAPAS_OSTRZ="${ZAPAS_OSTRZ:-12288}"
IO_BUF=4096                              # sdprog.h IO_BUF_SIZE - SUMY.txt i manifest musza sie zmiescic
CZEKAJ_S="${CZEKAJ_S:-900}"              # po-pushu: ile najwyzej czekac na GitHub Pages

# profil = "BOARD|PANEL|katalog budowy|id plytki" (bash 3.2 - bez tablic asocjacyjnych)
PROFILE="24||.build-24|cyd24 28R||.build-28R|cyd28 28R|st7789|.build-28R-st7789|cyd28s"

TRYB="pelny"
NAPISY_DOD=""
while [ $# -gt 0 ]; do
  case "$1" in
    --bez-budowania) TRYB="bez-budowania" ;;
    po-pushu)        TRYB="po-pushu" ;;
    --napis)         [ $# -ge 2 ] || { echo "--napis wymaga tekstu" >&2; exit 2; }
                     NAPISY_DOD="$NAPISY_DOD$2"$'\n'; shift ;;
    -h|--help)       sed -n '2,20p' "$0"; exit 0 ;;
    *)               echo "nieznany argument: $1 (tools/wydaj.sh --help)" >&2; exit 2 ;;
  esac
  shift
done

LOGI="$(mktemp -d "${TMPDIR:-/tmp}/kos-wydaj.XXXXXX")"    # logi zostaja po biegu (male pliki tekstowe)
NBLEDOW=0; NOSTRZ=0; BLEDY=""; OSTRZ=""
krok()  { echo; echo "== $*"; }
ok()    { echo "   ok     $*"; }
info()  { echo "   info   $*"; }
blad()  { NBLEDOW=$((NBLEDOW + 1)); BLEDY="$BLEDY   - $*"$'\n'; echo "   BLAD   $*"; }
ostrz() { NOSTRZ=$((NOSTRZ + 1)); OSTRZ="$OSTRZ   - $*"$'\n'; echo "   UWAGA  $*"; }
stop()  { echo; echo "PRZERWANE: $*" >&2; echo "logi: $LOGI" >&2; exit 1; }
rozmiar() { python3 -c 'import os,sys; print(os.path.getsize(sys.argv[1]))' "$1"; }
liczba()  { printf '%s' "$1" | sed -e :a -e 's/\(.*[0-9]\)\([0-9]\{3\}\)/\1 \2/;ta'; }
# porownanie wersji "1.2.3": wypisuje 1 (a > b), 0 (rowne), -1 (a < b); zly format = blad pythona
por_wersji() { python3 -c 'import sys; a=[int(x) for x in sys.argv[1].split(".")]; b=[int(x) for x in sys.argv[2].split(".")]; print((a>b)-(a<b))' "$1" "$2"; }
jest_wersja() { printf '%s' "$1" | grep -Eq '^[0-9]{1,3}(\.[0-9]{1,3}){1,3}$'; }
# wersja z manifestu (JSON) - z pliku albo z tekstu na stdin
wersja_manifestu() { python3 -c 'import json,sys; print(json.load(sys.stdin).get("version",""))'; }
# napis w binarce: szukanie bajtow w pliku, bez potoku
ma_napis() { python3 -c 'import sys; sys.exit(0 if sys.argv[2].encode() in open(sys.argv[1],"rb").read() else 1)' "$1" "$2"; }

[ -d "$LOADER/loader" ] || stop "nie ma $LOADER/loader - skrypt musi lezec w <KORZEN>/korona-programy/tools/"
[ -f "$LOADER/loader/version.h" ] || stop "nie ma $LOADER/loader/version.h"
WER="$(sed -n 's/^#define FW_VERSION "\([^"]*\)".*/\1/p' "$LOADER/loader/version.h")"
jest_wersja "$WER" || stop "FW_VERSION w version.h ma dziwny ksztalt: '$WER'"

echo "K-OS - lista kontrolna wydania ($TRYB), $(date '+%Y-%m-%d %H:%M')"
echo "   loader:  $LOADER"
echo "   portal:  $PORTAL (zrodlo strony)  ->  $SKLEP/portal (kopia w repo sklepu)"
echo "   wersja w version.h: $WER"

# =====================================================================================
# TRYB po-pushu: tylko czyta. Czeka na GitHub Pages dla HEAD repo sklepu i porownuje tresc.
# =====================================================================================
if [ "$TRYB" = "po-pushu" ]; then
  krok "repo sklepu wypchniete?"
  git -C "$SKLEP" fetch -q origin 2>/dev/null || ostrz "git fetch origin nie wyszedl - porownuje z ostatnim znanym origin/main"
  HEAD_SKLEP="$(git -C "$SKLEP" rev-parse HEAD)"
  ORIGIN_SKLEP="$(git -C "$SKLEP" rev-parse origin/main 2>/dev/null || echo brak)"
  if [ "$HEAD_SKLEP" = "$ORIGIN_SKLEP" ]; then ok "HEAD ${HEAD_SKLEP:0:7} = origin/main"
  else blad "HEAD ${HEAD_SKLEP:0:7} nie jest na origin/main (${ORIGIN_SKLEP:0:7}) - najpierw git push"; fi

  krok "GitHub Pages zbudowane dla TEGO commita (nie dla poprzedniego)"
  if [ "$NBLEDOW" -eq 0 ] && command -v gh >/dev/null 2>&1; then
    koniec=$(( $(date +%s) + CZEKAJ_S )); stan=""
    while :; do
      stan="$(gh api "repos/$REPO_GH/pages/builds/latest" --jq '.status + " " + .commit' 2>/dev/null || echo "blad-api -")"
      st="${stan%% *}"; cm="${stan#* }"
      if [ "$cm" = "$HEAD_SKLEP" ] && [ "$st" = "built" ]; then ok "Pages: built, commit ${cm:0:7}"; break; fi
      if [ "$cm" = "$HEAD_SKLEP" ] && [ "$st" = "errored" ]; then blad "Pages: budowanie commita ${cm:0:7} PADLO (errored)"; break; fi
      if [ "$(date +%s)" -ge "$koniec" ]; then blad "po ${CZEKAJ_S} s Pages dalej: '$stan' (czekam na built ${HEAD_SKLEP:0:7})"; break; fi
      info "Pages: '$st' dla ${cm:0:7} - czekam na ${HEAD_SKLEP:0:7} ..."; sleep 15
    done
  elif [ "$NBLEDOW" -eq 0 ]; then
    ostrz "brak gh - nie sprawdze commita zbudowanego przez Pages; zostaje porownanie tresci nizej"
  fi

  krok "co strona NAPRAWDE serwuje"
  t="$(date +%s)"                        # zapytanie z parametrem omija cache CDN
  if curl -fsS --max-time 30 "$STRONA/obrazy/SUMY.txt?t=$t" -o "$LOGI/SUMY-serwer.txt" 2>"$LOGI/curl.txt"; then
    if cmp -s "$LOGI/SUMY-serwer.txt" "$SKLEP/portal/obrazy/SUMY.txt"; then
      ok "obrazy/SUMY.txt na stronie = lokalny, bajt w bajt ($(head -1 "$LOGI/SUMY-serwer.txt"))"
    else
      blad "obrazy/SUMY.txt na stronie ROZNI SIE od lokalnego: serwer '$(head -1 "$LOGI/SUMY-serwer.txt")', lokalnie '$(head -1 "$SKLEP/portal/obrazy/SUMY.txt")'"
    fi
  else
    blad "nie pobralem $STRONA/obrazy/SUMY.txt ($(cat "$LOGI/curl.txt"))"
  fi
  for p in $PROFILE; do
    id="${p##*|}"
    if curl -fsS --max-time 30 "$STRONA/manifest-$id.json?t=$t" -o "$LOGI/manifest-$id.json" 2>/dev/null; then
      w="$(wersja_manifestu < "$LOGI/manifest-$id.json" || true)"
      if [ "$w" = "$WER" ]; then ok "manifest-$id.json na stronie: version $w"
      else blad "manifest-$id.json na stronie: version '$w', a wydajemy $WER"; fi
    else blad "nie pobralem manifest-$id.json ze strony"; fi
  done

  echo
  if [ "$NBLEDOW" -eq 0 ]; then
    echo "WYNIK: strona serwuje K-OS $WER. Ostatni krok (tez recznie) - podpowiedz \"jest nowy K-OS\" z pinga:"
    echo "   cd \"$KORZEN/k-os-stat\" && npx wrangler deploy --var KOS_WERSJA:$WER"
    echo "   (wrangler.toml: podbijac dopiero, gdy w portalu sa obrazy WSZYSTKICH plytek - zmienna jest jedna)"
    exit 0
  fi
  echo "WYNIK: NIE GOTOWE - $NBLEDOW blad(ow):"; printf '%s' "$BLEDY"; echo "logi: $LOGI"; exit 1
fi

# =====================================================================================
# TRYB pelny i --bez-budowania
# =====================================================================================
krok "1. stan repozytoriow"
if [ -n "$(git -C "$LOADER" status --porcelain)" ]; then
  blad "loader/ ma niezacommitowane zmiany - obraz nie odpowiadalby zadnemu commitowi:"
  git -C "$LOADER" status --porcelain | sed 's/^/          /'
else ok "loader/ czysty, HEAD $(git -C "$LOADER" rev-parse --short HEAD) ($(git -C "$LOADER" log -1 --format=%s | cut -c1-60))"; fi
PRZED_LOADER="$(git -C "$LOADER" rev-list --count '@{upstream}..HEAD' 2>/dev/null || echo '?')"
info "loader/: commitow niewypchnietych: $PRZED_LOADER"
if [ -n "$(git -C "$SKLEP" status --porcelain -- portal bin katalog.json 'katalog-*.json' plytki.json info)" ]; then
  ostrz "repo sklepu ma niezacommitowane zmiany w tresci sklepu - wejda do tego samego pusha:"
  git -C "$SKLEP" status --porcelain -- portal bin katalog.json 'katalog-*.json' plytki.json info | sed 's/^/          /'
else ok "repo sklepu: tresc sklepu bez niezacommitowanych zmian"; fi
PRZED_SKLEP="$(git -C "$SKLEP" rev-list --count origin/main..HEAD 2>/dev/null || echo '?')"
info "repo sklepu: commitow niewypchnietych: $PRZED_SKLEP (poleca razem z wydaniem)"

krok "2. numer wersji podbity? (FW_VERSION > opublikowany manifest)"
OPUB=""; SKAD=""
if curl -fsS --max-time 20 "$STRONA/manifest-cyd24.json?t=$(date +%s)" -o "$LOGI/manifest-serwer.json" 2>"$LOGI/curl-manifest.txt"; then
  OPUB="$(wersja_manifestu < "$LOGI/manifest-serwer.json" || true)"; SKAD="GitHub Pages"
else
  ostrz "strona nie odpowiada ($(cat "$LOGI/curl-manifest.txt")) - biore wersje z kopii w repo sklepu"
  OPUB="$(wersja_manifestu < "$SKLEP/portal/manifest-cyd24.json" || true)"; SKAD="repo sklepu (portal/manifest-cyd24.json)"
fi
OPUB="${WYDAJ_OPUBLIKOWANA:-$OPUB}"     # tylko do sprawdzenia samego skryptu
if ! jest_wersja "$OPUB"; then
  blad "nie umiem odczytac opublikowanej wersji ('$OPUB' z: $SKAD)"
else
  case "$(por_wersji "$WER" "$OPUB")" in
    1)  ok "version.h $WER > opublikowane $OPUB ($SKAD)" ;;
    0)  blad "NUMER NIEPODBITY: version.h mowi $WER, a opublikowane jest juz $OPUB ($SKAD). Kazde wydanie = nowy numer (loader/loader/version.h)." ;;
    *)  blad "version.h $WER jest STARSZE niz opublikowane $OPUB ($SKAD)" ;;
  esac
fi
LOK24="$(wersja_manifestu < "$SKLEP/portal/manifest-cyd24.json" || true)"
for p in $PROFILE; do
  id="${p##*|}"; w="$(wersja_manifestu < "$SKLEP/portal/manifest-$id.json" || true)"
  [ "$w" = "$LOK24" ] || ostrz "repo sklepu: manifest-$id.json ma version '$w', a manifest-cyd24.json '$LOK24' - manifesty rozjechane"
done
if [ "$SKAD" = "GitHub Pages" ] && [ "$LOK24" != "$OPUB" ]; then
  info "repo sklepu ma lokalnie manifest $LOK24, strona serwuje $OPUB - wydanie czeka na push?"
fi

krok "3. testy hostowe K-OS (loader/tests/run.sh)"
if [ -x "$LOADER/tests/run.sh" ]; then
  set +e; "$LOADER/tests/run.sh" > "$LOGI/testy.txt" 2>&1; rc=$?; set -e
  if [ "$rc" -eq 0 ]; then ok "testy hostowe: kod 0 (log: $LOGI/testy.txt)"
  else blad "testy hostowe: kod $rc - ostatnie linie:"; tail -15 "$LOGI/testy.txt" | sed 's/^/          /'; fi
else ostrz "brak $LOADER/tests/run.sh - testow hostowych nie ma"; fi

krok "4. budowanie trzech profili K-OS"
ZNACZNIK="$LOGI/start-budowania"; : > "$ZNACZNIK"; sleep 1     # binarka musi byc NOWSZA niz ten plik
if [ "$TRYB" = "pelny" ]; then
  [ "$NBLEDOW" -eq 0 ] || stop "$NBLEDOW blad(ow) przed budowaniem - najpierw je napraw (budowanie trwa kilka minut)"
  command -v arduino-cli >/dev/null 2>&1 || stop "brak arduino-cli"
  for p in $PROFILE; do
    IFS='|' read -r B P D I <<< "$p"
    L="$LOGI/budowanie-$I.txt"
    echo "   ...    $I: BOARD=$B${P:+ PANEL=$P} ./build.sh  (log: $L)"
    set +e
    # zmienne srodowiska, ktore build.sh bierze jako pokretla (INVERSION, SPI_MHZ, BUILDDIR, SKETCH),
    # zostaja wyczyszczone: wydanie ma miec flagi domyslne, a nie te z ostatniej proby w terminalu
    ( unset INVERSION SPI_MHZ BUILDDIR SKETCH; cd "$LOADER" && BOARD="$B" PANEL="${P:-ili9341}" ./build.sh ) > "$L" 2>&1
    rc=$?
    set -e
    if [ "$rc" -ne 0 ]; then
      tail -25 "$L" | sed 's/^/          /'
      stop "budowanie $I zakonczone kodem $rc - pelny log: $L"
    fi
    [ "$LOADER/$D/loader.ino.bin" -nt "$ZNACZNIK" ] || stop "$I: kod 0, ale $D/loader.ino.bin NIE jest z tego budowania (stary plik) - log: $L"
    ok "$I zbudowany (kod 0, binarka swieza)"
  done
else
  info "--bez-budowania: biore binarki, ktore leza w loader/.build-*"
fi

krok "5. binarki: swiezosc, magic, napisy, zapas w factory"
FACTORY="$(python3 - "$LOADER/partitions_loader.csv" <<'PY'
import csv, sys
for r in csv.reader(open(sys.argv[1])):
    if r and not r[0].lstrip().startswith("#") and r[0].strip() == "factory":
        print(int(r[4].strip(), 0)); break
PY
)"
[ -n "$FACTORY" ] || stop "nie znalazlem partycji factory w $LOADER/partitions_loader.csv"
HEAD_CZAS="$(git -C "$LOADER" log -1 --format=%ct)"
NAPISY="$WER"$'\n'"K-OS READY"$'\n'"KORONA-LOADER-OBRAZ-1"$'\n'"$NAPISY_DOD"
PODSUM=""
for p in $PROFILE; do
  IFS='|' read -r B P D I <<< "$p"
  BIN="$LOADER/$D/loader.ino.bin"
  if [ ! -f "$BIN" ]; then blad "$I: nie ma $BIN"; continue; fi
  SZ="$(rozmiar "$BIN")"; ZAPAS=$((FACTORY - SZ))
  CZAS="$(python3 -c 'import os,sys; print(int(os.path.getmtime(sys.argv[1])))' "$BIN")"
  if [ "$TRYB" = "bez-budowania" ]; then
    if [ "$CZAS" -lt "$HEAD_CZAS" ]; then blad "$I: binarka ($(date -r "$CZAS" '+%m-%d %H:%M')) STARSZA niz ostatni commit loader/ - przebuduj (tools/wydaj.sh bez --bez-budowania)"
    elif [ "$BIN" -ot "$LOADER/loader/version.h" ]; then blad "$I: binarka starsza niz version.h - przebuduj"
    else ok "$I: binarka z $(date -r "$CZAS" '+%Y-%m-%d %H:%M'), nowsza niz ostatni commit i version.h"; fi
  fi
  MAGIC="$(python3 -c 'import sys; print("%02x" % open(sys.argv[1],"rb").read(1)[0])' "$BIN")"
  [ "$MAGIC" = "e9" ] || blad "$I: pierwszy bajt 0x$MAGIC zamiast 0xE9 - to nie jest obraz aplikacji ESP32"
  BRAK=""
  while IFS= read -r n; do
    [ -n "$n" ] || continue
    ma_napis "$BIN" "$n" || BRAK="$BRAK '$n'"
  done <<< "$NAPISY"
  if [ -n "$BRAK" ]; then blad "$I: w binarce BRAK napisow:$BRAK"
  else ok "$I: napisy obecne ($(printf '%s' "$NAPISY" | grep -c . ) szt., w tym $WER i znacznik samoaktualizacji)"; fi
  if [ "$SZ" -gt "$FACTORY" ]; then blad "$I: obraz $(liczba "$SZ") B NIE MIESCI SIE w factory $(liczba "$FACTORY") B"
  elif [ "$ZAPAS" -lt "$ZAPAS_MIN" ]; then blad "$I: zapas w factory $(liczba "$ZAPAS") B - ponizej podlogi $(liczba "$ZAPAS_MIN") B"
  elif [ "$ZAPAS" -lt "$ZAPAS_OSTRZ" ]; then ostrz "$I: zapas w factory $(liczba "$ZAPAS") B - ponizej $(liczba "$ZAPAS_OSTRZ") B (kolejna funkcja musi przyjsc z oszczednoscia)"
  else ok "$I: zapas w factory $(liczba "$ZAPAS") B"; fi
  PODSUM="$PODSUM$(printf '   %-7s %11s B   zapas factory %8s B' "$I" "$(liczba "$SZ")" "$(liczba "$ZAPAS")")"$'\n'
done

krok "6. obrazy portalu (portal/zbuduj-obrazy.sh)"
if [ "$TRYB" = "pelny" ]; then
  if [ "$NBLEDOW" -ne 0 ]; then
    blad "obrazow portalu NIE skladam, bo sa bledy wyzej (zbuduj-obrazy.sh zapisuje do portal/)"
  else
    set +e; "$PORTAL/zbuduj-obrazy.sh" > "$LOGI/obrazy.txt" 2>&1; rc=$?; set -e
    if [ "$rc" -ne 0 ]; then blad "zbuduj-obrazy.sh: kod $rc - ostatnie linie:"; tail -15 "$LOGI/obrazy.txt" | sed 's/^/          /'
    else ok "zbuduj-obrazy.sh: kod 0 (log: $LOGI/obrazy.txt)"; fi
  fi
else
  info "--bez-budowania: obrazow nie skladam; w portal/ leza obrazy: $(head -1 "$PORTAL/obrazy/SUMY.txt" 2>/dev/null || echo 'brak SUMY.txt')"
fi
if [ "$TRYB" = "pelny" ] && [ "$NBLEDOW" -eq 0 ]; then
  L1="$(head -1 "$PORTAL/obrazy/SUMY.txt")"      # bez potoku head | grep (pipefail + SIGPIPE)
  case "$L1" in "# K-OS $WER "*) ;; *) blad "portal/obrazy/SUMY.txt nie mowi 'K-OS $WER': $L1" ;; esac
  for p in $PROFILE; do
    IFS='|' read -r B P D I <<< "$p"
    w="$(wersja_manifestu < "$PORTAL/manifest-$I.json" || true)"
    [ "$w" = "$WER" ] || blad "portal/manifest-$I.json: version '$w' zamiast $WER"
    grep -q "^$I/loader.bin " "$PORTAL/obrazy/SUMY.txt" || blad "portal/obrazy/SUMY.txt bez linii $I/loader.bin (samoaktualizacja jej szuka)"
    cmp -s "$PORTAL/obrazy/$I/loader.bin" "$LOADER/$D/loader.ino.bin" || blad "portal/obrazy/$I/loader.bin to nie jest binarka z $D"
    [ "$(rozmiar "$PORTAL/manifest-$I.json")" -lt "$IO_BUF" ] || blad "portal/manifest-$I.json ma >= $IO_BUF B - samoaktualizacja go nie przeczyta"
  done
  [ "$(rozmiar "$PORTAL/obrazy/SUMY.txt")" -lt "$IO_BUF" ] || blad "portal/obrazy/SUMY.txt ma >= $IO_BUF B - samoaktualizacja go nie przeczyta"
  [ "$NBLEDOW" -ne 0 ] || ok "portal/: SUMY.txt i 3 manifesty mowia $WER, obrazy = binarki, pliki < $IO_BUF B"
fi

krok "7. katalog sklepu (tools/katalog.py --sprawdz)"
set +e; python3 "$SKLEP/tools/katalog.py" --sprawdz > "$LOGI/katalog.txt" 2>&1; rc=$?; set -e
V2="$(sed -n 's/^katalog.json (v2[^)]*): .*programow, \([0-9]*\) B$/\1/p' "$LOGI/katalog.txt" | head -1)"
V2ZAPAS="$(sed -n 's/^  zapas v2: \(.*\)$/\1/p' "$LOGI/katalog.txt" | head -1)"
case "$rc" in
  0) ok "katalogi aktualne; v2 ${V2:-?} B (${V2ZAPAS:-zapas nieznany})" ;;
  1) blad "katalog.json (v2) ponad sufitem 26 000 B - generator nie zapisze NICZEGO:"; sed 's/^/          /' "$LOGI/katalog.txt" ;;
  3) blad "katalogi na dysku sa NIEAKTUALNE wobec bin/ i META - uruchom python3 tools/katalog.py i zacommituj:"; grep NIEAKTUALNE "$LOGI/katalog.txt" | sed 's/^/          /' || true ;;
  *) blad "tools/katalog.py --sprawdz: kod $rc"; tail -10 "$LOGI/katalog.txt" | sed 's/^/          /' ;;
esac

krok "8. portal/ a kopia w repo sklepu"
if diff -rq "$PORTAL" "$SKLEP/portal" > "$LOGI/portal-diff.txt" 2>&1; then
  ok "portal/ i korona-programy/portal/ identyczne"
else
  info "rsync przeniesie do repo sklepu ($(grep -c . "$LOGI/portal-diff.txt") roznic, pelna lista: $LOGI/portal-diff.txt):"
  head -12 "$LOGI/portal-diff.txt" | sed "s|$KORZEN/||g; s/^/          /"
fi

krok "9. GitHub Pages teraz"
if command -v gh >/dev/null 2>&1; then
  stan="$(gh api "repos/$REPO_GH/pages/builds/latest" --jq '.status + " " + .commit' 2>/dev/null || echo "?")"
  info "Pages: ${stan%% *}, commit $(printf '%s' "${stan#* }" | cut -c1-7); origin/main $(git -C "$SKLEP" rev-parse --short origin/main 2>/dev/null || echo '?'), lokalny HEAD $(git -C "$SKLEP" rev-parse --short HEAD)"
else info "brak gh - stanu Pages nie sprawdzam"; fi

echo
echo "================================================================================"
printf '%s' "$PODSUM"
echo "   katalog.json (v2): ${V2:-?} B z 26 000 B; ${V2ZAPAS:-}"
echo "   logi: $LOGI"
echo "================================================================================"
if [ "$NOSTRZ" -gt 0 ]; then echo "OSTRZEZENIA ($NOSTRZ):"; printf '%s' "$OSTRZ"; fi
if [ "$NBLEDOW" -gt 0 ]; then
  echo "WYNIK: NIE GOTOWE - $NBLEDOW blad(ow). Nic nie publikowac:"; printf '%s' "$BLEDY"
  exit 1
fi
if [ "$TRYB" = "bez-budowania" ]; then
  echo "WYNIK: KONTROLA PRZESZLA na binarkach z loader/.build-*. Do wydania potrzebny pelny bieg"
  echo "       (tools/wydaj.sh) - on sklada obrazy portalu. Nic nie zostalo zmienione."
  exit 0
fi
cat <<EOF
WYNIK: GOTOWE DO PUBLIKACJI K-OS $WER. NIC NIE ZOSTALO WYPCHNIETE - komendy do wykonania recznie:

  # 1. test na plytce (Piotr) - ./flash.sh, NIGDY ./build.sh upload (gubi knvs):
  cd "$LOADER" && ./flash.sh                                            # cyd24
  cd "$LOADER" && BUILDDIR="$LOADER/.build-28R" ./flash.sh              # cyd28
  cd "$LOADER" && BUILDDIR="$LOADER/.build-28R-st7789" ./flash.sh       # cyd28s

  # 2. strona do repo sklepu (repo PUBLICZNE) i do prywatnej kopii zrodel:
  rsync -a --delete "$PORTAL/" "$SKLEP/portal/"
  cd "$SKLEP" && git add portal && git commit -m "K-OS $WER: ..." && git push
  cd "$KORZEN" && git add portal && git commit -m "portal: K-OS $WER" && git push
  cd "$LOADER" && git push

  # 3. poczekaj na GitHub Pages dla TEGO commita i sprawdz, co strona serwuje:
  "$TOOLS/wydaj.sh" po-pushu > wydaj-po-pushu.log 2>&1; echo \$?

  # 4. dopiero po udanym "po-pushu": podpowiedz "jest nowy K-OS" z dziennego pinga
  cd "$KORZEN/k-os-stat" && npx wrangler deploy --var KOS_WERSJA:$WER
EOF
exit 0
