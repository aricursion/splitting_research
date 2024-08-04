"""
python3 inccnf_to_icnf.py <in_file> <out_file>
"""

import sys 
infile = open(sys.argv[1], "r")
outfile = open(sys.argv[2], "w")

for line in infile.readlines():
    if line[0:2] == "a ":
        outfile.write(line)
