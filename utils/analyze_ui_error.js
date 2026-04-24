import fs from "fs";
import path from "path";
import { SourceMapConsumer } from "source-map";

const FRAME_REGEX = /^\s*at\s+(.*?)\s+\((.*):(\d+):(\d+)\)$/;

const parseStackTrace = (text) => {
    return text.split(/\r?\n/).map((line) => {
        const match = line.match(FRAME_REGEX);
        if (match) {
            return {
                original: line,
                functionName: match[1],
                file: match[2],
                line: Number(match[3]),
                column: Number(match[4])
            };
        }
        return { original: line };
    });
};

const mapStackTrace = async () => {
    const errorTxtPath = path.resolve(process.cwd(), "error.txt");
    if (!fs.existsSync(errorTxtPath)) {
        console.error("error.txt not found in project root.");
        process.exit(1);
    }

    const stackTraceText = fs.readFileSync(errorTxtPath, "utf8");
    const frames = parseStackTrace(stackTraceText);
    const consumerMap = new Map();

    const mappedFrames = await Promise.all(frames.map(async (frame) => {
        if (frame.file && frame.line && frame.column) {
            const relativeFile = frame.file.replace(/^\//, "");
            let mapFilePath = path.resolve(process.cwd(), "dist", relativeFile + ".map");

            if (!fs.existsSync(mapFilePath)) {
                const dir = path.dirname(relativeFile);
                const base = path.basename(relativeFile);
                const match = base.match(/^(.*?)-[a-zA-Z0-9_-]+\.js$/);

                if (match) {
                    const prefix = match[1];
                    const dirPath = path.resolve(process.cwd(), "dist", dir);
                    if (fs.existsSync(dirPath)) {
                        const files = fs.readdirSync(dirPath).filter(f => f.startsWith(`${prefix}-`) && f.endsWith(".js.map"));
                        if (files.length > 0) mapFilePath = path.resolve(dirPath, files[0]);
                    }
                }
            }

            let consumer = consumerMap.get(mapFilePath);
            if (!consumer) {
                if (!fs.existsSync(mapFilePath)) return frame.original;
                const rawSourceMap = fs.readFileSync(mapFilePath, "utf8");
                consumer = await new SourceMapConsumer(rawSourceMap);
                consumerMap.set(mapFilePath, consumer);
            }

            const pos = consumer.originalPositionFor({ line: frame.line, column: frame.column });
            return (pos && pos.source && pos.line != null)
                ? `    at ${frame.functionName} (${pos.source}:${pos.line}:${pos.column})`
                : frame.original;
        }
        return frame.original;
    }));

    consumerMap.forEach(c => c.destroy());
    return mappedFrames.join("\n");
};

mapStackTrace().then(mapped => {
    console.log("--- Mapped Stack Trace ---");
    console.log(mapped);
}).catch(err => {
    console.error(err);
    process.exit(1);
});
