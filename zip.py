import os
import zipfile
import argparse

def zip_files_and_directory(zip_name, file_paths, dir_paths):
    # ZIPファイルを作成
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # ファイルを追加
        for file_path in file_paths:
            if os.path.isfile(file_path):
                zipf.write(file_path, os.path.basename(file_path))
                print(f"Add file: {file_path}")

        # ディレクトリを追加
        for dir_path in dir_paths:
            if os.path.isdir(dir_path):
                for foldername, subfolders, filenames in os.walk(dir_path):
                    for filename in filenames:
                        file_full_path = os.path.join(foldername, filename)
                        # ディレクトリを保持しつつ、ルートに配置
                        arcname = os.path.join(
                            os.path.basename(dir_path),
                            os.path.relpath(file_full_path, dir_path)
                        )
                        zipf.write(file_full_path, arcname)
                        print(f"Add file: {file_full_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip_name", type=str, default="VRCT.zip")
    parser.add_argument("--file_paths", type=str, nargs="*", default=["src-tauri/target/release/VRCT.exe", "src-tauri/target/release/VRCT-sidecar.exe"])
    parser.add_argument("--dir_paths", type=str, nargs="*", default=["src-tauri/target/release/_internal"])
    args = parser.parse_args()

    zip_files_and_directory(args.zip_name, args.file_paths, args.dir_paths)
    print("Complete!")