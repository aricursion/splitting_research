import sys
from concurrent.futures import ProcessPoolExecutor
import subprocess
import os

def run_cadical(cnf_loc, log_dir):
    log_name = cnf_loc.split(".")[0] + ".log"
    f = open(os.path.join(log_dir, log_name), "w")
    return subprocess.run(["cadical", cnf_loc], stdout=f, stderr=f)


if __name__ == "__main__":
    procs = int(sys.argv[3])

    executor = ProcessPoolExecutor(max_workers=int(sys.argv[3])) 
    cnf_dir = sys.argv[1]
    log_dir = sys.argv[2]

    procs = []
    for filename in os.listdir(cnf_dir):
        file = os.path.join(cnf_dir, filename)
        proc = executor.submit(run_cadical, file, log_dir)
        procs.append(proc)

    for proc in procs:
        print(proc.result())
