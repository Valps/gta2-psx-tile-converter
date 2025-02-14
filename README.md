# Readme

Python code which reads and extract GTA2 textures from PSX binary files.

## psx_create_tiles.py

Extract and create all tiles from PSX binary files. The .bmp files have size 64x64, colour depth of 8.

They are ready to use in STY Tool or another programs which reads GTA2 tiles.

More info about palettes usage can be seen in palettes.txt.

## psx_sty_injector.py

Inject all PSX tiles (from a level) created by "psx_create_tiles.py" into a .sty file.

## psx_page_tile_extractor.py

Extract and create all tile pages from PSX binary files. The .bmp files have size 256x256 and 512x512, colour depth of 24.
