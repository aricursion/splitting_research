"""
find lits along positive spine and hypercube
"""
import util
from concurrent.futures import ProcessPoolExecutor
import argparse
import multiprocessing
import os
import time


def config_to_string(args):
    out = "cnf: {} ".format(args.cnf)
    out += "lit-start: {} ".format(args.lit_start)
    return out


def find_new_lit(args, lit_start, current_cube):
    log_file = open(args.log, "a")
    start = time.time()
    new_cnf_loc = util.add_cube_to_cnf(args.cnf, current_cube)
    new_lit = util.find_lits_to_split(new_cnf_loc, 1, 0, 0, lit_start, False)[0]
    time_taken = time.time() - start

    log_file.write("Time finding cube: {:.2f}\n".format(time_taken))
    current_cube.append(new_lit)
    log_file.flush()
    log_file.close()
    os.remove(new_cnf_loc)
    return current_cube


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cnf", dest="cnf", required=True)
    parser.add_argument("--cube-size", dest="cube_size", type=int, required=True)
    parser.add_argument("--lit-start", dest="lit_start", type=int, default=5000)
    parser.add_argument("--lit-start-dec", dest="lit_start_decrease", type=int, default=0)
    parser.add_argument("--log", dest="log", required=True)
    parser.add_argument("--procs", dest="procs", type=int, default=multiprocessing.cpu_count() - 2)
    args = parser.parse_args()

    util.executor_sat = ProcessPoolExecutor(max_workers=args.procs)
    os.makedirs("tmp", exist_ok=True)
    try:
        os.makedirs(os.path.dirname(args.log), exist_ok=True)
    except Exception:
        pass
    with open(args.log, "a") as f:
        f.write("# cube log\n")
        f.write("# {}\n".format(config_to_string(args)))
        f.close()

    cube = []
    for i in range(args.cube_size):
        cube = find_new_lit(args, args.lit_start - (i * args.lit_start_decrease), cube)
        print(cube)

    util.run_hypercube_from_cube(args.cnf, cube, args.log)
