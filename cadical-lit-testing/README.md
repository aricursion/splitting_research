## singlelit_tree.py
Uses `cadical-lits` to find a list of potential splitting variables.
Runs all of these to completion, and picks the one with the least sum learned clauses.
Rinse and repeat.

## sinlelit_iter_cube.py
Uses `cadical-lits` to find a single variable.
Appends this variable to a list along the positive branch, and iterates this process to find a list.
Then hypercubes this list for a full cubing.

## singlelit_iter_cube_recursive.py
Uses `cadical-lits` to find a single variable.
Then, along both branches, find a single variable.
Rinse and repeat until a desired cube depth.


## util.py
Just a bunch of small utility functions.
