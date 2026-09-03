#!/bin/bash
# K-OS (KORONA OS for CYD) - skladanie obrazow dla portalu instalacyjnego (ESP Web Tools).
#
# Bierze GOTOWE wyniki builda z loader/.build-24 i loader/.build-28R i uklada
# je w portal/obrazy/<plytka>/ tak, jak je ma serwowac GitHub Pages.
#
# TEN SKRYPT NICZEGO NIE WGRYWA NA PLYTKE. Nie dotyka portu szeregowego,
# nie wola flash.sh ani arduino-cli. Uzywa wylacznie narzedzi hostowych:
#   gen_esp32part.py (rdzen esp32 3.3.11)  - tablica partycji z CSV
#   esptool >= 5.x, podkomenda merge-bin   - scalony obraz dla wiersza polecen
#
# Kolejnosc jest celowa: NAJPIERW kontrola obu plytek (istnieje, magic 0xE9,
# nie starszy niz version.h, miesci sie w factory), DOPIERO POTEM kopiowanie,
# manifesty, index.html i SUMY.txt. Kazdy blad przerywa skrypt PRZED zapisem
# czegokolwiek do portalu - nie ma stanu "manifest mowi 0.3.6, binarka ma 0.3.0".
#
# Uzycie:
#   ./zbuduj-obrazy.sh              - sklada to, co jest zbudowane
#   SCALONY=0 ./zbuduj-obrazy.sh    - bez scalonego obrazu (szybciej; strona
#                                     linkuje korona-*-scalony.bin, wiec do
#                                     publikacji zawsze z domyslnym SCALONY=1)
#
# Kompilacja to OSOBNY krok, robiony recznie w loader/:
#   ./build.sh            (2.4")
#   BOARD=28R ./build.sh  (2.8")
#
# Przenosnosc: pisane i sprawdzane na macOS. Rozmiar pliku i czas modyfikacji
# ida przez python3 (nie `stat -f`/`date -r`), sort -V jest w GNU i BSD sort -
# na Linuksie powinno dzialac, ale nie bylo tam uruchamiane.

set -euo pipefail
export PATH="/opt/homebrew/bin:$PATH"
HERE="$(cd "$(dirname "$0")" && pwd)"
LOADER="$(cd "$HERE/.." && pwd)/loader"
OUT="$HERE/obrazy"
CORE="$HOME/Library/Arduino15/packages/esp32/hardware/esp32/3.3.11"
ESPTOOL_BAZA="$HOME/Library/Arduino15/packages/esp32/tools/esptool_py"
SCALONY="${SCALONY:-1}"

# --- offsety: JEDNO zrodlo prawdy to loader/flash.sh ---
OFF_BOOTLOADER=0x1000
OFF_PARTITIONS=0x8000
OFF_OTADATA=0xe000
OFF_FACTORY=0x10000

blad() { echo; echo "BLAD: $*" >&2; exit 1; }
rozmiar() { python3 -c 'import os,sys; print(os.path.getsize(sys.argv[1]))' "$1"; }
data_pliku() { python3 -c 'import os,sys,time; print(time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(sys.argv[1]))))' "$1"; }

# --- pliki tymczasowe: osobny katalog, sprzatany ZAWSZE (takze po bledzie) ---
TMP="$(mktemp -d "${TMPDIR:-/tmp}/korona-obrazy.XXXXXX")"
sprzataj() {
  local rc=$?          # kod wyjscia skryptu - trap nie moze go zgubic
  rm -rf "$TMP"
  # slady po starych wersjach skryptu, ktore trzymaly tymczasowki na gorze obrazy/
  rm -f "$OUT/partitions.bin" "$OUT/otadata-pusta.bin"
  [ "$rc" = "0" ] || echo "PRZERWANE (kod $rc) - portal NIE jest gotowy do publikacji." >&2
  exit "$rc"
}
trap sprzataj EXIT

[ -d "$LOADER" ] || blad "nie widze $LOADER"

# --- narzedzia ---------------------------------------------------------------
GENPART="$(find "$CORE" -name gen_esp32part.py 2>/dev/null | head -1)"
[ -n "$GENPART" ] || blad "brak gen_esp32part.py w $CORE"

# esptool: najnowszy zainstalowany, sortowanie po numerze wersji (sort -V),
# nie tekstem - inaczej "10.0.0" wypadloby przed "4.5.1".
ESPTOOL=""
if [ -d "$ESPTOOL_BAZA" ]; then
  while IFS= read -r wer_kat; do
    [ -x "$ESPTOOL_BAZA/$wer_kat/esptool" ] && ESPTOOL="$ESPTOOL_BAZA/$wer_kat/esptool"
  done < <(ls "$ESPTOOL_BAZA" | sort -V)
fi
[ -n "$ESPTOOL" ] || ESPTOOL="$(command -v esptool || true)"
if [ "$SCALONY" = "1" ]; then
  [ -n "$ESPTOOL" ] || blad "nie widze esptool (ani w $ESPTOOL_BAZA, ani w PATH).
       Strona linkuje korona-*-scalony.bin, wiec bez esptool nie ma czego publikowac.
       Zainstaluj rdzen esp32 3.3.x (ma esptool 5.x) albo: pip install 'esptool>=5'."
  if ! "$ESPTOOL" merge-bin --help >/dev/null 2>&1; then
    if "$ESPTOOL" merge_bin --help >/dev/null 2>&1; then
      blad "$ESPTOOL to esptool 4.x (podkomenda merge_bin). Ten skrypt wymaga esptool 5.x (merge-bin)."
    fi
    blad "$ESPTOOL nie rozumie podkomendy merge-bin - wymagany esptool 5.x."
  fi
fi

# --- wersja K-OS z version.h -> pole "version" w manifestach ---
WER="$(sed -n 's/.*FW_VERSION[^"]*"\([^"]*\)".*/\1/p' "$LOADER/loader/version.h" | head -1)"
[ -n "$WER" ] || blad "nie umiem odczytac FW_VERSION z loader/loader/version.h"
echo "K-OS $WER"
[ -n "$ESPTOOL" ] && echo "esptool: $ESPTOOL"
echo

# --- tablica partycji z CSV (NIE z builda!) ---------------------------------
# W .build-*/ lezy loader.ino.partitions.bin, ale to tablica ARDUINO (huge_app:
# app0=ota_0 pod 0x10000, 3 MB, bez factory). Tablica KORONY jest w
# loader/partitions_loader.csv i tylko ona ma factory + ota_0 + knvs.
python3 "$GENPART" "$LOADER/partitions_loader.csv" "$TMP/partitions.bin" >/dev/null

FACTORY_SIZE="$(python3 - "$LOADER/partitions_loader.csv" <<'PY'
import sys, csv
with open(sys.argv[1], encoding="utf-8") as f:
    for row in csv.reader(f):
        if row and not row[0].startswith('#') and row[0].strip() == 'factory':
            print(int(row[4].strip(), 0)); break
PY
)"
[ -n "$FACTORY_SIZE" ] || blad "nie znalazlem partycji factory w partitions_loader.csv"

# --- pusta otadata (8 KB 0xFF) ----------------------------------------------
# flash.sh robi to przez `esptool erase_region 0xe000 0x2000`. Manifest ESP Web
# Tools nie umie kasowac regionu, umie tylko ZAPISAC plik pod offsetem - wiec
# zapisujemy 8192 bajtow 0xFF, co daje dokladnie ten sam stan flasha:
# otadata "czysta" -> bootloader startuje partycje factory (K-OS).
# NIE WOLNO tu uzyc boot_app0.bin z katalogu builda: ten plik ma ota_seq=1 z
# poprawnym CRC, czyli mowi bootloaderowi "startuj ota_0" - dokladnie odwrotnie
# niz chcemy (wystartowalby stary program albo pusty slot).
python3 - "$TMP/otadata-pusta.bin" <<'PY'
import sys
with open(sys.argv[1], 'wb') as f:
    f.write(b'\xff' * 0x2000)
PY

# --- plytki ------------------------------------------------------------------
# (bash 3.2 z macOS nie ma tablic asocjacyjnych - stad funkcje)
PLYTKI=(24 28R)
id_plytki()   { case "$1" in 24) echo cyd24 ;; 28R) echo cyd28 ;; *) blad "nieznana plytka $1" ;; esac; }
opis_plytki() { case "$1" in 24) echo 'CYD 2.4" ESP32-2432S024R' ;; 28R) echo 'CYD 2.8" ESP32-2432S028R - NIESPRAWDZONA' ;; esac; }

# ETAP 1: kontrola. Nic nie pisze do obrazy/. Kazdy problem = przerwanie.
sprawdz() {   # sprawdz <BOARD>
  local B="$1" SRC="$LOADER/.build-$1" BIN I O
  I="$(id_plytki "$B")"; O="$(opis_plytki "$B")"
  BIN="$SRC/loader.ino.bin"
  local JAK="cd loader && $([ "$B" = 24 ] || echo "BOARD=$B ")./build.sh"
  [ -f "$BIN" ] || blad "$I ($O): nie ma $BIN
       Zbuduj:  $JAK"
  [ -f "$SRC/loader.ino.bootloader.bin" ] || blad "$I: nie ma $SRC/loader.ino.bootloader.bin - przebuduj:  $JAK"

  local BS MAGIC
  BS="$(rozmiar "$BIN")"
  # magic 0xE9 - ten sam warunek, ktory ma sprawdzac self-update
  MAGIC="$(python3 -c "import sys; print('0x%02X' % open(sys.argv[1],'rb').read(1)[0])" "$BIN")"
  echo "== $I ($O)"
  printf "   loader.ino.bin    %9d B   build z %s   magic %s\n" "$BS" "$(data_pliku "$BIN")" "$MAGIC"
  [ "$MAGIC" = "0xE9" ] || blad "$I: $BIN nie zaczyna sie od 0xE9 - to nie jest obraz ESP32. Przebuduj:  $JAK"
  # Obraz starszy niz version.h = w manifescie bylaby wersja, ktorej ta binarka nie ma.
  if [ "$BIN" -ot "$LOADER/loader/version.h" ]; then
    blad "$I: obraz jest STARSZY niz loader/loader/version.h ($WER, $(data_pliku "$LOADER/loader/version.h")).
       Nic nie zostalo zapisane do portalu. Przebuduj i uruchom ponownie:
         $JAK
         cd ../portal && ./zbuduj-obrazy.sh"
  fi
  if [ "$BS" -gt "$FACTORY_SIZE" ]; then
    blad "$I: loader.ino.bin ($BS B) NIE MIESCI SIE w partycji factory ($FACTORY_SIZE B, brakuje $((BS - FACTORY_SIZE)) B).
       Portal by zamurowal plytke. Nic nie zostalo zapisane. Odchudz K-OS (grafiki/fonty) i przebuduj:  $JAK"
  fi
  printf "   partycja factory  %9d B   zapas %d B (%.1f%%)\n" "$FACTORY_SIZE" "$((FACTORY_SIZE - BS))" \
    "$(python3 -c 'import sys; print(100.0*int(sys.argv[1])/int(sys.argv[2]))' "$((FACTORY_SIZE - BS))" "$FACTORY_SIZE")"
}

for B in "${PLYTKI[@]}"; do sprawdz "$B"; done
echo "kontrola OK - obie plytki maja swiezy obraz $WER mieszczacy sie w factory"
echo

# ETAP 2: kopiowanie. Katalog plytki kasowany w calosci - stare pliki nie moga
# zostac i trafic do SUMY.txt.
WYTWORZONE=()
sklej() {   # sklej <BOARD>
  local B="$1" SRC="$LOADER/.build-$1" I DST
  I="$(id_plytki "$B")"; DST="$OUT/$I"
  rm -rf "$DST"
  mkdir -p "$DST"
  cp "$SRC/loader.ino.bin"            "$DST/loader.bin"
  cp "$SRC/loader.ino.bootloader.bin" "$DST/bootloader.bin"
  cp "$TMP/partitions.bin"            "$DST/partitions.bin"
  cp "$TMP/otadata-pusta.bin"         "$DST/otadata-pusta.bin"
  WYTWORZONE+=("$I/loader.bin" "$I/bootloader.bin" "$I/partitions.bin" "$I/otadata-pusta.bin")

  echo "== $I -> obrazy/$I/"
  printf "   loader.bin        %9d B   pod %s (factory)\n" "$(rozmiar "$DST/loader.bin")" "$OFF_FACTORY"
  printf "   bootloader.bin    %9d B   pod %s\n" "$(rozmiar "$DST/bootloader.bin")" "$OFF_BOOTLOADER"
  printf "   partitions.bin    %9d B   pod %s\n" "$(rozmiar "$DST/partitions.bin")" "$OFF_PARTITIONS"
  printf "   otadata-pusta.bin %9d B   pod %s (8 KB 0xFF = start z factory)\n" "$(rozmiar "$DST/otadata-pusta.bin")" "$OFF_OTADATA"

  if [ "$SCALONY" = "1" ]; then
    # Scalony obraz dla wiersza polecen (Firefox/Safari/Linux - patrz README).
    # Luki miedzy czesciami merge-bin wypelnia 0xFF - w tym partycje nvs
    # (0x9000-0xe000), ktorej droga WebSerial nie rusza. Patrz README.
    "$ESPTOOL" --chip esp32 merge-bin --format raw -o "$DST/korona-$I-scalony.bin" \
      --target-offset 0x0 --flash-mode dio --flash-freq 80m --flash-size 4MB \
      "$OFF_BOOTLOADER" "$DST/bootloader.bin" \
      "$OFF_PARTITIONS" "$DST/partitions.bin" \
      "$OFF_OTADATA"    "$DST/otadata-pusta.bin" \
      "$OFF_FACTORY"    "$DST/loader.bin" >/dev/null
    WYTWORZONE+=("$I/korona-$I-scalony.bin")
    printf "   scalony obraz     %9d B   korona-%s-scalony.bin (pod 0x0)\n" \
      "$(rozmiar "$DST/korona-$I-scalony.bin")" "$I"
  else
    echo "   scalony obraz     POMINIETY (SCALONY=0) - do publikacji uruchom bez SCALONY=0"
  fi
  echo
}

mkdir -p "$OUT"
for B in "${PLYTKI[@]}"; do sklej "$B"; done

# ETAP 3: wersja w index.html i manifestach - dopiero po udanych kontrolach
# i kopiowaniu OBU plytek, wiec wersja w manifescie zawsze odpowiada binarce.

# Strona ma znacznik <!--WER-->..<!--/WER-->, zeby nie przepisywac numeru recznie.
python3 - "$HERE/index.html" "$WER" <<'PY'
import re, sys
p, wer = sys.argv[1], sys.argv[2]
with open(p, encoding='utf-8') as f:
    h = orig = f.read()
h, n = re.subn(r'(<!--WER-->).*?(<!--/WER-->)', lambda m: m.group(1) + wer + m.group(2), h, flags=re.S)
if n == 0:
    print("  index.html: brak znacznika <!--WER-->..<!--/WER--> - wersji nie wpisano")
elif h != orig:
    with open(p, 'w', encoding='utf-8') as f:
        f.write(h)
    print("  index.html -> wersja %s" % wer)
else:
    print("  index.html ma juz wersje %s" % wer)
PY

for B in "${PLYTKI[@]}"; do
  M="$HERE/manifest-$(id_plytki "$B").json"
  [ -f "$M" ] || blad "brak $M"
  python3 - "$M" "$WER" <<'PY'
import json, sys
p, wer = sys.argv[1], sys.argv[2]
with open(p, encoding="utf-8") as f:
    d = json.load(f)          # dict zachowuje kolejnosc kluczy (py>=3.7)
nazwa = p.rsplit('/', 1)[-1]
if d.get("version") != wer:
    d["version"] = wer
    with open(p, "w", encoding="utf-8") as f:
        f.write(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    print("  %s -> version %s" % (nazwa, wer))
else:
    print("  %s ma juz version %s" % (nazwa, wer))
PY
done
echo

# --- sumy kontrolne: TYLKO pliki wytworzone w tym biegu -----------------------
{
  echo "# K-OS $WER - obrazy portalu, $(date '+%Y-%m-%d %H:%M')"
  echo "# offsety: bootloader $OFF_BOOTLOADER, tablica $OFF_PARTITIONS, otadata $OFF_OTADATA, factory (K-OS) $OFF_FACTORY"
  echo "# partycja factory: $FACTORY_SIZE B"
  echo
  for f in "${WYTWORZONE[@]}"; do
    printf "%-46s %9d  %s\n" "$f" "$(rozmiar "$OUT/$f")" "$(shasum -a 256 "$OUT/$f" | cut -c1-64)"
  done
} > "$OUT/SUMY.txt"
echo "sumy kontrolne: obrazy/SUMY.txt"
sed 's/^/  /' "$OUT/SUMY.txt"
echo
echo "GOTOWE: cyd24 cyd28 (K-OS $WER). Publikacja: patrz README.md §4."
