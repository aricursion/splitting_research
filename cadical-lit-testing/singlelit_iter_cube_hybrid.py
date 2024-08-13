"""
find a lit at level and recurse down tree
"""

import util
from concurrent.futures import ProcessPoolExecutor
import argparse
import multiprocessing
import os


def config_to_string(args):
    out = "cnf: {} ".format(args.cnf)
    out += "cutoff: {} ".format(args.cutoff)
    return out


def find_cube_par(args):
    result = []
    stack = [[]]
    log_file = open(args.log, "a")
    cubing_times = []
    depth = 0
    while stack != []:
        depth += 1
        procs = []
        if depth > args.static_depth:
            pass
        else:
            while stack != []:
                current_cube = stack.pop()
                cnf = util.add_cube_to_cnf(args.cnf, current_cube, tmp=args.tmp_dir)
                proc = util.executor_sat.submit(
                    util.run_cadical_lits, cnf, 1, 0, 0, args.cutoff, False
                )
                procs.append((proc, current_cube, cnf))
        for proc, cc, cnf in procs:
            output = proc.result().stdout.decode("utf-8").strip()
            if "SATISFIABLE" in output:
                # TODO: unreachable at the moment
                result.append(cc)
                os.remove(cnf)
                continue
            else:
                lit_line = util.parse_lit_line_ext(output)
                split_lit = lit_line.lit
                time = lit_line.runtime
                cubing_times.append(time)

                log_file.write("Time finding lit: {:2f}\n".format(time))
                log_file.flush()
                if len(cc) + 1 < args.cube_size:
                    stack.append(cc + [split_lit])
                    stack.append(cc + [-split_lit])
                else:
                    result.append(cc + [split_lit])
                    result.append(cc + [-split_lit])
            os.remove(cnf)
    log_file.close()
    return (result, cubing_times)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cnf", dest="cnf", required=True)
    parser.add_argument("--cube-size", dest="cube_size", type=int, required=True)
    parser.add_argument("--cutoff", dest="cutoff", type=int, required=True)
    parser.add_argument("--log", dest="log", required=True)
    parser.add_argument("--icnf", dest="icnf", default=None)
    parser.add_argument("--tmp-dir", dest="tmp_dir", default="tmp")
    parser.add_argument(
        "--cube-procs",
        dest="cube_procs",
        type=int,
        default=multiprocessing.cpu_count() - 2,
    )
    parser.add_argument(
        "--solve-procs",
        dest="solve_procs",
        type=int,
        default=multiprocessing.cpu_count() - 2,
    )
    parser.add_argument(
        "--cube-only",
        dest="cube_only",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    parser.add_argument("--static-depth", dest="static_depth", type=int, required=True)
    args = parser.parse_args()

    util.executor_sat = ProcessPoolExecutor(max_workers=args.cube_procs)
    os.makedirs(args.tmp_dir, exist_ok=True)
    os.makedirs(os.path.dirname(args.log), exist_ok=True)

    util.executor_sat = ProcessPoolExecutor(max_workers=args.solve_procs)
    final_hc, cubing_times = find_cube_par(args)
    with open(args.log, "a") as f:
        f.write("c {}\n".format(config_to_string(args)))
        f.write("c cubing stats\n")
        f.write("c sum time: {}\n".format(sum(cubing_times)))
        f.write("c max time: {}\n".format(max(cubing_times)))
        f.write("c avg time: {}\n".format(sum(cubing_times) / len(cubing_times)))
        f.close()
    if args.icnf != None:
        util.make_icnf(final_hc, args.icnf)
    if not args.cube_only:
        util.run_hypercube(args.cnf, final_hc, args.log, tmp=args.tmp_dir)
