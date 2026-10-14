"""Patrones clásicos: listas de strings ('*' viva, '.' muerta)."""

GLIDER = [
    ".*.",
    "..*",
    "***",
]

BLINKER = [
    "***",
]

BLOCK = [
    "**",
    "**",
]

PULSAR = [
    "..***...***..",
    ".............",
    "*....*.*....*",
    "*....*.*....*",
    "*....*.*....*",
    "..***...***..",
    ".............",
    "..***...***..",
    "*....*.*....*",
    "*....*.*....*",
    "*....*.*....*",
    ".............",
    "..***...***..",
]

GOSPER_GLIDER_GUN = [
    "........................*...........",
    "......................*.*...........",
    "............**......**............**",
    "...........*...*....**............**",
    "**........*.....*...**..............",
    "**........*...*.**....*.*...........",
    "..........*.....*.......*...........",
    "...........*...*....................",
    "............**......................",
]

R_PENTOMINO = [
    ".**",
    "**.",
    ".*.",
]

ACORN = [
    ".*.....",
    "...*...",
    "**..***",
]

PATTERNS: dict[str, list[str]] = {
    "glider": GLIDER,
    "blinker": BLINKER,
    "block": BLOCK,
    "pulsar": PULSAR,
    "gosper_glider_gun": GOSPER_GLIDER_GUN,
    "r_pentomino": R_PENTOMINO,
    "acorn": ACORN,
}


def place(buf, rows, cols, pattern, i, j):
    """Pone el patrón en un buffer plano (bytearray) con su esquina en (i, j)."""
    if isinstance(pattern, str):
        pattern = PATTERNS[pattern]
    for di, fila in enumerate(pattern):
        for dj, c in enumerate(fila):
            if c == '*' and 0 <= i + di < rows and 0 <= j + dj < cols:
                buf[(i + di) * cols + (j + dj)] = 1

