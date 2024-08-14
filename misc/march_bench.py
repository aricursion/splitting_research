import argparse
from concurrent.futures import ProcessPoolExecutor
import subprocess
import resource
import sys
import os
sys.path.append("../cadical-lit-testing")
import util 

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cnf", dest="cnf",required=True)
    parser.add_argument("--icnf", dest="icnf", default=None)
    parser.add_argument("--depth", dest="depth",default=None, type=int)
    parser.add_argument("--tmp-dir", dest="tmp_dir", required=True)
    parser.add_argument("--procs", type=int, required=True)
    parser.add_argument("--log", required=True)
    args = parser.parse_args()

    util.executor_sat = ProcessPoolExecutor(max_workers=args.procs)
    if args.icnf == None:
        icnf = "/tmp/cubes.icnf"
    else:
        icnf = args.icnf
    cmd = ["march", args.cnf, "-o", icnf]
    if args.depth != None:
        cmd.append("-d")
        cmd.append(str(args.depth))
    usage_start = resource.getrusage(resource.RUSAGE_CHILDREN)
    subprocess.run(cmd)
    usage_end = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu_time = usage_end.ru_utime - usage_start.ru_utime
    log_file = open(args.log, "w")
    log_file.write("cubing time {:2f}\n".format(cpu_time))
    
    icnf_file = open(icnf, "r")
    hc = []
    for line in icnf_file.readlines():
        cube = list(map(int, line[2:].strip().split(" ")[:-1]))
        hc.append(cube)

    util.run_hypercube(args.cnf, hc, args.log,tmp=args.tmp_dir)

    if args.icnf == None:
        os.remove(icnf)



