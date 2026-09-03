# Samoaktualizacja K-OS — projekt (bez kodu)

Autor: Piotr Korona. Dokument opisuje **plan**, nie implementację — w `loader/` nic tu nie
jest zmieniane. Pozycja 1 z kolejki w `SPEC-LADOWARKA.md` („portal + self-update”).

Cel: K-OS aktualizuje **sam siebie** z repo `korona-programy`, bez kabla USB i bez
Maca — z tego samego katalogu obrazów, który serwuje portal
(`portal/obrazy/<płytka>/loader.bin`).

---

## 1. Dlaczego to w ogóle jest wykonalne

Tablica partycji (`loader/partitions_loader.csv`):

```
otadata    0xe000    0x2000    (8 KB)
factory    0x10000   0x160000  (1408 KB = 1 441 792 B)  <- K-OS
ota_0      0x170000  0x270000  (2496 KB = 2 555 904 B)  <- slot roboczy
```

Obraz aplikacji ESP32 **nie jest przywiązany do offsetu**: kod wykonywany z flasha jest
mapowany przez MMU na stały adres wirtualny, a bootloader mapuje tę partycję, którą
wybrał. Ten sam bajt w bajt `loader.bin` działa z `factory` i z `ota_0` — dlatego
kopiowanie `factory` ↔ `ota_0` jest legalne. To dokładnie ta sama własność, na której stoi
`flashAndBoot()` w `loader/loader/sdprog.cpp`: aplikacja zbudowana pod „huge_app”
z app0 na `0x10000` startuje z `ota_0` na `0x170000`.

Warunek: obraz nie może **sam** twardo zakładać, z której partycji działa. Wszędzie
`esp_ota_get_running_partition()`, nigdy stały adres.

---

## 2. Przepływ (4 etapy, każdy przerywalny)

Etap 0 i 1 dzieją się w starej ładowarce (`factory`), etap 2–3 w nowej (`ota_0`).

### Etap 0 — pobranie i sprawdzenie

Źródło: `STORE_BASE` z `loader/loader/net.cpp`, czyli
`https://raw.githubusercontent.com/PixelPetrol/korona-programy/main/` +
`portal/obrazy/<BOARD_ID>/loader.bin`. Obok tego plik `loader.json` (do dopisania w repo)
z polami: `wersja`, `plik`, `rozmiar`, `sha256`, `plytka` — ten sam wzór, co `katalog.json`
(`tools/katalog.py` już liczy sha256).

Pobieranie na **kartę SD**, do `/korona/loader-<wersja>.bin`, przez istniejący
`downloadToCard()` z `loader/loader/net.cpp`. Karta jako poczekalnia daje trzy rzeczy:
warunek STOP z `Content-Length` (już zaimplementowany), możliwość ponowienia bez WiFi
i kopię awaryjną poprzedniej wersji.

Sprawdzenia **przed** dotknięciem flasha (kolejność ma znaczenie):

1. `plytka == BOARD_ID` — obraz cyd28 na cyd24 to złe piny dotyku i podświetlenia
   (`build.sh`: BL 27 vs 21, dotyk XPT2046 na magistrali LCD vs bit-bang 25/32/39/33).
   Płytka wystartuje, ale ekran/dotyk będą martwe. Wyjście: portal albo `flash.sh`.
2. pierwszy bajt pliku `== 0xE9` (magic obrazu ESP32). `zbuduj-obrazy.sh` sprawdza to samo
   na hoście, żeby portal nie serwował śmiecia.
3. `rozmiar <= 1 441 792` (partycja `factory`). **Tu jest ciasno:** K-OS 0.3.6 na cyd24
   to 1 359 744 B, czyli zapas 82 048 B = 5,7 % (aktualne liczby: `portal/obrazy/SUMY.txt`).
   Komunikat błędu musi podać obie liczby, bo to realny scenariusz („nowa wersja się nie
   mieści").
4. sha256 pliku na karcie == sha256 z `loader.json`. Bez tego pół-pobrany obraz
   pojedzie do `ota_0`.

Dodatkowo warto sprawdzić, że pobrany obraz **jest K-OS**, a nie zwykłą aplikacją ze
sklepu (inaczej „aktualizacja” zamieniłaby `factory` na program bez drogi powrotu). Prosto:
osobny plik `loader.json` (nie `katalog.json`) i osobny ekran w menu; twardo:
marker w obrazie (np. `esp_app_desc_t.project_name == "korona-loader"` — do sprawdzenia,
co Arduino wpisuje w `project_name`).

### Etap 1 — karta → `ota_0`, boot z `ota_0`

Ten kod już istnieje: `flashAndBoot()`. Do samoaktualizacji trzeba go **rozgałęzić**, bo
różni się końcówka:

| krok | uruchomienie aplikacji | samoaktualizacja |
|---|---|---|
| `esp_ota_begin/write/end` na `ota_0` | tak | tak (identycznie) |
| `appStateRestore(nazwa)` | tak | **nie** — startuje K-OS, nie aplikacja |
| `setLastApp(nazwa)` | tak | **nie** |
| `setStateDirtyApp(nazwa)` | tak | **nie**, wręcz `setStateDirtyApp("")` |
| flaga w `knvs` | nie | **`selfupd` = sha256 oczekiwany** |
| `esp_ota_set_boot_partition(ota_0)` | tak | tak |

Flaga **musi** siedzieć w `knvs` (0x3FC000), a nie w `nvs` (0x9000): `nvs` należy do
aplikacji i jest nadpisywany migawką przy każdym starcie aplikacji — flaga zniknęłaby
w najgorszym momencie. Narzędzie już jest: `prOpen()` w `loader/loader/settings.cpp` woła
`pr.begin(NVS_NS, ro, KORONA_NVS_PART)`, czyli `Preferences` z etykietą partycji `knvs`.

`esp_restart()` → bootloader czyta `otadata` → startuje `ota_0` → **nowy** K-OS.

### Etap 2 — nowy K-OS kopiuje się do `factory`

**Ten test musi być pierwszą rzeczą w `setup()`**, przed `sdMount()`,
`appStateSaveIfDirty()`, `netBegin()` i przed blokiem autostartu w `setup()`
(`loader/loader/loader.ino`, komentarz „autostart: odliczanie na ekranie startowym”).
Powód: autostart z zapisanym `lastApp` zrobiłby `flashAndBoot()`, a to `esp_ota_begin()` na
`ota_0` — czyli skasowanie partycji, z której właśnie działamy jako źródła kopii. Kolejność
tutaj jest kwestią „działa / nie działa”, nie estetyki.

Logika (idempotentna, bo etap może się powtórzyć po zaniku prądu):

```
run = esp_ota_get_running_partition()
flaga = knvs["selfupd"]
jeśli !flaga            -> normalny start, koniec
jeśli run == factory    -> kopiowanie już się udało (albo prąd padł po skasowaniu
                           otadata, przed czyszczeniem flagi): wyczyść flagę,
                           pokaż "zaktualizowano do <wersja>", normalny start
jeśli run == ota_0      -> kopiuj do factory (niżej)
```

Kopiowanie `ota_0` → `factory`:

- **Nie używamy API OTA do zapisu `factory`.** Nagłówek `esp_ota_begin()` w `esp_ota_ops.h`
  mówi tylko `ESP_ERR_INVALID_ARG: partition doesn't point to an OTA app partition` — czy
  podtyp `factory` przez to przechodzi, **nie zostało w tym projekcie sprawdzone**, a to
  nie jest miejsce na eksperyment. Trzeba surowo:
  `esp_partition_erase_range(factory, 0, rozmiar_zaokrąglony_do_4096)` a potem
  `esp_partition_write()` blokami po 4096 B, czytając źródło `esp_partition_read(run, ...)`.
- Czytanie z partycji, z której się wykonuje kod, jest bezpieczne
  (`esp_partition_read` sam ogarnia cache); zapis idzie do partycji, z której nic nie działa.
- Kasować i zapisywać **tylko tyle, ile ma obraz**, plus dopełnienie do 4 KB — nie cała
  1408 KB. Krócej = mniejsze okno na zanik prądu.
- Postęp na ekran przez istniejące `loadingScreen()` / `loadingBar()`.

Po zapisie: **odczytaj `factory` z powrotem i policz sha256**, porównaj z flagą. Dopiero
zgodność uprawnia do etapu 3.

### Etap 3 — czyszczenie `otadata` i powrót do `factory`

```
od = esp_partition_find_first(ESP_PARTITION_TYPE_DATA, ESP_PARTITION_SUBTYPE_DATA_OTA, NULL)
esp_partition_erase_range(od, 0, od->size)     // 8 KB, czysta otadata = start z factory
knvs["selfupd"] = ""                           // dopiero TERAZ
esp_restart()
```

To dokładnie „Model B” tego projektu — ten sam dwuwiersz, który ma każdy program ze sklepu
(`porty/btspeaker/btspeaker/btspeaker.ino`, `adsb_pion/adsb_pion/adsb_pion.ino` i pozostałe programy sklepu)
i który po stronie hosta robi `loader/flash.sh` (`erase_region 0xe000 0x2000`), a po stronie
portalu — zapis 8 KB `0xFF` pod `0xe000`.

`esp_ota_set_boot_partition(factory)` prawdopodobnie też by zadziałało: nagłówek
(`esp_ota_ops.h`) mówi o „valid OTA partition of type app”, nie „tylko `ota_N`”, a implementacja
w ESP-IDF ma jawną gałąź dla podtypu `FACTORY` (kasuje `otadata`). Ale **w tym projekcie nikt
tego nie uruchomił**, a `esp_partition_erase_range` na `otadata` jest sprawdzony na sprzęcie
w kilku programach ze sklepu — dlatego wybór pada na niego. Powód to „niesprawdzone u nas”,
nie „nagłówek zabrania”.

---

## 3. Pułapki, które ten projekt już zna

### (a) Watchdog i głodzenie IDLE0 — obowiązkowo `wdtLong()`

`esp_ota_begin(slot, size)` **kasuje cały zakres synchronicznie**: 2496 KB to kilkanaście
sekund `flash erase`. To samo dotyczy `esp_partition_erase_range()` na `factory` (1408 KB)
i całej pętli zapisu: każda operacja na flashu parkuje drugi rdzeń (IPC, cache off), więc
zadanie IDLE0 nie dostaje czasu i task watchdog ubija płytkę w połowie
(objaw z historii: reboot ~13 s po starcie dużej aplikacji).

Rozwiązanie już jest w kodzie — `wdtLong()` (`loader/loader/sdprog.cpp`):

```c
esp_task_wdt_config_t c = {};
c.timeout_ms     = on ? 90000u : 5000u;
c.idle_core_mask = 1u;      // jak w rdzeniu Arduino: pilnowany IDLE0
c.trigger_panic  = true;
esp_task_wdt_reconfigure(&c);
```

Zasady przeniesione z `flashAndBoot()`:

- `wdtLong(true)` **przed** `esp_ota_begin()` / `esp_partition_erase_range()`, nie dopiero
  przy pętli kopiowania (kasowanie jest tą długą częścią);
- `wdtLong(false)` przed **każdym** wyjściem z funkcji — w `flashAndBoot()` są dwa
  wywołania: przy błędzie `esp_ota_begin()` i po skończonym kopiowaniu. Inaczej płytka
  zostaje z limitem 90 s i prawdziwe zawieszenie przestaje być widoczne;
- `delay(1)` co ~64 kB w pętli zapisu (`if ((done & 0xFFFF) < sizeof(buf))`), żeby oddać
  czas planiście.

**`disableCore0WDT()` / `disableCore1WDT()` — w ładowarce przy operacjach na flashu: NIE.**
To reguła **lokalna** dla tego jednego przypadku, nie ogólny zakaz w projekcie:

- **K-OS, kasowanie/zapis flasha** (`esp_ota_begin`, `esp_partition_erase_range`,
  pętla `esp_partition_write`): na IDF 5 (tu 5.5.5) hook zadania IDLE nadal woła
  `esp_task_wdt_reset()`, a po `disableCore*WDT()` błąd „task not found” leci przez
  `ESP_LOGE` z kodu leżącego **we flashu** — w trakcie kasowania flasha z wyłączonym cache
  to natychmiastowy reset. Dlatego tu wyłącznie `wdtLong()` (przedłużenie limitu, IDLE0
  nadal pilnowany). Komentarz nad `wdtLong()` w `sdprog.cpp` opisuje ten sam mechanizm.
- **Porty ze sklepu, wokół `tft.calibrateTouch()`**: tam `disableCore0WDT()` /
  `disableCore1WDT()` (i włączenie z powrotem po kalibracji) jest **WYMAGANE** — kalibracja
  blokuje pętlę w oczekiwaniu na dotyk, cache jest włączony, a bez tego watchdog ubija
  program. Tak robią openHASP, BT Speaker, NerdMiner i Bruce; reguła jest spisana
  w `SPEC-LADOWARKA.md`. Ten dokument jej **nie** uchyla.

### (b) Obraz nie jest przywiązany do offsetu

Patrz §1. Konsekwencja praktyczna: **nie trzeba dwóch builda** („loader dla factory”
i „loader dla ota_0”). Jeden `loader.bin` z `zbuduj-obrazy.sh` obsługuje portal
(→ `factory`) i samoaktualizację (→ `ota_0`, potem `factory`).

### (c) Walidacja: magic `0xE9` + mieści się w `factory`

Zapas jest mały i będzie się kurczyć:

| | rozmiar | zapas w `factory` (1 441 792 B) |
|---|---|---|
| loader 0.3.6, cyd24 | 1 359 744 B | 82 048 B (5,7 %) |
| loader 0.3.6, cyd28 | 1 357 504 B | 84 288 B (5,8 %) |

Dlatego kolejność sprawdzeń z etapu 0 jest twarda: rozmiar **przed** `esp_ota_begin()`, nie
po. Warto też, żeby ekran „o programie” pokazywał ten zapas — nowa grafika albo font potrafi
zjeść 80 kB bez ostrzeżenia.

Jeśli K-OS kiedyś przekroczy 1 441 792 B, samoaktualizacja **przestaje być możliwa**:
zmiana tablicy partycji wymaga zapisu pod `0x8000`, a przesunięcie granicy
`factory`/`ota_0` z działającego obrazu to gwarantowany brick. **Zmiana tablicy = tylko
portal albo `flash.sh` po USB.** To trzeba napisać w ekranie aktualizacji, nie tylko tutaj.

### (d) Zanik prądu w połowie kopiowania do `factory`

`factory` to **jedyna** partycja, z której płytka startuje po czystej `otadata` — więc pół
zapisany `factory` byłby najgorszym stanem. Cała odporność siedzi w **jednej** zasadzie:

> `otadata` jest czyszczona **dopiero** po odczytaniu `factory` z powrotem i potwierdzeniu
> sha256. Ani chwili wcześniej.

Co się dzieje przy zaniku prądu w każdym momencie:

| moment | stan `otadata` | co startuje | co robi |
|---|---|---|---|
| w trakcie pobierania na kartę | bez zmian (`factory`) | stary K-OS | plik `.part` usunięty przez `downloadToCard()`, ponów |
| w trakcie `esp_ota_begin/write` na `ota_0` | bez zmian (`factory`) | stary K-OS | `ota_0` jest śmieciem, ale nikt z niego nie startuje; ponów |
| po `set_boot_partition(ota_0)`, przed kopiowaniem | `ota_0` | **nowy** K-OS z `ota_0` | flaga `selfupd` w `knvs` → wchodzi w etap 2 |
| **w trakcie kasowania/zapisu `factory`** | `ota_0` | **nowy** K-OS z `ota_0` | flaga wciąż jest → kopiuje od początku. `factory` jest połamany, ale **nikt z niego nie startuje** |
| po weryfikacji, w trakcie kasowania `otadata` | 8 KB, jeden sektor może być skasowany | `factory` albo `ota_0` — oba mają dobry obraz | flaga jeszcze jest → gałąź „run == factory” czyści flagę, albo etap 2 leci jeszcze raz (kopia identycznych bajtów, nieszkodliwa) |
| po skasowaniu `otadata`, przed czyszczeniem flagi | czysta (`factory`) | nowy K-OS z `factory` | gałąź „run == factory” czyści flagę i idzie dalej |

Czyli: **nie ma stanu, w którym płytka startuje z połamanej partycji.** Cena to okno
kilkunastu sekund, w którym `factory` jest nieważny, a wyjściem jest wyłącznie `ota_0` —
i dlatego etap 2 nie ma prawa niczego z `ota_0` nadpisać (patrz zakaz autostartu wyżej).

Czego **nie** wolno zakładać: że bootloader ESP-IDF sam przeskoczy z połamanego `factory`
na `ota_0`. Zachowanie „spróbuj kolejnego slotu” zależy od konfiguracji bootloadera i **nie
zostało w tym projekcie sprawdzone** — plan nie może się na nim opierać.

Ostatnia furtka jest zawsze ta sama i warto ją napisać na ekranie aktualizacji: ROM
download mode ESP32 nie da się zepsuć zapisem do flasha, więc każdy stan da się odkręcić
**portalem** (`index.html`, WebSerial) albo `loader/flash.sh` po USB. Samoaktualizacja może
zatem doprowadzić do „trzeba wziąć kabel”, nigdy do trwałego bricka.

Miękkie zabezpieczenie na dodatek: **stary `loader.bin` zostaje na karcie**
(`/korona/loader-<wersja>.bin`, kasowany dopiero po udanym starcie nowej wersji), żeby
cofnięcie wersji nie wymagało internetu.

---

## 4. Otwarte pytania do rozstrzygnięcia przed pisaniem kodu

1. Co Arduino wpisuje w `esp_app_desc_t.project_name` / `.version` przy `arduino-cli
   compile`? Jeśli coś sensownego, marker „to jest K-OS” wychodzi darmowo.
2. Ile realnie trwa `esp_partition_erase_range` na 1408 KB tej kostki (do zmierzenia na
   sprzęcie) — od tego zależy, czy 90 s w `wdtLong()` wystarcza z zapasem.
3. Czy `esp_partition_read` z **działającej** partycji jest wystarczająco szybki, czy
   opłaca się kopiować z karty (plik na karcie i tak jest) — kopia z karty jest wolniejsza,
   ale zdejmuje pytanie 3 i pozwala kopiować do `factory` już w etapie 1, bez restartu.
   To alternatywny, prostszy wariant: **karta → `factory` wprost, bez `ota_0` i bez
   przeładowania**, kosztem tego, że kod kasujący `factory` działa Z `factory` (kod we
   flashu, który sam siebie kasuje — trzeba by go trzymać w IRAM; ryzyko dużo większe).
   Wariant z `ota_0` jest bezpieczniejszy i to on jest opisany wyżej.
4. Gdzie w menu: „ustawienia → o programie → sprawdź aktualizację” czy osobna pozycja
   w menu głównym. Ekran musi pokazywać: wersja teraz → wersja w repo, rozmiar, zapas
   w `factory`, ostrzeżenie „nie odłączaj zasilania” i „nie zmienia tablicy partycji”.
