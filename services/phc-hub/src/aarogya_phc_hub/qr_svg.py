"""Minimal, 100% offline pure-Python QR Code SVG generator (Byte mode, ECC Level M, Versions 1-6).

Zero external dependencies so Tier-2 PHC Hubs can render scannable LAN connection
QR codes completely offline.
"""

from __future__ import annotations

from html import escape

# Version -> (size, data_codewords_M, ecc_codewords_per_block_M, num_blocks_M, alignment_centers)
_VERSION_SPECS: dict[int, tuple[int, int, int, int, tuple[int, ...]]] = {
    1: (21, 16, 10, 1, ()),
    2: (25, 28, 16, 1, (6, 18)),
    3: (29, 44, 26, 1, (6, 22)),
    4: (33, 64, 18, 2, (6, 26)),
    5: (37, 86, 24, 2, (6, 30)),
    6: (41, 108, 16, 4, (6, 34)),
}

# GF(256) with primitive polynomial 0x11D
_GF_EXP = [0] * 512
_GF_LOG = [0] * 256
_x = 1
for _i in range(255):
    _GF_EXP[_i] = _x
    _GF_LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    _GF_EXP[_i] = _GF_EXP[_i - 255]


def _gf_mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _GF_EXP[_GF_LOG[a] + _GF_LOG[b]]


def _rs_generator_poly(degree: int) -> list[int]:
    poly = [1]
    for i in range(degree):
        next_poly = [0] * (len(poly) + 1)
        factor = _GF_EXP[i]
        for idx, coef in enumerate(poly):
            next_poly[idx] ^= coef
            next_poly[idx + 1] ^= _gf_mul(coef, factor)
        poly = next_poly
    return poly


def _rs_remainder(data: list[int], ecc_len: int) -> list[int]:
    gen = _rs_generator_poly(ecc_len)
    rem = list(data) + [0] * ecc_len
    for i in range(len(data)):
        coef = rem[i]
        if coef != 0:
            for j in range(1, len(gen)):
                rem[i + j] ^= _gf_mul(gen[j], coef)
    return rem[len(data) :]


def _select_version(byte_len: int) -> int:
    # Byte mode header: 4-bit mode + 8-bit length = 12 bits (+ 4-bit terminator)
    for version, (_size, data_cw, _ecc_cw, _blocks, _align) in _VERSION_SPECS.items():
        capacity_bytes = data_cw - 2  # 4-bit mode + 8-bit count = 1.5 bytes -> round up 2
        if byte_len <= capacity_bytes:
            return version
    raise ValueError(f"QR payload too long ({byte_len} bytes); max supported is 106 bytes.")


def _encode_codewords(payload: bytes) -> tuple[int, list[int]]:
    version = _select_version(len(payload))
    _size, data_cw, ecc_cw, num_blocks, _align = _VERSION_SPECS[version]

    bits: list[int] = []

    def _push_bits(val: int, count: int) -> None:
        for shift in range(count - 1, -1, -1):
            bits.append((val >> shift) & 1)

    _push_bits(0b0100, 4)  # Byte mode
    _push_bits(len(payload), 8)
    for b in payload:
        _push_bits(b, 8)

    total_data_bits = data_cw * 8
    terminator = min(4, total_data_bits - len(bits))
    _push_bits(0, terminator)
    while len(bits) % 8 != 0:
        bits.append(0)

    data_bytes = [
        sum(bits[i + j] << (7 - j) for j in range(8)) for i in range(0, len(bits), 8)
    ]
    pad_cycle = (0xEC, 0x11)
    pad_idx = 0
    while len(data_bytes) < data_cw:
        data_bytes.append(pad_cycle[pad_idx % 2])
        pad_idx += 1

    # Split into equal-sized blocks (all v1-v6 ECC-M have even block counts)
    block_len = data_cw // num_blocks
    data_blocks: list[list[int]] = []
    ecc_blocks: list[list[int]] = []
    offset = 0
    for _ in range(num_blocks):
        blk = data_bytes[offset : offset + block_len]
        offset += block_len
        data_blocks.append(blk)
        ecc_blocks.append(_rs_remainder(blk, ecc_cw))

    interleaved: list[int] = []
    for i in range(block_len):
        for blk in data_blocks:
            interleaved.append(blk[i])
    for i in range(ecc_cw):
        for blk in ecc_blocks:
            interleaved.append(blk[i])
    return version, interleaved


def _place_finder(grid: list[list[int | None]], reserved: list[list[bool]], r0: int, c0: int) -> None:
    size = len(grid)
    for dr in range(-1, 8):
        for dc in range(-1, 8):
            r, c = r0 + dr, c0 + dc
            if not (0 <= r < size and 0 <= c < size):
                continue
            if dr in (-1, 7) or dc in (-1, 7):
                val = 0
            elif dr in (0, 6) or dc in (0, 6) or (2 <= dr <= 4 and 2 <= dc <= 4):
                val = 1
            else:
                val = 0
            grid[r][c] = val
            reserved[r][c] = True


def _place_alignment(grid: list[list[int | None]], reserved: list[list[bool]], r0: int, c0: int) -> None:
    for dr in range(-2, 3):
        for dc in range(-2, 3):
            r, c = r0 + dr, c0 + dc
            val = 1 if (abs(dr) == 2 or abs(dc) == 2 or (dr == 0 and dc == 0)) else 0
            grid[r][c] = val
            reserved[r][c] = True


def _format_bits(mask_id: int) -> int:
    # ECC Level M = 0b00
    data = (0b00 << 3) | mask_id
    rem = data << 10
    gen = 0b10100110111
    for bit in range(14, 9, -1):
        if (rem >> bit) & 1:
            rem ^= gen << (bit - 10)
    return ((data << 10) | rem) ^ 0b101010000010010


def _apply_format(grid: list[list[int | None]], mask_id: int) -> None:
    size = len(grid)
    fmt = _format_bits(mask_id)
    coords_a = [
        (8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
        (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8),
    ]
    coords_b = [
        (size - 1, 8), (size - 2, 8), (size - 3, 8), (size - 4, 8),
        (size - 5, 8), (size - 6, 8), (size - 7, 8),
        (8, size - 8), (8, size - 7), (8, size - 6), (8, size - 5),
        (8, size - 4), (8, size - 3), (8, size - 2), (8, size - 1),
    ]
    for i in range(15):
        bit = (fmt >> (14 - i)) & 1
        r1, c1 = coords_a[i]
        r2, c2 = coords_b[i]
        grid[r1][c1] = bit
        grid[r2][c2] = bit


def _mask_fn(mask_id: int, r: int, c: int) -> bool:
    if mask_id == 0:
        return (r + c) % 2 == 0
    if mask_id == 1:
        return r % 2 == 0
    if mask_id == 2:
        return c % 3 == 0
    if mask_id == 3:
        return (r + c) % 3 == 0
    if mask_id == 4:
        return (r // 2 + c // 3) % 2 == 0
    if mask_id == 5:
        return ((r * c) % 2 + (r * c) % 3) == 0
    if mask_id == 6:
        return (((r * c) % 2 + (r * c) % 3) % 2) == 0
    return (((r + c) % 2 + (r * c) % 3) % 2) == 0


def _penalty_score(grid: list[list[int | None]]) -> int:
    size = len(grid)
    score = 0
    # Rule 1: 5+ consecutive same-color modules in rows/cols
    for r in range(size):
        run = 1
        for c in range(1, size):
            if grid[r][c] == grid[r][c - 1]:
                run += 1
            else:
                if run >= 5:
                    score += 3 + (run - 5)
                run = 1
        if run >= 5:
            score += 3 + (run - 5)
    for c in range(size):
        run = 1
        for r in range(1, size):
            if grid[r][c] == grid[r - 1][c]:
                run += 1
            else:
                if run >= 5:
                    score += 3 + (run - 5)
                run = 1
        if run >= 5:
            score += 3 + (run - 5)
    # Rule 2: 2x2 blocks
    for r in range(size - 1):
        for c in range(size - 1):
            v = grid[r][c]
            if v == grid[r][c + 1] == grid[r + 1][c] == grid[r + 1][c + 1]:
                score += 3
    return score


def build_qr_matrix(text: str) -> list[list[int]]:
    """Encode ``text`` into a 0/1 QR matrix (Byte mode, ECC Level M)."""
    version, codewords = _encode_codewords(text.encode("utf-8"))
    size, _dcw, _ecw, _blocks, align_centers = _VERSION_SPECS[version]

    base: list[list[int | None]] = [[None] * size for _ in range(size)]
    reserved: list[list[bool]] = [[False] * size for _ in range(size)]

    _place_finder(base, reserved, 0, 0)
    _place_finder(base, reserved, 0, size - 7)
    _place_finder(base, reserved, size - 7, 0)

    # Alignment patterns
    for r0 in align_centers:
        for c0 in align_centers:
            if reserved[r0][c0]:
                continue
            _place_alignment(base, reserved, r0, c0)

    # Timing patterns
    for i in range(8, size - 8):
        bit = 1 if i % 2 == 0 else 0
        if not reserved[6][i]:
            base[6][i] = bit
            reserved[6][i] = True
        if not reserved[i][6]:
            base[i][6] = bit
            reserved[i][6] = True

    # Dark module & reserve format info areas
    base[size - 8][8] = 1
    reserved[size - 8][8] = True
    for i in range(9):
        reserved[8][i] = True
        reserved[i][8] = True
    for i in range(8):
        reserved[8][size - 1 - i] = True
        reserved[size - 1 - i][8] = True

    bit_stream = [(cw >> shift) & 1 for cw in codewords for shift in range(7, -1, -1)]
    bit_idx = 0
    col = size - 1
    upward = True
    while col > 0:
        if col == 6:
            col -= 1
        row_range = range(size - 1, -1, -1) if upward else range(size)
        for row in row_range:
            for dc in (0, -1):
                c = col + dc
                if not reserved[row][c]:
                    base[row][c] = bit_stream[bit_idx] if bit_idx < len(bit_stream) else 0
                    bit_idx += 1
        upward = not upward
        col -= 2

    best_grid: list[list[int | None]] | None = None
    best_score = 10**9
    for mask_id in range(8):
        candidate = [row[:] for row in base]
        for r in range(size):
            for c in range(size):
                if not reserved[r][c] and _mask_fn(mask_id, r, c):
                    candidate[r][c] = 1 - (candidate[r][c] or 0)
        _apply_format(candidate, mask_id)
        sc = _penalty_score(candidate)
        if sc < best_score:
            best_score = sc
            best_grid = candidate

    assert best_grid is not None
    return [[1 if cell else 0 for cell in row] for row in best_grid]


def render_qr_svg(text: str, *, quiet_zone: int = 4) -> str:
    """Render a crisp, scannable SVG QR code for ``text``."""
    matrix = build_qr_matrix(text)
    size = len(matrix)
    total = size + 2 * quiet_zone
    rects = "".join(
        f'<rect x="{c + quiet_zone}" y="{r + quiet_zone}" width="1" height="1"/>'
        for r, row in enumerate(matrix)
        for c, cell in enumerate(row)
        if cell
    )
    label = escape(f"QR code for {text}")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total} {total}" '
        f'width="220" height="220" role="img" aria-label="{label}" shape-rendering="crispEdges">'
        f'<rect width="{total}" height="{total}" fill="#ffffff"/>'
        f'<g fill="#0f172a">{rects}</g>'
        "</svg>"
    )
