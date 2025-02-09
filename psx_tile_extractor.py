import imageio.v3 as iio
from PIL import Image
from pathlib import Path

ROOT_DIR = Path(__file__).parent

LEVELS = ["bil", "ste", "wil"]
TILE_WIDTH = 32
TILE_HEIGHT = 32
PAGE_TILES_HEIGHT = 8       #  8 tiles x 8 tiles
PAGE_WIDTH = 256
PAGE_HEIGHT = 256

def two_nibble_from_byte(byte):
    upper_nibble = byte // 16
    lower_nibble = byte % 16
    return (upper_nibble, lower_nibble)


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
                #print(len(tile_palette))
                palette.append(tile_palette)
                tile_palette = []
                #print(palette[-1])
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

def get_tile_from_xy(x,y):
    great_y = y // 32
    great_x = x // 32
    return great_x + PAGE_TILES_HEIGHT*great_y

def write_page_bmp(b_tile_path, rgb_colours, out_bmp_path):
    page_bmp = Image.new('RGB', (PAGE_WIDTH, PAGE_HEIGHT))
    pixels = page_bmp.load()

    with open(b_tile_path, 'rb') as file:
        for y in range(PAGE_HEIGHT):
            for x in range(0,PAGE_WIDTH,2):
                
                idx1, idx2 = two_nibble_from_byte( int.from_bytes(file.read(1)))

                tile_idx = get_tile_from_xy(x,y)

                pixels[x,y] = rgb_colours[tile_idx][idx2]
                pixels[x+1,y] = rgb_colours[tile_idx][idx1]
    page_bmp.save(out_bmp_path)
    return

def main():
    for level in LEVELS:
        for page in range(6):   #  page + 1
            binary_tiles_path = ROOT_DIR / level / "b_tiles" / (level + "_" + str(page+1) + ".data")
            binary_pal_path = ROOT_DIR / level / "b_palettes" / (level + "_" + str(page+1) + "_palettes.data")
            output_path = ROOT_DIR / level / "converted" / (level + "_page_" + str(page+1) + ".bmp")

            if binary_tiles_path.exists() and binary_pal_path.exists():
                binary_colours = colours_from_binary(binary_pal_path)
                rgb_colours = convert_colours_from_15_bits(binary_colours)

                print("Opening file: " + str(binary_tiles_path))
                write_page_bmp(binary_tiles_path, rgb_colours, output_path)


if __name__ == "__main__":
    main()

