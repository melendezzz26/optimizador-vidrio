"""Crea la figura monocroma PNG con primitivas de la biblioteca estándar."""
import struct
import zlib
from pathlib import Path

WIDTH, HEIGHT = 1200, 650
pixels = bytearray([255] * (WIDTH * HEIGHT * 3))
FONT = {
    'A':'01110 10001 10001 11111 10001 10001 10001','B':'11110 10001 10001 11110 10001 10001 11110',
    'C':'01111 10000 10000 10000 10000 10000 01111','D':'11110 10001 10001 10001 10001 10001 11110',
    'E':'11111 10000 10000 11110 10000 10000 11111','F':'11111 10000 10000 11110 10000 10000 10000',
    'G':'01111 10000 10000 10111 10001 10001 01111','H':'10001 10001 10001 11111 10001 10001 10001',
    'I':'11111 00100 00100 00100 00100 00100 11111','J':'00111 00010 00010 00010 10010 10010 01100',
    'K':'10001 10010 10100 11000 10100 10010 10001','L':'10000 10000 10000 10000 10000 10000 11111',
    'M':'10001 11011 10101 10101 10001 10001 10001','N':'10001 11001 10101 10011 10001 10001 10001',
    'O':'01110 10001 10001 10001 10001 10001 01110','P':'11110 10001 10001 11110 10000 10000 10000',
    'Q':'01110 10001 10001 10001 10101 10010 01101','R':'11110 10001 10001 11110 10100 10010 10001',
    'S':'01111 10000 10000 01110 00001 00001 11110','T':'11111 00100 00100 00100 00100 00100 00100',
    'U':'10001 10001 10001 10001 10001 10001 01110','V':'10001 10001 10001 10001 10001 01010 00100',
    'W':'10001 10001 10001 10101 10101 10101 01010','X':'10001 10001 01010 00100 01010 10001 10001',
    'Y':'10001 10001 01010 00100 00100 00100 00100','Z':'11111 00001 00010 00100 01000 10000 11111',
    '0':'01110 10001 10011 10101 11001 10001 01110','1':'00100 01100 00100 00100 00100 00100 01110',
    '2':'01110 10001 00001 00010 00100 01000 11111','3':'11110 00001 00001 01110 00001 00001 11110',
    '4':'00010 00110 01010 10010 11111 00010 00010','5':'11111 10000 10000 11110 00001 00001 11110',
    '6':'01110 10000 10000 11110 10001 10001 01110','7':'11111 00001 00010 00100 01000 01000 01000',
    '8':'01110 10001 10001 01110 10001 10001 01110','9':'01110 10001 10001 01111 00001 00001 01110',
    ':':'00000 00100 00100 00000 00100 00100 00000','-':'00000 00000 00000 11111 00000 00000 00000',
    '.':'00000 00000 00000 00000 00000 00100 00100'
}

def rect(x, y, w, h, value=220, border=0, thickness=4):
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            if 0 <= xx < WIDTH and 0 <= yy < HEIGHT:
                edge = xx < x+thickness or xx >= x+w-thickness or yy < y+thickness or yy >= y+h-thickness
                c = border if edge else value
                i=(yy*WIDTH+xx)*3; pixels[i:i+3]=bytes((c,c,c))

def text(x, y, message, scale=3):
    for char in message.upper():
        if char == ' ':
            x += 4*scale; continue
        rows=FONT.get(char, FONT['-']).split()
        for row,bits in enumerate(rows):
            for col,bit in enumerate(bits):
                if bit == '1':
                    rect(x+col*scale,y+row*scale,scale,scale,0,0,0)
        x += 6*scale

def line(x1,y1,x2,y2,color=0,width=5):
    dx,dy=abs(x2-x1),abs(y2-y1); sx=1 if x1<x2 else -1; sy=1 if y1<y2 else -1; err=dx-dy
    while True:
        rect(x1-width//2,y1-width//2,width,width,color,color,0)
        if x1==x2 and y1==y2: break
        e=2*err
        if e>-dy: err-=dy; x1+=sx
        if e<dx: err+=dx; y1+=sy

def arrow(x1,y1,x2,y2):
    line(x1,y1,x2,y2)
    line(x2,y2,x2-18,y2-12); line(x2,y2,x2-18,y2+12)

rect(50,75,500,360,245,0,5)
text(70,45,'FUENTE ACTIVA 1',3)
rect(85,115,150,110,190)
text(100,155,'PIEZA',3); text(100,180,'PREVIA',3)
rect(255,115,250,270,255,0,3)
text(75,255,'HUECO RESTANTE',2)
rect(610,95,220,85,210)
text(640,115,'PIEZA GRANDE',2); text(665,145,'NO CABE',2)
arrow(555,250,605,150)
rect(610,225,220,85,180)
text(640,245,'PIEZA PEQUENA',2); text(660,275,'SI CABE',2)
rect(610,355,220,85,180)
text(640,375,'PIEZA PEQUENA',2); text(660,405,'SI CABE',2)
arrow(720,315,500,325); arrow(720,445,500,365)
text(620,475,'FILLER MANTIENE FUENTE 1',2)
arrow(500,440,500,520)
rect(250,535,500,70,235,0,4)
text(330,555,'CAMBIA SOLO AL AGOTAR',2)
text(330,580,'PIEZAS FACTIBLES',2)
text(50,625,'FIGURA CONCEPTUAL - NO RESULTADO EXPERIMENTAL',2)

def chunk(kind, payload):
    return struct.pack('!I',len(payload))+kind+payload+struct.pack('!I',zlib.crc32(kind+payload)&0xffffffff)

raw=b''.join(b'\0'+pixels[y*WIDTH*3:(y+1)*WIDTH*3] for y in range(HEIGHT))
png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',WIDTH,HEIGHT,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b'')
target=Path(__file__).resolve().parents[3]/'docs/spikes/assets/SP-004-filler-example.png'
target.parent.mkdir(parents=True,exist_ok=True)
target.write_bytes(png)
print(target)
