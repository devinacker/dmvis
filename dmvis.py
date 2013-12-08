#!/usr/bin/env python
"""
	Doom map drawer thingy!
	by Revenant
	pre-release secret gist version 2
	
	Scroll down for render settings.
"""

from __future__ import print_function
# http://omgifol.sourceforge.net
# http://files.funcrusherplus.net/static/omg/
from omg import *
from sys import argv, stderr, exit
from PIL import Image, ImageDraw
from PIL.GifImagePlugin import getheader, getdata
from time import clock

def usage():
	stderr.write(
	"""
	Usage:
	    dmvis.py wad map

	Example:
	    dmvis.py DOOM2.WAD MAP01
	    dmvis.py DOOM.WAD E1M1
	""".replace('\t', ''))
	
	exit(-1)

class DrawMap():
	# TODO: allow to change these from the command line probably
	#
	# ~ settings !!! ~
	#
	# width of image in pixels (including borders)
	image_width = 1024
	# size of border in pixels
	border = 8
	# length of frame in seconds
	frame_length = 0.04
	# make gif loop
	loop = True
	# length of last frame (only matters when looping, obviously)
	loop_delay = 5
	# draw one frame for each line (sloooowww)
	# (otherwise draws one frame per group of adjacent lines, which is much faster)
	frame_per_line = True
	# don't redraw 2-sided lines that have been drawn already (saves frames but can look weird)
	draw_lines_once = True
	# draw frame bounding boxes (debug)
	show_bbox = False
	
	# GIF palette
	# color 0 (background)
	color_bg  = [255, 255, 255]
	# color 1 (new lines)
	color_new = [220, 0, 0]
	# color 2 (action lines)
	color_act = [220, 130, 50]
	# color 3 (1-sided lines)
	color_1s  = [0, 0, 0]
	# color 4 (2-sided lines)
	color_2s  = [144, 144, 144]

	def __init__(self, map):
		self.edit = MapEditor(map)
		
		self.xmin = min([ v.x for v in self.edit.vertexes])
		self.xmax = max([ v.x for v in self.edit.vertexes])
		self.ymin = min([-v.y for v in self.edit.vertexes])
		self.ymax = max([-v.y for v in self.edit.vertexes])
		
		self.scale = (self.image_width - self.border*2) / float(max(self.xmax - self.xmin, self.ymax - self.ymin))
		# normalize min/max
		self.xmin = int(self.scale * self.xmin); self.xmax = int(self.scale * self.xmax)
		self.ymin = int(self.scale * self.ymin); self.ymax = int(self.scale * self.ymax)
		
		self.image_height = self.ymax - self.ymin + 2*self.border
		
		# normalize vertices
		for v in self.edit.vertexes:
			v.x = (self.scale * v.x) - self.xmin
			v.y = (self.scale * -v.y) - self.ymin
		
		# initialize image / gif stuff		
		self.frames = 0
		self.old_lines = []
		self.new_lines = []
		
		self.frame = Image.new('P', (self.image_width, self.image_height), 0)
		self.frame.putpalette(self.color_bg + self.color_new + self.color_act + self.color_1s + self.color_2s)
		self.draw = ImageDraw.Draw(self.frame)

	def draw_line(self, line, new = True):
		p1x = self.edit.vertexes[line.vx_a].x + self.border
		p1y = self.edit.vertexes[line.vx_a].y + self.border
		p2x = self.edit.vertexes[line.vx_b].x + self.border
		p2y = self.edit.vertexes[line.vx_b].y + self.border
		
		if new:
			color = 1
			self.new_lines.append(line)
		elif line.action:
			color = 2
		elif not line.two_sided:
			color = 3
		else:
			color = 4
		
		self.draw.line((p1x, p1y, p2x, p2y), fill=color)
		self.draw.line((p1x+1, p1y, p2x+1, p2y), fill=color)
		self.draw.line((p1x, p1y+1, p2x, p2y+1), fill=color)

	def emit_frame(self, file, final = False):
		# redraw old lines with the regular color
		for line in self.old_lines:
			self.draw_line(line, new = False)
		
		# write a "graphic control extension" with frame length
		def emit_gce(time, trans = True):
			file.write("\x21\xF9\x04")
			# disposition + transparency
			file.write("\x05" if trans else "\x04")
			
			ti = min(int(time * 100), 65535)
			file.write(chr(ti & 0xFF))
			file.write(chr(ti >> 8))
			
			# transparent color 0
			file.write("\x00\x00")
		
		# actually emit a GIF frame
		# (this code adapted from gifmaker.py in PIL but with GIF89a extensions)
		bb = (0, 0, self.image_width, self.image_height)
		
		if len(self.old_lines) == 0:
			header = getheader(self.frame)
			# aaaaarrrrgggghhhh!!!
			header[0] = "GIF89a" + header[0][6:]
			
			for s in header:
				file.write(s)
			
			# AAAAAAAAAAARRRRRRGGGGGGHHHHHH!!!!!!!!
			if self.loop:
				file.write("\x21\xFF\x0BNETSCAPE2.0\x03\x01\x00\x00\x00")
			
			self.frames += 1
			emit_gce(self.frame_length, trans = False)
			for s in getdata(self.frame):
				file.write(s)
				
		else:
			lines = self.old_lines + self.new_lines
			#get bounding box based on outer corners of lines being drawn
			points = [self.edit.vertexes[i.vx_a] for i in lines] + [self.edit.vertexes[i.vx_b] for i in lines]
			
			sx = sorted(points, key = lambda i: i.x)
			sy = sorted(points, key = lambda i: i.y)
			bb = (int(sx[0].x) + self.border, int(sy[0].y) + self.border,
				  int(sx[-1].x) + self.border + 2, int(sy[-1].y) + self.border + 2)
				  # add 1 for minimum bbox size plus 1 more for line thickness
			
			self.frames += 1
			emit_gce(self.loop_delay if final else self.frame_length)
		
			if self.show_bbox:
				self.draw.rectangle((bb[0], bb[1], bb[2] - 1, bb[3] - 1), outline=1)
			
			for s in getdata(self.frame.crop(bb), offset = bb[:2]):
				file.write(s)
		
		self.old_lines[:] = self.new_lines[:]
		del self.new_lines[:]
		# erase frame to improve compression of subsequent frames
		self.draw.rectangle(bb, outline = 0, fill = 0)
		
		if final:
			file.write(";")

	def trace_lines(self, line, sector=None, visited=None):
		if visited is None:
			visited = []
		
		visited.append(line)
		
		# how to get next line?
		if sector is None:
			# first, which sector are we looking at? either the only one, or the lowest-numbered one.
			sector = self.edit.sidedefs[line.front].sector
			if line.two_sided:
				sector = min(self.edit.sidedefs[line.front].sector, self.edit.sidedefs[line.back].sector)
		
		# find another line with other connected point, same sector
		next_lines = filter(lambda other: (line.vx_b == other.vx_a or line.vx_b == other.vx_b
		                                   or line.vx_a == other.vx_a or line.vx_a == other.vx_b)
		                              and (sector == self.edit.sidedefs[other.front].sector 
		                                   or (other.two_sided and sector == self.edit.sidedefs[other.back].sector)),
		                    self.edit.linedefs)
		for other in next_lines:
			if other not in visited:
				visited = self.trace_lines(other, sector, visited)
		
		return visited
	
	def save(self, filename):
		linenum = 0
		lines_left = list(self.edit.linedefs)
		
		file = open(filename, "wb")
		
		start = clock()
		all_visited = []
		
		while len(lines_left) > 0:
			try:
				msg = "%d linedefs left, please wait... (frame %d)" % (len(lines_left), self.frames + 1)
				print(msg, end='')
				
				for line in self.trace_lines(lines_left[0]):
					if line not in all_visited:
						linenum += 1
					if not self.draw_lines_once or line not in all_visited:
						all_visited.append(line)
						
						self.draw_line(line)
						if self.frame_per_line:
							self.emit_frame(file)
						
						if line in lines_left:
							lines_left.remove(line)
				
				if not self.frame_per_line:
					self.emit_frame(file)
				
				print('\r' + ' '*len(msg) + '\r', end='')
				
			except KeyboardInterrupt:
				print("\nRendering canceled.")
				break
				
		# emit the last frame with all sectors drawn
		self.emit_frame(file, final = True)
		file.close()
		print("Rendered %d linedefs into %d frames in %f seconds." % (linenum, self.frames, clock() - start))
		print("%s saved." % filename)

if __name__ == "__main__":
	print("Doom map GIF maker thingy")
	print("by Devin Acker (Revenant), 2013\n")

	# TODO: switches to change drawing parameters
	if len(argv) != 3:
		usage()
	
	filename = argv[-2]
	mapname = argv[-1].upper()
	
	wad = WAD()
	
	try:
		wad.from_file(filename)
		
	except AssertionError:
		stderr.write("Unable to load WAD file.")
		exit(-1)
	
	if mapname not in wad.maps:
		stderr.write("Map %s not found in WAD." % mapname)
		exit(-1)
	
	draw = DrawMap(wad.maps[mapname])
	draw.save("%s_%s.gif" % (filename, mapname))
	