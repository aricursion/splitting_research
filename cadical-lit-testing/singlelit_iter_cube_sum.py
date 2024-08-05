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
    out += "batch-size: {} ".format(args.batch_size)
    out += "samples: {} ".format(args.num_samples)
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
                proc = util.executor_sat.submit(util.run_cadical_litset, cnf, 1, args.lit_start, args.lit_set_size)
                procs.append((proc, sample, cnf, i))
        batch_data = {}
        for (proc, cc, cnf, i) in procs:
            output = proc.result().stdout.decode("utf-8").strip()
            os.remove(cnf)
            lit_count_dict = util.parse_lit_set(output)
            if i in batch_data:
                batch_data[i] = batch_data[i] + [(cc, lit_count_dict)]
            else:
                batch_data[i] = [(cc, lit_count_dict)]
        todo = []
        print(batch_data)
        for (i, batch_data_list) in batch_data.items():
            split_lit = -1
            combined_dict = {}
            for sample, lit_count_dict in batch_data_list:
                for (k, v) in lit_count_dict.items():
                    if k not in combined_dict:
                        combined_dict[k] = v
                    else:
                        combined_dict[k] = combined_dict[k] + v
            split_lit = max(combined_dict, key=combined_dict.get)
            print(split_lit)

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
    parser.add_argument("--lit-set-size", dest="lit_set_size", type=int, default=5)
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
        util.make_icnf(final_hc, args.icnf)
    print(final_hc)
    if not args.cube_only:
        util.run_hypercube(args.cnf, final_hc, args.log)
