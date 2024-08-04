from itertools import batched
import sys
import math

icnf_file_loc = sys.argv[1]
num_parts = int(sys.argv[2])

icnf_file = open(icnf_file_loc, "r")
lines = list(icnf_file.readlines())
partitions = batched(lines, math.ceil(len(lines)/num_parts))
prefix = icnf_file_loc.split(".")[0]
for i, partition in enumerate(partitions):
    f = open(prefix + "_" + str(i) + ".icnf", "w")
    for line in partition:
        f.write(line)
    f.close()

