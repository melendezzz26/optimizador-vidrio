"""Genera la figura esquemática monocroma DJD en PNG sin paquetes gráficos."""
import struct
import zlib
from pathlib import Path

WIDTH, HEIGHT = 1200, 700
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
 '/':'00001 00010 00010 00100 01000 01000 10000','=':'00000 11111 00000 11111 00000 00000 00000',
 '>':'10000 01000 00100 00010 00100 01000 10000','+':'00000 00100 00100 11111 00100 00100 00000',
 '-':'00000 00000 00000 11111 00000 00000 00000',
 '.':'00000 00000 00000 00000 00000 00100 00100'
}

def rect(x, y, w, h, value=220, border=0, thickness=4):
    for yy in range(y, y+h):
        for xx in range(x, x+w):
            if 0 <= xx < WIDTH and 0 <= yy < HEIGHT:
                edge=xx<x+thickness or xx>=x+w-thickness or yy<y+thickness or yy>=y+h-thickness
                shade=border if edge else value
                offset=(yy*WIDTH+xx)*3
                pixels[offset:offset+3]=bytes((shade,shade,shade))

def text(x,y,label,scale=3):
    for char in label.upper():
        if char==' ':
            x+=4*scale
            continue
        for row,bits in enumerate(FONT.get(char,FONT['-']).split()):
            for col,bit in enumerate(bits):
                if bit=='1':
                    rect(x+col*scale,y+row*scale,scale,scale,0,0,0)
        x+=6*scale

def line(x1,y1,x2,y2,width=5):
    dx,dy=abs(x2-x1),abs(y2-y1)
    sx=1 if x1<x2 else -1
    sy=1 if y1<y2 else -1
    error=dx-dy
    while True:
        rect(x1-width//2,y1-width//2,width,width,0,0,0)
        if x1==x2 and y1==y2:
            break
        twice=2*error
        if twice>-dy:
            error-=dy
            x1+=sx
        if twice<dx:
            error+=dx
            y1+=sy

def arrow(x1,y1,x2,y2):
    line(x1,y1,x2,y2)
    line(x2,y2,x2-16,y2-12)
    line(x2,y2,x2-16,y2+12)

# La plancha muestra una franja inicial ya ocupada y el espacio libre restante.
text(70,35,'FUENTE ACTIVA DJD 1/3',3)
rect(55,75,500,420,245,0,5)
rect(70,90,470,155,185,0,3)
text(125,150,'LLENADO INICIAL >= 1/3',3)
rect(70,265,470,215,255,0,3)
text(205,360,'CAPACIDAD LIBRE',3)

# La lista explica candidatos de una, dos y tres piezas tras el llenado inicial.
text(635,74,'GRUPOS PENDIENTES',3)
rect(610,100,510,70,235,0,3)
text(645,122,'TAMANO 1: B',3)
rect(610,185,510,70,225,0,3)
text(645,207,'TAMANO 2: B + C',3)
rect(610,270,510,70,210,0,3)
text(645,292,'TAMANO 3: B + C + D',3)

# La pareja seleccionada se conecta con el espacio libre conceptual.
arrow(610,220,555,345)
rect(610,380,510,100,185,0,4)
text(645,400,'SELECCION: B + C',3)
text(645,438,'WASTE TOLERANCIA = 5',2)
arrow(865,485,865,545)
rect(450,555,500,70,235,0,4)
text(535,575,'PLACEMENT GEOMETRICO',2)

text(50,650,'FIGURA CONCEPTUAL - NO RESULTADO EXPERIMENTAL',2)

def chunk(kind,payload):
    return struct.pack('!I',len(payload))+kind+payload+struct.pack('!I',zlib.crc32(kind+payload)&0xffffffff)

raw=b''.join(b'\0'+pixels[y*WIDTH*3:(y+1)*WIDTH*3] for y in range(HEIGHT))
png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',WIDTH,HEIGHT,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b'')
target=Path(__file__).resolve().parents[3]/'docs/spikes/assets/SP-004-djd-example.png'
target.parent.mkdir(parents=True,exist_ok=True)
target.write_bytes(png)
print(target)
