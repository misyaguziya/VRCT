import zipfile
import argparse
from pathlib import Path
import time
from tqdm import tqdm # tqdmをインポート

def zip_files_and_directory(zip_name, file_paths, dir_paths, verbose=False):
    zip_file_path = Path(zip_name)
    # ZIPファイルを作成
    try:
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # ファイルを追加
            for file_path_str in tqdm(file_paths, desc="Adding files", unit="file"):
                file_path = Path(file_path_str)
                if file_path.is_file():
                    zipf.write(file_path, file_path.name)
                    if verbose:
                        print(f"Add file: {file_path}")
                else:
                    print(f"Warning: File not found or is not a file: {file_path}")

            # ディレクトリを追加
            for dir_path_str in dir_paths:
                dir_path = Path(dir_path_str)
                if dir_path.is_dir():
                    all_files_in_dir = [item for item in dir_path.rglob("*") if item.is_file()]
                    for item in tqdm(all_files_in_dir, desc=f"Adding files from {dir_path.name}", unit="file"):
                        # ディレクトリ構造を保持しつつ、ルートに配置
                        arcname = Path(dir_path.name) / item.relative_to(dir_path)
                        zipf.write(item, arcname)
                        if verbose:
                            print(f"Add file: {item}")
                else:
                    print(f"Warning: Directory not found or is not a directory: {dir_path}")
        print(f"Successfully created zip file: {zip_file_path}")
    except IOError as e:
        print(f"Error: Could not create zip file {zip_file_path}. Reason: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    start_time = time.time()
    parser = argparse.ArgumentParser(description="Create a zip file from specified files and directories.")
    parser.add_argument("--zip_name", type=str, default="VRCT.zip", help="Name of the output zip file.")
    parser.add_argument(
        "--file_paths",
        type=str,
        nargs="*",
        default=["src-tauri/target/release/VRCT.exe", "src-tauri/target/release/VRCT-sidecar.exe"],
        help="List of file paths to include in the zip."
    )
    parser.add_argument(
        "--dir_paths",
        type=str,
        nargs="*",
        default=["src-tauri/target/release/_internal"],
        help="List of directory paths to include in the zip."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Increase output verbosity."
    )
    args = parser.parse_args()

    zip_files_and_directory(args.zip_name, args.file_paths, args.dir_paths, args.verbose)
    end_time = time.time()
    processing_time = end_time - start_time
    print(f"Complete! Processing time: {processing_time:.2f} seconds")