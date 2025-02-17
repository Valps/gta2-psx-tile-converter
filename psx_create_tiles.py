from PIL import Image
from pathlib import Path
import sys

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

            tiles_per_palette = 1      # reset num tiles per palette
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
    

def write_all_tiles_from_level(level, palettes, tiles_per_palette_array):
    for page in range(NUM_PAGES):
        b_tile_path = ROOT_DIR / level / "b_tiles" / f"{level}_{page+1}.data"
        b_pal_path = ROOT_DIR / level / "b_palettes" / f"{level}_{page+1}_palettes.data"

        if not b_tile_path.exists():
            print("Tile binary file not found.")
            print("File: " + str(b_tile_path))
            sys.exit(-1)

        if not b_pal_path.exists():
            print("Palette binary file not found.")
            print("File: " + str(b_pal_path))
            sys.exit(-1)

        binary_colours = colours_from_binary(b_pal_path)
        rgb_colours = convert_colours_from_15_bits(binary_colours)

        with open(b_tile_path, 'rb') as file:
            for tile_idx in range(TILES_PER_PAGE):
                offset_x , offset_y = get_xy_from_tile(tile_idx)

                tile_rgb_bmp = Image.new('RGB', (2*TILE_WIDTH, 2*TILE_HEIGHT))
                pixels = tile_rgb_bmp.load()

                # position the first byte to be read in the binary
                file.seek((TILE_WIDTH//2)*tile_idx + ( PAGE_WIDTH*(TILE_HEIGHT - 1) // 2 )*(tile_idx // PAGE_TILES_HEIGHT))

                for y in range(offset_y, offset_y + TILE_HEIGHT):
                    for x in range(offset_x, offset_x + TILE_WIDTH, 2):   # 2 pixels per byte
                        idx1, idx2 = two_nibble_from_byte( int.from_bytes(file.read(1)))

                        page_x , page_y = 2*(x - offset_x), 2*(y - offset_y)

                        colour_1 = rgb_colours[tile_idx][idx2]
                        colour_2 = rgb_colours[tile_idx][idx1]

                        pixels[page_x, page_y] = colour_1
                        pixels[page_x +1 , page_y] = colour_1
                        pixels[page_x, page_y + 1] = colour_1
                        pixels[page_x + 1, page_y + 1] = colour_1

                        pixels[page_x + 2, page_y] = colour_2
                        pixels[page_x + 3, page_y] = colour_2
                        pixels[page_x + 2, page_y + 1] = colour_2
                        pixels[page_x + 3, page_y + 1] = colour_2
                    
                    # skip some bytes to get the row below
                    file.read( TILE_WIDTH*(PAGE_TILES_HEIGHT - 1) // 2 )  
                
                true_tile_idx = tile_idx + page*TILES_PER_PAGE  # 0 to 383
                
                out_bmp_path = ROOT_DIR / level / "all_tiles" / f"{level}_{true_tile_idx}.bmp"  # level + "_" + str(true_tile_idx) + ".bmp"

                palette_idx = get_new_palette_idx_from_tile(true_tile_idx, tiles_per_palette_array)
                palette = palettes[palette_idx]

                # convert ...(r,g,b)... to ...r,g,b...
                pal = ajust_palette(palette)

                # contraption to convert the RGB to palette
                p_img = Image.new('P', (16, 16))
                p_img.putpalette(pal)

                tile_bmp = tile_rgb_bmp.quantize(colors=NUM_COLOURS_PER_PALETTE, palette=p_img, dither=0)
                tile_bmp.save(out_bmp_path)

def print_all_palettes_used(level, tiles_per_palette_array):
    sum = 0
    for i in range(len(tiles_per_palette_array)):
        print(f"{level}_{sum}.bmp to {level}_{sum + tiles_per_palette_array[i] - 1}.bmp uses palette {i}")
        sum += tiles_per_palette_array[i]
    print(f"{level}_{sum}.bmp to {level}_383.bmp uses palette {i+1}", end="\n\n")


def main():
    all_colours = []
    for level in LEVELS:
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
        
        all_colours.append(all_level_colours)

    for level in LEVELS:
        print(f"Creating palette for level {level.upper()}")
        level_idx = LEVELS.index(level)
        palettes, tiles_per_palette_array = create_8bits_palettes(all_colours[level_idx])

        print(f"Creating {2*TILE_WIDTH}x{2*TILE_HEIGHT} tiles for level {level.upper()}", end="\n\n")
        write_all_tiles_from_level(level, palettes, tiles_per_palette_array) # write .bmp of tiles on hard disk

        print_all_palettes_used(level, tiles_per_palette_array) # print which palette the tiles uses

    

if __name__ == "__main__":
    main()

