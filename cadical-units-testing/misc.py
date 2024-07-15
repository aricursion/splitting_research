from concurrent.futures import ProcessPoolExecutor
import util
import sys

util.executor_sat = ProcessPoolExecutor(10)

hc = util.generate_hypercube([395, 424, 366, 504, 281])
util.run_hypercube(sys.argv[1], hc, sys.argv[2])