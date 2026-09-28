DOOM na K-OS - gotowe dane gry z Freedoomu (BETA)
=================================================

Plik doom.kwad to darmowe dane gry dla programu DOOM (BETA) ze sklepu K-OS, zrobione
z Freedoom 0.13.0 (licencja BSD-3-Clause - patrz LICENCJA-FREEDOOM.txt). Nie potrzebujesz
Pythona ani zadnego programu na komputerze.

Jak polozyc na karte:
  1. Wyjmij karte SD z plytki i wloz ja do komputera.
  2. Na karcie zaloz folder "doom" (jesli go nie ma).
  3. Skopiuj do niego plik doom.kwad - tak, zeby lezal jako /doom/doom.kwad.
     Nie zmieniaj nazwy pliku.
  4. Wloz karte do plytki i uruchom DOOM z K-OS. Za pierwszym razem program przez
     okolo 10 sekund instaluje dane (pasek postepu); kolejne starty sa od razu.

Dobrze wiedziec:
  * W pliku jest jedna plansza: E1M1. Grafika Freedoomu 0.13 jest duzo wieksza niz
    w DOOM-ie, wiec nawet sama E1M1 zmiescila sie w 1852 kB plytki dopiero ze scianami
    i postaciami w polowie rozdzielczosci poziomej (silnik i tak rysuje 120 kolumn).
  * Koniec E1M1 = koniec epizodu. Zapisy gry: /doom/zapisy.sav na karcie.
  * Sprawdzenie pliku: sha256 w pliku "sha256" obok (1 750 448 B).
  * Wlasny doom1.wad / doom.wad (albo inne plansze Freedoomu) przerobisz dalej sam
    skryptem wad2kos.py: https://github.com/PixelPetrol/cyd-doom-kos (kos/INSTRUKCJA.md).
  * Powrot do K-OS: przycisk RST.
  * DOOM jest znakiem towarowym id Software; to nieoficjalny port silnika.
    Freedoom nie zawiera danych id Software.


DOOM on K-OS - ready-made game data from Freedoom (BETA)
========================================================

doom.kwad is free game data for the DOOM (BETA) program from the K-OS store, made from
Freedoom 0.13.0 (BSD-3-Clause licence - see LICENCJA-FREEDOOM.txt). You do not need
Python or any other program on a computer.

How to put it on the card:
  1. Take the SD card out of the board and put it into a computer.
  2. Create a folder named "doom" on the card (if it is not there).
  3. Copy doom.kwad into it, so that it is /doom/doom.kwad. Do not rename the file.
  4. Put the card back into the board and start DOOM from K-OS. The first time, the
     program installs the data for about 10 seconds (progress bar); later starts are
     immediate.

Good to know:
  * The file contains one level: E1M1. Freedoom 0.13 graphics are much bigger than
    DOOM's, so even E1M1 alone fits in the board's 1852 kB only with walls and
    characters at half horizontal resolution (the engine draws 120 columns anyway).
  * The end of E1M1 = the end of the episode. Saved games: /doom/zapisy.sav on the card.
  * File check: sha256 in the "sha256" file next to it (1 750 448 B).
  * Your own doom1.wad / doom.wad (or other Freedoom levels) you can still convert
    yourself with wad2kos.py: https://github.com/PixelPetrol/cyd-doom-kos (kos/INSTRUKCJA.md).
  * Back to K-OS: the RST button.
  * DOOM is a trademark of id Software; this is an unofficial engine port.
    Freedoom contains no id Software data.
