import imageio.v3 as iio
from PIL import Image
from pathlib import Path

ROOT_DIR = Path(__file__).parent

LEVELS = ["bil", "ste", "wil"]
TILE_WIDTH = 32
TILE_HEIGHT = 32
PAGE_SIZE = 8       #  8 tiles x 8 tiles

def byte_to_two_nibble(byte):
    upper_nibble = byte // 16
    lower_nibble = byte % 16
    return [upper_nibble, lower_nibble]

def colours_from_bmp(pal_path):
    with open(pal_path, 'rb') as file:
        signature = file.read(2).decode('ascii')
        file_size = int.from_bytes(file.read(4), 'little')
        reserved_1 = int.from_bytes(file.read(2), 'little')
        reserved_2 = int.from_bytes(file.read(2), 'little')
        pixel_data_offset = int.from_bytes(file.read(4), 'little')

        dib_header_size = int.from_bytes(file.read(4), 'little')
        width = int.from_bytes(file.read(4), 'little', signed=True)
        height = int.from_bytes(file.read(4), 'little', signed=True)
        colour_planes = int.from_bytes(file.read(2), 'little')
        bit_depth = int.from_bytes(file.read(2), 'little')
        compression_type = int.from_bytes(file.read(4), 'little')
        image_size = int.from_bytes(file.read(4), 'little')
        horizontal_res = int.from_bytes(file.read(4), 'little', signed=True)
        vertical_res = int.from_bytes(file.read(4), 'little', signed=True)
        num_colours_in_palette = int.from_bytes(file.read(4), 'little')
        num_important_colours = int.from_bytes(file.read(4), 'little')

        #print(bit_depth)
        if (bit_depth != 32):
            print("Wrong bit depth")
            return -1

        row_size = ((bit_depth * width + 31) // 32) * 4
        padding = row_size - ((bit_depth * width) // 8)
        #file.seek(pixel_data_offset)

        
        
        tile_palette_colours = []

        for i in range(abs(height)):
            row = []
            #print(f"\ni = {i}\n")
            for j in range(width):
                b = ord(file.read(1))
                g = ord(file.read(1))
                r = ord(file.read(1))
                a = ord(file.read(1))   # not used
                row.append( (r,g,b) )   # (r,g,b,a)
                if (j % 16 == 15):      
                    tile_palette_colours.append(row)    # store tile palette
                    row = []    # reset
                    #print(tile_palette_colours[-1], end='\n\n')
                #print(f"R: {r}, G: {g}, B: {b}, A: {a}")
            
            file.read(padding)  # Skip padding bytes, if any


    #  colour_rgb = tile_palette_colours[tile_idx][colour_idx]
    
    return tile_palette_colours

def get_colour_indexes_from_bmp(bmp_path):
    with open(bmp_path, 'rb') as file:
        signature = file.read(2).decode('ascii')                        # 0x0
        file_size = int.from_bytes(file.read(4), 'little')              # 0x2
        reserved_1 = int.from_bytes(file.read(2), 'little')             # 0x6
        reserved_2 = int.from_bytes(file.read(2), 'little')             # 0x8
        pixel_data_offset = int.from_bytes(file.read(4), 'little')      # 0xA

        dib_header_size = int.from_bytes(file.read(4), 'little')        # 0xE
        width = int.from_bytes(file.read(4), 'little', signed=True)     # 0x12
        height = int.from_bytes(file.read(4), 'little', signed=True)    # 0x16
        colour_planes = int.from_bytes(file.read(2), 'little')          # 0x1A
        bit_depth = int.from_bytes(file.read(2), 'little')              # 0x1C
        compression_type = int.from_bytes(file.read(4), 'little')       # 0x1E
        image_size = int.from_bytes(file.read(4), 'little')             # 0x22
        horizontal_res = int.from_bytes(file.read(4), 'little', signed=True)    # 0x26
        vertical_res = int.from_bytes(file.read(4), 'little', signed=True)      # 0x2A
        num_colours_in_palette = int.from_bytes(file.read(4), 'little')         # 0x2E
        num_important_colours = int.from_bytes(file.read(4), 'little')          # 0x32

        
        if (bit_depth != 4):
            print("Wrong bit depth for greyscale bmp")
            return -1

        print(f"Bit depth: {bit_depth}")
        print(f"Width: {width}")
        print(f"Height: {height}")
        print(f"Compression type: {compression_type}")
        print(f"Num palette colours: {num_colours_in_palette}")
        print(f"Num important colours: {num_important_colours}")

        
        # skip colour table,  4 bits per pixel
        file.read(64)   # 64 = 16 * 4,   16 colours,  4 = r,g,b,a

        pixel_indexes_offset = file.tell()  # current stream position

        pixel_colour_indexes = []

        for y_tile in range(PAGE_SIZE):
            for x_tile in range(PAGE_SIZE):
                tile_colour_indexes = []
                #file.seek(pixel_indexes_offset + (TILE_WIDTH//2)*x_tile + (TILE_WIDTH*PAGE_SIZE*TILE_HEIGHT//2)*y_tile)
                
                # current position = first pixel of tile

                for y_pixel in range(TILE_HEIGHT):
                    file.seek(pixel_indexes_offset + (TILE_WIDTH//2)*x_tile + (TILE_WIDTH*PAGE_SIZE*TILE_HEIGHT//2)*y_tile + (TILE_WIDTH*PAGE_SIZE//2)*y_pixel)
                    for x_pixel in range(TILE_WIDTH//2):
                        tile_colour_indexes += byte_to_two_nibble( int.from_bytes(file.read(1), 'little'))
                
                pixel_colour_indexes.append(tile_colour_indexes)
                if (y_tile == PAGE_SIZE-2  and x_tile == 0):
                    #print(len(tile_colour_indexes))
                    #print(tile_colour_indexes)
                    pass
    
    return pixel_colour_indexes

def write_tile_bmp(out_bmp_path, tile_palette, colours_indexes, tile_idx):

    tile_bmp = Image.new('RGB', (TILE_WIDTH, TILE_HEIGHT))
    pixels = tile_bmp.load()

    pixel_idx = 0
    #print(colours_indexes[tile_idx])
    #print(tile_palette[tile_idx])
    for y in range(TILE_HEIGHT):
        for x in range(TILE_WIDTH):
            #r = int((32*y + x)*255/1024)
            #g = int((32*y + x)*255/1024)
            #b = int((32*y + x)*255/1024)
            #print(colours_indexes[tile_idx][pixel_idx])
            c_idx = colours_indexes[tile_idx][pixel_idx]
            #c_idx += 1
            #if (c_idx > 15):
            #    c_idx = 0
            r, g, b = tile_palette[tile_idx][c_idx]
            pixels[x,TILE_HEIGHT - y - 1] = (r, g, b)
            pixel_idx += 1
    tile_bmp = tile_bmp.convert(colors=16)
    tile_bmp.save(out_bmp_path) # 'test.bmp'
    return



def main():
    for level in LEVELS:
        for page in range(6):   #  page + 1
            grey_path = ROOT_DIR / level / "greyscale" / (level + "_" + str(page+1) + "_grey.bmp")
            pal_path = ROOT_DIR / level / "palettes" / (level + "_" + str(page+1) + "_pal.bmp")

            if grey_path.exists() and pal_path.exists():
                #print(level + "_" + str(page+1) + "_grey.bmp exists")
                #extract_from_page(grey_path, pal_path)
                pass


if __name__ == "__main__":
    #main()
    grey_path = ROOT_DIR / "ste" / "greyscale" / "ste_1_grey.bmp"
    pal_path = ROOT_DIR / "ste" / "palettes" / "ste_1_pal.bmp"
    if grey_path.exists() and pal_path.exists():
        print("Opening file: " + str(pal_path))

        #extract_from_page(grey_path, pal_path)

        colours = colours_from_bmp(pal_path)
        colours_indexes = get_colour_indexes_from_bmp(grey_path)

        tile_rows = 8   # TODO: 7 in ste page 6, read from palette bmp

        for tile_idx in range(PAGE_SIZE*PAGE_SIZE):    #  PAGE_SIZE*PAGE_SIZE
            tile_path = ROOT_DIR / "ste" / "converted" / ("ste_tile_" + str(tile_idx) + ".bmp")
            write_tile_bmp(tile_path, colours, colours_indexes, tile_idx)

        #tile_idx = 57
        #tile_path = ROOT_DIR / "bil" / "converted" / ("bil_tile_" + str(tile_idx) + ".bmp")
        #write_tile_bmp(tile_path, colours, colours_indexes, tile_idx)




