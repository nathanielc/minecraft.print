import pymclevel.mclevel as mclevel
import sys
import os
from pymclevel.box import BoundingBox
import numpy
from numpy import zeros, bincount
import logging
import itertools
import traceback
import shlex
import operator
import codecs


from math import floor
try:
    import readline
except:
    pass

class UsageError(RuntimeError): pass
class BlockMatchError(RuntimeError): pass
class PlayerNotFound(RuntimeError): pass

class MinecraftPrint:

    def __init__(self, level, output, marker1, marker2):
        self.level_name = level
        self.output_name = output + '.stl'

        #The list of goodness and markers
        #Format: [[chunk_x, chunk_z, block_x, block_z, block_y]]
        self.markers = [marker1, marker2]

        self.chunk_positions = []
        self.num_chunks = 0
        self.chunk_counter = 0

        self.diamond_check = []
        self.object_array = []

        #Data value for each block type
        self.glass = 20
        self.carpet = 171
        self.glass_pane = 102
        self.lily_pad = 111
        self.vines = 106
        self.torch = 50
        self.grass = 31
        self.deadbush = 32
        self.tall_grass = 175
        self.snow = 78


        self.no_print = {
                self.glass : True,
                self.carpet: True,
                self.glass_pane : True,
                self.lily_pad : True,
                self.vines : True,
                self.torch : True,
                self.grass : True,
                self.deadbush: True,
                self.tall_grass : True,
                self.snow: True,
            }

    def generate(self):
        self.world = mclevel.loadWorld(self.level_name)

        self.copy_marked_area()
        self.fill_cavities()
        self.remove_floating()
        self.generate_stl()

    def copy_marked_area(self):
        # Now we have the markers. Time to get serious
        if len(self.markers) == 2:
            print "Congrats, looks like we have two markers"
            print "..."
            print "Capturing marked area... this may take a minute..."

            # Calculate x0 and x1
            x0 = (16 * self.markers[0][0]) + self.markers[0][2]
            x1 = (16 * self.markers[1][0]) + self.markers[1][2]
            x_len = 0
            if x0 < x1:
                x_len = x1 - x0
            else:
                x_len = x0 - x1
                x0, x1 = x1, x0

            # Calculate y0 and y1
            y0 = min(self.markers[0][4], self.markers[1][4])
            y1 = max(self.markers[0][4], self.markers[1][4])

            y_len = y1 - y0

            # Calculate z0 and z1
            z0 = (16 * self.markers[0][1]) + self.markers[0][3]
            z1 = (16 * self.markers[1][1]) + self.markers[1][3]
            z_len = 0
            if z0 < z1:
                z_len = z1 - z0
            else:
                z_len = z0 - z1
                z0, z1 = z1, z0

            print "Area is", x_len, y_len, z_len


            # Construct an array to fit the object
            self.object_array = [[[0 for z in xrange(z_len)] for y in xrange(y_len)] for x in xrange(x_len)]


            chunks = {}

            # Copy marked blocks to object_array
            for x in range(x_len):
                cx = (x + x0) / 16
                bx = (x + x0) % 16
                for z in range(z_len):
                    cz = (z + z0) / 16
                    bz = (z + z0) % 16
                    c = (cx, cz)
                    chunk = None
                    if chunks.has_key(c):
                        chunk = chunks[c]
                    else:
                        chunk = self.world.getChunk(*c)
                        chunks[c] = chunk
                    for y in range(y_len):
                        by = y + y0
                        block_type = 0
                        block_type = chunk.Blocks[bx, bz, by]
                        if block_type in self.no_print:
                            block_type = 0
                        self.object_array[x][y][z_len-z-1] = block_type

        else:
            print "Freak out! There are somehow more or less than 2 markers!"


    def fill_cavities(self):
        print "fill_cavities"
        x_len = len(self.object_array)
        y_len = len(self.object_array[0])
        z_len = len(self.object_array[0][0])

        size = x_len * y_len * z_len
        print "size", size

        # make flat bottom
        for x in range(x_len):
            for z in range(z_len):
                self.object_array[x][0][z] = 1

        # make flat sides
        for x in range(x_len):
            for z in [0, z_len-1]:
                self._make_flat(x,z,y_len)

        for z in range(z_len):
            for x in [0, x_len-1]:
                self._make_flat(x,z,y_len)



        not_cavity = {}
        for y in range(y_len-1, -1, -1):
            for x in range(x_len):
                for z in range(z_len):
                    if self.object_array[x][y][z] == 0 and \
                        not not_cavity.has_key((x,y,z)):
                        cavity, is_cavity = self._drain(x,y,z,x_len,y_len,z_len)
                        if len(cavity) > 0:
                            if is_cavity:
                                print "filling in cavity of size", len(cavity)
                                for x0,y0,z0 in cavity:
                                    self.object_array[x0][y0][z0] = 1
                            else:
                                not_cavity.update(cavity)
                                print len(not_cavity)
    def remove_floating(self):
        print "Removing Floating Islands"
        x_len = len(self.object_array)
        y_len = len(self.object_array[0])
        z_len = len(self.object_array[0][0])

        not_island = {}
        for y in range(y_len-1, -1, -1):
            for x in range(x_len):
                for z in range(z_len):
                    if self.object_array[x][y][z] > 0 and \
                        not not_island.has_key((x,y,z)):
                        island, is_island = self._island(x,y,z,x_len,y_len,z_len)
                        if len(island) > 0:
                            if is_island:
                                print "removing island of size", len(island)
                                for x0,y0,z0 in island:
                                    self.object_array[x0][y0][z0] = 0
                            else:
                                not_island.update(island)
                                print len(not_island)


    def _make_flat(self, x,z, y_len):
        found = False
        for y in range(y_len-1,-1,-1):
            if self.object_array[x][y][z] > 0:
                found = True
                continue
            if found and self.object_array[x][y][z] == 0:
                self.object_array[x][y][z] = 1


    sides = [
            (1, 0, 0),
            (-1, 0, 0),
            (0, 1, 0),
            (0, -1, 0),
            (0, 0, 1),
            (0, 0, -1),
        ]

    def _drain(self, x, y, z, x_len, y_len, z_len):
        cavity = {}
        is_cavity = True
        stack = []
        stack.append((x,y,z))
        while len(stack) > 0:
            pos = stack.pop()

            if cavity.has_key(pos):
                continue
            cavity[pos] = True

            x, y, z = pos
            for dx, dy, dz in self.sides:
                x0 = x + dx
                y0 = y + dy
                z0 = z + dz
                if x0 >= 0 and \
                   y0 >= 0 and \
                   z0 >= 0 and \
                   x0 < x_len and \
                   y0 < y_len and \
                   z0 < z_len:

                    if self.object_array[x0][y0][z0] == 0:
                        stack.append((x0,y0,z0))
                else:
                    is_cavity = False
        return cavity, is_cavity

    def _island(self, x, y, z, x_len, y_len, z_len):
        island = {}
        is_island = True
        stack = []
        stack.append((x,y,z))
        while len(stack) > 0:
            pos = stack.pop()

            if island.has_key(pos):
                continue
            island[pos] = True


            x, y, z = pos
            if y == 0:
                is_island = False

            for dx, dy, dz in self.sides:
                x0 = x + dx
                y0 = y + dy
                z0 = z + dz
                if x0 >= 0 and \
                   y0 >= 0 and \
                   z0 >= 0 and \
                   x0 < x_len and \
                   y0 < y_len and \
                   z0 < z_len:

                    if self.object_array[x0][y0][z0] > 0:
                        stack.append((x0,y0,z0))
        return island, is_island


    def generate_stl(self):
        """Generate STL file"""
        filename = self.output_name

        width = len(self.object_array)
        try:
            height = len(self.object_array[0])
        except:
            print self.object_array
        depth = len(self.object_array[0][0])

        str_o = "solid Minecraft\n";
        str_e = "    endloop\n  endfacet\n"
        str_s = "  facet normal %d %d %d\n    outer loop\n"
        str_v = "      vertex %d %d %d\n"

        print "start"

        f=open(filename, 'w')
        f.write(str_o)
        for x in range(width):
            print str(x/float(width)*100) + "%"
            for y in range(height):
                for z in range(depth):
                    if self.object_array[x][y][z] > 0:
                        if x==0 or self.object_array[x-1][y][z]<=0:
                            f.write("".join([str_s%(-1,0,0),str_v%(x,z+1,y), str_v%(x,z,y+1),str_v%(x,z+1,y+1),str_e]))
                            f.write("".join([str_s%(-1,0,0),str_v%(x,z+1,y), str_v%(x,z,y),str_v%(x,z,y+1),str_e]))
                        if x==width-1 or self.object_array[x+1][y][z]<=0:
                            f.write("".join([str_s%(1,0,0),str_v%(x+1,z+1,y), str_v%(x+1,z+1,y+1),str_v%(x+1,z,y+1),str_e]))
                            f.write("".join([str_s%(1,0,0),str_v%(x+1,z+1,y), str_v%(x+1,z,y+1),str_v%(x+1,z,y),str_e]))
                        if (z==0) or self.object_array[x][y][z-1]<=0:
                            f.write("".join([str_s%(0,0,-1),str_v%(x,z,y), str_v%(x+1,z,y+1),str_v%(x,z,y+1),str_e]))
                            f.write("".join([str_s%(0,0,-1),str_v%(x,z,y), str_v%(x+1,z,y),str_v%(x+1,z,y+1),str_e]))
                        if (z==depth-1) or self.object_array[x][y][z+1]<=0:
                            f.write("".join([str_s%(0,0,1),str_v%(x,z+1,y), str_v%(x,z+1,y+1),str_v%(x+1,z+1,y+1),str_e]))
                            f.write("".join([str_s%(0,0,1),str_v%(x,z+1,y), str_v%(x+1,z+1,y+1),str_v%(x+1,z+1,y),str_e]))
                        if (y==0) or self.object_array[x][y-1][z]<=0:
                            f.write("".join([str_s%(0,-1,0),str_v%(x+1,z,y), str_v%(x,z+1,y),str_v%(x+1,z+1,y),str_e]))
                            f.write("".join([str_s%(0,-1,0),str_v%(x+1,z,y), str_v%(x,z,y),str_v%(x,z+1,y),str_e]))
                        if (y==height-1) or self.object_array[x][y+1][z]<=0:
                            f.write("".join([str_s%(0,1,0),str_v%(x+1,z,y+1), str_v%(x+1,z+1,y+1),str_v%(x,z+1,y+1),str_e]))
                            f.write("".join([str_s%(0,1,0),str_v%(x+1,z,y+1), str_v%(x,z+1,y+1),str_v%(x,z,y+1),str_e]))

        f.write("endsolid Minecraft\n")
        print "100%"
        f.close()

        print "Done!"
