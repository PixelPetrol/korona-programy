# KORONA - programy dla plytek CYD

Serwerek z programami (.bin) dla ladowarki **KORONA** (menu-bootloader na ESP32
"Cheap Yellow Display"). Ladowarka pobiera `katalog.json` i wybrany `.bin`
wprost z tego repo (raw.githubusercontent.com).

## Uklad

```
katalog.json          format v2: lista plytek, w kazdej lista programow
bin/cyd24/*.bin       CYD 2.4"  (ESP32-2432S024)
bin/cyd28/*.bin       CYD 2.8"  (ESP32-2432S028R)
tools/katalog.py      generuje katalog.json z bin/ i tabeli META (nazwa/opis/wersja)
```

Kazdy program to pelny obraz aplikacji ESP32 (magic 0xE9), mieszczacy sie w
slocie ota_0 ladowarki (2560 KB). Program MUSI na poczatku `setup()` kasowac
partycje otadata ("Model B"), inaczej po resecie nie wroci do ladowarki.

## Dodanie programu

1. wrzuc `.bin` do `bin/<plytka>/`,
2. dopisz wpis w `META` w `tools/katalog.py` (nazwa, opis, wersja),
3. `python3 tools/katalog.py`,
4. `git add -A && git commit && git push`.

Ladowarka na plytce X pokazuje domyslnie programy dla X; przyciskiem
"inne plytki" mozna pobrac program dla innej plytki (np. przed przeniesieniem karty).
