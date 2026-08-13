#!/usr/bin/env python3
"""
Add Module1 standard VBA module to vbaProject.bin so form-control buttons can call it.
All patches are done in-place on the binary:
  1. Fix vba_compress for small chunks
  2. Build Module1 compressed source
  3. Allocate mini-sectors 174+175 for Module1
  4. Update mini-FAT
  5. Update Root Entry size
  6. Extend directory: add sector 28, update FAT, add Module1 dir entry
  7. Update RB-tree: dir entry[9] right → 12
  8. Patch dir stream: increment PROJECTMODULECOUNT, insert Module1 MODULE record
  9. Patch PROJECT stream: add Module1 entries
 10. Recompress dir and PROJECT streams
 11. Write VML FmlaMacro to reference Module1
 12. Repack xlsm
"""

import zipfile, struct, shutil, os, math, re

WORK_DIR = "/tmp/claude-0/-home-user-Susi/b0a230a7-31e1-539f-ba58-ad030fd9c1d6/scratchpad/xlsm_work"
OUT_XLSM = "/tmp/claude-0/-home-user-Susi/b0a230a7-31e1-539f-ba58-ad030fd9c1d6/scratchpad/Gesamt_Anlagenstrategie_MIT_BUTTON.xlsm"
VBA_PATH = os.path.join(WORK_DIR, 'xl', 'vbaProject.bin')

SECTOR_SIZE      = 512
MINI_SECTOR_SIZE = 64
FREESECT   = 0xFFFFFFFF
ENDOFCHAIN = 0xFFFFFFFE
FATSECT    = 0xFFFFFFFD
DIFSECT    = 0xFFFFFFFC

# ────────────────────────────────────────────────────────────────────────────────
# Fixed MS-OVBA LZ77 (handles small chunks correctly)
# ────────────────────────────────────────────────────────────────────────────────

def _copytoken_help(decompressed_current, chunk_start):
    difference = decompressed_current - chunk_start
    if   difference <= 16:   length_shift = 12
    elif difference <= 32:   length_shift = 11
    elif difference <= 64:   length_shift = 10
    elif difference <= 128:  length_shift = 9
    elif difference <= 256:  length_shift = 8
    elif difference <= 512:  length_shift = 7
    elif difference <= 1024: length_shift = 6
    elif difference <= 2048: length_shift = 5
    else:                    length_shift = 4
    copy_bit_count = 16 - length_shift
    length_mask    = (1 << length_shift) - 1
    offset_mask    = 0xFFFF ^ length_mask
    max_length     = length_mask + 3
    return (length_mask, offset_mask, copy_bit_count, max_length)


def _compress_chunk(chunk: bytes, chunk_start: int) -> bytes:
    out = bytearray()
    i = 0
    n = len(chunk)
    while i < n:
        flag_byte_pos = len(out)
        out.append(0)
        flag_byte = 0
        for bit in range(8):
            if i >= n:
                break
            best_len = 0
            best_off = 0
            if i > 0:
                lm, om, bc, max_len = _copytoken_help(chunk_start + i, chunk_start)
                max_offset = (om >> (16 - bc)) + 1
                search_start = max(0, i - max_offset)
                for j in range(search_start, i):
                    run = 0
                    while run < max_len and i + run < n and chunk[j + run % (i - j)] == chunk[i + run]:
                        run += 1
                    if run > best_len:
                        best_len = run
                        best_off = i - j
            if best_len >= 3:
                lm, om, bc, _ = _copytoken_help(chunk_start + i, chunk_start)
                len_field = (best_len - 3) & lm
                off_field = ((best_off - 1) << (16 - bc)) & om
                out += struct.pack('<H', off_field | len_field)
                flag_byte |= (1 << bit)
                i += best_len
            else:
                out.append(chunk[i])
                i += 1
        out[flag_byte_pos] = flag_byte
    return bytes(out)


def vba_compress(data: bytes) -> bytes:
    """Compress using MS-OVBA LZ77. Always uses compressed format for sub-4096 chunks."""
    out = bytearray([0x01])  # SignatureByte
    i = 0
    n = len(data)
    while i < n:
        chunk_start = i
        chunk_data  = data[chunk_start : chunk_start + 4096]
        chunk_len   = len(chunk_data)
        compressed  = _compress_chunk(chunk_data, chunk_start)
        # Use compressed format when: it saves space OR chunk is smaller than 4096
        # (raw chunk always pads to 4096 bytes, so compressed is better for small chunks)
        if chunk_len < 4096 or len(compressed) < chunk_len:
            size_field = len(compressed) - 3
            header = (1 << 15) | (0b011 << 12) | (size_field & 0x0FFF)
            out += struct.pack('<H', header)
            out += compressed
        else:
            header = (0 << 15) | (0b011 << 12) | 0x7FF
            out += struct.pack('<H', header)
            out += chunk_data.ljust(4096, b'\x00')
        i += chunk_len
    return bytes(out)


def vba_decompress(data: bytes) -> bytes:
    if not data or data[0] != 0x01:
        raise ValueError("Not a compressed stream")
    decompressed = bytearray()
    i = 1
    while i < len(data):
        if i + 1 >= len(data):
            break
        header = struct.unpack_from('<H', data, i)[0]
        i += 2
        is_compressed  = bool(header >> 15)
        chunk_size     = (header & 0x0FFF) + 3 if is_compressed else 4096
        chunk_end      = i + chunk_size
        chunk_start_d  = len(decompressed)
        if not is_compressed:
            decompressed += data[i:i+4096]
            i += 4096
            continue
        while i < chunk_end and i < len(data):
            flag_byte = data[i]; i += 1
            for bit in range(8):
                if i >= chunk_end or i >= len(data):
                    break
                if flag_byte & (1 << bit):
                    tok = struct.unpack_from('<H', data, i)[0]; i += 2
                    lm, om, bc, _ = _copytoken_help(len(decompressed), chunk_start_d)
                    length = (tok & lm) + 3
                    offset = ((tok & om) >> (16 - bc)) + 1
                    src = len(decompressed) - offset
                    for k in range(length):
                        decompressed.append(decompressed[src + k])
                else:
                    decompressed.append(data[i]); i += 1
    return bytes(decompressed)


# ────────────────────────────────────────────────────────────────────────────────
# OLE2 helpers
# ────────────────────────────────────────────────────────────────────────────────

def sec_off(s): return (s + 1) * SECTOR_SIZE

def read_fat(data):
    return list(struct.unpack_from('<128I', data, sec_off(0)))

def write_fat(data, fat):
    struct.pack_into('<128I', data, sec_off(0), *fat)

def read_minifat(data, fat):
    mf_start = struct.unpack_from('<I', data, 0x3C)[0]
    sectors = []
    s = mf_start
    while s not in (ENDOFCHAIN, FREESECT, FATSECT, DIFSECT):
        sectors.append(s)
        s = fat[s]
    entries = []
    for s in sectors:
        entries += list(struct.unpack_from('<128I', data, sec_off(s)))
    return entries, sectors

def write_minifat(data, fat, mf_entries):
    _, sectors = read_minifat(data, fat)
    for idx, s in enumerate(sectors):
        chunk = mf_entries[idx*128 : (idx+1)*128]
        chunk += [FREESECT] * (128 - len(chunk))
        struct.pack_into('<128I', data, sec_off(s), *chunk)

def follow_chain(fat, start):
    chain = []
    s = start
    while s not in (ENDOFCHAIN, FREESECT, FATSECT, DIFSECT):
        chain.append(s)
        if s >= len(fat): break
        s = fat[s]
    return chain

def follow_mini_chain(mf, start):
    chain = []
    s = start
    while s not in (ENDOFCHAIN, FREESECT, FATSECT, DIFSECT):
        chain.append(s)
        if s >= len(mf): break
        s = mf[s]
    return chain

def read_ministream(data, fat):
    root_start = struct.unpack_from('<I', data, sec_off(1) + 116)[0]
    chain = follow_chain(fat, root_start)
    ms = bytearray()
    for s in chain:
        ms += data[sec_off(s) : sec_off(s) + SECTOR_SIZE]
    return ms, chain

def write_ministream(data, fat, ms):
    _, chain = read_ministream(data, fat)
    for i, s in enumerate(chain):
        chunk = bytes(ms[i*SECTOR_SIZE : (i+1)*SECTOR_SIZE]).ljust(SECTOR_SIZE, b'\x00')
        data[sec_off(s) : sec_off(s)+SECTOR_SIZE] = chunk

def read_mini_stream_bytes_mf(ms, mf, start, size):
    chain = follow_mini_chain(mf, start)
    raw = b''
    for s in chain:
        raw += bytes(ms[s*64 : (s+1)*64])
    return raw[:size]

def write_mini_stream_bytes(ms, mf, start, payload):
    chain = follow_mini_chain(mf, start)
    padded = payload.ljust(len(chain) * 64, b'\x00')
    for i, s in enumerate(chain):
        ms[s*64 : (s+1)*64] = padded[i*64 : (i+1)*64]

def read_dir_sector(data, s):
    entries = []
    for i in range(4):
        entries.append(bytearray(data[sec_off(s)+i*128 : sec_off(s)+(i+1)*128]))
    return entries

def write_dir_sector(data, s, entries):
    for i, e in enumerate(entries):
        data[sec_off(s)+i*128 : sec_off(s)+(i+1)*128] = bytes(e).ljust(128, b'\x00')

def read_all_dir(data, fat):
    dir_start = struct.unpack_from('<I', data, 0x30)[0]
    chain = follow_chain(fat, dir_start)
    entries = []
    for s in chain:
        entries += read_dir_sector(data, s)
    return entries, chain

def write_all_dir(data, fat, entries):
    dir_start = struct.unpack_from('<I', data, 0x30)[0]
    chain = follow_chain(fat, dir_start)
    for si, s in enumerate(chain):
        for ei in range(4):
            gi = si*4 + ei
            raw = bytes(entries[gi]).ljust(128, b'\x00') if gi < len(entries) else b'\x00'*128
            data[sec_off(s)+ei*128 : sec_off(s)+(ei+1)*128] = raw

def parse_dir(raw):
    nl = struct.unpack_from('<H', raw, 64)[0]
    return {
        'name': raw[:(nl-2)].decode('utf-16-le') if nl >= 2 else '',
        'type': raw[66], 'color': raw[67],
        'left': struct.unpack_from('<I', raw, 68)[0],
        'right': struct.unpack_from('<I', raw, 72)[0],
        'child': struct.unpack_from('<I', raw, 76)[0],
        'clsid': raw[80:96],
        'start': struct.unpack_from('<I', raw, 116)[0],
        'size': struct.unpack_from('<I', raw, 120)[0],
    }

def make_dir_entry(name, entry_type, color, left, right, child, clsid, start, size):
    raw = bytearray(128)
    enc = name.encode('utf-16-le')
    raw[0:len(enc)] = enc
    struct.pack_into('<H', raw, 64, len(enc)+2 if name else 0)
    raw[66] = entry_type
    raw[67] = color
    struct.pack_into('<I', raw, 68, left)
    struct.pack_into('<I', raw, 72, right)
    struct.pack_into('<I', raw, 76, child)
    raw[80:96] = clsid
    struct.pack_into('<I', raw, 116, start)
    struct.pack_into('<I', raw, 120, size)
    return raw

def find_entry(entries, name):
    for i, e in enumerate(entries):
        if parse_dir(e)['name'] == name:
            return i
    return -1

# ────────────────────────────────────────────────────────────────────────────────
# DIR stream TLV builder
# ────────────────────────────────────────────────────────────────────────────────

def tlv(rec_id, data):
    return struct.pack('<HI', rec_id, len(data)) + data

def build_module1_dir_record():
    """Build the MODULE TLV record for Module1 (standard/procedural module)."""
    name    = b'Module1'
    name16  = 'Module1'.encode('utf-16-le')
    r  = tlv(0x0019, name)                     # MODULENAME
    r += tlv(0x0047, name16)                   # MODULENAMEUNICODE
    r += tlv(0x001a, name)                     # MODULESTREAMNAME
    r += tlv(0x0032, name16)                   # MODULESTREAMNAMEUNICODE
    r += tlv(0x001c, b'')                      # MODULEDOCSTRING
    r += tlv(0x0048, b'')                      # MODULEDOCSTRINGUNICODE
    r += tlv(0x0031, struct.pack('<I', 0))     # MODULEOFFSET (TextOffset=0)
    r += tlv(0x001e, struct.pack('<I', 0))     # MODULEHELPCONTEXT
    r += tlv(0x002c, b'\xff\xff')              # MODULECOOKIE
    r += tlv(0x0021, b'')                      # MODULETYPE PROCEDURAL (standard!)
    r += tlv(0x002b, b'')                      # MODULE_TERMINATOR
    return r


# ────────────────────────────────────────────────────────────────────────────────
# Main patch
# ────────────────────────────────────────────────────────────────────────────────

def patch():
    with open(VBA_PATH, 'rb') as f:
        data = bytearray(f.read())

    print(f"vbaProject.bin: {len(data)} bytes")

    fat = read_fat(data)
    mf, mf_sectors = read_minifat(data, fat)
    ms, root_chain  = read_ministream(data, fat)
    entries, dir_chain = read_all_dir(data, fat)

    print(f"FAT[0:30]: {fat[:30]}")
    print(f"Dir chain: {dir_chain}")
    print(f"Mini-FAT sectors: {mf_sectors}")
    print(f"Root chain: {root_chain} ({len(root_chain)} sectors = {len(root_chain)*512} bytes)")
    print(f"Mini-stream: {len(ms)} bytes physical = {len(ms)//64} mini-sectors capacity")

    # ── Identify entries ───────────────────────────────────────────────────────
    root_idx  = 0
    vba_idx   = find_entry(entries, 'VBA')
    dir_idx   = find_entry(entries, 'dir')
    proj_idx  = find_entry(entries, 'PROJECT')
    dam_idx   = find_entry(entries, 'DieseArbeitsmappe')

    root_e  = parse_dir(entries[root_idx])
    dir_e   = parse_dir(entries[dir_idx])
    proj_e  = parse_dir(entries[proj_idx])

    print(f"\nRoot size: {root_e['size']}")
    print(f"dir: idx={dir_idx}, start={dir_e['start']}, size={dir_e['size']}, right={dir_e['right']:#x}")

    # ── Verify 'dir' right child is currently FREESECT ────────────────────────
    if dir_e['right'] != FREESECT:
        print(f"WARNING: dir entry already has right child {dir_e['right']}")

    # ── Step 1: Extend file by one sector (sector 28) ─────────────────────────
    # Sector 28 = new directory sector
    NEW_DIR_SEC = 28
    data += bytearray(SECTOR_SIZE)
    print(f"\nExtended file to {len(data)} bytes (added sector {NEW_DIR_SEC})")

    # Re-read FAT (file extended, bytearray resized)
    fat = read_fat(data)

    # ── Step 2: Update FAT ────────────────────────────────────────────────────
    # Chain directory: sector 17 → sector 28 → ENDOFCHAIN
    last_dir_sec = dir_chain[-1]
    fat[last_dir_sec] = NEW_DIR_SEC
    fat[NEW_DIR_SEC]  = ENDOFCHAIN
    write_fat(data, fat)
    print(f"FAT: sector {last_dir_sec} now chains to {NEW_DIR_SEC}")

    # ── Step 3: Module1 VBA source and compressed stream ─────────────────────
    mod1_src = (
        b'Attribute VB_Name = "Module1"\r\n'
        b'Public Sub AktualisiereFondsdaten()\r\n'
        b'    ThisWorkbook.RefreshAll\r\n'
        b'End Sub\r\n'
    )
    mod1_compressed = vba_compress(mod1_src)
    # Verify round-trip
    dec = vba_decompress(mod1_compressed)
    assert dec[:len(mod1_src)] == mod1_src, "Module1 compress round-trip failed!"
    print(f"\nModule1 source: {len(mod1_src)} bytes")
    print(f"Module1 compressed: {len(mod1_compressed)} bytes")
    mod1_mini_needed = math.ceil(len(mod1_compressed) / MINI_SECTOR_SIZE)
    print(f"Module1 mini-sectors needed: {mod1_mini_needed}")

    # ── Step 4: Allocate mini-sectors for Module1 ─────────────────────────────
    # Current last used mini-sector: the root chain has 22 sectors = 176 capacity
    # Used: 0-172 + 173 = 174 mini-sectors. Physical capacity = 176.
    # Free: 174, 175. We can use those without extending the root chain.

    # Find what mini-sectors are free
    free_mini = [i for i in range(len(mf)) if mf[i] == FREESECT]
    print(f"Free mini-sectors (first few): {free_mini[:10]}")

    # Physical capacity
    phys_mini_cap = len(ms) // MINI_SECTOR_SIZE
    print(f"Physical mini-sector capacity: {phys_mini_cap}")

    # Extend physical capacity if needed
    total_needed_mini = max(free_mini[:1][0] if free_mini else 0, phys_mini_cap) + mod1_mini_needed
    # Just use sequential mini-sectors after last allocated
    all_used = set()
    for i, v in enumerate(mf):
        if v != FREESECT:
            all_used.add(i)
    last_alloc_mini = max(all_used)
    mod1_mini_start = last_alloc_mini + 1
    mod1_mini_chain = list(range(mod1_mini_start, mod1_mini_start + mod1_mini_needed))
    print(f"Allocating Module1 mini-sectors: {mod1_mini_chain}")

    # Ensure mini-stream physical space is large enough
    needed_ms_bytes = (mod1_mini_chain[-1] + 1) * MINI_SECTOR_SIZE
    if len(ms) < needed_ms_bytes:
        ms += bytearray(needed_ms_bytes - len(ms))
        print(f"Extended mini-stream to {len(ms)} bytes")

    # Ensure root chain has enough sectors
    needed_root_sectors = math.ceil(len(ms) / SECTOR_SIZE)
    while len(root_chain) < needed_root_sectors:
        # Find next free regular sector
        next_free = max(len(fat), 28) + 1
        for s in range(29, 256):
            if s < len(fat) and fat[s] == FREESECT:
                next_free = s
                break
        fat[root_chain[-1]] = next_free
        fat[next_free] = ENDOFCHAIN
        root_chain.append(next_free)
        data += bytearray(SECTOR_SIZE)
        write_fat(data, fat)
        print(f"Extended root chain with sector {next_free}")

    # Update mini-FAT for Module1 chain
    while len(mf) <= mod1_mini_chain[-1]:
        mf.extend([FREESECT] * 128)

    for i in range(len(mod1_mini_chain) - 1):
        mf[mod1_mini_chain[i]] = mod1_mini_chain[i+1]
    mf[mod1_mini_chain[-1]] = ENDOFCHAIN

    # Write Module1 data into mini-stream
    padded = mod1_compressed.ljust(mod1_mini_needed * MINI_SECTOR_SIZE, b'\x00')
    for i, s in enumerate(mod1_mini_chain):
        ms[s*64 : (s+1)*64] = padded[i*64 : (i+1)*64]

    # Update Root Entry size
    new_root_size = (mod1_mini_chain[-1] + 1) * MINI_SECTOR_SIZE
    if new_root_size > root_e['size']:
        struct.pack_into('<I', entries[root_idx], 120, new_root_size)
        print(f"Root Entry size: {root_e['size']} → {new_root_size}")

    # Write updated mini-stream back
    write_ministream(data, fat, ms)

    # Write updated mini-FAT
    write_minifat(data, fat, mf)

    # ── Step 5: Add Module1 directory entry ───────────────────────────────────
    MOD1_IDX = len(entries)  # Will be 12

    # Module1 dir entry: standard stream, start=mod1_mini_chain[0], size=compressed_len
    # Color=RED (new node), left/right/child=FREESECT
    mod1_dir = make_dir_entry(
        name='Module1',
        entry_type=2,        # STGTY_STREAM
        color=0,             # RED
        left=FREESECT,
        right=FREESECT,
        child=FREESECT,
        clsid=bytes(16),
        start=mod1_mini_chain[0],
        size=len(mod1_compressed),
    )
    # Pad sector 28 with 4 empty entries
    entries.append(mod1_dir)
    for _ in range(3):
        entries.append(bytearray(128))

    # Update RB-tree: set dir entry[dir_idx].right = MOD1_IDX
    # (Module1 sorts after 'dir' and before 'Tabelle1')
    struct.pack_into('<I', entries[dir_idx], 72, MOD1_IDX)
    print(f"\nModule1 dir entry at [{MOD1_IDX}], mini-start={mod1_mini_chain[0]}")
    print(f"dir entry[{dir_idx}].right = {MOD1_IDX}")

    # Write all dir entries
    write_all_dir(data, fat, entries)

    # ── Step 6: Patch dir stream (PROJECTMODULECOUNT + Module1 MODULE record) ─
    dir_raw_compressed = read_mini_stream_bytes_mf(ms, mf, dir_e['start'], dir_e['size'])
    dir_decompressed   = vba_decompress(dir_raw_compressed)

    # Find PROJECTMODULECOUNT record (ID=0x000F, len=2)
    mc_off = dir_decompressed.find(b'\x0f\x00\x02\x00\x00\x00')
    if mc_off < 0:
        raise RuntimeError("PROJECTMODULECOUNT not found in dir stream!")
    old_count = struct.unpack_from('<H', dir_decompressed, mc_off+6)[0]
    new_count = old_count + 1
    dir_mod = bytearray(dir_decompressed)
    struct.pack_into('<H', dir_mod, mc_off+6, new_count)
    print(f"\nPROJECTMODULECOUNT: {old_count} → {new_count}")

    # Find the reserved end marker (0x0010, len=0) at the very end
    # Insert Module1 MODULE record right before it
    end_marker = b'\x10\x00\x00\x00\x00\x00'
    end_off = dir_mod.find(end_marker)
    if end_off < 0:
        raise RuntimeError("End marker 0x0010 not found in dir stream!")
    print(f"Inserting Module1 MODULE record at dir offset {end_off:#x}")

    mod1_module_rec = build_module1_dir_record()
    print(f"Module1 MODULE record: {len(mod1_module_rec)} bytes")
    dir_mod = dir_mod[:end_off] + mod1_module_rec + dir_mod[end_off:]
    print(f"Dir decompressed: {len(dir_decompressed)} → {len(dir_mod)} bytes")

    # Recompress dir stream
    new_dir_compressed = vba_compress(bytes(dir_mod))
    print(f"Dir compressed: {dir_e['size']} → {len(new_dir_compressed)} bytes")

    # Check if it fits in current mini-sectors (10 mini-sectors = 640 bytes)
    dir_chain_mini = follow_mini_chain(mf, dir_e['start'])
    dir_capacity = len(dir_chain_mini) * MINI_SECTOR_SIZE
    print(f"Dir current capacity: {dir_capacity} bytes ({len(dir_chain_mini)} mini-sectors)")

    if len(new_dir_compressed) > dir_capacity:
        # Need more mini-sectors for dir
        extra = math.ceil((len(new_dir_compressed) - dir_capacity) / MINI_SECTOR_SIZE)
        # Find next free mini-sectors after Module1
        next_free_mini = mod1_mini_chain[-1] + 1
        new_dir_minis = list(range(next_free_mini, next_free_mini + extra))
        print(f"Extending dir mini-chain with {new_dir_minis}")

        # Extend mini-stream if needed
        needed_ms = (new_dir_minis[-1] + 1) * MINI_SECTOR_SIZE
        if len(ms) < needed_ms:
            ms += bytearray(needed_ms - len(ms))

        # Update mini-FAT
        while len(mf) <= new_dir_minis[-1]:
            mf.extend([FREESECT] * 128)
        mf[dir_chain_mini[-1]] = new_dir_minis[0]
        for i in range(len(new_dir_minis) - 1):
            mf[new_dir_minis[i]] = new_dir_minis[i+1]
        mf[new_dir_minis[-1]] = ENDOFCHAIN
        dir_chain_mini += new_dir_minis
        dir_capacity = len(dir_chain_mini) * MINI_SECTOR_SIZE

        # Update root chain if needed
        needed_root_sectors = math.ceil(len(ms) / SECTOR_SIZE)
        while len(root_chain) < needed_root_sectors:
            for s in range(29, 256):
                if fat[s] == FREESECT:
                    fat[root_chain[-1]] = s
                    fat[s] = ENDOFCHAIN
                    root_chain.append(s)
                    data += bytearray(SECTOR_SIZE)
                    write_fat(data, fat)
                    break

        # Update Root size
        new_root_size2 = (new_dir_minis[-1] + 1) * MINI_SECTOR_SIZE
        if new_root_size2 > struct.unpack_from('<I', entries[root_idx], 120)[0]:
            struct.pack_into('<I', entries[root_idx], 120, new_root_size2)

        write_ministream(data, fat, ms)
        write_minifat(data, fat, mf)

    # Write new dir stream into mini-sectors
    padded_dir = new_dir_compressed.ljust(dir_capacity, b'\x00')
    for i, s in enumerate(dir_chain_mini):
        ms[s*64 : (s+1)*64] = padded_dir[i*64 : (i+1)*64]

    # Update dir entry size
    struct.pack_into('<I', entries[dir_idx], 120, len(new_dir_compressed))

    # ── Step 7: Patch PROJECT stream ──────────────────────────────────────────
    proj_chain_mini = follow_mini_chain(mf, proj_e['start'])
    proj_data = read_mini_stream_bytes_mf(ms, mf, proj_e['start'], proj_e['size'])
    proj_text = proj_data.decode('latin-1')
    print(f"\nPROJECT stream ({len(proj_data)} bytes):\n{proj_text[:400]}")

    # Add Module1 after the last Document= line (before HelpContextID)
    # Insert: Module=Module1/&H00000000
    insert_after = 'Document=Tabelle5/&H00000000\r\n'
    if insert_after not in proj_text:
        insert_after = 'Document=Tabelle5/&H00000000\n'
    if insert_after in proj_text:
        proj_text = proj_text.replace(
            insert_after,
            insert_after + 'Module=Module1/&H00000000\r\n'
        )
    else:
        # Fallback: insert before Name=
        proj_text = proj_text.replace('Name=', 'Module=Module1/&H00000000\r\nName=', 1)

    # Add to [Workspace] section
    if 'Module1=' not in proj_text:
        ws_marker = 'Tabelle5=0, 0, 0, 0, C'
        if ws_marker in proj_text:
            proj_text = proj_text.replace(
                ws_marker,
                ws_marker + '\r\nModule1=0, 0, 0, 0, '
            )
        else:
            proj_text += '\r\nModule1=0, 0, 0, 0, \r\n'

    new_proj = proj_text.encode('latin-1')
    print(f"PROJECT: {proj_e['size']} → {len(new_proj)} bytes")

    proj_capacity = len(proj_chain_mini) * MINI_SECTOR_SIZE
    if len(new_proj) > proj_capacity:
        # Extend PROJECT mini-chain
        extra = math.ceil((len(new_proj) - proj_capacity) / MINI_SECTOR_SIZE)
        last_used_mini2 = max(i for i, v in enumerate(mf) if v != FREESECT and i < len(mf))
        new_proj_minis = list(range(last_used_mini2 + 1, last_used_mini2 + 1 + extra))
        print(f"Extending PROJECT mini-chain with {new_proj_minis}")
        while len(mf) <= new_proj_minis[-1]:
            mf.extend([FREESECT] * 128)
        mf[proj_chain_mini[-1]] = new_proj_minis[0]
        for i in range(len(new_proj_minis) - 1):
            mf[new_proj_minis[i]] = new_proj_minis[i+1]
        mf[new_proj_minis[-1]] = ENDOFCHAIN
        proj_chain_mini += new_proj_minis
        proj_capacity = len(proj_chain_mini) * MINI_SECTOR_SIZE

        # Extend root if needed
        needed_ms_bytes2 = (new_proj_minis[-1] + 1) * MINI_SECTOR_SIZE
        if len(ms) < needed_ms_bytes2:
            ms += bytearray(needed_ms_bytes2 - len(ms))
        needed_sectors2 = math.ceil(len(ms) / SECTOR_SIZE)
        while len(root_chain) < needed_sectors2:
            for s in range(29, 512):
                if s < len(fat) and fat[s] == FREESECT or s >= len(fat):
                    if s >= len(fat):
                        data += bytearray(SECTOR_SIZE)
                        fat = read_fat(data)
                    fat[root_chain[-1]] = s
                    fat[s] = ENDOFCHAIN
                    root_chain.append(s)
                    write_fat(data, fat)
                    break

        new_root_sz3 = (new_proj_minis[-1] + 1) * MINI_SECTOR_SIZE
        if new_root_sz3 > struct.unpack_from('<I', entries[root_idx], 120)[0]:
            struct.pack_into('<I', entries[root_idx], 120, new_root_sz3)

    padded_proj = new_proj.ljust(proj_capacity, b'\x00')
    for i, s in enumerate(proj_chain_mini):
        ms[s*64 : (s+1)*64] = padded_proj[i*64 : (i+1)*64]
    struct.pack_into('<I', entries[proj_idx], 120, len(new_proj))

    # ── Step 8: Write everything back ─────────────────────────────────────────
    write_ministream(data, fat, ms)
    write_minifat(data, fat, mf)
    write_fat(data, fat)
    write_all_dir(data, fat, entries)

    # Final verification
    print(f"\nFinal file size: {len(data)} bytes")
    print(f"FAT[17]={fat[17]}, FAT[28]={fat[28]}")

    with open(VBA_PATH, 'wb') as f:
        f.write(data)
    print("vbaProject.bin written.")


def verify_patch():
    """Quick sanity check using olefile."""
    import olefile
    f = olefile.OleFileIO(VBA_PATH)
    print("\n=== Verification ===")
    for e in f.listdir():
        print(' ', e)
    proj = f.openstream('PROJECT').read().decode('latin-1')
    print(f"\nPROJECT (first 500):\n{proj[:500]}")
    f.close()


def repack_xlsm():
    """Repack the xlsm from WORK_DIR."""
    xlsm_src = "/root/.claude/uploads/b0a230a7-31e1-539f-ba58-ad030fd9c1d6/a8ae01c5-Gesamt_Anlagenstrategie_Fondsaktualisierung_FINAL.xlsm"
    if os.path.exists(OUT_XLSM):
        os.remove(OUT_XLSM)
    with zipfile.ZipFile(OUT_XLSM, 'w', compression=zipfile.ZIP_DEFLATED) as z_out:
        for dirpath, dirnames, filenames in os.walk(WORK_DIR):
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                arcname   = os.path.relpath(full_path, WORK_DIR).replace(os.sep, '/')
                with open(full_path, 'rb') as f:
                    content = f.read()
                comp = zipfile.ZIP_STORED if arcname == 'xl/vbaProject.bin' else zipfile.ZIP_DEFLATED
                z_out.writestr(zipfile.ZipInfo(arcname), content, compress_type=comp)
    print(f"\nRepacked: {OUT_XLSM}")
    print(f"Size: {os.path.getsize(OUT_XLSM)} bytes")
    with zipfile.ZipFile(OUT_XLSM, 'r') as z:
        print(f"ZIP entries: {len(z.namelist())}")


if __name__ == '__main__':
    patch()
    verify_patch()
    repack_xlsm()
    print("\nDone!")
