import ure as re

# ============================================================================
# KONSTANTEN - exakt wie im Original
# ============================================================================
ERROR_CORRECT_L = 1
ERROR_CORRECT_M = 0
ERROR_CORRECT_Q = 3
ERROR_CORRECT_H = 2

MODE_NUMBER = 1 << 0
MODE_ALPHA_NUM = 1 << 1
MODE_8BIT_BYTE = 1 << 2
MODE_KANJI = 1 << 3

PAD0 = 0xEC
PAD1 = 0x11

G15 = (1 << 10) | (1 << 8) | (1 << 5) | (1 << 4) | (1 << 2) | (1 << 1) | (1 << 0)
G18 = (1 << 12) | (1 << 11) | (1 << 10) | (1 << 9) | (1 << 8) | (1 << 5) | (1 << 2) | (1 << 0)
G15_MASK = (1 << 14) | (1 << 12) | (1 << 10) | (1 << 4) | (1 << 1)

ALPHA_NUM = b'0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:'

NUMBER_LENGTH = {3: 10, 2: 7, 1: 4}

MODE_SIZE_SMALL = {
    MODE_NUMBER: 10,
    MODE_ALPHA_NUM: 9,
    MODE_8BIT_BYTE: 8,
    MODE_KANJI: 8,
}
MODE_SIZE_MEDIUM = {
    MODE_NUMBER: 12,
    MODE_ALPHA_NUM: 11,
    MODE_8BIT_BYTE: 16,
    MODE_KANJI: 10,
}
MODE_SIZE_LARGE = {
    MODE_NUMBER: 14,
    MODE_ALPHA_NUM: 13,
    MODE_8BIT_BYTE: 16,
    MODE_KANJI: 12,
}

RS_BLOCK_OFFSET = {
    ERROR_CORRECT_L: 0,
    ERROR_CORRECT_M: 1,
    ERROR_CORRECT_Q: 2,
    ERROR_CORRECT_H: 3,
}

# ============================================================================
# KOMPAKTE TABELLEN - als bytes statt viele einzelne Byte-Strings
# ============================================================================

# Galois Field: EXP_TABLE[0..255] und LOG_TABLE[0..255]
# Berechnet zur Ladezeit, gespeichert als bytearray (spart RAM vs list)
_EXP_TABLE = bytearray(512)
_LOG_TABLE = bytearray(256)
for i in range(8):
    _EXP_TABLE[i] = 1 << i
for i in range(8, 256):
    _EXP_TABLE[i] = _EXP_TABLE[i - 4] ^ _EXP_TABLE[i - 5] ^ _EXP_TABLE[i - 6] ^ _EXP_TABLE[i - 8]
for i in range(255):
    _LOG_TABLE[_EXP_TABLE[i]] = i
# Spiegelung für schnellen Zugriff ohne Modulo
for i in range(256, 512):
    _EXP_TABLE[i] = _EXP_TABLE[i - 255]

def glog(n):
    if n < 1:
        raise ValueError("glog(%s)" % n)
    return _LOG_TABLE[n]

def gexp(n):
    return _EXP_TABLE[n & 0xFF]

# RS Block Daten - kompakt als ein bytes-Objekt
# Format: 40 Versionen * 4 Error-Level = 160 Einträge, je 3 Bytes
_RS_BLOCK_DATA = bytes([
    1,26,19, 1,26,16, 1,26,13, 1,26,9,
    1,44,34, 1,44,28, 1,44,22, 1,44,16,
    1,70,55, 1,70,44, 2,35,17, 2,35,13,
    1,100,80, 2,50,32, 2,50,24, 4,25,9,
    1,134,108, 2,67,43, 2,33,15, 2,33,11,
    2,86,68, 4,43,27, 4,43,19, 4,43,15,
    2,98,78, 4,49,31, 2,32,14, 4,39,13,
    2,121,97, 2,60,38, 4,40,18, 4,40,14,
    2,146,116, 3,58,36, 4,36,16, 4,36,12,
    2,86,68, 4,69,43, 6,43,19, 6,43,15,
    4,101,81, 1,80,50, 4,50,22, 4,50,16,
    2,116,92, 6,58,36, 4,46,20, 7,42,14,
    4,133,107, 8,59,37, 8,44,20, 12,33,11,
    3,145,115, 4,64,40, 11,36,16, 11,36,12,
    5,109,87, 5,65,41, 5,54,24, 5,54,20,
    5,122,98, 7,73,45, 15,43,19, 3,45,15,
    1,135,107, 10,74,46, 1,50,22, 2,42,14,
    5,150,120, 9,69,43, 17,50,22, 2,42,14,
    3,141,113, 3,70,44, 17,47,21, 9,39,13,
    3,135,107, 3,67,41, 15,54,24, 15,43,15,
    4,144,116, 17,68,42, 17,50,22, 19,46,16,
    2,139,111, 17,74,46, 7,54,24, 34,37,13,
    4,151,121, 4,75,47, 11,54,24, 16,45,15,
    6,147,117, 6,73,45, 11,54,24, 30,46,16,
    8,132,106, 8,75,47, 7,54,24, 22,45,15,
    10,142,114, 19,74,46, 28,50,22, 33,46,16,
    8,152,122, 22,73,45, 8,53,23, 12,45,15,
    3,147,117, 3,73,45, 4,54,24, 11,45,15,
    7,146,116, 21,73,45, 1,53,23, 19,45,15,
    5,145,115, 19,75,47, 15,54,24, 23,45,15,
    13,145,115, 2,74,46, 42,54,24, 23,45,15,
    17,145,115, 10,74,46, 10,54,24, 19,45,15,
    17,145,115, 14,74,46, 29,54,24, 11,45,15,
    13,145,115, 14,74,46, 44,54,24, 59,46,16,
    12,151,121, 12,75,47, 39,54,24, 22,45,15,
    6,151,121, 6,75,47, 46,54,24, 2,45,15,
    17,152,122, 29,74,46, 49,54,24, 24,45,15,
    4,152,122, 13,74,46, 48,54,24, 42,45,15,
    20,147,117, 40,75,47, 43,54,24, 10,45,15,
    19,148,118, 18,75,47, 34,54,24, 20,45,15,
])

# Pattern Positionen - kompakt
# Format: Anzahl Positionen, dann Positionen
_PATTERN_POS = bytes([
    0,
    2,6,18,
    2,6,22,
    2,6,26,
    2,6,30,
    2,6,34,
    3,6,22,38,
    3,6,24,42,
    3,6,26,46,
    3,6,28,50,
    3,6,30,54,
    3,6,32,58,
    3,6,34,62,
    4,6,26,46,66,
    4,6,26,48,70,
    4,6,26,50,74,
    4,6,30,54,78,
    4,6,30,56,82,
    4,6,30,58,86,
    4,6,34,62,90,
    5,6,28,50,72,94,
    5,6,26,50,74,98,
    5,6,30,54,78,102,
    5,6,28,54,80,106,
    5,6,32,58,84,110,
    5,6,30,58,86,114,
    5,6,34,62,90,118,
    6,6,26,50,74,98,122,
    6,6,30,54,78,102,126,
    6,6,26,52,78,104,130,
    6,6,30,56,82,108,134,
    6,6,34,60,86,112,138,
    6,6,30,58,86,114,142,
    6,6,34,62,90,118,146,
    7,6,30,54,78,102,126,150,
    7,6,24,50,76,102,128,154,
    7,6,28,54,80,106,132,158,
    7,6,32,58,84,110,136,162,
    7,6,26,54,82,110,138,166,
    7,6,30,58,86,114,142,170,
])

# Bit-Limit Tabelle - als kompaktes bytes für 16-bit Werte (big-endian)
_BIT_LIMIT_RAW = bytes([
    # L: Version 0-40
    0,0, 0,152, 1,16, 1,184, 2,128, 3,96, 4,64, 4,224, 6,16, 7,64,
    8,144, 10,32, 11,128, 13,96, 14,104, 16,88, 18,104, 20,56, 22,136, 24,216,
    26,232, 29,32, 31,80, 34,64, 36,176, 39,224, 42,208, 45,224, 47,184, 50,248,
    54,56, 57,152, 61,40, 64,184, 68,120, 72,16, 76,16, 80,48, 84,80, 88,160, 92,96,
    # M: Version 0-40
    0,0, 0,128, 0,224, 1,96, 2,0, 2,176, 3,96, 3,224, 4,208, 5,160,
    6,192, 7,240, 9,16, 10,160, 11,152, 12,248, 14,24, 15,216, 17,184, 19,152, 21,248,
    20,232, 22,80, 24,160, 26,224, 28,64, 31,64, 33,80, 35,64, 37,40, 39,248,
    42,232, 45,104, 48,40, 51,16, 53,232, 56,224, 59,184, 62,80, 65,160, 69,32, 72,208,
    # Q: Version 0-40
    0,0, 0,104, 0,176, 1,16, 1,128, 1,240, 2,96, 2,192, 3,112, 4,32,
    4,208, 5,160, 6,112, 7,160, 8,40, 9,56, 10,40, 11,120, 12,104, 13,232,
    15,40, 16,0, 17,192, 19,64, 20,224, 22,160, 23,160, 25,64, 27,184, 28,88,
    30,248, 32,168, 34,208, 36,168, 38,168, 40,48, 42,80, 44,160, 46,176, 49,80, 51,176,
    # H: Version 0-40
    0,0, 0,72, 0,128, 0,208, 1,32, 1,112, 1,224, 2,16, 2,176, 3,32,
    3,208, 4,96, 4,240, 5,160, 6,40, 6,248, 7,232, 8,216, 9,232, 10,168,
    12,8, 12,176, 13,192, 14,144, 16,16, 16,224, 18,128, 19,160, 20,128, 21,232,
    23,104, 24,184, 26,96, 28,112, 30,8, 30,248, 32,240, 34,64, 35,160, 38,32, 38,96,
])

# ============================================================================
# HILFSFUNKTIONEN
# ============================================================================

def _get_bit_limit(version, error_correction):
    """Holt Bit-Limit aus kompakter Tabelle"""
    idx = (error_correction * 41 + version) * 2
    return (_BIT_LIMIT_RAW[idx] << 8) | _BIT_LIMIT_RAW[idx + 1]

def _get_rs_block(version, error_correction):
    """Holt RS Block Daten (count, total_count, data_count)"""
    offset = RS_BLOCK_OFFSET[error_correction]
    idx = ((version - 1) * 4 + offset) * 3
    return _RS_BLOCK_DATA[idx:idx + 3]

def _pattern_position(version):
    """Gibt Pattern-Positionen als tuple zurück"""
    idx = 0
    for v in range(1, version):
        idx += 1 + _PATTERN_POS[idx]
    count = _PATTERN_POS[idx]
    idx += 1
    return tuple(_PATTERN_POS[idx:idx + count])

def _mode_sizes_for_version(version):
    if version < 10:
        return MODE_SIZE_SMALL
    elif version < 27:
        return MODE_SIZE_MEDIUM
    else:
        return MODE_SIZE_LARGE

def _length_in_bits(mode, version):
    return _mode_sizes_for_version(version)[mode]

def BCH_digit(data):
    digit = 0
    while data != 0:
        digit += 1
        data >>= 1
    return digit

def BCH_type_info(data):
    d = data << 10
    while BCH_digit(d) - BCH_digit(G15) >= 0:
        d ^= G15 << (BCH_digit(d) - BCH_digit(G15))
    return ((data << 10) | d) ^ G15_MASK

def BCH_type_number(data):
    d = data << 12
    while BCH_digit(d) - BCH_digit(G18) >= 0:
        d ^= G18 << (BCH_digit(d) - BCH_digit(G18))
    return (data << 12) | d

def _make_mask_func(pattern):
    if pattern == 0:
        return lambda i, j: (i + j) % 2 == 0
    if pattern == 1:
        return lambda i, j: i % 2 == 0
    if pattern == 2:
        return lambda i, j: j % 3 == 0
    if pattern == 3:
        return lambda i, j: (i + j) % 3 == 0
    if pattern == 4:
        return lambda i, j: (int(i / 2) + int(j / 3)) % 2 == 0
    if pattern == 5:
        return lambda i, j: (i * j) % 2 + (i * j) % 3 == 0
    if pattern == 6:
        return lambda i, j: ((i * j) % 2 + (i * j) % 3) % 2 == 0
    if pattern == 7:
        return lambda i, j: ((i * j) % 3 + (i + j) % 2) % 2 == 0
    raise TypeError("Bad mask pattern: " + str(pattern))

def _to_bytestring(data):
    if not isinstance(data, bytes):
        data = str(data).encode('utf-8')
    return data

def _optimal_mode(data):
    if data.isdigit():
        return MODE_NUMBER
    for b in data:
        if b not in ALPHA_NUM:
            return MODE_8BIT_BYTE
    return MODE_ALPHA_NUM

# ============================================================================
# REED-SOLOMON
# ============================================================================

class RSBlock:
    __slots__ = ('total_count', 'data_count')

    def __init__(self, total_count, data_count):
        self.total_count = total_count
        self.data_count = data_count

def _make_rs_blocks(version, error_correction):
    raw = _get_rs_block(version, error_correction)
    count, total_count, data_count = raw[0], raw[1], raw[2]
    return [RSBlock(total_count, data_count) for _ in range(count)]

# Cache für RS-Polynome
_RS_POLY_CACHE = {}

def _get_rs_poly(ec_count):
    if ec_count not in _RS_POLY_CACHE:
        poly = Polynomial([1], 0)
        for i in range(ec_count):
            poly = poly * Polynomial([1, gexp(i)], 0)
        _RS_POLY_CACHE[ec_count] = poly
    return _RS_POLY_CACHE[ec_count]

# ============================================================================
# POLYNOMIAL - Galois Field
# ============================================================================

class Polynomial:
    __slots__ = ('num',)

    def __init__(self, num, shift=0):
        offset = 0
        for i in range(len(num)):
            if num[i] != 0:
                offset = i
                break
        else:
            offset = len(num)

        # bytearray statt list
        self.num = bytearray(num[offset:]) + bytearray(shift)

    def __getitem__(self, index):
        return self.num[index]

    def __len__(self):
        return len(self.num)

    def __mul__(self, other):
        num = bytearray(len(self) + len(other) - 1)
        for i, item in enumerate(self.num):
            if item == 0:
                continue
            log_item = glog(item)
            for j, other_item in enumerate(other.num):
                if other_item == 0:
                    continue
                num[i + j] ^= gexp(log_item + glog(other_item))
        return Polynomial(num, 0)

    def __mod__(self, other):
        this = self.num[:]
        while len(this) >= len(other):
            difference = len(this) - len(other)
            ratio = glog(this[0]) - glog(other[0])
            for i, other_item in enumerate(other.num):
                this[i] ^= gexp(ratio + glog(other_item))
            # Entferne führende Nullen
            while this and this[0] == 0:
                this = this[1:]
        return Polynomial(this, 0)

# ============================================================================
# QR DATA
# ============================================================================

class QRData:
    __slots__ = ('mode', 'data')

    def __init__(self, data, mode=None, check_data=True):
        if check_data:
            data = _to_bytestring(data)

        if mode is None:
            self.mode = _optimal_mode(data)
        else:
            self.mode = mode
            if mode not in (MODE_NUMBER, MODE_ALPHA_NUM, MODE_8BIT_BYTE, MODE_KANJI):
                raise TypeError("Invalid mode (%s)" % mode)
            if check_data and mode < _optimal_mode(data):
                raise ValueError("Provided data can not be represented in mode %s" % mode)

        self.data = data

    def __len__(self):
        return len(self.data)

    def write(self, buffer):
        if self.mode == MODE_NUMBER:
            for i in range(0, len(self.data), 3):
                chars = self.data[i:i + 3]
                bit_length = NUMBER_LENGTH[len(chars)]
                buffer.put(int(chars), bit_length)
        elif self.mode == MODE_ALPHA_NUM:
            for i in range(0, len(self.data), 2):
                chars = self.data[i:i + 2]
                if len(chars) > 1:
                    buffer.put(
                        ALPHA_NUM.find(chars[0]) * 45 +
                        ALPHA_NUM.find(chars[1]), 11)
                else:
                    buffer.put(ALPHA_NUM.find(chars), 6)
        else:
            for c in self.data:
                buffer.put(c, 8)

    def __repr__(self):
        return repr(self.data)

def _optimal_data_chunks(data, minimum=4):
    data = _to_bytestring(data)
    num_pattern = re.compile(b'\d?' * minimum)
    num_bits = _optimal_split(data, num_pattern)
    alpha_pattern = re.compile(b"(" + (b'[' + ALPHA_NUM + b']?') * minimum + b")")
    for is_num, chunk in num_bits:
        if is_num:
            yield QRData(chunk, mode=MODE_NUMBER, check_data=False)
        else:
            for is_alpha, sub_chunk in _optimal_split(chunk, alpha_pattern):
                if is_alpha:
                    mode = MODE_ALPHA_NUM
                else:
                    mode = MODE_8BIT_BYTE
                yield QRData(sub_chunk, mode=mode, check_data=False)

def _optimal_split(data, pattern):
    while data:
        match = pattern.search(data)
        if not match:
            break
        matched = match.group(0)
        start = data.rfind(matched)
        end = len(matched) + start
        if start:
            yield False, data[:start]
        yield True, data[start:end]
        data = data[end:]
    if data:
        yield False, data

# ============================================================================
# BIT BUFFER
# ============================================================================

class BitBuffer:
    __slots__ = ('buffer', 'length')

    def __init__(self):
        self.buffer = []
        self.length = 0

    def __repr__(self):
        return ".".join([str(n) for n in self.buffer])

    def get(self, index):
        buf_index = int(index / 8)
        return ((self.buffer[buf_index] >> (7 - index % 8)) & 1) == 1

    def put(self, num, length):
        for i in range(length):
            self.put_bit(((num >> (length - i - 1)) & 1) == 1)

    def __len__(self):
        return self.length

    def put_bit(self, bit):
        buf_index = self.length // 8
        if len(self.buffer) <= buf_index:
            self.buffer.append(0)
        if bit:
            self.buffer[buf_index] |= (0x80 >> (self.length % 8))
        self.length += 1

# ============================================================================
# DATA ERZEUGUNG
# ============================================================================

def _create_bytes(buffer, rs_blocks):
    offset = 0
    maxDcCount = 0
    maxEcCount = 0
    dcdata = [0] * len(rs_blocks)
    ecdata = [0] * len(rs_blocks)

    for r in range(len(rs_blocks)):
        dcCount = rs_blocks[r].data_count
        ecCount = rs_blocks[r].total_count - dcCount

        maxDcCount = max(maxDcCount, dcCount)
        maxEcCount = max(maxEcCount, ecCount)

        dcdata[r] = [0] * dcCount
        for i in range(len(dcdata[r])):
            dcdata[r][i] = 0xff & buffer.buffer[i + offset]
        offset += dcCount

        rsPoly = _get_rs_poly(ecCount)
        rawPoly = Polynomial(dcdata[r], len(rsPoly) - 1)
        modPoly = rawPoly % rsPoly

        ecdata[r] = [0] * (len(rsPoly) - 1)
        for i in range(len(ecdata[r])):
            modIndex = i + len(modPoly) - len(ecdata[r])
            if modIndex >= 0:
                ecdata[r][i] = modPoly[modIndex]
            else:
                ecdata[r][i] = 0

    totalCodeCount = 0
    for rs_block in rs_blocks:
        totalCodeCount += rs_block.total_count

    data = [None] * totalCodeCount
    index = 0

    for i in range(maxDcCount):
        for r in range(len(rs_blocks)):
            if i < len(dcdata[r]):
                data[index] = dcdata[r][i]
                index += 1

    for i in range(maxEcCount):
        for r in range(len(rs_blocks)):
            if i < len(ecdata[r]):
                data[index] = ecdata[r][i]
                index += 1

    return data

def _create_data(version, error_correction, data_list):
    buffer = BitBuffer()
    for data in data_list:
        buffer.put(data.mode, 4)
        buffer.put(len(data), _length_in_bits(data.mode, version))
        data.write(buffer)

    rs_blocks = _make_rs_blocks(version, error_correction)
    bit_limit = 0
    for block in rs_blocks:
        bit_limit += block.data_count * 8

    if len(buffer) > bit_limit:
        raise Exception("Code length overflow. Data size (%s) > size available (%s)" % (len(buffer), bit_limit))

    for i in range(min(bit_limit - len(buffer), 4)):
        buffer.put_bit(False)

    delimit = len(buffer) % 8
    if delimit:
        for i in range(8 - delimit):
            buffer.put_bit(False)

    bytes_to_fill = (bit_limit - len(buffer)) // 8
    for i in range(bytes_to_fill):
        if i % 2 == 0:
            buffer.put(PAD0, 8)
        else:
            buffer.put(PAD1, 8)

    return _create_bytes(buffer, rs_blocks)

# ============================================================================
# LOST POINT (Masken-Bewertung)
# ============================================================================

def _make_lost_point(modules):
    modules_count = len(modules)
    lost_point = 0

    # Level 1
    lost_point = _lost_point_level1(modules, modules_count)
    lost_point += _lost_point_level2(modules, modules_count)
    lost_point += _lost_point_level3(modules, modules_count)
    lost_point += _lost_point_level4(modules, modules_count)

    return lost_point

def _lost_point_level1(modules, modules_count):
    lost_point = 0
    modules_range = range(modules_count)
    container = [0] * (modules_count + 1)

    for row in modules_range:
        this_row = modules[row]
        previous_color = this_row[0]
        length = 0
        for col in modules_range:
            if this_row[col] == previous_color:
                length += 1
            else:
                if length >= 5:
                    container[length] += 1
                length = 1
                previous_color = this_row[col]
        if length >= 5:
            container[length] += 1

    for col in modules_range:
        previous_color = modules[0][col]
        length = 0
        for row in modules_range:
            if modules[row][col] == previous_color:
                length += 1
            else:
                if length >= 5:
                    container[length] += 1
                length = 1
                previous_color = modules[row][col]
        if length >= 5:
            container[length] += 1

    lost_point += sum(container[each_length] * (each_length - 2)
        for each_length in range(5, modules_count + 1))

    return lost_point

def _lost_point_level2(modules, modules_count):
    lost_point = 0
    modules_range = range(modules_count - 1)
    for row in modules_range:
        this_row = modules[row]
        next_row = modules[row + 1]
        modules_range_iter = iter(modules_range)
        for col in modules_range_iter:
            top_right = this_row[col + 1]
            if top_right != next_row[col + 1]:
                try:
                    next(modules_range_iter)
                except StopIteration:
                    pass
            elif top_right != this_row[col]:
                continue
            elif top_right != next_row[col]:
                continue
            else:
                lost_point += 3
    return lost_point

def _lost_point_level3(modules, modules_count):
    modules_range = range(modules_count)
    modules_range_short = range(modules_count - 10)
    lost_point = 0

    for row in modules_range:
        this_row = modules[row]
        modules_range_short_iter = iter(modules_range_short)
        for col in modules_range_short_iter:
            if (
                not this_row[col + 1]
                and this_row[col + 4]
                and not this_row[col + 5]
                and this_row[col + 6]
                and not this_row[col + 9]
                and (
                    (this_row[col + 0] and this_row[col + 2] and this_row[col + 3] and not this_row[col + 7] and not this_row[col + 8] and not this_row[col + 10])
                    or
                    (not this_row[col + 0] and not this_row[col + 2] and not this_row[col + 3] and this_row[col + 7] and this_row[col + 8] and this_row[col + 10])
                )
            ):
                lost_point += 40
            if this_row[col + 10]:
                try:
                    next(modules_range_short_iter)
                except StopIteration:
                    pass

    for col in modules_range:
        modules_range_short_iter = iter(modules_range_short)
        for row in modules_range_short_iter:
            if (
                not modules[row + 1][col]
                and modules[row + 4][col]
                and not modules[row + 5][col]
                and modules[row + 6][col]
                and not modules[row + 9][col]
                and (
                    (modules[row + 0][col] and modules[row + 2][col] and modules[row + 3][col] and not modules[row + 7][col] and not modules[row + 8][col] and not modules[row + 10][col])
                    or
                    (not modules[row + 0][col] and not modules[row + 2][col] and not modules[row + 3][col] and modules[row + 7][col] and modules[row + 8][col] and modules[row + 10][col])
                )
            ):
                lost_point += 40
            if modules[row + 10][col]:
                try:
                    next(modules_range_short_iter)
                except StopIteration:
                    pass

    return lost_point

def _lost_point_level4(modules, modules_count):
    dark_count = sum(map(sum, modules))
    percent = float(dark_count) / (modules_count ** 2)
    rating = int(abs(percent * 100 - 50) / 5)
    return rating * 10

# ============================================================================
# HAUPTKLASSE: QRCode
# ============================================================================

class QRCode:
    def __init__(self, version=None,
                 error_correction=ERROR_CORRECT_M,
                 box_size=10, border=4,
                 mask_pattern=None):
        self.version = version and int(version)
        self.error_correction = int(error_correction)
        self.box_size = int(box_size)
        self.border = int(border)
        self.mask_pattern = mask_pattern
        self.modules = None
        self.modules_count = 0
        self.data_cache = None
        self.data_list = []

    def clear(self):
        self.modules = None
        self.modules_count = 0
        self.data_cache = None
        self.data_list = []

    def add_data(self, data, optimize=20):
        if isinstance(data, QRData):
            self.data_list.append(data)
        else:
            if optimize:
                self.data_list.extend(_optimal_data_chunks(data, optimize))
            else:
                self.data_list.append(QRData(data))
        self.data_cache = None

    def make(self, fit=True):
        if fit or (self.version is None):
            self.best_fit(start=self.version)
        if self.mask_pattern is None:
            self.makeImpl(False, self.best_mask_pattern())
        else:
            self.makeImpl(False, self.mask_pattern)

    def makeImpl(self, test, mask_pattern):
        self.modules_count = self.version * 4 + 17
        self.modules = [None] * self.modules_count

        for row in range(self.modules_count):
            self.modules[row] = [None] * self.modules_count
            for col in range(self.modules_count):
                self.modules[row][col] = None

        self.setup_position_probe_pattern(0, 0)
        self.setup_position_probe_pattern(self.modules_count - 7, 0)
        self.setup_position_probe_pattern(0, self.modules_count - 7)
        self.setup_position_adjust_pattern()
        self.setup_timing_pattern()
        self.setup_type_info(test, mask_pattern)

        if self.version >= 7:
            self.setup_type_number(test)

        if self.data_cache is None:
            self.data_cache = _create_data(self.version, self.error_correction, self.data_list)
        self.map_data(self.data_cache, mask_pattern)

    def setup_position_probe_pattern(self, row, col):
        for r in range(-1, 8):
            if row + r <= -1 or self.modules_count <= row + r:
                continue
            for c in range(-1, 8):
                if col + c <= -1 or self.modules_count <= col + c:
                    continue
                if (0 <= r and r <= 6 and (c == 0 or c == 6)) or                    (0 <= c and c <= 6 and (r == 0 or r == 6)) or                    (2 <= r and r <= 4 and 2 <= c and c <= 4):
                    self.modules[row + r][col + c] = True
                else:
                    self.modules[row + r][col + c] = False

    def setup_timing_pattern(self):
        for r in range(8, self.modules_count - 8):
            if self.modules[r][6] is not None:
                continue
            self.modules[r][6] = (r % 2 == 0)
        for c in range(8, self.modules_count - 8):
            if self.modules[6][c] is not None:
                continue
            self.modules[6][c] = (c % 2 == 0)

    def setup_position_adjust_pattern(self):
        pos = _pattern_position(self.version)
        for i in range(len(pos)):
            for j in range(len(pos)):
                row = pos[i]
                col = pos[j]
                if self.modules[row][col] is not None:
                    continue
                for r in range(-2, 3):
                    for c in range(-2, 3):
                        if (r == -2 or r == 2 or c == -2 or c == 2 or
                                (r == 0 and c == 0)):
                            self.modules[row + r][col + c] = True
                        else:
                            self.modules[row + r][col + c] = False

    def setup_type_number(self, test):
        bits = BCH_type_number(self.version)
        for i in range(18):
            mod = (not test and ((bits >> i) & 1) == 1)
            self.modules[i // 3][i % 3 + self.modules_count - 8 - 3] = mod
            self.modules[i % 3 + self.modules_count - 8 - 3][i // 3] = mod

    def setup_type_info(self, test, mask_pattern):
        data = (self.error_correction << 3) | mask_pattern
        bits = BCH_type_info(data)

        for i in range(15):
            mod = (not test and ((bits >> i) & 1) == 1)
            if i < 6:
                self.modules[i][8] = mod
            elif i < 8:
                self.modules[i + 1][8] = mod
            else:
                self.modules[self.modules_count - 15 + i][8] = mod

            if i < 8:
                self.modules[8][self.modules_count - i - 1] = mod
            elif i < 9:
                self.modules[8][15 - i - 1 + 1] = mod
            else:
                self.modules[8][15 - i - 1] = mod

        self.modules[self.modules_count - 8][8] = (not test)

    def map_data(self, data, mask_pattern):
        inc = -1
        row = self.modules_count - 1
        bitIndex = 7
        byteIndex = 0
        data_len = len(data)
        mask_func = _make_mask_func(mask_pattern)

        for col in range(self.modules_count - 1, 0, -2):
            if col <= 6:
                col -= 1
            col_range = (col, col - 1)
            while True:
                for c in col_range:
                    if self.modules[row][c] is None:
                        dark = False
                        if byteIndex < data_len:
                            dark = ((data[byteIndex] >> bitIndex) & 1) == 1
                        if mask_func(row, c):
                            dark = not dark
                        self.modules[row][c] = dark
                        bitIndex -= 1
                        if bitIndex == -1:
                            byteIndex += 1
                            bitIndex = 7
                row += inc
                if row < 0 or self.modules_count <= row:
                    row -= inc
                    inc = -inc
                    break

    def best_fit(self, start=None):
        if start is None:
            start = 1
        if start < 1 or start > 40:
            raise ValueError("Invalid version (was %s, expected 1 to 40)" % start)

        self.version = start

        while self.version <= 40:
            mode_sizes = _mode_sizes_for_version(self.version)
            buffer = BitBuffer()
            for data in self.data_list:
                buffer.put(data.mode, 4)
                buffer.put(len(data), mode_sizes[data.mode])
                data.write(buffer)

            bit_limit = _get_bit_limit(self.version, self.error_correction)
            if len(buffer) <= bit_limit:
                break
            self.version += 1

        if self.version > 40:
            raise Exception("Data too long")

        # Rekursion falls mode_sizes sich geändert haben
        if mode_sizes is not _mode_sizes_for_version(self.version):
            self.best_fit(start=self.version)

    def best_mask_pattern(self):
        min_lost_point = 0
        pattern = 0
        for i in range(8):
            self.makeImpl(True, i)
            lost_point = _make_lost_point(self.modules)
            if i == 0 or min_lost_point > lost_point:
                min_lost_point = lost_point
                pattern = i
        return pattern

    def get_matrix(self):
        if self.data_cache is None:
            self.make()
        if not self.border:
            return self.modules

        width = len(self.modules) + self.border * 2
        code = [[False] * width] * self.border
        x_border = [False] * self.border
        for module in self.modules:
            code.append(x_border + module + x_border)
        code += [[False] * width] * self.border
        return code

    def render_matrix(self):
        out = ""
        for row in self.get_matrix():
            out += "".join([{False: " ", True: "█"}[x] if x in (False, True) else "╳" for x in row])
            out += "\n"
        return out

# ============================================================================
# KONVENIENZFUNKTION
# ============================================================================

def make(data=None, **kwargs):
    qr = QRCode(**kwargs)
    qr.add_data(data)
    return qr.get_matrix()
