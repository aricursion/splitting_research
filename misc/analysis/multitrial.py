import argparse
import subprocess
import os


def main(temp_dir, log_dir, cnf_file):
    # Ensure the log directory exists
    os.makedirs(log_dir, exist_ok=True)

    # Loop to run the command 20 times
    for i in range(1, 21):
        # Construct the command (fill in the actual command as needed)
        cmd = [
            "python",
            "../../cadical-lit-testing/singlelit_iter_cube_sum.py",
            "--cnf",
            cnf_file,
            "--lit-start",
            str(i * 100000),
            "--cube-size",
            "10",
            "--log",
            str(os.path.join(log_dir, str(i) + ".log")),
            "--cube-procs",
            "20",
            "--solve-procs",
            "8",
            "--batch-size",
            "1000000",
            "--samples",
            "32",
            "--tmp-dir",
            temp_dir,
            "--mode",
            "1",
            "--lit-set-size",
            "32"
        ]
        subprocess.run(cmd)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run a command 20 times and log the output."
    )
    parser.add_argument(
        "--tmp-dir", required=True, help="Path to the temporary directory"
    )
    parser.add_argument("--log-dir", required=True, help="Path to the log directory")
    parser.add_argument(
        "--cnf", required=True, help="Path to the CNF configuration file"
    )

    args = parser.parse_args()

    main(args.temp_dir, args.log_dir, args.cnf_file)
