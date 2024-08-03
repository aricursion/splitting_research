"""
find a lit at level and recurse down tree
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


final_hc = []
exectuor_rec = ProcessPoolExecutor(max_workers=6)

def find_cube(args, depth, current_cube):
    log_file = open(args.log, "a")
    start = time.time()
    new_cnf_loc = util.add_cube_to_cnf(args.cnf, current_cube)
    try:
        new_lit = util.find_lits_to_split(
            new_cnf_loc, 1, 0, 0, args.lit_start - args.lit_start_dec * (depth - 1), False
        )[0]
    except Exception:
        final_hc.append(current_cube)
        return

    time_taken = time.time() - start

    log_file.write("Time finding cube: {:.2f}\n".format(time_taken))
    log_file.flush()
    log_file.close()
    os.remove(new_cnf_loc)
    if depth < args.cube_size:
        find_cube(args, depth + 1, current_cube + [new_lit])
        find_cube(args, depth + 1, current_cube + [-new_lit])
        # p1 = util.executor_sat.submit(find_cube, args, depth + 1, current_cube + [new_lit])
        # p2 = util.executor_sat.submit(find_cube, args, depth + 1, current_cube + [-new_lit])
        # print(p1.result().stdout.decode("utf-8"))
        # print(p2.result().stdout.decode("utf-8"))
    else:
        final_hc.append(current_cube + [new_lit])
        final_hc.append(current_cube + [-new_lit])

def find_cube_par(args):
    result = []
    stack = [[]]
    log_file = open(args.log, "a")
    while stack != []:
        procs = []
        while stack != []:
            current_cube = stack.pop()
            cnf = util.add_cube_to_cnf(args.cnf, current_cube)
            proc = util.executor_sat.submit(util.run_cadical_lits, cnf, 1, 0, 0, args.lit_start, False)
            procs.append((proc, current_cube, cnf))
        for proc, cc, cnf in procs:
            output = proc.result().stdout.decode("utf-8").strip()
            if "SATISFIABLE" in output:
                result.append(cc)
                os.remove(cnf)
                continue
            else:
                lit_line = util.parse_lit_line_ext(output)
                split_lit = lit_line.lit
                time = lit_line.runtime

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
    return result

        



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cnf", dest="cnf", required=True)
    parser.add_argument("--cube-size", dest="cube_size", type=int, required=True)
    parser.add_argument("--lit-start", dest="lit_start", type=int, default=100000)
    parser.add_argument("--lit-start-dec", dest="lit_start_dec", type=int, default=0)
    parser.add_argument("--log", dest="log", required=True)
    parser.add_argument("--cube-procs", dest="cube_procs", type=int, default=multiprocessing.cpu_count() - 2)
    parser.add_argument("--solve-procs", dest="solve_procs", type=int, default=multiprocessing.cpu_count() - 2)
    args = parser.parse_args()

    util.executor_sat = ProcessPoolExecutor(max_workers=args.cube_procs)
    os.makedirs("tmp", exist_ok=True)
    try:
        os.makedirs(os.path.dirname(args.log), exist_ok=True)
    except Exception:
        pass

    util.executor_sat = ProcessPoolExecutor(max_workers=args.solve_procs)
    # find_cube(args, 1, [])
    final_hc = find_cube_par(args)
    with open(args.log, "a") as f:
        f.write("# cube log\n")
        f.write("# {}\n".format(config_to_string(args)))
        for cube in final_hc:
            f.write("cube: " + ",".join(map(str, cube)) + "\n")
        f.close()
    print(final_hc)
    util.run_hypercube(args.cnf, final_hc, args.log)
