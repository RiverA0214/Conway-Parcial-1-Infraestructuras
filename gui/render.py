"""Matriz -> imagen. Funciones puras, sin Tk."""

VIVA = (52, 211, 153)
MUERTA = (17, 24, 39)

# una tabla de traducción por canal: 0 -> color de célula muerta, 1 -> color de célula viva
_TABLAS = [bytes.maketrans(b"\x00\x01", bytes([m, v])) for m, v in zip(MUERTA, VIVA)]


def to_ppm(raw: bytes, ancho: int, alto: int) -> bytes:
    """Imagen PPM de ancho x alto píxeles (1 por célula) a partir de ancho*alto bytes con 0 o 1.

    Cada canal (R, G, B) sale de una sola traducción de bytes hecha en C, y se
    intercalan con slices; mucho más rápido que armar el píxel célula por célula.
    """
    rgb = bytearray(3 * len(raw))
    rgb[0::3], rgb[1::3], rgb[2::3] = (raw.translate(t) for t in _TABLAS)
    return b"P6 %d %d 255\n" % (ancho, alto) + rgb
