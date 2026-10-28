"""Read PE import names from a native Windows wheel, without loading DLLs."""
import struct
from pathlib import Path


def imports(path):
    """Return owned DLL names from PE32+ import descriptors, raising on malformed data.

    Input is a file Path; offsets/sizes are bytes. Pure synchronous read-only test
    helper, no GPU ownership. Source: Microsoft PE/COFF import-table layout.
    """
    b = Path(path).read_bytes()
    if b[:2] != b'MZ': raise ValueError('Not PE')
    pe = struct.unpack_from('<I', b, 0x3c)[0]
    if b[pe:pe+4] != b'PE\0\0': raise ValueError('Invalid PE signature')
    sections = struct.unpack_from('<H', b, pe+6)[0]
    optional_size = struct.unpack_from('<H', b, pe+20)[0]
    optional = pe+24
    if struct.unpack_from('<H', b, optional)[0] != 0x20b: raise ValueError('Expected PE32+')
    table_rva = struct.unpack_from('<I', b, optional+120)[0]
    table = []
    for i in range(sections):
        start = optional+optional_size+40*i
        virtual_size, rva, raw_size, raw = struct.unpack_from('<IIII', b, start+8)
        table.append((rva, max(virtual_size, raw_size), raw))
    def offset(rva):
        for start, size, raw in table:
            if start <= rva < start+size: return raw+rva-start
        raise ValueError('PE RVA outside sections')
    if not table_rva: return []
    pos = offset(table_rva); names = []
    while True:
        entry = struct.unpack_from('<IIIII', b, pos)
        if not any(entry): break
        start = offset(entry[3]); end = b.index(0, start)
        names.append(b[start:end].decode('ascii')); pos += 20
    return sorted(names, key=str.lower)
