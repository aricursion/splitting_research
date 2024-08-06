"""
python3 run_icnf_cadical.py <cnf> <icnf> <log> <tmp_dir> <procs>
"""
import sys
sys.path.append("../cadical-lit-testing")
import util 
from concurrent.futures import ProcessPoolExecutor

util.executor_sat = ProcessPoolExecutor(max_workers=int(sys.argv[5])) 
hc = []
f = open(sys.argv[2], "r")
for line in f.readlines():
    cube = list(map(int, line[2:].strip().split(" ")[:-1]))
    hc.append(cube)

util.run_hypercube(sys.argv[1], hc, sys.argv[3], tmp=sys.argv[4])

