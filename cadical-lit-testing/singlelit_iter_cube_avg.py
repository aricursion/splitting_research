"""
tree, but partition layers and take samples, find best literal, and use for the partition
"""
import util
import random
from concurrent.futures import ProcessPoolExecutor
import argparse
import itertools
import multiprocessing
import os


def config_to_string(args):
    out = "cnf: {} ".format(args.cnf)
    out += "lit-start: {} ".format(args.lit_start)
    return out


final_hc = []
exectuor_rec = ProcessPoolExecutor(max_workers=6)

def find_cube_par(args):
    result = []
    todo = [[]]
    log_file = open(args.log, "a")
    while todo != []:
        procs = []
        batches = list(itertools.batched(todo, args.batch_size))
        for i, batch in enumerate(batches):
            if len(batch) >= args.num_samples:
                samples = random.sample(batch, args.num_samples)
            else:
                samples = batch
            for sample in samples:
                cnf = util.add_cube_to_cnf(args.cnf, sample)
                proc = util.executor_sat.submit(util.run_cadical_lits, cnf, 1, 0, 0, args.lit_start, False)
                procs.append((proc, sample, i))
        batch_data = {}
        for (proc, cc, i) in procs:
            output = proc.result().stdout.decode("utf-8").strip()
            lit_line = util.parse_lit_line_ext(output)
            if i in batch_data:
                batch_data[i] = batch_data[i] + [(cc, lit_line)]
            else:
                batch_data[i] = [(cc, lit_line)]
        todo = []
        print(batch_data)
        for (i, batch_data_list) in batch_data.items():
            split_lit = -1
            best_props = 999999999999
            for sample, lit_line in batch_data_list:
                if lit_line.props < best_props:
                    split_lit = lit_line.lit 
                    best_props = lit_line.props

            for cc in batches[i]:
                if len(cc) + 1 < args.cube_size:
                    todo.append(cc + [split_lit])
                    todo.append(cc + [-split_lit])
                else:
                    result.append(cc + [split_lit])
                    result.append(cc + [-split_lit])
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
    parser.add_argument("--batch-size", dest="batch_size", type=int, default=1)
    parser.add_argument("--samples", dest="num_samples", type=int, default=8)
    parser.add_argument("--icnf", dest="icnf", type=str, default=None)
    parser.add_argument("--cube-only", action=argparse.BooleanOptionalAction, default=False)
    args = parser.parse_args()

    util.executor_sat = ProcessPoolExecutor(max_workers=args.cube_procs)
    os.makedirs("tmp", exist_ok=True)
    try:
        os.makedirs(os.path.dirname(args.log), exist_ok=True)
    except Exception:
        pass

    util.executor_sat = ProcessPoolExecutor(max_workers=args.solve_procs)
    with open(args.log, "a") as f:
        f.write("# cube log\n")
        f.write("# {}\n".format(config_to_string(args)))
        f.close()

    final_hc = find_cube_par(args)
    if args.icnf != None:
        with open(args.icnf, "a") as f:
            for cube in final_hc:
                f.write("a " + " ".join(map(str, cube)) + "\n")
    print(final_hc)
    if not args.cube_only:
        util.run_hypercube(args.cnf, final_hc, args.log)
