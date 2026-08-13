#!/usr/bin/env python3
"""
Patch the Excel .xlsm file to add a button that triggers RefreshAll.
Strategy:
  1. Extract xlsm (it's a ZIP)
  2. Patch vbaProject.bin: extend DieseArbeitsmappe stream with new macro sub
  3. Add VML button drawings for sheet4 and sheet5
  4. Update relationship files and worksheet XML
  5. Repack as xlsm
"""

import zipfile
import struct
import shutil
import os
import math
import re

XLSM_SRC = "/root/.claude/uploads/b0a230a7-31e1-539f-ba58-ad030fd9c1d6/a8ae01c5-Gesamt_Anlagenstrategie_Fondsaktualisierung_FINAL.xlsm"
WORK_DIR  = "/tmp/claude-0/-home-user-Susi/b0a230a7-31e1-539f-ba58-ad030fd9c1d6/scratchpad/xlsm_work"
OUT_XLSM  = "/tmp/claude-0/-home-user-Susi/b0a230a7-31e1-539f-ba58-ad030fd9c1d6/scratchpad/Gesamt_Anlagenstrategie_MIT_BUTTON.xlsm"

# ────────────────────────────────────────────────────────────────────────────────
# MS-OVBA LZ77 Compression (MS-OVBA section 2.4)
# ────────────────────────────────────────────────────────────────────────────────

def vba_compress(data: bytes) -> bytes:
    """Compress bytes using MS-OVBA LZ77 variant (MS-OVBA 2.4).
    CompressedChunkFlag: bit15=1 → compressed, bit15=0 → raw.
    CompressedChunkSignature: bits14-12 = 0b011 = 3.
    CompressedChunkSize: bits11-0 = (compressed_data_bytes - 3) when compressed.
    """
    out = bytearray()
    out.append(0x01)          # SignatureByte

    i = 0
    n = len(data)

    while i < n:
        # Each 4096-byte window forms one CompressedChunk
        chunk_start = i
        chunk_data = data[chunk_start : chunk_start + 4096]
        chunk_len  = len(chunk_data)

        compressed = _compress_chunk(chunk_data, chunk_start)

        if len(compressed) < chunk_len:
            # Emit as compressed chunk
            # bit15=1 (compressed), bits14-12=011 (signature=3), bits11-0=size-3
            size_field = len(compressed) - 3
            header = (1 << 15) | (0b011 << 12) | (size_field & 0x0FFF)
            out += struct.pack('<H', header)
            out += compressed
        else:
            # Raw chunk: bit15=0 (raw), bits14-12=011, bits11-0=0x7FF
            header = (0 << 15) | (0b011 << 12) | 0x7FF
            out += struct.pack('<H', header)
            # Raw chunk is always 4096 bytes padded with zeros
            raw = chunk_data.ljust(4096, b'\x00')
            out += raw

        i += chunk_len

    return bytes(out)


def _copytoken_help(decompressed_current, chunk_start):
    """Return (length_mask, offset_mask, copy_bit_count, max_length).
    copy_bit_count = number of bits for offset field (MS-OVBA naming: CopyBitCount).
    length_shift   = 16 - copy_bit_count = bits used for length field.
    """
    difference = decompressed_current - chunk_start
    if difference <= 16:
        length_shift = 12
    elif difference <= 32:
        length_shift = 11
    elif difference <= 64:
        length_shift = 10
    elif difference <= 128:
        length_shift = 9
    elif difference <= 256:
        length_shift = 8
    elif difference <= 512:
        length_shift = 7
    elif difference <= 1024:
        length_shift = 6
    elif difference <= 2048:
        length_shift = 5
    else:
        length_shift = 4
    copy_bit_count = 16 - length_shift          # CopyBitCount: bits for offset
    length_mask    = (1 << length_shift) - 1
    offset_mask    = 0xFFFF ^ length_mask
    max_length     = length_mask + 3
    return (length_mask, offset_mask, copy_bit_count, max_length)


def _compress_chunk(chunk: bytes, chunk_start: int) -> bytes:
    """Compress one chunk (up to 4096 bytes)."""
    out = bytearray()
    i = 0
    n = len(chunk)

    while i < n:
        # Build one FlagByte group (up to 8 tokens)
        flag_byte_pos = len(out)
        out.append(0)           # placeholder for FlagByte
        flag_byte = 0

        for bit in range(8):
            if i >= n:
                break

            # Try to find the best back-reference in the window
            window_start = max(0, i - 4096)   # within current chunk for offsets
            # Actually window is from chunk_start in the full decompressed data,
            # but here chunk is a slice so window is from 0 to i
            best_len = 0
            best_off = 0

            if i > 0:
                length_mask, offset_mask, bit_count, max_len = _copytoken_help(
                    chunk_start + i, chunk_start)
                # bit_count = CopyBitCount; length_shift = 16 - bit_count
                # max representable offset: offset_mask >> length_shift = (offset_mask >> (16-bit_count))
                max_offset = (offset_mask >> (16 - bit_count)) + 1
                search_start = max(0, i - max_offset)

                for j in range(search_start, i):
                    # Find run length starting at j
                    run = 0
                    while (run < max_len and
                           i + run < n and
                           chunk[j + run % (i - j)] == chunk[i + run]):
                        run += 1
                    if run > best_len:
                        best_len = run
                        best_off = i - j

            if best_len >= 3:
                # Emit copy token
                length_mask, offset_mask, bit_count, max_len = _copytoken_help(
                    chunk_start + i, chunk_start)
                # off_field: (best_off-1) placed in the high CopyBitCount bits
                # shift by length_shift = 16 - bit_count
                len_field = (best_len - 3) & length_mask
                off_field = ((best_off - 1) << (16 - bit_count)) & offset_mask
                copy_token = off_field | len_field
                out += struct.pack('<H', copy_token)
                flag_byte |= (1 << bit)
                i += best_len
            else:
                # Emit literal
                out.append(chunk[i])
                i += 1

        out[flag_byte_pos] = flag_byte

    return bytes(out)


def vba_decompress(data: bytes) -> bytes:
    """Decompress MS-OVBA LZ77 (for verification)."""
    if data[0] != 0x01:
        raise ValueError("Not a compressed stream")
    decompressed = bytearray()
    i = 1
    while i < len(data):
        if i + 1 >= len(data):
            break
        header = struct.unpack_from('<H', data, i)[0]
        i += 2
        is_compressed = bool(header >> 15)   # bit15=1 → compressed, bit15=0 → raw
        chunk_size = (header & 0x0FFF) + 3 if is_compressed else 4098
        chunk_end  = i + (chunk_size if is_compressed else 4096)
        chunk_start_d = len(decompressed)

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
                    # copy token
                    copy_token = struct.unpack_from('<H', data, i)[0]; i += 2
                    lm, om, bc, _ = _copytoken_help(len(decompressed), chunk_start_d)
                    length = (copy_token & lm) + 3
                    offset = ((copy_token & om) >> (16 - bc)) + 1
                    copy_index = len(decompressed) - offset
                    for k in range(length):
                        decompressed.append(decompressed[copy_index + k])
                else:
                    decompressed.append(data[i]); i += 1
    return bytes(decompressed)


# ────────────────────────────────────────────────────────────────────────────────
# OLE2 / vbaProject.bin helpers
# ────────────────────────────────────────────────────────────────────────────────

SECTOR_SIZE      = 512
MINI_SECTOR_SIZE = 64
FREESECT   = 0xFFFFFFFF
ENDOFCHAIN = 0xFFFFFFFE
FATSECT    = 0xFFFFFFFD
DIFSECT    = 0xFFFFFFFC

def sector_offset(sec_num):
    """Physical byte offset of a regular sector."""
    return (sec_num + 1) * SECTOR_SIZE

def read_sector(data, sec_num):
    off = sector_offset(sec_num)
    return data[off : off + SECTOR_SIZE]

def read_fat(data):
    """Read FAT from sector 0 (28 entries for our file)."""
    off = sector_offset(0)
    fat = list(struct.unpack_from('<128I', data, off))
    return fat

def read_minifat(data, fat, minifat_start_sectors):
    """Read mini-FAT from sectors 2 and 20 (173 entries)."""
    entries = []
    for sec in minifat_start_sectors:
        raw = read_sector(data, sec)
        entries += list(struct.unpack_from('<128I', raw))
    return entries

def read_root_ministream(data, fat, root_start):
    """Follow root FAT chain and return the mini-stream bytes."""
    chain = []
    sec = root_start
    while sec not in (ENDOFCHAIN, FREESECT, FATSECT, DIFSECT):
        chain.append(sec)
        sec = fat[sec]
    raw = b''
    for s in chain:
        raw += read_sector(data, s)
    return bytearray(raw), chain

def get_mini_sector_data(ministream, mini_sec_num):
    off = mini_sec_num * MINI_SECTOR_SIZE
    return ministream[off : off + MINI_SECTOR_SIZE]

def set_mini_sector_data(ministream, mini_sec_num, payload):
    off = mini_sec_num * MINI_SECTOR_SIZE
    ministream[off : off + MINI_SECTOR_SIZE] = payload.ljust(MINI_SECTOR_SIZE, b'\x00')[:MINI_SECTOR_SIZE]

def follow_mini_chain(minifat, start):
    chain = []
    sec = start
    while sec not in (ENDOFCHAIN, FREESECT, FATSECT, DIFSECT):
        chain.append(sec)
        if sec >= len(minifat):
            break
        sec = minifat[sec]
    return chain

def read_mini_stream_bytes(ministream, minifat, start, size):
    chain = follow_mini_chain(minifat, start)
    raw = b''
    for s in chain:
        raw += bytes(get_mini_sector_data(ministream, s))
    return raw[:size]

# Directory entry structure: 128 bytes each
# offsets: 0=name(64B), 64=nameLen(2B), 66=type(1B), 67=color(1B),
#          68=leftSib(4B), 72=rightSib(4B), 76=child(4B),
#          80=CLSID(16B), 96=stateBits(4B), 100=created(8B), 108=modified(8B),
#          116=isectStart(4B), 120=size(4B), 124=unused(4B)

def read_dir_entries(data, fat, dir_start):
    """Read all directory entries."""
    chain = []
    sec = dir_start
    while sec not in (ENDOFCHAIN, FREESECT):
        chain.append(sec)
        sec = fat[sec]
    entries = []
    for s in chain:
        raw = read_sector(data, s)
        for i in range(4):
            entry_raw = raw[i*128 : (i+1)*128]
            entries.append(entry_raw)
    return entries, chain

def parse_dir_entry(raw):
    name_bytes = raw[0:64]
    name_len   = struct.unpack_from('<H', raw, 64)[0]
    entry_type = raw[66]
    color      = raw[67]
    left_sib   = struct.unpack_from('<I', raw, 68)[0]
    right_sib  = struct.unpack_from('<I', raw, 72)[0]
    child      = struct.unpack_from('<I', raw, 76)[0]
    start_sec  = struct.unpack_from('<I', raw, 116)[0]
    size       = struct.unpack_from('<I', raw, 120)[0]
    name = name_bytes[:name_len-2].decode('utf-16-le') if name_len >= 2 else ''
    return {
        'name': name, 'name_len': name_len, 'type': entry_type, 'color': color,
        'left': left_sib, 'right': right_sib, 'child': child,
        'start': start_sec, 'size': size, 'raw': bytearray(raw)
    }

def find_entry(entries, name):
    for i, e in enumerate(entries):
        if parse_dir_entry(e)['name'] == name:
            return i, parse_dir_entry(e)
    return None, None


# ────────────────────────────────────────────────────────────────────────────────
# Main patch routine
# ────────────────────────────────────────────────────────────────────────────────

def patch_vba_project(vba_bin: bytes) -> bytes:
    data = bytearray(vba_bin)

    # 1. Read FAT (sector 0)
    fat = read_fat(data)
    print(f"FAT: {fat[:28]}")

    # 2. Read directory entries (sectors 1→8→17)
    dir_start = struct.unpack_from('<I', data, 0x30)[0]   # DIRSECT offset in header
    print(f"Dir start sector: {dir_start}")
    dir_entries_raw, dir_chain = read_dir_entries(data, fat, dir_start)
    print(f"Directory chain: {dir_chain}, {len(dir_entries_raw)} entries")

    # Print all entries
    for i, raw in enumerate(dir_entries_raw):
        e = parse_dir_entry(raw)
        if e['type'] != 0:
            print(f"  [{i}] '{e['name']}' type={e['type']} start={e['start']} size={e['size']}")

    # 3. Find DieseArbeitsmappe entry
    dam_idx, dam_entry = find_entry(dir_entries_raw, 'DieseArbeitsmappe')
    if dam_idx is None:
        raise RuntimeError("DieseArbeitsmappe not found!")
    print(f"\nDieseArbeitsmappe: idx={dam_idx}, start={dam_entry['start']}, size={dam_entry['size']}")

    # 4. Read mini-FAT (sectors 2 and 20, total 256 entries)
    # First find mini-FAT start from header
    minifat_start = struct.unpack_from('<I', data, 0x3C)[0]   # first mini-FAT sector
    print(f"Mini-FAT start sector: {minifat_start}")
    minifat_sectors = []
    sec = minifat_start
    while sec not in (ENDOFCHAIN, FREESECT, FATSECT, DIFSECT):
        minifat_sectors.append(sec)
        sec = fat[sec]
    print(f"Mini-FAT sectors: {minifat_sectors}")
    minifat = read_minifat(data, fat, minifat_sectors)
    print(f"Mini-FAT (first 200): {minifat[:200]}")

    # 5. Find Root Entry to get mini-stream
    root_raw = dir_entries_raw[0]
    root = parse_dir_entry(root_raw)
    print(f"\nRoot Entry: start={root['start']}, size={root['size']}")
    ministream, root_chain = read_root_ministream(data, fat, root['start'])
    print(f"Root chain: {root_chain}")
    print(f"Mini-stream length: {len(ministream)} bytes, {len(ministream)//64} mini-sectors")

    # 6. Read current DieseArbeitsmappe compressed bytes
    dam_chain = follow_mini_chain(minifat, dam_entry['start'])
    print(f"\nDieseArbeitsmappe mini-chain: {dam_chain}")
    dam_raw = read_mini_stream_bytes(ministream, minifat, dam_entry['start'], dam_entry['size'])
    print(f"DieseArbeitsmappe raw ({len(dam_raw)} bytes): {dam_raw[:40].hex()}")

    # 7. Find TextOffset: bytes 0..TextOffset-1 are the pCode binary, rest is compressed source
    # TextOffset is at offset 0x31 in the module stream (little-endian DWORD after 0x002B record)
    # We need to parse the ModuleOffset from the dir stream
    # Actually easier: scan for the 0x01 signature byte (start of compressed stream)
    # The module stream starts with pCode, then at TextOffset comes the 0x01 compressed stream
    # From summary: TextOffset=945 for DieseArbeitsmappe
    text_offset = None
    for off in range(len(dam_raw)):
        if dam_raw[off] == 0x01:
            # verify it decompresses
            try:
                dec = vba_decompress(dam_raw[off:])
                if b'Attribute VB_Name' in dec:
                    text_offset = off
                    break
            except:
                pass

    if text_offset is None:
        raise RuntimeError("Could not find TextOffset in DieseArbeitsmappe stream")
    print(f"TextOffset found at: {text_offset}")

    # 8. Decompress and modify the source
    compressed_src = dam_raw[text_offset:]
    original_src   = vba_decompress(compressed_src)
    print(f"Decompressed source ({len(original_src)} bytes):\n{original_src.decode('latin-1')}")

    new_sub = (
        "\r\n"
        "Public Sub AktualisiereFondsdaten()\r\n"
        "    ThisWorkbook.RefreshAll\r\n"
        "    MsgBox \"Fondsdaten wurden aktualisiert!\", 64, \"Fertig\"\r\n"
        "End Sub\r\n"
    )
    new_src = original_src.rstrip(b'\x00') + new_sub.encode('latin-1')
    print(f"New source ({len(new_src)} bytes):\n{new_src.decode('latin-1')}")

    # 9. Compress new source
    new_compressed = vba_compress(new_src)
    print(f"New compressed: {len(new_compressed)} bytes (was {len(compressed_src)})")

    # Verify round-trip (allow trailing nulls from raw-chunk padding)
    verify = vba_decompress(new_compressed)
    assert verify[:len(new_src)] == new_src, \
        f"Compression round-trip failed!\nExpected prefix: {new_src!r}\nGot: {verify[:len(new_src)+20]!r}"
    print("Compression round-trip: OK")

    # 10. Build new DieseArbeitsmappe stream
    pcode = bytes(dam_raw[:text_offset])
    new_dam_stream = pcode + bytes(new_compressed)
    print(f"New stream size: {len(new_dam_stream)} bytes (was {len(dam_raw)})")

    # How many mini-sectors do we need?
    needed = math.ceil(len(new_dam_stream) / MINI_SECTOR_SIZE)
    current_needed = len(dam_chain)
    print(f"Mini-sectors needed: {needed}, currently allocated: {current_needed}")

    if needed > current_needed:
        extra = needed - current_needed
        # Find free mini-sectors: look for FREESECT in minifat
        # We know 173, 174, 175 are physically available but not in minifat
        # First check if minifat marks them as free
        free_mini_secs = []
        for idx in range(len(minifat)):
            if minifat[idx] == FREESECT:
                free_mini_secs.append(idx)
        print(f"Free mini-sectors (FREESECT marked): {free_mini_secs[:10]}")

        # If no free ones, use the physically available ones (173, 174, 175)
        # which exist in Root Entry sector 27 but aren't tracked yet
        if not free_mini_secs or min(free_mini_secs) > 200:
            # Extend: use 173, 174, 175
            # Check if Root Entry can accommodate them
            root_size = root['size']
            root_capacity = len(ministream)  # physical capacity
            print(f"Root size: {root_size}, Root capacity: {root_capacity}")

            # We need to extend mini-FAT and Root Entry size
            next_mini = len(minifat)  # start after currently tracked entries
            # Actually use 173, 174, 175 which we know are in sector 27
            phys_available = len(ministream) // MINI_SECTOR_SIZE
            print(f"Physically available mini-sectors: {phys_available}")
            needed_extra_mini = needed - current_needed
            if phys_available < needed:
                # Need to add more physical space to Root Entry (add a new sector)
                # For now, let's try to avoid this by keeping the stream smaller
                pass
            for i in range(needed_extra_mini):
                new_mini_sec = current_needed + len(dam_chain) + i
                # Actually: just use sequential from after last used
                pass
            # Find the last used mini-sector
            last_used = max(idx for idx, v in enumerate(minifat) if v != FREESECT and v < 0xFFFFFF00)
            if last_used == -1:
                last_used = current_needed - 1
            # Allocate from after last tracked mini-sector
            # First figure out: what's the last allocated mini-sector overall?
            all_used = set()
            for i, v in enumerate(minifat):
                if v != FREESECT:
                    all_used.add(i)
            last_alloc = max(all_used) if all_used else 0
            print(f"Last allocated mini-sector: {last_alloc}")
            new_allocs = list(range(last_alloc + 1, last_alloc + 1 + extra))
            print(f"Will allocate new mini-sectors: {new_allocs}")
        else:
            new_allocs = free_mini_secs[:extra]

        # Extend dam_chain with new_allocs
        # Update minifat: chain last of dam_chain to new_allocs[0], etc.
        extended_chain = dam_chain + new_allocs
        # Update mini-FAT in minifat list
        for i in range(len(extended_chain) - 1):
            minifat[extended_chain[i]] = extended_chain[i + 1]
        minifat[extended_chain[-1]] = ENDOFCHAIN
        print(f"Extended dam_chain: {extended_chain}")

        # Ensure ministream is big enough
        total_mini_needed = (max(extended_chain) + 1) * MINI_SECTOR_SIZE
        if len(ministream) < total_mini_needed:
            ministream += bytearray(total_mini_needed - len(ministream))

        # Update Root Entry size if needed
        new_root_size = (max(extended_chain) + 1) * MINI_SECTOR_SIZE
        if new_root_size > root['size']:
            root['size'] = new_root_size
    else:
        extended_chain = dam_chain[:needed]
        # Terminate at needed
        for i in range(needed - 1):
            minifat[extended_chain[i]] = extended_chain[i + 1]
        minifat[extended_chain[-1]] = ENDOFCHAIN
        # Free leftover
        for s in dam_chain[needed:]:
            minifat[s] = FREESECT

    # 11. Write new stream data into ministream
    padded = new_dam_stream.ljust(len(extended_chain) * MINI_SECTOR_SIZE, b'\x00')
    for i, mini_sec in enumerate(extended_chain):
        off = mini_sec * MINI_SECTOR_SIZE
        chunk = padded[i*MINI_SECTOR_SIZE : (i+1)*MINI_SECTOR_SIZE]
        ministream[off : off + MINI_SECTOR_SIZE] = chunk
    print(f"Written new stream into ministream mini-sectors {extended_chain}")

    # 12. Update DieseArbeitsmappe directory entry size
    # The entry is in dir_entries_raw[dam_idx]
    dam_raw_entry = bytearray(dir_entries_raw[dam_idx])
    struct.pack_into('<I', dam_raw_entry, 120, len(new_dam_stream))
    dir_entries_raw[dam_idx] = dam_raw_entry
    print(f"Updated DieseArbeitsmappe size to {len(new_dam_stream)}")

    # 13. Write ministream back into Root Entry chain sectors
    # The mini-stream spans root_chain sectors
    for i, sec in enumerate(root_chain):
        chunk = bytes(ministream[i*SECTOR_SIZE : (i+1)*SECTOR_SIZE]).ljust(SECTOR_SIZE, b'\x00')
        off = sector_offset(sec)
        data[off : off + SECTOR_SIZE] = chunk

    # 14. Update Root Entry size in directory
    root_raw_entry = bytearray(dir_entries_raw[0])
    struct.pack_into('<I', root_raw_entry, 120, root['size'])
    dir_entries_raw[0] = root_raw_entry
    print(f"Updated Root Entry size to {root['size']}")

    # 15. Write updated mini-FAT back to minifat sectors
    for sec_idx, sec in enumerate(minifat_sectors):
        entries_for_sec = minifat[sec_idx*128 : (sec_idx+1)*128]
        # Pad to 128 entries
        entries_for_sec = list(entries_for_sec) + [FREESECT] * (128 - len(entries_for_sec))
        raw = struct.pack('<128I', *entries_for_sec)
        off = sector_offset(sec)
        data[off : off + SECTOR_SIZE] = raw
    print(f"Updated mini-FAT sectors {minifat_sectors}")

    # 16. Write updated FAT back to sector 0
    # FAT should be unchanged unless we added new sectors
    fat_raw = struct.pack('<128I', *fat)
    data[sector_offset(0) : sector_offset(0) + SECTOR_SIZE] = fat_raw

    # 17. Write updated directory entries back to dir sectors
    for sec_idx, sec in enumerate(dir_chain):
        sec_start = sec_idx * 4
        for entry_idx in range(4):
            global_idx = sec_start + entry_idx
            if global_idx < len(dir_entries_raw):
                raw = bytes(dir_entries_raw[global_idx]).ljust(128, b'\x00')
            else:
                raw = b'\x00' * 128
            off = sector_offset(sec) + entry_idx * 128
            data[off : off + 128] = raw
    print(f"Updated directory sectors {dir_chain}")

    return bytes(data)


def make_vml_drawing(macro_name, button_label, shape_id_base=1025):
    """Generate a VML drawing XML with one form control button."""
    vml = f'''<xml xmlns:v="urn:schemas-microsoft-com:vml"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:x="urn:schemas-microsoft-com:office:excel">
 <o:shapelayout v:ext="edit">
  <o:idmap v:ext="edit" data="1"/>
 </o:shapelayout>
 <v:shapetype id="_x0000_t201" coordsize="21600,21600" o:spt="201"
  path="m,l,21600r21600,l21600,xe">
  <v:stroke joinstyle="miter"/>
  <v:path shadowok="f" o:extrusionok="f" gradientshapeok="t" o:connecttype="rect"/>
 </v:shapetype>
 <v:shape id="_x0000_s{shape_id_base}" type="#_x0000_t201" style="position:absolute;
  margin-left:120pt;margin-top:10pt;width:120pt;height:24pt;z-index:1"
  fillcolor="buttonFace [67]" o:insetmode="auto">
  <v:fill color2="buttonFace [67]"/>
  <v:shadow color="buttonShadow [45]" obscured="t"/>
  <v:path o:connecttype="rect"/>
  <v:textbox>
   <div style="text-align:center"><font style="font:8pt Tahoma">&#160;{button_label}&#160;</font></div>
  </v:textbox>
  <x:ClientData ObjectType="Button">
   <x:Anchor>4,15,1,10,7,54,3,16</x:Anchor>
   <x:PrintObject>False</x:PrintObject>
   <x:AutoFill>False</x:AutoFill>
   <x:FmlaMacro>{macro_name}</x:FmlaMacro>
  </x:ClientData>
 </v:shape>
</xml>'''
    return vml


def main():
    # ── Step 1: Extract xlsm ───────────────────────────────────────────────────
    if os.path.exists(WORK_DIR):
        shutil.rmtree(WORK_DIR)
    os.makedirs(WORK_DIR)
    with zipfile.ZipFile(XLSM_SRC, 'r') as z:
        z.extractall(WORK_DIR)
    print(f"Extracted to {WORK_DIR}")
    for root, dirs, files in os.walk(WORK_DIR):
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), WORK_DIR)
            print(f"  {rel}")

    # ── Step 2: Patch vbaProject.bin ──────────────────────────────────────────
    vba_path = os.path.join(WORK_DIR, 'xl', 'vbaProject.bin')
    with open(vba_path, 'rb') as f:
        vba_original = f.read()
    print(f"\nvbaProject.bin: {len(vba_original)} bytes")

    vba_patched = patch_vba_project(vba_original)

    with open(vba_path, 'wb') as f:
        f.write(vba_patched)
    print(f"\nPatched vbaProject.bin written ({len(vba_patched)} bytes)")

    # ── Step 3: Determine which sheets are sheet4 and sheet5 ──────────────────
    # Read workbook.xml to find sheet names and IDs
    wb_path = os.path.join(WORK_DIR, 'xl', 'workbook.xml')
    with open(wb_path, 'r', encoding='utf-8') as f:
        wb_xml = f.read()
    print(f"\nworkbook.xml snippet:\n{wb_xml[:3000]}")

    # Find Dividendenermittlung sheets
    import re as _re
    sheets = _re.findall(r'<sheet\s[^>]*name="([^"]*)"[^>]*r:id="([^"]*)"[^>]*/>', wb_xml)
    if not sheets:
        sheets = _re.findall(r'<sheet[^>]+name="([^"]+)"[^>]+r:id="([^"]+)"', wb_xml)
    print(f"Sheets: {sheets}")

    # Find workbook rels to map rId -> sheet file
    wb_rels_path = os.path.join(WORK_DIR, 'xl', '_rels', 'workbook.xml.rels')
    with open(wb_rels_path, 'r', encoding='utf-8') as f:
        wb_rels = f.read()
    print(f"workbook.xml.rels:\n{wb_rels}")

    # Map rId to target (worksheets/sheetN.xml)
    rels_map = dict(_re.findall(r'Id="([^"]+)"[^>]+Target="([^"]+)"', wb_rels))
    print(f"Rels map: {rels_map}")

    # Find Dividendenermittlung sheets
    target_sheets = []
    for name, rid in sheets:
        if 'Dividendenermittlung' in name:
            target = rels_map.get(rid, '')
            # target might be "worksheets/sheetN.xml" or "/xl/worksheets/sheetN.xml"
            if target.startswith('/'):
                target = target.lstrip('/')
            sheet_file = os.path.join(WORK_DIR, 'xl', target) if not os.path.isabs(target) else target
            if not os.path.exists(sheet_file):
                sheet_file = os.path.join(WORK_DIR, 'xl', target.replace('worksheets/', 'worksheets/'))
            target_sheets.append((name, rid, target, sheet_file))
            print(f"  Dividendenermittlung sheet: '{name}' -> {target} -> {sheet_file}")

    if not target_sheets:
        # Fallback: just use sheet4 and sheet5
        print("Fallback: using sheet4.xml and sheet5.xml")
        target_sheets = [
            ("Dividendenermittlung im Bestand", "rId4", "worksheets/sheet4.xml",
             os.path.join(WORK_DIR, 'xl', 'worksheets', 'sheet4.xml')),
            ("Dividendenermittlung Neuanlage", "rId5", "worksheets/sheet5.xml",
             os.path.join(WORK_DIR, 'xl', 'worksheets', 'sheet5.xml')),
        ]

    # ── Step 4: Add VML button to each Dividendenermittlung sheet ─────────────
    drawings_dir = os.path.join(WORK_DIR, 'xl', 'drawings')
    os.makedirs(drawings_dir, exist_ok=True)

    # Check existing drawings
    existing_drawings = os.listdir(drawings_dir)
    print(f"Existing drawings: {existing_drawings}")
    next_vml_idx = len([f for f in existing_drawings if f.startswith('vmlDrawing')]) + 1

    for sheet_name, sheet_rid, sheet_target, sheet_file in target_sheets:
        # Derive sheet number from target path
        sheet_basename = os.path.basename(sheet_target)  # e.g. "sheet4.xml"
        sheet_num_str  = ''.join(filter(str.isdigit, sheet_basename))
        sheet_num      = int(sheet_num_str) if sheet_num_str else 4

        vml_filename = f"vmlDrawing{sheet_num}.vml"
        vml_path     = os.path.join(drawings_dir, vml_filename)
        vml_target   = f"../drawings/{vml_filename}"

        # Write VML file
        macro_name = "AktualisiereFondsdaten"
        vml_content = make_vml_drawing(macro_name, "Aktualisieren", shape_id_base=1025 + sheet_num)
        with open(vml_path, 'w', encoding='utf-8') as f:
            f.write(vml_content)
        print(f"Wrote VML: {vml_path}")

        # Update or create the sheet rels file
        rels_dir  = os.path.join(WORK_DIR, 'xl', 'worksheets', '_rels')
        os.makedirs(rels_dir, exist_ok=True)
        rels_file = os.path.join(rels_dir, f"{sheet_basename}.rels")
        vml_type  = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/vmlDrawing"
        vml_rel_id = f"rId_vml{sheet_num}"

        if os.path.exists(rels_file):
            with open(rels_file, 'r', encoding='utf-8') as f:
                rels_content = f.read()
            # Add vml relationship if not already present
            if vml_filename not in rels_content:
                # Insert before </Relationships>
                new_rel = f'  <Relationship Id="{vml_rel_id}" Type="{vml_type}" Target="{vml_target}"/>\n'
                rels_content = rels_content.replace('</Relationships>', new_rel + '</Relationships>')
                with open(rels_file, 'w', encoding='utf-8') as f:
                    f.write(rels_content)
                print(f"Updated rels: {rels_file}")
        else:
            rels_content = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="{vml_rel_id}" Type="{vml_type}" Target="{vml_target}"/>
</Relationships>'''
            with open(rels_file, 'w', encoding='utf-8') as f:
                f.write(rels_content)
            print(f"Created rels: {rels_file}")

        # Update sheet XML to add <legacyDrawing>
        if not os.path.exists(sheet_file):
            print(f"WARNING: sheet file not found: {sheet_file}")
            continue
        with open(sheet_file, 'r', encoding='utf-8') as f:
            sheet_xml = f.read()

        # Add legacyDrawing element before </worksheet> if not present
        legacy_tag = f'<legacyDrawing r:id="{vml_rel_id}"/>'
        if 'legacyDrawing' not in sheet_xml:
            # Add xmlns:r if not present
            if 'xmlns:r=' not in sheet_xml:
                sheet_xml = sheet_xml.replace(
                    '<worksheet ',
                    '<worksheet xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
                )
            sheet_xml = sheet_xml.replace('</worksheet>', f'  {legacy_tag}\n</worksheet>')
            with open(sheet_file, 'w', encoding='utf-8') as f:
                f.write(sheet_xml)
            print(f"Added legacyDrawing to {sheet_file}")
        else:
            print(f"legacyDrawing already in {sheet_file}")

    # ── Step 5: Repack as xlsm ─────────────────────────────────────────────────
    if os.path.exists(OUT_XLSM):
        os.remove(OUT_XLSM)

    # Repack: preserve original compression and ordering as much as possible
    with zipfile.ZipFile(XLSM_SRC, 'r') as z_orig:
        orig_names = {info.filename: info for info in z_orig.infolist()}

    with zipfile.ZipFile(OUT_XLSM, 'w', compression=zipfile.ZIP_DEFLATED) as z_out:
        # Walk all files in WORK_DIR and add them
        for dirpath, dirnames, filenames in os.walk(WORK_DIR):
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                arcname   = os.path.relpath(full_path, WORK_DIR)
                arcname   = arcname.replace(os.sep, '/')

                # vbaProject.bin should be stored uncompressed (binary macro file)
                if arcname == 'xl/vbaProject.bin':
                    comp = zipfile.ZIP_STORED
                else:
                    comp = zipfile.ZIP_DEFLATED

                with open(full_path, 'rb') as f:
                    content = f.read()
                z_out.writestr(zipfile.ZipInfo(arcname), content, compress_type=comp)

    print(f"\nRepacked xlsm: {OUT_XLSM}")
    print(f"File size: {os.path.getsize(OUT_XLSM)} bytes")

    # Verify it opens as a valid zip
    with zipfile.ZipFile(OUT_XLSM, 'r') as z:
        names = z.namelist()
        print(f"ZIP entries ({len(names)}): {names[:15]}...")
    print("\nDone!")


if __name__ == '__main__':
    main()
