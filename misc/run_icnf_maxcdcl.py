"""
python3 run_icnf_maxcdcl <base_cnf> <icnf_file> <tmp_dir> <log_dir> <num_processes>
"""
import sys
from concurrent.futures import ProcessPoolExecutor
import subprocess
import os
from time import sleep

def add_cube_to_cnf(base_wcnf, cube, tmp_dir, tag):
    base = open(base_wcnf, "r")
    lines = list(base.readlines())
    header = lines[0].split(" ")
    hard_weight = int(header[4])
    header[3] = str(int(header[3]) + len(cube))

    lines[0] = " ".join(header)
    out = "".join(lines)

    for lit in cube:
        out += f"{hard_weight} {lit} 0\n"

    f = open(f"{tmp_dir}/{tag}.wcnf", "w+")
    f.write(out)
    f.close()
    return f"{tmp_dir}/{tag}.wcnf"


def run_maxcdcl(cnf_loc, cube, tmp_dir, log_dir):
    log_file_prefix = "_".join(map(str, cube)).replace("-", "n")
    new_cnf = add_cube_to_cnf(cnf_loc, cube, tmp_dir, log_file_prefix)
    log_file = open(os.path.join(log_dir, log_file_prefix + ".log"), "a")
    error_file = open(os.path.join(log_dir, "error.txt"), "a")
    success_file = open(os.path.join(log_dir, "success.txt"), "a")
    timeout_file = open(os.path.join(log_dir, "timeout.txt"), "a")
    try:
        p = subprocess.run(["maxcdcl", new_cnf], stdout=log_file, timeout=18000)
        while (p.returncode < 0):
            error_file.write(log_file_prefix + " " + str(p.returncode) +"\n")
            p = subprocess.run(["maxcdcl", new_cnf], stdout=log_file, timeout=18000)
        success_file.write(log_file_prefix + "\n")

    except subprocess.TimeoutExpired:
        p = "TIMEOUT"
        timeout_file.write(log_file_prefix + "\n")
    os.remove(new_cnf)
    error_file.close()
    log_file.close()
    success_file.close()
    timeout_file.close()


if __name__ == "__main__":
    if len(sys.argv) != 6:
        exit(1)
    base_cnf = sys.argv[1]
    icnf_file = open(sys.argv[2], "r")
    tmp_dir = sys.argv[3]
    log_dir = sys.argv[4]
    procs = int(sys.argv[5])

    executor = ProcessPoolExecutor(max_workers=procs) 

    procs = []
    for line in icnf_file.readlines():
        cube = list(map(int, line[2:].strip().split(" ")[:-1]))
        proc = executor.submit(run_maxcdcl, base_cnf, cube, tmp_dir, log_dir)
        procs.append(proc)

    for proc in procs:
        print(proc.result())
