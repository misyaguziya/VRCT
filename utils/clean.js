import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

// --soft: src-tauri/target を残して cargo の差分ビルドを活かす
const soft = process.argv.includes("--soft");

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const targets = ["build", "dist", path.join("src-tauri", "bin")];
if (!soft) targets.push(path.join("src-tauri", "target"));

for (const t of targets) {
    fs.rmSync(path.join(root, t), { recursive: true, force: true });
}
