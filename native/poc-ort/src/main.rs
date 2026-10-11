//! PoC 2: Python と同じ ONNX 推論を ort (Rust) で再現し、結果を数値で比べる。
//!
//! 使い方:
//!   poc-ort <vad|yolox|ocr|all> --venv <.venv> --data <tmp/poc-ort> [--ort-dll <onnxruntime.dll>]
//!           [--ep cpu|cuda|dml] [--threads N]
//!
//! 比較相手は scripts/make_reference.py が書く *_py.json と、scripts/rapidocr_stages.py が書く
//! stages_<auto|Korean>.json (OCR の段階ごとの途中結果。ocr はリポジトリ直下で実行する)。
//! OCR は RapidOCR 3.9.2 の前後処理を src/rapidocr.rs に、OpenCV 4.11 の該当処理を src/cv.rs に、
//! numpy 1.26 の並べ替え・平均・丸めを src/npy.rs に移植したもの (Apache-2.0 / BSD-3 の表示は各ファイル)。
//! unclip は pyclipper と同じ Clipper 6.4.2 (third_party/clipper、Boost) を使う。ビルド:
//!   $env:CARGO_TARGET_DIR = "<repo>\tmp\target-poc-ort"
//!   cargo build --release --manifest-path native\poc-ort\Cargo.toml
//!     (既定: load-dynamic。--ort-dll 省略時は <venv>\...\onnxruntime\capi\onnxruntime.dll を読む)
//!   cargo build --release --no-default-features --features download --manifest-path ...
//!     (ort が CDN から onnxruntime 1.28 を取得して静的リンクする版)

use std::error::Error;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::Instant;

#[cfg(feature = "gpu")]
use ort::ep;
use ort::session::Session;
use ort::value::Tensor;
use serde_json::{Value, json};

type R<T> = Result<T, Box<dyn Error + Send + Sync>>;

#[derive(Clone, Copy, PartialEq)]
enum Ep {
    Cpu,
    Cuda,
    Dml,
}

struct Args {
    cmd: String,
    venv: PathBuf,
    data: PathBuf,
    #[cfg_attr(not(feature = "dynamic"), allow(dead_code))]
    ort_dll: Option<PathBuf>,
    ep: Ep,
    threads: usize,
}

fn parse_args() -> R<Args> {
    let mut it = std::env::args().skip(1);
    let cmd = it.next().ok_or("usage: poc-ort <vad|yolox|ocr|all> --venv DIR --data DIR")?;
    let (mut venv, mut data, mut ort_dll, mut ep, mut threads) = (None, None, None, Ep::Cpu, None);
    while let Some(flag) = it.next() {
        let value = it.next().ok_or_else(|| format!("{flag} needs a value"))?;
        match flag.as_str() {
            "--venv" => venv = Some(PathBuf::from(value)),
            "--data" => data = Some(PathBuf::from(value)),
            "--ort-dll" => ort_dll = Some(PathBuf::from(value)),
            "--threads" => threads = Some(value.parse()?),
            "--ep" => {
                ep = match value.as_str() {
                    "cpu" => Ep::Cpu,
                    "cuda" => Ep::Cuda,
                    "dml" => Ep::Dml,
                    other => return Err(format!("unknown ep {other}").into()),
                }
            }
            other => return Err(format!("unknown flag {other}").into()),
        }
    }
    // ocr_languages.ocr_onnx_threads() と同じ: コアの半分、最大4。
    let default_threads = (std::thread::available_parallelism().map_or(2, |n| n.get()) / 2).clamp(1, 4);
    Ok(Args {
        cmd,
        venv: venv.ok_or("--venv is required")?,
        data: data.ok_or("--data is required")?,
        ort_dll,
        ep,
        threads: threads.unwrap_or(default_threads),
    })
}

/// プロセスで1つの ort Environment を作る。以降の Session はすべてこれを共有する。
#[cfg_attr(not(feature = "dynamic"), allow(unused_variables))]
fn init_ort(args: &Args) -> R<()> {
    #[cfg(feature = "dynamic")]
    let builder = {
        let dll = args
            .ort_dll
            .clone()
            .unwrap_or_else(|| args.venv.join("Lib/site-packages/onnxruntime/capi/onnxruntime.dll"));
        ort::init_from(&dll)?
    };
    #[cfg(not(feature = "dynamic"))]
    let builder = ort::init();
    builder.with_name("poc-ort").commit();
    eprintln!("onnxruntime: {}", ort::info());
    Ok(())
}

fn session(path: &Path, threads: usize, ep: Ep) -> ort::Result<Session> {
    let mut builder = Session::builder()?.with_intra_threads(threads)?.with_inter_threads(1)?;
    builder = match ep {
        Ep::Cpu => builder,
        #[cfg(feature = "gpu")]
        Ep::Cuda => builder.with_execution_providers([ep::CUDA::default().build().error_on_failure()])?,
        // DirectML はメモリパターン最適化と並列実行に対応していない。
        #[cfg(feature = "gpu")]
        Ep::Dml => builder
            .with_memory_pattern(false)?
            .with_parallel_execution(false)?
            .with_execution_providers([ep::DirectML::default().build().error_on_failure()])?,
        #[cfg(not(feature = "gpu"))]
        _ => return Err(ort::Error::new("built without the gpu feature")),
    };
    Ok(builder.commit_from_file(path)?)
}

fn read_json(path: &Path) -> R<Value> {
    Ok(serde_json::from_str(&fs::read_to_string(path)?)?)
}

// ---------------------------------------------------------------- Silero VAD

/// audio_vad.SileroFrameProbability と同じ: 64サンプルの文脈 + 512サンプルを encoder へ、
/// その出力 (1,128) と状態 (2,1,128) を decoder へ。
struct Silero {
    encoder: Session,
    decoder: Session,
    state: Vec<f32>,
    context: Vec<f32>,
}

impl Silero {
    fn new(venv: &Path, ep: Ep) -> R<Self> {
        let assets = venv.join("Lib/site-packages/faster_whisper/assets");
        // faster-whisper の SileroVADModel と同じく 1 スレッド。
        Ok(Self {
            encoder: session(&assets.join("silero_encoder_v5.onnx"), 1, ep)?,
            decoder: session(&assets.join("silero_decoder_v5.onnx"), 1, ep)?,
            state: vec![0.0; 2 * 128],
            context: vec![0.0; 64],
        })
    }

    fn prob(&mut self, frame: &[f32]) -> R<f32> {
        assert_eq!(frame.len(), 512);
        let mut input = Vec::with_capacity(576);
        input.extend_from_slice(&self.context);
        input.extend_from_slice(frame);
        let out = self.encoder.run(ort::inputs!["input" => Tensor::from_array(([1usize, 576], input))?])?;
        let encoded = out[0].try_extract_tensor::<f32>()?.1.to_vec();
        drop(out);
        let state = std::mem::take(&mut self.state);
        let out = self.decoder.run(ort::inputs![
            "input" => Tensor::from_array(([1usize, 128], encoded))?,
            "state" => Tensor::from_array(([2usize, 1, 128], state))?,
        ])?;
        let prob = out[0].try_extract_tensor::<f32>()?.1[0];
        self.state = out[1].try_extract_tensor::<f32>()?.1.to_vec();
        self.context.copy_from_slice(&frame[448..]);
        Ok(prob)
    }
}

fn read_wav_i16(path: &Path) -> R<Vec<i16>> {
    // make_reference.py が書く 44バイトヘッダの PCM16 mono のみ扱う。
    let bytes = fs::read(path)?;
    if bytes.len() < 44 || &bytes[0..4] != b"RIFF" || &bytes[36..40] != b"data" {
        return Err("unexpected wav layout".into());
    }
    Ok(bytes[44..].chunks_exact(2).map(|b| i16::from_le_bytes([b[0], b[1]])).collect())
}

fn run_vad(args: &Args, vad: &mut Silero) -> R<Value> {
    let pcm = read_wav_i16(&args.data.join("vad_input.wav"))?;
    let reference = read_json(&args.data.join("vad_py.json"))?;
    let py: Vec<f64> = reference["probs"].as_array().ok_or("probs")?.iter().filter_map(Value::as_f64).collect();
    let start = Instant::now();
    let mut probs = Vec::new();
    for chunk in pcm.chunks_exact(512) {
        let frame: Vec<f32> = chunk.iter().map(|&s| s as f32 / 32768.0).collect();
        probs.push(vad.prob(&frame)?);
    }
    let elapsed = start.elapsed().as_secs_f64() * 1000.0;
    let max_abs = probs.iter().zip(&py).map(|(&a, &b)| (a as f64 - b).abs()).fold(0.0, f64::max);
    // VadSegmenter の既定しきい値 0.25 / 0.10 で判定が食い違うフレーム数。
    let flips = |t: f64| probs.iter().zip(&py).filter(|&(&a, &b)| ((a as f64) >= t) != (b >= t)).count();
    Ok(json!({
        "frames": probs.len(), "py_frames": py.len(), "max_abs_diff": max_abs,
        "threshold_flips_0.25": flips(0.25), "threshold_flips_0.10": flips(0.10),
        "rust_ms": elapsed, "py_ms": reference["elapsed_ms"],
    }))
}

// ---------------------------------------------------------------- YOLOX

const IMAGE_SIZE: f64 = 1280.0;
const CONFIDENCE: f32 = 0.7;
const NMS_IOU: f32 = 0.65;
const PAD: f32 = 114.0;
const CROP_PADDING: i64 = 4;

/// cv2.resize(INTER_LINEAR) の 8bit 経路 (係数を 2048 倍した固定小数点) をなぞった双線形縮小。
/// 入出力は BGR の HWC u8。
fn resize_linear_bgr(src: &[u8], w: usize, h: usize, nw: usize, nh: usize) -> Vec<u8> {
    fn taps(dst: usize, src: usize) -> Vec<(usize, i32)> {
        // cv::resize と同じく inv_scale = dst/src の逆数を倍精度で、端数は float で持つ。
        let scale = 1.0 / (dst as f64 / src as f64);
        (0..dst)
            .map(|d| {
                let f = ((d as f64 + 0.5) * scale - 0.5) as f32;
                let mut s = f.floor() as i64;
                let mut frac = f - s as f32;
                if s < 0 {
                    s = 0;
                    frac = 0.0;
                }
                if s >= src as i64 - 1 {
                    s = src as i64 - 1;
                    frac = 0.0;
                }
                (s as usize, ((1.0 - frac) * 2048.0).round_ties_even() as i32)
            })
            .collect()
    }
    let xs = taps(nw, w);
    let ys = taps(nh, h);
    let mut out = vec![0u8; nw * nh * 3];
    let mut row0 = vec![0i32; nw * 3];
    let mut row1 = vec![0i32; nw * 3];
    let hrow = |y: usize, row: &mut [i32]| {
        let line = &src[y * w * 3..(y + 1) * w * 3];
        for (dx, &(sx, c0)) in xs.iter().enumerate() {
            let sx1 = (sx + 1).min(w - 1);
            for c in 0..3 {
                row[dx * 3 + c] = line[sx * 3 + c] as i32 * c0 + line[sx1 * 3 + c] as i32 * (2048 - c0);
            }
        }
    };
    for (dy, &(sy, b0)) in ys.iter().enumerate() {
        hrow(sy, &mut row0);
        hrow((sy + 1).min(h - 1), &mut row1);
        // OpenCV の SIMD 経路 (VResizeLinearVec_32s8u) の丸め: ((S0>>4)*b0>>16) + ((S1>>4)*b1>>16) を
        // +2>>2。スカラー経路の (b0*S0 + b1*S1 + 2^21) >> 22 とは1ずれることがある。端数の要素も
        // SIMD 側の式で一致した (16の倍数でない幅で確認)。
        for i in 0..nw * 3 {
            let v = ((((row0[i] >> 4) * b0) >> 16) + (((row1[i] >> 4) * (2048 - b0)) >> 16) + 2) >> 2;
            out[dy * nw * 3 + i] = v.clamp(0, 255) as u8;
        }
    }
    out
}

/// ocr_bubble_detector.BubbleDetector._letterbox と同じ: BGR・0-255・左上寄せ・32の倍数へ切り上げ。
fn letterbox(bgr: &[u8], w: usize, h: usize) -> (Vec<f32>, [usize; 4], f64) {
    let scale = (IMAGE_SIZE / w as f64).min(IMAGE_SIZE / h as f64);
    let nw = ((w as f64 * scale) as usize).max(1);
    let nh = ((h as f64 * scale) as usize).max(1);
    let resized = resize_linear_bgr(bgr, w, h, nw, nh);
    let cw = nw.div_ceil(32) * 32;
    let ch = nh.div_ceil(32) * 32;
    let mut tensor = vec![PAD; 3 * ch * cw];
    for y in 0..nh {
        for x in 0..nw {
            for c in 0..3 {
                tensor[c * ch * cw + y * cw + x] = resized[(y * nw + x) * 3 + c] as f32;
            }
        }
    }
    (tensor, [1, 3, ch, cw], scale)
}

/// ocr_bubble_detector.nonMaxSuppression と同じ。強い順に残した添字を返す。
fn nms(boxes: &[[f32; 4]], scores: &[f32], threshold: f32) -> Vec<usize> {
    let mut order: Vec<usize> = (0..scores.len()).collect();
    // numpy の argsort()[::-1] と同点時の順序まで合わせる必要はない (同点はまず出ない)。
    order.sort_by(|&a, &b| scores[b].total_cmp(&scores[a]));
    let area = |b: &[f32; 4]| (b[2] - b[0]) * (b[3] - b[1]);
    let mut keep = Vec::new();
    while let Some((&cur, rest)) = order.split_first() {
        keep.push(cur);
        let c = boxes[cur];
        order = rest
            .iter()
            .copied()
            .filter(|&r| {
                let b = boxes[r];
                let overlap = (c[2].min(b[2]) - c[0].max(b[0])).max(0.0) * (c[3].min(b[3]) - c[1].max(b[1])).max(0.0);
                overlap / (area(&c) + area(&b) - overlap).max(1e-6) <= threshold
            })
            .collect();
    }
    keep
}

struct Detection {
    raw: Vec<(f32, [f32; 4])>,
    boxes: Vec<[i64; 4]>,
}

fn decode(output: &[f32], scale: f64, w: usize, h: usize) -> Detection {
    let mut boxes = Vec::new();
    let mut scores = Vec::new();
    for p in output.chunks_exact(6) {
        let score = p[4] * p[5];
        if score >= CONFIDENCE {
            scores.push(score);
            boxes.push([p[0] - p[2] / 2.0, p[1] - p[3] / 2.0, p[0] + p[2] / 2.0, p[1] + p[3] / 2.0]);
        }
    }
    let keep = nms(&boxes, &scores, NMS_IOU);
    let mut out = Vec::new();
    for &k in &keep {
        // Python の int(round(x / scale)) は偶数丸め。f64::round_ties_even で揃える。
        let b = boxes[k];
        let to = |v: f32| (v as f64 / scale).round_ties_even() as i64;
        let x0 = (to(b[0]) - CROP_PADDING).max(0);
        let y0 = (to(b[1]) - CROP_PADDING).max(0);
        let x1 = (to(b[2]) + CROP_PADDING).min(w as i64);
        let y1 = (to(b[3]) + CROP_PADDING).min(h as i64);
        if x1 - x0 >= 2 && y1 - y0 >= 2 {
            out.push([x0, y0, x1 - x0, y1 - y0]);
        }
    }
    Detection { raw: keep.iter().map(|&k| (scores[k], boxes[k])).collect(), boxes: out }
}

fn yolox_session(args: &Args) -> R<Session> {
    let model = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../src-python/models/ocr/onnx/chatbox_yolox_tiny.onnx");
    Ok(session(&model, args.threads, args.ep)?)
}

fn run_yolox(args: &Args, yolox: &mut Session) -> R<Value> {
    let reference = read_json(&args.data.join("yolox_py.json"))?;
    let input_name = yolox.inputs()[0].name().to_string();
    let mut report = Vec::new();
    let (mut max_score_diff, mut max_coord_diff, mut max_pixel_diff, mut box_mismatch) = (0f64, 0f64, 0f32, 0);
    let (mut elapsed, mut letterbox_ms) = (0.0, 0.0);
    for (i, item) in reference["images"].as_array().ok_or("images")?.iter().enumerate() {
        let path = item["path"].as_str().ok_or("path")?;
        let rgb = image::open(path)?.to_rgb8();
        let (w, h) = (rgb.width() as usize, rgb.height() as usize);
        let bgr: Vec<u8> = rgb.pixels().flat_map(|p| [p[2], p[1], p[0]]).collect();
        let start = Instant::now();
        let (tensor, shape, scale) = letterbox(&bgr, w, h);
        letterbox_ms += start.elapsed().as_secs_f64() * 1000.0;
        // Python の letterbox 済みテンソルがあれば、前処理の差だけを測る。
        let py_tensor = args.data.join(format!("yolox_tensor_{i}.bin"));
        let mut tensor_input_diff = None;
        if let Ok(bytes) = fs::read(&py_tensor) {
            let py: Vec<f32> = bytes.chunks_exact(4).map(|b| f32::from_le_bytes([b[0], b[1], b[2], b[3]])).collect();
            let d = py.iter().zip(&tensor).map(|(a, b)| (a - b).abs()).fold(0.0, f32::max);
            let n = py.iter().zip(&tensor).filter(|(a, b)| a != b).count();            max_pixel_diff = max_pixel_diff.max(d);
            // 同じテンソルを入れたときの出力差 (推論そのものの一致度)。
            let out = yolox.run(ort::inputs![input_name.as_str() => Tensor::from_array((shape, py))?])?;
            let py_input_det = decode(out[0].try_extract_tensor::<f32>()?.1, scale, w, h);
            tensor_input_diff = Some(json!({
                "tensor_max_abs_diff": d, "tensor_diff_count": n,
                "boxes_from_py_tensor": py_input_det.boxes,
                "raw_from_py_tensor": py_input_det.raw.iter().map(|(s, b)| json!({"score": s, "xyxy": b})).collect::<Vec<_>>(),
            }));
        }
        let start = Instant::now();
        let out = yolox.run(ort::inputs![input_name.as_str() => Tensor::from_array((shape, tensor))?])?;
        let det = decode(out[0].try_extract_tensor::<f32>()?.1, scale, w, h);
        elapsed += start.elapsed().as_secs_f64() * 1000.0;

        let py_boxes: Vec<Vec<i64>> = serde_json::from_value(item["boxes"].clone())?;
        let py_raw = item["raw"].as_array().ok_or("raw")?;
        if py_boxes.len() != det.boxes.len() || py_raw.len() != det.raw.len() {
            box_mismatch += 1;
        }
        for (pb, rb) in py_boxes.iter().zip(&det.boxes) {
            for k in 0..4 {
                max_coord_diff = max_coord_diff.max((pb[k] - rb[k]).abs() as f64);
            }
        }
        for (pr, (score, _)) in py_raw.iter().zip(&det.raw) {
            max_score_diff = max_score_diff.max((pr["score"].as_f64().unwrap_or(0.0) - *score as f64).abs());
        }
        report.push(json!({
            "path": path, "py_boxes": py_boxes, "rust_boxes": det.boxes,
            "py_raw": py_raw, "rust_raw": det.raw.iter().map(|(s, b)| json!({"score": s, "xyxy": b})).collect::<Vec<_>>(),
            "same_tensor": tensor_input_diff,
        }));
    }
    fs::write(args.data.join("yolox_rust.json"), serde_json::to_string_pretty(&report)?)?;
    Ok(json!({
        "images": report.len(), "images_with_count_mismatch": box_mismatch,
        "max_final_box_coord_diff_px": max_coord_diff, "max_score_diff": max_score_diff,
        "max_letterbox_pixel_diff": max_pixel_diff, "rust_ms": elapsed + letterbox_ms, "rust_letterbox_ms": letterbox_ms, "py_ms": reference["elapsed_ms"],
        "detail": "yolox_rust.json",
    }))
}

// ---------------------------------------------------------------- PP-OCR (RapidOCR port)

mod cv;
mod npy;
mod rapidocr;

/// rapidocr with VRCT's models for a language: auto = PP-OCRv6 small, Korean = PP-OCRv5 mobile.
fn rapidocr(args: &Args, language: &str) -> R<rapidocr::RapidOcr> {
    let models = args.venv.join("Lib/site-packages/rapidocr/models");
    let (det, rec) = match language {
        "auto" => ("PP-OCRv6_det_small.onnx", "PP-OCRv6_rec_small.onnx"),
        "Korean" => ("ch_PP-OCRv5_det_mobile.onnx", "korean_PP-OCRv5_rec_mobile.onnx"),
        other => return Err(format!("no models for {other}").into()),
    };
    let open = |name: &str| session(&models.join(name), args.threads, args.ep);
    Ok(rapidocr::RapidOcr::new(open(det)?, open("ch_ppocr_mobile_v2.0_cls_mobile.onnx")?, open(rec)?,
                               rapidocr::Params::default())?)
}

fn read_bgr(path: &str) -> R<cv::Img> {
    let rgb = image::open(path)?.to_rgb8();
    let (w, h) = (rgb.width() as usize, rgb.height() as usize);
    Ok(cv::Img { w, h, c: 3, data: rgb.pixels().flat_map(|p| [p[2], p[1], p[0]]).collect() })
}

/// Compares every stage with scripts/rapidocr_stages.py's stages_<language>.json.
fn run_ocr(args: &Args, ocr: &mut rapidocr::RapidOcr, language: &str) -> R<Value> {
    let reference = read_json(&args.data.join(format!("stages_{language}.json")))?;
    let (mut total, mut final_equal, mut elapsed) = (0, 0, 0.0);
    let mut first_diff: std::collections::BTreeMap<&str, usize> = Default::default();
    let mut mismatches = Vec::new();
    for item in reference.as_array().ok_or("stages")? {
        let path = item["path"].as_str().ok_or("path")?;
        let img = read_bgr(path)?;
        let mut st = rapidocr::Stages::default();
        let start = Instant::now();
        let out = ocr.run(&img, &mut st)?;
        elapsed += start.elapsed().as_secs_f64() * 1000.0;
        total += 1;
        let pre = &item["pre"];
        let py_pre = (pre["shape"][0].as_u64(), pre["shape"][1].as_u64(), pre["ratio_h"].as_f64(), pre["ratio_w"].as_f64(),
                      pre["pad_top"].as_u64());
        let rs_pre = (Some(st.pre.0 as u64), Some(st.pre.1 as u64), Some(st.pre.2), Some(st.pre.3), Some(st.pre.4 as u64));
        let det_in = &item["det"]["input"];
        let py_boxes: Vec<[[f32; 2]; 4]> = serde_json::from_value(item["det"]["boxes"].clone())?;
        let py_lines: Vec<(usize, usize, String)> = item["lines"].as_array().map(|l| l.iter().map(|x| {
            (x["shape"][0].as_u64().unwrap() as usize, x["shape"][1].as_u64().unwrap() as usize,
             x["cls"][0].as_str().unwrap().to_string())
        }).collect()).unwrap_or_default();
        let py_rec: Vec<(String, f64)> = serde_json::from_value(item["rec"].clone()).unwrap_or_default();
        let py_final = rapidocr::OcrOutput {
            txts: serde_json::from_value(item["final"]["txts"].clone())?,
            scores: serde_json::from_value(item["final"]["scores"].clone())?,
            boxes: serde_json::from_value(item["final"]["boxes"].clone())?,
        };
        let rs_lines: Vec<(usize, usize, String)> = st.lines.iter().map(|l| (l.0, l.1, l.2.clone())).collect();
        let stage = if py_pre != rs_pre {
            "pre"
        } else if det_in[2].as_u64() != Some(st.det_input.0 as u64) || det_in[3].as_u64() != Some(st.det_input.1 as u64) {
            "det_input"
        } else if py_boxes != st.det_boxes {
            "det_boxes"
        } else if py_lines != rs_lines {
            "lines"
        } else if py_rec != st.rec {
            "rec"
        } else if py_final.txts != out.txts || py_final.scores != out.scores || py_final.boxes != out.boxes {
            "final"
        } else {
            ""
        };
        if stage.is_empty() {
            final_equal += 1;
        } else {
            *first_diff.entry(stage).or_default() += 1;
            mismatches.push(json!({"path": path, "first_diff": stage,
                "py": {"pre": item["pre"], "det_boxes": py_boxes, "lines": py_lines, "rec": py_rec, "final": py_final},
                "rust": {"pre": st.pre, "det_input": st.det_input, "det_boxes": st.det_boxes, "lines": rs_lines, "rec": st.rec, "final": out}}));
        }
    }
    fs::write(args.data.join(format!("stages_{language}_rust_mismatches.json")), serde_json::to_string_pretty(&mismatches)?)?;
    Ok(json!({"crops": total, "all_stages_equal": final_equal, "first_diff_stage": first_diff, "rust_ms": elapsed}))
}

// ---------------------------------------------------------------- main

fn main() -> R<()> {
    let args = parse_args()?;
    init_ort(&args)?;
    let mut summary = serde_json::Map::new();
    match args.cmd.as_str() {
        "vad" => {
            let mut vad = Silero::new(&args.venv, args.ep)?;
            summary.insert("vad".into(), run_vad(&args, &mut vad)?);
        }
        "yolox" => {
            let mut yolox = yolox_session(&args)?;
            summary.insert("yolox".into(), run_yolox(&args, &mut yolox)?);
        }
        "ocr" => {
            for language in ["auto", "Korean"] {
                if args.data.join(format!("stages_{language}.json")).exists() {
                    let mut ocr = rapidocr(&args, language)?;
                    summary.insert(format!("ocr_{language}"), run_ocr(&args, &mut ocr, language)?);
                }
            }
        }
        "all" => {
            // 1プロセスで3つを初期化し、別スレッドで同時に回す (Environment は共有)。
            let start = Instant::now();
            let mut vad = Silero::new(&args.venv, args.ep)?;
            let mut yolox = yolox_session(&args)?;
            let mut ocr = rapidocr(&args, "auto")?;
            summary.insert("init_ms".into(), json!(start.elapsed().as_secs_f64() * 1000.0));
            let start = Instant::now();
            let (v, y, o) = std::thread::scope(|s| {
                let v = s.spawn(|| run_vad(&args, &mut vad));
                let y = s.spawn(|| run_yolox(&args, &mut yolox));
                let o = s.spawn(|| run_ocr(&args, &mut ocr, "auto"));
                (v.join().unwrap(), y.join().unwrap(), o.join().unwrap())
            });
            summary.insert("concurrent_wall_ms".into(), json!(start.elapsed().as_secs_f64() * 1000.0));
            summary.insert("vad".into(), v?);
            summary.insert("yolox".into(), y?);
            summary.insert("ocr".into(), o?);
        }
        other => return Err(format!("unknown command {other}").into()),
    }
    println!("{}", serde_json::to_string_pretty(&summary)?);
    Ok(())
}
