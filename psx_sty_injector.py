from PIL import Image
from pathlib import Path
import shutil
import argparse
import sys
import os

PROGRAM_NAME = os.path.basename(sys.argv[0])
ROOT_DIR = Path(__file__).parent

LEVELS = ["bil", "ste", "wil"]

TILE_WIDTH = 32
TILE_HEIGHT = 32
PAGE_TILES_HEIGHT = 8       #  8 tiles x 8 tiles
PAGE_WIDTH = 256
PAGE_HEIGHT = 256
NUM_PAGES = 6

COLOURS_PER_TILE = 16
NUM_COLOURS_PER_PALETTE = 256
PAD_COLOUR = (0, 0, 0)

TOTAL_NUM_TILES = 384
TILES_PER_PAGE = 64

def two_nibble_from_byte(byte):
    upper_nibble = byte // 16
    lower_nibble = byte % 16
    return (upper_nibble, lower_nibble)

def ajust_palette(palette):
    new_palette = []
    for colour in palette:
        new_palette.append(colour[0])   # r
        new_palette.append(colour[1])   # g
        new_palette.append(colour[2])   # b
    return new_palette

def colours_from_binary(b_pal_path):
    with open(b_pal_path, 'rb') as file:
        palette = []

        # get palette length
        file.read()
        eof = file.tell()

        file.seek(0)
        offset = 0

        tile_palette = []
        while (offset < eof):
            tile_palette.append( int.from_bytes(file.read(2), 'little')  )
            offset += 2
            # has tile palette ended? 
            # store its palette and start read another tile palette
            if (offset % 32 == 0):
                palette.append(tile_palette)
                tile_palette = []
    return palette

def pull_colours(word):
    # remove leading 1 if it exists
    if (word >= 32768):
        word -= 32768

    r = (word % 32)*255 // 32

    word = word >> 5
    g = (word % 32)*255 // 32

    word = word >> 5
    b = (word*255) // 32
    
    return (r, g, b)

def convert_colours_from_15_bits(binary_colours):
    colours = []
    for tile_pal_idx in range(len(binary_colours)): # 0 to 63
        tile_colours = []
        for colour in range(len(binary_colours[tile_pal_idx])): # 0 to 15
            tile_colours.append( pull_colours(binary_colours[tile_pal_idx][colour]) )
        colours.append(tile_colours)
    return colours

def verify_slots(palette_chunk, rgb_array):
    if (len(rgb_array) != 16):
        print(f"Error: rgb array size is not {COLOURS_PER_TILE}")
        sys.exit(-1)
    
    current_num_colors = len(palette_chunk)

    for colour in rgb_array:
        if (colour not in palette_chunk):
            current_num_colors += 1
    
    if (current_num_colors > NUM_COLOURS_PER_PALETTE):
        return False
    return True

def insert_colours(palette_chunk, rgb_array):
    for colour in rgb_array:
        if (colour not in palette_chunk):
            palette_chunk.append(colour)
    return

def pad_palette(palette_chunk):
    while (len(palette_chunk) < NUM_COLOURS_PER_PALETTE):
        palette_chunk.append(PAD_COLOUR)

def create_8bits_palettes(all_level_colours):
    """Create 256 colour palettes using 16 colour palettes of each tile from original PSX files,
    and also optimize for repeated colours."""
    palettes = []
    palette_chunk = []

    tiles_per_palette_array = []
    tiles_per_palette = 0

    for tile_idx in range(TOTAL_NUM_TILES):

        # Verify if the tile palette fits in palette chunk
        if ( verify_slots(palette_chunk, all_level_colours[tile_idx]) ):
            # it fits, thus insert tile palette
            insert_colours(palette_chunk, all_level_colours[tile_idx])
            tiles_per_palette += 1
        else:
            # wrap palette

            pad_palette(palette_chunk)      # fill in the last slots with pad colours, if they are empty
            palettes.append(palette_chunk)  # add palette chunk

            # attach number of tiles for this palette
            tiles_per_palette_array.append(tiles_per_palette)

            tiles_per_palette = 0      # reset num tiles per palette
            palette_chunk = []         # reset array
    
    # finish last palette
    pad_palette(palette_chunk)
    palettes.append(palette_chunk)

    return ( palettes, tiles_per_palette_array )


def get_tile_from_xy(x,y):
    great_y = y // TILE_HEIGHT
    great_x = x // TILE_WIDTH
    return great_x + PAGE_TILES_HEIGHT*great_y

def get_xy_from_tile(tile_idx):
    y = (tile_idx // PAGE_TILES_HEIGHT) * TILE_WIDTH
    x = (tile_idx % PAGE_TILES_HEIGHT) * TILE_HEIGHT
    return ( x , y )


def get_new_palette_idx_from_tile(tile_idx, tiles_per_palette_array):
    sum = 0
    for palette_idx in range(len(tiles_per_palette_array)):
        sum += tiles_per_palette_array[palette_idx]
        if (sum > tile_idx):
            return palette_idx
    # last palette
    return len(tiles_per_palette_array) - 1

def print_all_palettes_used(level, tiles_per_palette_array):
    sum = 0
    for i in range(len(tiles_per_palette_array)):
        print(f"{level}_{sum}.bmp to {level}_{sum + tiles_per_palette_array[i] - 1}.bmp uses palette {i}")
        sum += tiles_per_palette_array[i]
    print(f"{level}_{sum}.bmp to {level}_383.bmp uses palette {i+1}", end="\n\n")






####  STY stuff


def detect_headers_and_get_chunks(sty_path):

    chunk_info = dict(PALX = [None, None], 
                   PPAL = [None, None], 
                   PALB = [None, None], 
                   TILE = [None, None], 
                   SPRG = [None, None], 
                   SPRX = [None, None], 
                   SPRB = [None, None],
                   DELS = [None, None],
                   DELX = [None, None],
                   FONB = [None, None],
                   CARI = [None, None],
                   OBJI = [None, None],
                   PSXT = [None, None],
                   RECY = [None, None],
                   SPEC = [None, None])
    

    with open(sty_path, 'rb') as file:
        signature = file.read(4).decode('ascii')

        if (signature != "GBST"):
            print("Error!\n")
            print(f"{sty_path} is not a sty file!")
            sys.exit(-1)

        version_code = int.from_bytes(file.read(2),'little')

        print(f"File Header: {signature}")
        print(f"Version Code: {version_code}\n")

        data_offset = file.tell()
        size = file.seek(0, os.SEEK_END)
        file.seek(data_offset)

        print("File Size: {:,} bytes".format(size))

        current_offset = data_offset

        while (current_offset < size):
            chunk_header = file.read(4).decode('ascii')
            current_offset += 4
            if (chunk_header == "PALX" 
                or chunk_header == "PPAL"
                or chunk_header == "PALB"
                or chunk_header == "TILE"
                or chunk_header == "SPRG"
                or chunk_header == "SPRX"
                or chunk_header == "SPRB"
                or chunk_header == "DELS"
                or chunk_header == "DELX"
                or chunk_header == "FONB"
                or chunk_header == "CARI"
                or chunk_header == "OBJI"
                or chunk_header == "PSXT"
                or chunk_header == "RECY"
                or chunk_header == "SPEC"
                ):
                header_data_offset = file.tell() + 4
                chunk_info[chunk_header][0] = header_data_offset

                header_size = int.from_bytes(file.read(4),'little')
                chunk_info[chunk_header][1] = header_size

                print(f"Header {chunk_header} found! Offset: {hex(header_data_offset)}, Size: {hex(header_size)}")

                file.read(header_size)  # skip data
                current_offset += header_size
    print("")
    return chunk_info




def change_palettes_idx(sty_path, chunk_infos, tiles_per_palette_array):

    print("Changing virtual palettes indexes...")

    with open(sty_path, 'r+b') as file:
        
        palx_offset = chunk_infos["PALX"][0]

        file.seek(palx_offset)

        for tile_idx in range(TOTAL_NUM_TILES):
            physical_pal_idx = get_new_palette_idx_from_tile(tile_idx, tiles_per_palette_array)

            word = bytes([physical_pal_idx % 256, physical_pal_idx // 256])     # low endian stuff

            file.write(word)


def change_physical_palettes(output_path, chunk_infos, palettes_array):

    print("Changing physical palettes...")

    with open(output_path, 'r+b') as tgt_sty_file:
        
        ppal_offset = chunk_infos["PPAL"][0]

        for pal_idx, palette in enumerate(palettes_array):
            #print(f"Palette {pal_idx}: ")
            for sty_palette_row in range(NUM_COLOURS_PER_PALETTE):

                tgt_sty_file.seek(ppal_offset + 256*sty_palette_row + 4*pal_idx)

                #print(f"({palette[sty_palette_row][0]}, {palette[sty_palette_row][1]}, {palette[sty_palette_row][2]})")
                # (R,G,B) -> B G R A
                dword = bytes([ palette[sty_palette_row][2], 
                                palette[sty_palette_row][1], 
                                palette[sty_palette_row][0], 
                                0 ])

                tgt_sty_file.write(dword)
            #print("")


def inject_tiles(sty_path, chunk_infos, level):
    
    print("Changing tiles...")

    with open(sty_path, 'r+b') as tgt_sty_file:

        tile_data_offset = chunk_infos["TILE"][0]

        for tile_idx in range(TOTAL_NUM_TILES):       #  TODO:  TOTAL_NUM_TILES
            bmp_tile_path = ROOT_DIR / level / "all_tiles" / f"{level}_{tile_idx}.bmp"

            if not bmp_tile_path.exists():
                print(f"ERROR: bmp file of tile {tile_idx} not found.")
                print("Path: " + str(bmp_tile_path))
                sys.exit(-1)

            with open(bmp_tile_path, 'rb') as bmp_tile_file:
                signature = bmp_tile_file.read(2).decode('ascii')

                if (signature != "BM"):
                    print(f"ERROR: The file {bmp_tile_path} is not a bmp file!")
                    sys.exit(-1)
                
                bmp_tile_file.read(8)   # skip some data
                pixel_data_offset = int.from_bytes(bmp_tile_file.read(4), 'little')

                bmp_tile_file.seek(pixel_data_offset)   # go to pixel data

                # TODO: fix this
                #data_size = bmp_tile_file.seek(pixel_data_offset, os.SEEK_END)  # get data size
                data_size = 4096

                bmp_tile_file.seek(pixel_data_offset)

                bmp_data = bmp_tile_file.read(data_size)    # get pixel data
                bmp_data_reversed = bmp_data[::-1]          # reverse it

                # now inject it into .sty file
                for row_idx in range(64):
                    tgt_sty_file.seek(tile_data_offset + 64*tile_idx + 256*row_idx + 63*256*(tile_idx // 4) )   # get row offset in .sty binary
                    tgt_sty_file.write(bmp_data_reversed[ (row_idx*64 + 64) : (row_idx*64) : -1 ])  # reverse this piece of the row

# TODO:
def change_surface_types(output_path, chunk_infos, PSX_sty_file_path, game_ovl_file_path):
    return




def main():
    parser = argparse.ArgumentParser(PROGRAM_NAME)
    parser.add_argument("sty_path")
    parser.add_argument("level")
    args = parser.parse_args()

    if not args.sty_path:
        print("Usage: python [program path] [sty path] [level=bil,ste,wil]")
        sys.exit(-1)

    # get target .sty path
    if ("\\" not in args.sty_path and "/" not in args.sty_path):
        sty_path = ROOT_DIR / args.sty_path
    else:
        sty_path = Path(args.sty_path)

    if not sty_path.exists():
        print(f"File not found: {str(sty_path)}")
        sys.exit(-1)

    if args.level.lower() not in LEVELS:
        print(f"Invalid level. Level can be: bil, ste or wil")
        sys.exit(-1)

    level = args.level.lower()

    all_level_colours = []
    for page in range(6):   #  page + 1
        binary_pal_path = ROOT_DIR / level / "b_palettes" / f"{level}_{page+1}_palettes.data"
        if binary_pal_path.exists():
                
            print("Getting colours from file: " + str(binary_pal_path))
            binary_colours = colours_from_binary(binary_pal_path)
            rgb_colours = convert_colours_from_15_bits(binary_colours)
            all_level_colours += rgb_colours
        else:
            print("Palette binary files not found")
            sys.exit(-1)


    print(f"Creating palette for level {level.upper()}")
    palettes_array, tiles_per_palette_array = create_8bits_palettes(all_level_colours)

    #print_all_palettes_used(level, tiles_per_palette_array) # print which palette the tiles uses

    # now read .sty file
    print("Reading target .sty file...\n")

    chunk_infos = detect_headers_and_get_chunks(sty_path)

    if chunk_infos["PALX"][0] is None:
        print("ERROR: PALX Header is missing in .sty file.")
        sys.exit(-1)

    if chunk_infos["PPAL"][0] is None:
        print("ERROR: PPAL Header is missing in .sty file.")
        sys.exit(-1)

    if chunk_infos["TILE"][0] is None:
        print("ERROR: TILE Header is missing in .sty file.")
        sys.exit(-1)

    # create a copy of sty file
    str_gmp_path = str(sty_path)
    i = str_gmp_path.rfind('\\') + 1
    j = str_gmp_path.rfind('.')

    filename = str_gmp_path[i:j]
    output_path = ROOT_DIR / f"{filename}_edited.sty"

    print(f"Creating copy of {filename}.gmp")
    shutil.copyfile(sty_path, output_path)

    # change virtual palettes indexes, since the number of tiles with the same palette isn't always 32
    change_palettes_idx(output_path, chunk_infos, tiles_per_palette_array)

    # change physical palettes
    change_physical_palettes(output_path, chunk_infos, palettes_array)

    # change .sty tiles
    inject_tiles(output_path, chunk_infos, level)

    # change surface types
    # load directly from PSX file
    PSX_sty_file_path = ROOT_DIR / (f"{level.upper()}.STY")
    game_ovl_file_path = ROOT_DIR / ("GAME.OVL")

    if ( PSX_sty_file_path.exists()
        and game_ovl_file_path.exists() ):
        print(f"Original PSX file found: {level.upper()}.STY and GAME.OVL")
        change_surface_types(output_path, chunk_infos, PSX_sty_file_path, game_ovl_file_path)

    print("All PSX tiles injected successfully")

        

    

if __name__ == "__main__":
    main()

