#!/usr/bin/env python
from dmvis import DrawMap
from omg   import WAD
from sys   import argv, stderr

filename = argv[1]

wad = WAD()

try:
	wad.from_file(filename)
	
except AssertionError:
	stderr.write("Error: Unable to load WAD file.\n")
	exit(-1)

for mapname in wad.maps.keys():
	try:
		draw = DrawMap(wad.maps[mapname])
		draw.save("%s_%s.gif" % (filename, mapname))
	except ValueError as e:
		stderr.write("Error in %s: %s.\n" % (mapname, e))
		# try to go to the next map
		# exit(-1)