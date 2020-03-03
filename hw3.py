import math
import time
import threading

import random
from colors import COLORS

import numpy as np

try:
    # for Python2
    from Tkinter import *   ## notice capitalized T in Tkinter 
except ImportError:
    # for Python3
    from tkinter import *   ## notice lowercase 't' in tkinter here
import os

## Takes in a filename and return the created grid and list of routes to be wired
def parseFile(filename):
    with open(filename) as f:
        ## Get general problem information
        info = f.readline().split(' ')
        numcells = int(info[0])
        numconn = int(info[1])
        numrows = int(info[2])
        numcols = int(info[3])

        ## return the info on the sinks
        content = f.readlines()
        data = [x.strip() for x in content]
        nets = []
        for net in data:
            ## skip over empty rows
            if net == '':
                continue
            nets.append(list(map(lambda x: int(x), net.split(' '))))
        return nets, numcells, numconn, numrows, numcols

## Takes in a coordinate, color, and the existing canvas to draw a color in the grid
def drawcell(i, j, color, c):
    c.create_rectangle(sizex*i,sizey*j,sizex*(i+1),sizey*(j+1), fill=color)

## Draw a line between two coordinates
def drawline(i1, j1, i2, j2, c):
    x1 = sizey * (2 * i1 + 1) / 2
    x2 = sizey * (2 * i2 + 1) / 2
    y1 = sizex * (2 * j1 + 1) / 2
    y2 = sizex * (2 * j2 + 1) / 2
    print(x1, x2, y1, y2)
    c.create_line(x1, y1, x2, y2, fill='black')

## draw the updated grid colors
def updategrid(grid, c):
    for i in range(len(grid)):
        for j in range(len(grid[0])):
            value = grid[i][j]
            colorid = value % len(COLORS)
            if colorid == 0 and value > len(COLORS):
                colorid += 1
            drawcell(i, j, COLORS[colorid], c)

def indexToCoord(grid, index):
    return [index % len(grid), int(index / len(grid))]

## draw final graphics from partition results
def drawresults(grid, partition, c):
    ## for partition 0, draw start from the first index in 2d grid, 
    ## partition 1, draw starting from last index
    part1ind = 0
    part2ind = len(grid) * len(grid[0]) - 1
    for key in partition:
        coord = None
        if partition[key] == 0:
            coord = indexToCoord(grid, part1ind)
        else:
            coord = indexToCoord(grid, part2ind)
        grid[coord[0]][coord[1]] = key

    ## Draw out the final partitioning results
    updategrid(grid, c)

def cutsize(conn, partition):
    cutsize = 0
    for key in conn:
        for i in range(len(conn[key])): ## see if in same partition
            if partition[key] != partition[conn[key][i]]:
                cutsize += 0.5 ## gets counted both ways so 0.5 to add up to 1 crossing for cutsize
    return cutsize

## K&L algorithm
## Partition: {"3": "0", "2", "1"} 
## Gain: {"3": 1, "4": 5, "2": 1}
## -> block 3 is in first group, 2 in second
def computeCrossings(conn, partition):
    same = 0
    diff = 0
    gain = {}
    for key in conn:
        for i in range(len(conn[key])): ## see if in same partition
            if partition[key] == partition[conn[key][i]]:
                same += 1
            else:
                diff += 1
        gain[key] = diff - same
    return gain

## Compute number of nets that crosses over partition boundary
def numNetsCrossing(nets, partition):
    numNets = 0
    for i in range(len(nets)):
        first = nets[i][1]
        for j in range(2, len(nets[i])):
            if partition[nets[i][j]] != partition[first]:
                numNets += 1
                break
    return numNets

import copy 
def parseConn(nets):
    conn = {}
    for i in range(len(nets)):
        cpy = copy.deepcopy(nets[i])
        cpy.pop(0)
        first = cpy.pop(0)
        if first not in conn:
            conn[first] = []
        conn[first].extend(cpy[:])

        for j in range(len(cpy)):
            if cpy[j] not in conn:
                conn[cpy[j]] = []
            conn[cpy[j]].append(first)
    return conn

## conn -> key and value list of connected blocks
def KL(grid, conn, numcells, c):
    ## initially assign half half to the two partitions
    counts = [0, 0] ## amount in first partition and second partition
    partition = {}
    gain = {}

    ## assign half half
    for key in conn:
        partnum = (counts[0] + counts[1]) % 2 
        partition[key] = partnum
        counts[partnum] += 1

    ## Check current cutsize
    bestState = copy.deepcopy(partition)
    bestcutsize = cutsize(conn, partition)

    ## Store best min net solution for final answer
    mincross_cutsize = bestcutsize
    bestcrossState = copy.deepcopy(partition)
    bestmincross = numNetsCrossing(nets, partition)

    ## Do up to 6 K & L cycles at limit
    for i in range(6):
        locked = set() ## clear the lock, go to the best cutsize
        partition = bestState

        while True:
            ## compute gain
            oldgain = computeCrossings(conn, partition)
            gain = {}
            ## an addition to the gain function
            ## add in average gain values after swap
            for key in oldgain:
                ## perform fake swap and compute new gains 
                # cpypart = copy.deepcopy(partition)
                partition[key] = 1 - partition[key]
                newgain = computeCrossings(conn, partition)
                partition[key] = 1 - partition[key]

                ## compute net gain change for this swap
                change = 0
                for key2 in newgain:
                    change += (oldgain[key] - newgain[key2])
                gain[key] = change

            ## choose max gain that still forms valid partition swap
            ## if count[0] == count[1], can pick either
            ## if count[0] > count[1], need to pick count[0]
            ## else pick count[1]
            maxgain = -1
            unset = True
            if counts[0] == counts[1]:
                for key in gain:
                    if key in locked:
                        continue
                    if unset or gain[key] > gain[maxgain]: 
                        maxgain = key 
                        unset = False
            elif counts[0] > counts[1]:
                for key in gain:
                    if key not in locked and partition[key] % 2 == 0:
                        if unset or gain[key] > gain[maxgain]: 
                            maxgain = key 
                            unset = False
            else:
                for key in gain:
                    if key not in locked and partition[key] % 2 == 1:
                        if unset or gain[key] > gain[maxgain]: 
                            maxgain = key 
                            unset = False
            ## Could not find a possible swap
            if unset:
                break

            ## use this to make a move swap and lock the key
            locked.add(maxgain)
            counts[partition[maxgain]] -= 1
            counts[1 - partition[maxgain]] += 1
            partition[maxgain] = 1 - partition[maxgain]

            ## Store better cutsize if exist
            currcutsize = cutsize(conn ,partition)
            currmincross = numNetsCrossing(nets, partition)
            print("Best Cutsize:", bestcutsize, "Best Min Cross:", bestmincross, "Curr Cutsize:", currcutsize)

            if currcutsize < bestcutsize:
                bestState = copy.copy(partition)
                bestcutsize = currcutsize
            if currmincross < bestmincross:
                bestcrossState = copy.copy(partition)
                bestmincross = currmincross
                mincross_cutsize = currcutsize
            ## Terminate K&L iteration as all are locked
            print("NumCells:", numcells, "NumLocked:", len(locked))
            if len(locked) == numcells:
                break
            # print("Num Cross:", currmincross)
        print("Final cutsize:", mincross_cutsize, "Final min net crossings:", bestmincross)

    ## Draw final location
    drawresults(grid, partition, c)


## Main function
if __name__== "__main__":
    filename = sys.argv[1]

    nets, numcells, numconn, numrows, numcols = parseFile("./ass2_files/"+filename+".txt")
    conn = parseConn(nets)
    root = Tk()

    grid = [[0 for x in range(numcols)] for y in range(numrows)]
    sizex = 1000/numcols
    sizey = 500/numrows
    locations = [0] * (numcells)

    # KL(conn, numcells)
    # # set up white grids
    frame = Frame(root, width=1000, height=1000)
    frame.pack()
    c = Canvas(frame, bg='white', width=1000, height=1000)
    c.focus_set()
    c.pack()

    # Run algorithm in background via a thread
    updategrid(grid, c)

    thread = threading.Thread(target = KL, args = (grid, conn, numcells, c))
    thread.start()

    root.mainloop()


