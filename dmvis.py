#!/usr/bin/env python
"""
	dmvis - Doom map visualizer
	by Revenant
	
	Scroll down for render settings.
	
	Copyright (c) 2013-2018 Devin Acker

	Permission is hereby granted, free of charge, to any person obtaining a copy
	of this software and associated documentation files (the "Software"), to deal
	in the Software without restriction, including without limitation the rights
	to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
	copies of the Software, and to permit persons to whom the Software is
	furnished to do so, subject to the following conditions:

	The above copyright notice and this permission notice shall be included in
	all copies or substantial portions of the Software.

	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
	IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
	FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
	AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
	LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
	OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
	THE SOFTWARE.
"""

from __future__ import print_function
from omg import *
from sys import argv, stderr, exit
from PIL import Image, ImageDraw
from PIL.GifImagePlugin import getheader, getdata
from time import clock
from argparse import ArgumentParser

class DrawMap():
	#
	# default parameters (these can be changed from the command line)
	#
	# width of image in pixels (including borders)
	image_width = 1024
	# size of border in pixels
	border = 8
	# transparent background
	trans = False
	# length of frame in 1/100 seconds
	frame_length = 4
	# make gif loop
	loop = True
	# length of last frame (only matters when looping, obviously)
	loop_delay = 500
	# draw one frame for each line (sloooowww)
	# (otherwise draws one frame per group of adjacent lines, which is much faster)
	draw_shapes = False
	# don't redraw 2-sided lines that have been drawn already (saves frames but can look weird)
	draw_twice = False
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
		from struct import error as StructError
		try:
			self.edit = MapEditor(map)
		except StructError:
			raise ValueError("Hexen / ZDoom maps are not currently supported")
		
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
			file.write(b"\x21\xF9\x04")
			# disposition + transparency
			file.write(b"\x05" if trans else b"\x04")
			
			ti = min(time, 65535)
			file.write(bytearray((ti & 0xFF, ti >> 8)))
			
			# transparent color 0
			file.write(b"\x00\x00")
		
		# actually emit a GIF frame
		# (this code adapted from gifmaker.py in PIL but with GIF89a extensions)
		bb = (0, 0, self.image_width, self.image_height)
		
		if len(self.old_lines) == 0:
			header = getheader(self.frame)
			# aaaaarrrrgggghhhh!!!
			if isinstance(header[0], list):
				header = (bytes().join(header[0]),) + header[1:]
			header = (b"GIF89a" + header[0][6:],) + header[1:]
			
			for s in header:
				if s:
					file.write(s)
			
			# AAAAAAAAAAARRRRRRGGGGGGHHHHHH!!!!!!!!
			if self.loop:
				file.write(b"\x21\xFF\x0BNETSCAPE2.0\x03\x01\x00\x00\x00")
			
			self.frames += 1
			emit_gce(self.frame_length, trans = self.trans)
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
			file.write(b";")

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
		next_lines = self.lines_in_sector[sector][line.vx_a] + self.lines_in_sector[sector][line.vx_b]

		for other in next_lines:
			if other not in visited:
				visited = self.trace_lines(other, sector, visited)
		
		return visited
	
	def save(self, filename):
		linenum = 0
		lines_left = list(self.edit.linedefs)
		
		file = open(filename, "wb")
		
		start = clock()
		
		# group lines by sector and vertex for faster searching later
		self.lines_in_sector = [{} for s in self.edit.sectors]
		def addline_sv(sector, vertex, line):
			if vertex not in self.lines_in_sector[sector]:
				self.lines_in_sector[sector][vertex] = []
			self.lines_in_sector[sector][vertex].append(line)
		
		def addline_s(sector, line):
			addline_sv(sector, line.vx_a, line)
			addline_sv(sector, line.vx_b, line)
		
		def addline(line):
			addline_s(self.edit.sidedefs[line.front].sector, line)
			if line.two_sided:
				addline_s(self.edit.sidedefs[line.back].sector, line)
		
		for line in self.edit.linedefs:
			addline(line)
		
		while len(lines_left) > 0:
			try:
				msg = "%d linedefs left, please wait... (frame %d)" % (len(lines_left), self.frames + 1)
				print(msg, end='')
				
				for line in self.trace_lines(lines_left[0]):
					if self.draw_twice or line in lines_left:
						self.draw_line(line)
						if not self.draw_shapes:
							self.emit_frame(file)
						
						if line in lines_left:
							linenum += 1
							lines_left.remove(line)
				
				if self.draw_shapes:
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

def get_args():
	ap = ArgumentParser()
	ap.add_argument("filename", help="path to WAD file")
	ap.add_argument("map",      help="name of map (ex. MAP01, E1M1)")
	
	ap.add_argument("-w", "--width", type=int, default=DrawMap.image_width,
	                help="width of image, including borders (default: %(default)s)")
	ap.add_argument("-b", "--border", type=int, default=DrawMap.border,
	                help="size of border (default: %(default)s)")
	ap.add_argument("-t", "--trans", action="store_true",
	                help="make image background transparent")
	ap.add_argument("-l", "--length", type=int, default=DrawMap.frame_length,
	                help="length of frames in 1/100 sec. (default: %(default)s)")
	ap.add_argument("-d", "--loop-delay", type=int, default=DrawMap.loop_delay,
	                help="length of last frame in 1/100 sec. (default: %(default)s)")
	ap.add_argument("-nl", "--no-loop", action="store_true",
	                help="don't loop GIF")
	ap.add_argument("-s", "--draw-shapes", action="store_true",
	                help="add one frame per shape instead of per line")
	ap.add_argument("-2", "--draw-twice", action="store_true",
	                help="draw two-sided lines two times")
	ap.add_argument("-bb", "--show-bbox", action="store_true",
	                help="show frame bounding boxes (debug)")

	if len(argv) < 3:
		ap.print_help()
		exit(-1)
	
	args = ap.parse_args()
	
	# apply optional arguments to DrawMap settings
	DrawMap.image_width  = args.width
	DrawMap.border       = args.border
	DrawMap.trans        = args.trans
	DrawMap.frame_length = args.length
	DrawMap.loop_delay   = args.loop_delay
	DrawMap.loop         = not args.no_loop
	DrawMap.draw_shapes  = args.draw_shapes
	DrawMap.draw_twice   = args.draw_twice
	DrawMap.show_bbox    = args.show_bbox
	
	return args
	
if __name__ == "__main__":
	print("dmvis - Doom map visualizer")
	print("by Devin Acker (Revenant), 2013-2018\n")
	
	args = get_args()
	
	filename = args.filename
	mapname  = args.map.upper()
	
	wad = WAD()
	
	# quick hack to support non-standard map names in omgifol 0.2
	# (not required with my fork)
	try:
		omg.wad._mapheaders.append(mapname)
	except AttributeError:
		pass
	
	try:
		wad.from_file(filename)
		
	except AssertionError:
		stderr.write("Error: Unable to load WAD file.\n")
		exit(-1)
	
	if mapname not in wad.maps:
		stderr.write("Error: Map %s not found in WAD.\n" % mapname)
		exit(-1)
	
	try:
		draw = DrawMap(wad.maps[mapname])
		draw.save("%s_%s.gif" % (filename, mapname))
	except ValueError as e:
		stderr.write("Error: %s.\n" % e)
		exit(-1)
	