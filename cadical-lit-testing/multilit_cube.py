import util
import numpy as np
from concurrent.futures import ProcessPoolExecutor
import argparse
import multiprocessing
import os
import time


def config_to_string(args):
    out = "cnf: {} ".format(args.cnf)
    out += "lit-gap: {} ".format(args.lit_gap)
    out += "lit-gap-grow: {} ".format(args.lit_gap_grow)
    out += "lit-start: {} ".format(args.lit_start)
    return out


def find_hypercube(args):
    log_file = open(args.log, "a")
    start = time.time()
    cube_lits = util.find_lits_to_split(args.cnf, args.cube_size, args.lit_gap, args.lit_gap_grow, args.lit_start)
    time_taken = time.time() - start

    log_file.write("Time finding cube: {:.2f}\n".format(time_taken))
    hypercube = util.generate_hypercube(cube_lits)
    procs = []
    times = []
    for cube in hypercube:
        new_cnf_loc = util.add_cube_to_cnf(args.cnf, cube)
        proc = util.executor_sat.submit(util.run_cadical, new_cnf_loc, 999999)
        procs.append((proc, cube))
    for proc, cube in procs:
        try:
            output = str(proc.result().stdout.decode("utf-8")).strip()
            cadical_result = util.cadical_parse_results(output)
        except Exception:
            cadical_result = util.CadicalResult(8888, 8888, 8888)

        log_file.write(
            ",".join(list(map(str, cube)))
            + " time: {}, learned: {}, props: {}\n".format(
                cadical_result.time, cadical_result.learned, cadical_result.props
            )
        )
        times.append(cadical_result.time)
        log_file.flush()

    log_file.write("Cube sum time: {:.2f}\n".format(sum(times)))
    m = sum(times) / len(times)
    log_file.write("Avg cube time: {:.2f}\n".format(m))
    log_file.write("StdDev cube time: {:.2f}\n".format(np.std(times)))
    log_file.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cnf", dest="cnf", required=True)
    parser.add_argument("--cube-size", dest="cube_size", type=int, required=True)
    parser.add_argument("--lit-gap", dest="lit_gap", type=int, default=100)
    parser.add_argument("--lit-gapgrow", dest="lit_gap_grow", type=int, default=1)
    parser.add_argument("--lit-start", dest="lit_start", type=int, default=5000)
    parser.add_argument("--log", dest="log", required=True)
    parser.add_argument("--procs", dest="procs", type=int, default=multiprocessing.cpu_count() - 2)
    args = parser.parse_args()

    util.executor_sat = ProcessPoolExecutor(max_workers=args.procs)
    os.makedirs("tmp", exist_ok=True)
    os.makedirs(os.path.dirname(args.log), exist_ok=True)
    with open(args.log, "a") as f:
        f.write("# cube log\n")
        f.write("# {}\n".format(config_to_string(args)))
        f.close()

    find_hypercube(args)
