import argparse
import os
import shutil

parser = argparse.ArgumentParser()
parser.add_argument(
    "--soft",
    action="store_true",
    help="Keep src-tauri/target so cargo incremental builds survive.",
)
args = parser.parse_args()

root = os.path.dirname(os.path.dirname(__file__))
shutil.rmtree(os.path.join(root, "build"), ignore_errors=True)
shutil.rmtree(os.path.join(root, "dist"), ignore_errors=True)
shutil.rmtree(os.path.join(root, "src-tauri", "bin"), ignore_errors=True)
if not args.soft:
    shutil.rmtree(os.path.join(root, "src-tauri", "target"), ignore_errors=True)
