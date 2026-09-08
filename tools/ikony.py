#!/usr/bin/env python3
"""Ikony programow dla ekranu glownego K-OS: bin/<plytka>/<nazwa>.ico

SKAD RYSUNKI: **Material Symbols Outlined** (Google, Apache-2.0) - te same, z ktorych
zrobione sa ikony wbudowane w K-OS (loader/tools/gen_assets.py). Dzieki temu ikona
programu i ikona systemowa obok niej wygladaja jak jedna rodzina, a nie jak dwa swiaty.
Pierwsza wersja tego skryptu rysowala ksztalty recznie z prostokatow i kol - wygladalo
to znosnie, ale gorzej niz komplet robiony przez zawodowcow, ktory i tak juz mamy.

FORMAT JEST TEN SAM, CO IKON WBUDOWANYCH - i to nie jest wygoda, tylko decyzja:
  * maska alfa 4-bit, 32x32, dwa piksele na bajt, STARSZY POLBAJT PIERWSZY = 512 B,
  * rysuje ja ta sama funkcja co ikony systemowe (blitMask w loader/loader/assets.cpp),
    wiec K-OS nie potrzebuje ani jednej nowej linii kodu graficznego,
  * maska BIERZE KOLOR Z MOTYWU - ikona jest zielona w zielonym i zlota w zlotym.
    Kolorowy obrazek wygladalby dobrze w jednym motywie i obco w trzech pozostalych,
    a zajmowalby 2 kB zamiast 512 B.

Gdy ikony nie ma, K-OS rysuje KAFELEK Z INICJALAMI nazwy - nigdy nie moze zabraknac,
a odroznia programy lepiej niz jeden wspolny znak zapytania dla wszystkich.

CZEGO POTRZEBUJE: PIL (jest) oraz `qlmanage` z macOS do rasteryzacji SVG - dokladnie ta
sama droga co gen_assets.py, zeby nie wprowadzac drugiej zaleznosci na to samo.
Pliki SVG sa cache'owane w art/icons/, wiec drugi przebieg nie rusza sieci.

Uzycie (z katalogu repo):  python3 tools/ikony.py
"""
import os, re, shutil, struct, subprocess, sys, tempfile, zlib
from PIL import Image, ImageChops

S = 32          # docelowy bok ikony
SS = 4          # nadprobkowanie
N = S * SS
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Plotno:
    """Maska 0/1 w skali SS, zamieniana na koncu na 16 poziomow alfy."""
    def __init__(self):
        self.p = bytearray(N * N)

    def rect(self, x, y, w, h):
        x, y, w, h = int(x*SS), int(y*SS), int(w*SS), int(h*SS)
        for yy in range(max(0,y), min(N, y+h)):
            r = yy*N
            for xx in range(max(0,x), min(N, x+w)):
                self.p[r+xx] = 1

    def kolo(self, cx, cy, r, r_in=0):
        cx, cy, r, r_in = cx*SS, cy*SS, r*SS, r_in*SS
        for yy in range(max(0,int(cy-r)), min(N, int(cy+r)+1)):
            for xx in range(max(0,int(cx-r)), min(N, int(cx+r)+1)):
                d = (xx+0.5-cx)**2 + (yy+0.5-cy)**2
                if d <= r*r and d >= r_in*r_in:
                    self.p[yy*N+xx] = 1

    def zaokr(self, x, y, w, h, r):
        self.rect(x+r, y, w-2*r, h); self.rect(x, y+r, w, h-2*r)
        for (cx, cy) in ((x+r,y+r),(x+w-r,y+r),(x+r,y+h-r),(x+w-r,y+h-r)):
            self.kolo(cx, cy, r)

    def linia(self, x0, y0, x1, y1, gr):
        x0,y0,x1,y1 = x0*SS,y0*SS,x1*SS,y1*SS
        n = int(max(abs(x1-x0), abs(y1-y0)))*2 + 1
        for i in range(n+1):
            t = i/float(n)
            cx, cy = x0+(x1-x0)*t, y0+(y1-y0)*t
            rr = gr*SS/2.0
            for yy in range(int(cy-rr), int(cy+rr)+1):
                for xx in range(int(cx-rr), int(cx+rr)+1):
                    if 0<=xx<N and 0<=yy<N and (xx+0.5-cx)**2+(yy+0.5-cy)**2 <= rr*rr:
                        self.p[yy*N+xx] = 1

    def trojkat(self, a, b, c):
        pts = [(p[0]*SS, p[1]*SS) for p in (a,b,c)]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        def zn(p,q,r): return (p[0]-r[0])*(q[1]-r[1]) - (q[0]-r[0])*(p[1]-r[1])
        for yy in range(max(0,int(min(ys))), min(N,int(max(ys))+1)):
            for xx in range(max(0,int(min(xs))), min(N,int(max(xs))+1)):
                p = (xx+0.5, yy+0.5)
                d1,d2,d3 = zn(p,pts[0],pts[1]), zn(p,pts[1],pts[2]), zn(p,pts[2],pts[0])
                if not ((d1<0 or d2<0 or d3<0) and (d1>0 or d2>0 or d3>0)):
                    self.p[yy*N+xx] = 1

    def wytnij(self, inne):
        for i in range(N*N):
            if inne.p[i]: self.p[i] = 0

    def alfa(self):
        """Usrednienie SSxSS -> poziomy 0..15."""
        out = bytearray(S*S)
        for y in range(S):
            for x in range(S):
                s = 0
                for dy in range(SS):
                    r = (y*SS+dy)*N + x*SS
                    for dx in range(SS):
                        s += self.p[r+dx]
                out[y*S+x] = (s * 15 + (SS*SS)//2) // (SS*SS)
        return out


def pakuj(a):
    """0..15 -> po dwa piksele w bajcie, starszy polbajt pierwszy (jak blitMask)."""
    b = bytearray(S*S//2)
    for i in range(0, S*S, 2):
        b[i//2] = (a[i] << 4) | a[i+1]
    return bytes(b)


# --------------------------------------------------------------------- rysunki
def i_pad(p):                       # gry: pad
    p.zaokr(2, 10, 28, 13, 6)
    d = Plotno(); d.rect(6, 15, 7, 2); d.rect(8.5, 12.5, 2, 7)      # krzyzak
    d.kolo(22, 15, 2); d.kolo(26, 19, 2)                            # przyciski
    p.wytnij(d)

def i_chmura(p):                    # meteo: chmura z deszczem
    # Pierwsza wersja miala slonce ZA chmura i przy 32 px czytalo sie jako lizak - chmura
    # zjadala pierscien slonca. Deszcz jest jednoznaczny w tej skali i pasuje do radaru opadow.
    p.kolo(12, 13, 6); p.kolo(20, 14, 5); p.zaokr(6, 12, 21, 9, 4)
    for i in range(3):
        p.linia(9 + i*7, 23, 7 + i*7, 29, 2)

def i_dokument(p):                  # office: kartka z liniami
    p.rect(6, 3, 20, 26)
    d = Plotno()
    for i in range(4): d.rect(10, 8+i*5, 12, 2)
    p.wytnij(d)

def i_antena(p):                    # mesh/handset: maszt i fale
    p.rect(15, 12, 2, 17); p.kolo(16, 9, 3)
    for r in (7, 11):
        f = Plotno(); f.kolo(16, 9, r); g = Plotno(); g.kolo(16, 9, r-1.6); f.wytnij(g)
        h = Plotno(); h.rect(0, 9, 32, 23); f.wytnij(h)
        for i in range(N*N):
            if f.p[i]: p.p[i] = 1

def i_samolot(p):                   # radar: samolot
    p.trojkat((16,2),(13,12),(19,12))
    p.trojkat((16,10),(1,19),(31,19)); p.rect(13,12,6,14)
    p.trojkat((16,22),(9,29),(23,29))

def i_nietoperz(p):                 # bruce: nietoperz (maskotka projektu)
    p.kolo(16, 16, 4)
    p.trojkat((16,13),(2,9),(6,22)); p.trojkat((16,13),(30,9),(26,22))
    p.trojkat((12,12),(14,5),(16,12)); p.trojkat((16,12),(18,5),(20,12))   # uszy
    d = Plotno()                                                          # wciecia skrzydel
    d.trojkat((6,22),(10,17),(11,23)); d.trojkat((26,22),(22,17),(21,23))
    p.wytnij(d)

def i_radar(p):                     # marauder: okrag z wycinkiem
    for r in (14, 9, 4):
        f = Plotno(); f.kolo(16,16,r); g = Plotno(); g.kolo(16,16,r-1.6); f.wytnij(g)
        for i in range(N*N):
            if f.p[i]: p.p[i] = 1
    p.linia(16, 16, 27, 7, 2)

def i_uklad(p):                     # esp32div: scalak z nozkami
    p.zaokr(8, 8, 16, 16, 3)
    d = Plotno(); d.zaokr(11, 11, 10, 10, 2); p.wytnij(d)
    for i in range(3):
        y = 11 + i*5
        p.rect(3, y, 5, 2); p.rect(24, y, 5, 2)
        p.rect(11+i*5, 3, 2, 5); p.rect(11+i*5, 24, 2, 5)

def i_dom(p):                       # openhasp: dom
    p.trojkat((16,3),(2,15),(30,15)); p.rect(6,15,20,14)
    d = Plotno(); d.rect(13,20,6,9); p.wytnij(d)

def i_kilof(p):                     # nerdminer: kilof
    p.linia(6, 26, 26, 6, 3)
    p.linia(19, 4, 29, 14, 3)
    d = Plotno(); d.kolo(24, 9, 3); p.wytnij(d)

# program (nazwa pliku .bin bez rozszerzenia) -> nazwa ikony Material Symbols.
# Dobierane pod TRESC programu, nie pod jego logo: w 32 px czytelny jest tylko prosty
# znak, a nie znak firmowy. Nazwy sprawdzone - kazda musi istniec w Material Symbols,
# inaczej skrypt konczy sie bledem zamiast po cichu pominac ikone.
IKONY = {
    "gry-vol1":     "sports_esports",     # pad
    "meteo-pion":   "rainy",              # chmura z deszczem
    "meteo-poziom": "rainy",
    "pogoda":       "partly_cloudy_day",
    "office":       "description",        # kartka z tekstem
    "mesh":         "forum",              # dymki rozmowy
    "radar-pion":   "flight",             # samolot
    "radar-poziom": "flight",
    "bruce":        "security",           # tarcza
    "marauder":     "wifi_find",          # wifi z lupa
    "esp32div":     "memory",             # scalak
    "openhasp":     "home",               # dom
    "nerdminer":    "currency_bitcoin",
}
MATERIAL_URL = ("https://fonts.gstatic.com/s/i/short-term/release/"
                "materialsymbolsoutlined/{name}/default/24px.svg")
SVG_PX = 320                     # rasteryzujemy duzo i schodzimy LANCZOSEM - jak w gen_assets
ICONS_DIR = os.path.join(ROOT, "art", "icons")


def sciagnij(nazwy):
    os.makedirs(ICONS_DIR, exist_ok=True)
    for n in sorted(set(nazwy)):
        dst = os.path.join(ICONS_DIR, n + ".svg")
        if os.path.exists(dst):
            continue
        print("sciagam %s" % n)
        kod = subprocess.run(["curl", "-s", "-o", dst, "-w", "%{http_code}",
                              MATERIAL_URL.format(name=n)],
                             capture_output=True, text=True).stdout.strip()
        if kod != "200":
            if os.path.exists(dst):
                os.remove(dst)
            sys.exit("ikony: nie ma ikony '%s' (HTTP %s) - dobierz inna nazwe w IKONY" % (n, kod))


def rasteryzuj(nazwy):
    """SVG -> maska alfy 32x32 w 16 poziomach. Ta sama droga co gen_assets.py."""
    tmp = tempfile.mkdtemp(prefix="korona-ikony-")
    pliki = []
    for n in sorted(set(nazwy)):
        with open(os.path.join(ICONS_DIR, n + ".svg"), encoding="utf-8") as f:
            svg = f.read()
        svg = re.sub(r'\swidth="[^"]*"', ' width="%d"' % SVG_PX, svg, count=1)
        svg = re.sub(r'\sheight="[^"]*"', ' height="%d"' % SVG_PX, svg, count=1)
        svg = re.sub(r'fill="#[0-9a-fA-F]{3,8}"', 'fill="#000000"', svg)
        pth = os.path.join(tmp, n + ".svg")
        with open(pth, "w", encoding="utf-8") as f:
            f.write(svg)
        pliki.append(pth)
    subprocess.run(["qlmanage", "-t", "-s", str(SVG_PX), "-o", tmp] + pliki,
                   capture_output=True, check=True)
    out = {}
    for n in sorted(set(nazwy)):
        png_ = os.path.join(tmp, n + ".svg.png")
        if not os.path.exists(png_):
            sys.exit("ikony: qlmanage nie wyrenderowal %s" % n)
        im = ImageChops.invert(Image.open(png_).convert("L")).resize((S, S), Image.LANCZOS)
        out[n] = bytearray((px * 15 + 127) // 255 for px in im.getdata())
    shutil.rmtree(tmp, ignore_errors=True)
    return out


# --------------------------------------------------------------------- podglad
def png(sciezka, w, h, px):
    def kawalek(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    surowe = b"".join(b"\x00" + bytes(px[y*w*3:(y+1)*w*3]) for y in range(h))
    with open(sciezka, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(kawalek(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)))
        f.write(kawalek(b"IDAT", zlib.compress(surowe, 9)))
        f.write(kawalek(b"IEND", b""))


def arkusz(ikony, sciezka, skala=3):
    kol = len(ikony)
    w, h = kol*(S*skala+8)+8, S*skala+26
    px = bytearray([12]*(w*h*3))
    for i, (nazwa, a) in enumerate(sorted(ikony.items())):
        ox = 8 + i*(S*skala+8)
        for y in range(S*skala):
            for x in range(S*skala):
                v = a[(y//skala)*S + (x//skala)]
                # zielen motywu na czarnym tle - tak to wyjdzie na plytce
                r, g, b = 0, v*255//15, 0
                j = ((y+8)*w + ox + x)*3
                px[j], px[j+1], px[j+2] = r, g, b
    png(sciezka, w, h, px)


def main():
    sciagnij(IKONY.values())
    maski = rasteryzuj(IKONY.values())
    zrobione = {prog: maski[nazwa] for prog, nazwa in IKONY.items()}

    ile = 0
    for plytka in sorted(os.listdir(os.path.join(ROOT, "bin"))):
        d = os.path.join(ROOT, "bin", plytka)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith(".bin"):
                continue
            baza = f[:-4]
            if baza not in zrobione:
                print("UWAGA: brak ikony dla %s (K-OS pokaze inicjaly)" % baza, file=sys.stderr)
                continue
            with open(os.path.join(d, baza + ".ico"), "wb") as fh:
                fh.write(pakuj(zrobione[baza]))
            ile += 1
    art = os.path.join(ROOT, "art")
    os.makedirs(art, exist_ok=True)
    arkusz({p: zrobione[p] for p in sorted(zrobione)}, os.path.join(art, "podglad-ikony.png"))
    print("ikony: %d rysunkow Material Symbols -> %d plikow .ico po %d B (podglad: art/podglad-ikony.png)"
          % (len(set(IKONY.values())), ile, S * S // 2))


if __name__ == "__main__":
    main()
