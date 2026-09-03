# KORONA - sklep programow dla K-OS

Serwerek z programami (.bin) dla **K-OS - KORONA OS for CYD** (menu programow na ESP32
"Cheap Yellow Display"). K-OS pobiera `katalog.json` i wybrany `.bin`
wprost z tego repo (raw.githubusercontent.com).

## Uklad

```
katalog.json                      format v2: lista plytek, w kazdej lista programow
bin/cyd24/*.bin                   CYD 2.4"  (ESP32-2432S024) - programy sklepu (META w tools/katalog.py)
bin/cyd28/*.bin                   CYD 2.8"  (ESP32-2432S028R)
bin/<plytka>/uzytkownicy/*.bin    programy uzytkownikow + <nazwa>.meta.json obok (META z pliku)
zgloszenia/<id>/                  skrzynka na nowe zgloszenia (PR); po merge automat ja oproznia
tools/katalog.py                  generuje katalog.json z bin/ (tabela META + *.meta.json)
tools/sprawdz_bin.py              czy .bin nadaje sie do slotu ota_0 (czysty/scalony, rozmiar, app_desc)
tools/sprawdz_zgloszenie.py       walidator zgloszenia (meta.json + .bin)
tools/przyjmij_zgloszenia.py      przenosi poprawne zgloszenia do bin/<plytka>/uzytkownicy/
portal/                           strona instalacyjna (GitHub Pages) + poradnik dla autorow (programy.html)
.github/workflows/zgloszenie.yml  PR z zgloszeniem -> walidacja + komentarz
.github/workflows/przyjmij.yml    merge do main -> przeniesienie + katalog.json + commit bota
```

Kazdy program to pelny obraz aplikacji ESP32 (magic 0xE9), mieszczacy sie w
slocie ota_0 K-OS (2 555 904 B). Program MUSI na poczatku `setup()` kasowac
partycje otadata ("Model B"), inaczej po resecie nie wroci do K-OS.
Szczegoly dla autorow: https://pixelpetrol.github.io/korona-programy/portal/programy.html

## Dodanie programu sklepu (autorskie / zewnetrzne)

1. wrzuc `.bin` do `bin/<plytka>/`,
2. dopisz wpis w `META` w `tools/katalog.py` (nazwa, opis, wersja, kategoria, autor, info),
3. `python3 tools/katalog.py`,
4. `git add -A && git commit && git push`.

K-OS na plytce X pokazuje domyslnie programy dla X; przyciskiem
"inne plytki" mozna pobrac program dla innej plytki (np. przed przeniesieniem karty).

## Programy uzytkownikow (kategoria `uzytkownicy`)

Kazdy moze zglosic swoj program. Procedura:

1. Przygotuj program wedlug poradnika `portal/programy.html` (Model B, flagi plytki,
   rozmiar <= 2 555 904 B, czysty obraz aplikacji). Przetestuj na plytce: uruchom pod K-OS,
   nacisnij RST - musi wrocic menu.
2. Zrob fork repo i dodaj katalog `zgloszenia/<id>/` z dwoma plikami: `<id>.bin` i `meta.json`
   (szablon i opis pol: `zgloszenia/README.md`). `<id>` = male litery, cyfry, `-`, `_`; to bedzie
   nazwa pliku w sklepie i klucz ustawien na karcie - nie zmienia sie po publikacji.
3. Sprawdz lokalnie: `python3 tools/sprawdz_zgloszenie.py zgloszenia/<id>`.
4. Otworz Pull Request. Action `zgloszenie` sprawdza zgloszenie i wkleja raport (rozmiar,
   sha256, app_desc, bledy). Czerwony check = popraw i wypchnij jeszcze raz.
5. Przegladajacy (Piotr) robi to, czego automat nie umie: wgrywa `.bin` na karte, uruchamia,
   naciska RST. Jesli menu wraca i licencja/autorstwo sie zgadzaja - merge.
6. Po merge Action `przyjmij` przenosi `.bin` do `bin/<plytka>/uzytkownicy/<id>.bin`, zapisuje
   `<id>.meta.json` obok, przebudowuje `katalog.json` i commituje jako `github-actions[bot]`.
   K-OS widzi program po kilku minutach (raw.githubusercontent cache).

Aktualizacja: ten sam `<id>`, wyzsza `wersja`, znowu PR. Zgloszenie moze byc scalonym obrazem
flasha (bootloader + tablica + aplikacja) - automat wycina z niego aplikacje, ale lepiej
wysylac czysty `firmware.bin` / `*.ino.bin`.

Reguly: `autor` to autor programu (przy porcie - oryginalny autor, zglaszajacy w polu
`zglaszajacy`); GPL wymaga `zrodlo`; `model_b: true` to oswiadczenie autora. Programy, ktore
po RST nie wracaja do menu, nie beda przyjete - plytke odzyskuje sie wtedy tylko po USB.

Dla przegladajacego: PR z forka moze zmieniac tez `tools/` i `.github/` - Action ostrzega o
plikach poza `zgloszenia/`; takich PR nie scalac bez przeczytania roznicy.

### Jak K-OS traktuje kategorie

`katalog.json` ma pole `kategoria`: `autorskie`, `zewnetrzne`, `uzytkownicy`. K-OS <= 0.3.6
zna dwie pierwsze i wszystko, co nie jest `autorskie`, pokazuje w "zewnetrzne" (`net.cpp`,
`progInCat`) - stare wersje zobacza programy uzytkownikow w tej zakladce. Nowszy K-OS ma
pokazywac trzecia zakladke "uzytkownicy" (programy zgloszone przez uzytkownikow, sprawdzone
tylko formalnie: rozmiar, format, reset -> menu; za tresc odpowiada autor).
