#!/usr/bin/env node
// 使用例: node map-stack.js
// カレントディレクトリの error.txt を読み込み、各エラーフレームから
// 対応するソースマップ（dist/assets/ 以下の *.js.map）を用いて元の位置情報を出力する

import fs from "fs";
import path from "path";
import { SourceMapConsumer } from "source-map";

// 各スタックフレームにマッチする正規表現
const FRAME_REGEX = /^\s*at\s+(.*?)\s+\((.*):(\d+):(\d+)\)$/;

// スタックトレースのパース関数
const parseStackTrace = (text) => {
    return text
        .split(/\r?\n/)
        .map((line) => {
            const match = line.match(FRAME_REGEX);
            if (match) {
                return {
                    original: line,
                    functionName: match[1],
                    file: match[2],
                    line: Number(match[3]),
                    column: Number(match[4])
                };
            } else {
                return { original: line };
            }
        });
};

// エラースタックをソースマップから逆引きする関数（位置情報のみを表示）
const mapStackTrace = async () => {
    const errorTxtPath = path.resolve(process.cwd(), "error.txt");
    const stackTraceText = fs.readFileSync(errorTxtPath, "utf8");
    const frames = parseStackTrace(stackTraceText);

    const consumerMap = new Map();

    const mappedFrames = await Promise.all(frames.map(async (frame) => {
        if (frame.file && frame.line && frame.column) {
            const relativeFile = frame.file.replace(/^\//, ""); // 例: "assets/main-Td8-sruo.js"
            const mapFilePath = path.resolve(process.cwd(), "dist", relativeFile + ".map");
            let consumer = consumerMap.get(mapFilePath);
            if (!consumer) {
                const rawSourceMap = fs.readFileSync(mapFilePath, "utf8");
                consumer = await new SourceMapConsumer(rawSourceMap);
                consumerMap.set(mapFilePath, consumer);
            }
            const pos = consumer.originalPositionFor({
                line: frame.line,
                column: frame.column
            });

            if (pos && pos.source && pos.line != null && pos.column != null) {
                return `    at ${frame.functionName} (${pos.source}:${pos.line}:${pos.column})`;
            } else {
                return frame.original;
            }
        } else {
            return frame.original;
        }
    }));

    consumerMap.forEach((consumer) => consumer.destroy());
    return mappedFrames.join("\n");
};

mapStackTrace()
    .then((mapped) => {
        console.log("--- Mapped Stack Trace ---");
        console.log(mapped);
    })
    .catch((err) => {
        console.error(err);
        process.exit(1);
    });
