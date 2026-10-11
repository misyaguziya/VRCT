//! RapidOCR's pipeline (det -> crop -> cls -> rec) with VRCT's settings, on ort.
//!
//! Ported from RapidOCR 3.9.2 (https://github.com/RapidAI/RapidOCR): rapidocr/main.py,
//! ch_ppocr_det/{main,utils}.py, ch_ppocr_cls/{main,utils}.py, ch_ppocr_rec/{main,utils}.py,
//! utils/process_img.py. Copyright (c) RapidAI (SWHL); parts of it come from PaddleOCR,
//! Copyright (c) 2020 PaddlePaddle Authors. Licensed under the Apache License, Version 2.0 (see
//! LICENSE-APACHE-2.0 in this crate); this file is a modified, translated version of those sources.
//!
//! numpy semantics that change results are kept: float32 vs float64 arithmetic, round half to
//! even, np.argsort's order (batches), np.mean / round of the confidences.

use std::error::Error;

use ort::session::Session;
use ort::value::Tensor;

use crate::cv::{self, Img};
use crate::npy;

type R<T> = Result<T, Box<dyn Error + Send + Sync>>;

/// VRCT's parameters (ocr_engine_rapidocr.getReader) on top of RapidOCR's config.yaml.
#[derive(Clone, Copy)]
pub struct Params {
    pub text_score: f64,     // Global.text_score
    pub min_height: usize,   // Global.min_height
    pub width_height_ratio: f64,
    pub min_side_len: f64,   // Global.min_side_len
    pub max_side_len: f64,   // Global.max_side_len
    pub limit_side_len: f64, // Det.limit_side_len (VRCT: 320), limit_type "min"
    pub thresh: f32,         // Det.thresh
    pub box_thresh: f64,
    pub max_candidates: usize,
    pub unclip_ratio: f64,
    pub cls_thresh: f64,
    pub cls_batch_num: usize,
    pub rec_batch_num: usize,
}

impl Default for Params {
    fn default() -> Self {
        Params {
            text_score: 0.5,
            min_height: 30,
            width_height_ratio: 8.0,
            min_side_len: 30.0,
            max_side_len: 2000.0,
            limit_side_len: 320.0,
            thresh: 0.3,
            box_thresh: 0.5,
            max_candidates: 1000,
            unclip_ratio: 1.6,
            cls_thresh: 0.9,
            cls_batch_num: 6,
            rec_batch_num: 6,
        }
    }
}

pub struct RapidOcr {
    pub det: Session,
    pub cls: Session,
    pub rec: Session,
    pub characters: Vec<String>,
    pub params: Params,
}

/// Intermediate results, to compare stage by stage with scripts/rapidocr_stages.py.
#[derive(Default, serde::Serialize)]
pub struct Stages {
    pub pre: (usize, usize, f64, f64, usize), // h, w, ratio_h, ratio_w, pad_top
    pub det_input: (usize, usize),
    pub det_boxes: Vec<[[f32; 2]; 4]>,
    pub lines: Vec<(usize, usize, String, f32)>, // h, w, cls label, cls score
    pub rec: Vec<(String, f64)>,
}

#[derive(Default, serde::Serialize)]
pub struct OcrOutput {
    pub txts: Vec<String>,
    pub scores: Vec<f64>,
    pub boxes: Vec<[[f32; 2]; 4]>,
}

/// str.splitlines(): the separators Python recognises, no trailing empty line.
pub fn splitlines(s: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut cur = String::new();
    let mut chars = s.chars().peekable();
    while let Some(c) = chars.next() {
        match c {
            '\r' => {
                if chars.peek() == Some(&'\n') {
                    chars.next();
                }
                out.push(std::mem::take(&mut cur));
            }
            '\n' | '\x0b' | '\x0c' | '\x1c' | '\x1d' | '\x1e' | '\u{85}' | '\u{2028}' | '\u{2029}' => {
                out.push(std::mem::take(&mut cur))
            }
            _ => cur.push(c),
        }
    }
    if !cur.is_empty() {
        out.push(cur);
    }
    out
}

/// Python's int(x) on a float: truncation toward zero.
fn trunc(x: f64) -> i64 {
    x.trunc() as i64
}

/// round(v / 32) * 32 with Python's round (half to even).
fn round32(v: i64) -> i64 {
    ((v as f64 / 32.0).round_ties_even() as i64) * 32
}

/// np.linalg.norm of a float32 2-vector: sqrt(dot) in float32.
fn norm32(a: (f32, f32), b: (f32, f32)) -> f32 {
    let (dx, dy) = (a.0 - b.0, a.1 - b.1);
    (dx * dx + dy * dy).sqrt()
}

impl RapidOcr {
    pub fn new(det: Session, cls: Session, rec: Session, params: Params) -> R<RapidOcr> {
        let dict = rec.metadata()?.custom("character").ok_or("rec model has no character list")?;
        // CTCLabelDecode: [blank] + characters + [" "]
        let mut characters = vec!["blank".to_string()];
        characters.extend(splitlines(&dict));
        characters.push(" ".to_string());
        Ok(RapidOcr { det, cls, rec, characters, params })
    }

    /// RapidOCR.__call__ on a BGR image (an ndarray input: no colour conversion).
    pub fn run(&mut self, ori: &Img, stages: &mut Stages) -> R<OcrOutput> {
        let p = self.params;
        // preprocess_img: resize_image_within_bounds
        let (img, ratio_h, ratio_w) = resize_within_bounds(ori, p.min_side_len, p.max_side_len);
        // detect_and_crop: apply_vertical_padding
        let (h, w) = (img.h, img.w);
        let use_limit_ratio = p.width_height_ratio != -1.0 && w as f64 / h as f64 > p.width_height_ratio;
        let pad_top = if h <= p.min_height || use_limit_ratio {
            let new_h = (trunc(w as f64 / p.width_height_ratio)).max(p.min_height as i64) * 2;
            trunc((new_h - h as i64).abs() as f64 / 2.0) as usize
        } else {
            0
        };
        let img = if pad_top > 0 { cv::pad_vertical(&img, pad_top, pad_top) } else { img };
        stages.pre = (h, w, ratio_h, ratio_w, pad_top);

        let boxes = self.detect(&img, stages)?;
        if boxes.is_empty() {
            return Ok(OcrOutput::default());
        }
        stages.det_boxes = boxes.iter().map(|b| b.map(|p| [p.0, p.1])).collect();
        let crops: Vec<Img> = boxes.iter().map(|b| rotate_crop(&img, b)).collect();
        let lines = self.classify(crops, stages)?;
        let rec = self.recognize(&lines)?;
        stages.rec = rec.clone();

        // build_final_output: boxes back to the original image, drop empty and low-score lines
        let (ori_h, ori_w) = (ori.h as f32, ori.w as f32);
        let mut out = OcrOutput::default();
        for (b, (txt, score)) in boxes.iter().zip(rec) {
            if txt.trim().is_empty() || score < p.text_score {
                continue;
            }
            let mapped = b.map(|(x, y)| {
                // padding first (reversed op order), then the preprocess ratios, in float32
                let (x, y) = ((x - 0.0) * ratio_w as f32, (y - pad_top as f32) * ratio_h as f32);
                let (x, y) = (if x < 0.0 { 0.0 } else { x }, if y < 0.0 { 0.0 } else { y });
                [if x > ori_w { ori_w } else { x }, if y > ori_h { ori_h } else { y }]
            });
            out.boxes.push(mapped);
            out.txts.push(txt);
            out.scores.push(score);
        }
        Ok(out)
    }

    /// TextDetector.__call__ + DBPostProcess + sorted_boxes. Boxes are float32 4x2 (tl, tr, br, bl).
    fn detect(&mut self, img: &Img, stages: &mut Stages) -> R<Vec<[(f32, f32); 4]>> {
        let p = self.params;
        let (h, w) = (img.h, img.w);
        // DetPreProcess.resize, limit_type "min"
        let ratio = if (h.min(w) as f64) < p.limit_side_len {
            if h < w { p.limit_side_len / h as f64 } else { p.limit_side_len / w as f64 }
        } else {
            1.0
        };
        let (rh, rw) = (round32(trunc(h as f64 * ratio)), round32(trunc(w as f64 * ratio)));
        if rh <= 0 || rw <= 0 {
            return Ok(vec![]);
        }
        let (rh, rw) = (rh as usize, rw as usize);
        let resized = cv::resize_linear(img, rw, rh);
        stages.det_input = (rh, rw);
        // normalize: (x_f32 * (1/255)_f32 - mean_f64) / std_f64, then float32; HWC -> CHW
        let scale = (1.0f64 / 255.0) as f32;
        let mut input = vec![0f32; 3 * rh * rw];
        for i in 0..rh * rw {
            for c in 0..3 {
                let v = resized.data[i * 3 + c] as f32 * scale;
                input[c * rh * rw + i] = ((v as f64 - 0.5) / 0.5) as f32;
            }
        }
        let out = self.det.run(ort::inputs!["x" => Tensor::from_array(([1usize, 3, rh, rw], input))?])?;
        let (shape, pred) = out[0].try_extract_tensor::<f32>()?;
        let (ph, pw) = (shape[2] as usize, shape[3] as usize);
        let pred = pred.to_vec();

        // DBPostProcess
        let seg: Vec<u8> = pred.iter().map(|&v| (v > p.thresh) as u8).collect();
        let mask = cv::dilate_2x2(&seg, pw, ph);
        let contours = cv::find_contours_list_simple(&mask, pw, ph);
        let mut boxes: Vec<[(i32, i32); 4]> = Vec::new();
        for contour in contours.iter().take(p.max_candidates) {
            let (points, sside) = mini_box(&cv::min_area_rect(contour));
            if sside < 3.0 {
                continue;
            }
            let score = box_score_fast(&pred, pw, ph, &points);
            if p.box_thresh > score {
                continue;
            }
            let expanded = unclip(&points, p.unclip_ratio);
            if expanded.is_empty() {
                continue;
            }
            let (b, sside) = mini_box(&cv::min_area_rect(&expanded));
            if sside < 5.0 {
                continue;
            }
            // np.clip(np.round(box / width * dest_width), 0, dest_width) in float32
            boxes.push(b.map(|(x, y)| {
                let x = ((x / pw as f32) * w as f32).round_ties_even().clamp(0.0, w as f32);
                let y = ((y / ph as f32) * h as f32).round_ties_even().clamp(0.0, h as f32);
                (x as i32, y as i32)
            }));
        }
        // filter_det_res: order_points_clockwise, clip, drop thin boxes
        let mut kept: Vec<[(f32, f32); 4]> = Vec::new();
        for b in boxes {
            let mut r = order_points_clockwise(&b);
            for pt in r.iter_mut() {
                pt.0 = (pt.0 as i32).clamp(0, w as i32 - 1) as f32;
                pt.1 = (pt.1 as i32).clamp(0, h as i32 - 1) as f32;
            }
            let rect_width = norm32(r[0], r[1]) as i32;
            let rect_height = norm32(r[0], r[3]) as i32;
            if rect_width <= 3 || rect_height <= 3 {
                continue;
            }
            kept.push(r);
        }
        Ok(sorted_boxes(kept))
    }

    /// TextClassifier.__call__: 180-degree text lines are turned upright.
    fn classify(&mut self, mut imgs: Vec<Img>, stages: &mut Stages) -> R<Vec<Img>> {
        let (img_c, img_h, img_w) = (3usize, 48usize, 192usize);
        let ratios: Vec<f64> = imgs.iter().map(|i| i.w as f64 / i.h as f64).collect();
        let indices = npy::argsort(&ratios);
        let mut cls_res = vec![(String::new(), 0f32); imgs.len()];
        for beg in (0..imgs.len()).step_by(self.params.cls_batch_num) {
            let end = (beg + self.params.cls_batch_num).min(imgs.len());
            let mut batch = Vec::with_capacity((end - beg) * img_c * img_h * img_w);
            for &i in &indices[beg..end] {
                batch.extend(resize_norm(&imgs[i], img_h, img_w, None));
            }
            let out = self.cls.run(ort::inputs!["x" => Tensor::from_array(([end - beg, img_c, img_h, img_w], batch))?])?;
            let (_, prob) = out[0].try_extract_tensor::<f32>()?;
            for (rno, &i) in indices[beg..end].iter().enumerate() {
                let row = &prob[rno * 2..rno * 2 + 2];
                let idx = if row[1] > row[0] { 1 } else { 0 }; // argmax, first max wins
                let (label, score) = (["0", "180"][idx], row[idx]);
                cls_res[i] = (label.to_string(), score);
                // numpy scalar float32 vs Python float compares in float64
                if label == "180" && score as f64 > self.params.cls_thresh {
                    imgs[i] = cv::rotate_180(&imgs[i]);
                }
            }
        }
        stages.lines = imgs.iter().zip(&cls_res).map(|(i, c)| (i.h, i.w, c.0.clone(), c.1)).collect();
        // ponytail: stages.lines reports the shapes after rotation; 180-degree turns keep them
        Ok(imgs)
    }

    /// TextRecognizer.__call__ + CTCLabelDecode.
    fn recognize(&mut self, imgs: &[Img]) -> R<Vec<(String, f64)>> {
        let (img_c, img_h, img_w0) = (3usize, 48usize, 320usize);
        let ratios: Vec<f64> = imgs.iter().map(|i| i.w as f64 / i.h as f64).collect();
        let indices = npy::argsort(&ratios);
        let mut res = vec![(String::new(), 0f64); imgs.len()];
        for beg in (0..imgs.len()).step_by(self.params.rec_batch_num) {
            let end = (beg + self.params.rec_batch_num).min(imgs.len());
            let mut max_wh_ratio = img_w0 as f64 / img_h as f64;
            for &i in &indices[beg..end] {
                let wh = imgs[i].w as f64 * 1.0 / imgs[i].h as f64;
                max_wh_ratio = max_wh_ratio.max(wh);
            }
            let img_w = trunc(img_h as f64 * max_wh_ratio) as usize;
            let mut batch = Vec::with_capacity((end - beg) * img_c * img_h * img_w);
            for &i in &indices[beg..end] {
                batch.extend(resize_norm(&imgs[i], img_h, img_w, Some(img_w)));
            }
            let out = self.rec.run(ort::inputs!["x" => Tensor::from_array(([end - beg, img_c, img_h, img_w], batch))?])?;
            let (shape, preds) = out[0].try_extract_tensor::<f32>()?;
            let (t, c) = (shape[1] as usize, shape[2] as usize);
            for (rno, &i) in indices[beg..end].iter().enumerate() {
                res[i] = ctc_decode(&self.characters, &preds[rno * t * c..(rno + 1) * t * c], t, c);
            }
        }
        Ok(res)
    }

}

/// CTCLabelDecode.decode(remove_duplicate=True) for one sequence.
fn ctc_decode(characters: &[String], probs: &[f32], t: usize, c: usize) -> (String, f64) {
    let mut text = String::new();
    let mut confs: Vec<f64> = Vec::new();
    let mut prev: Option<usize> = None;
    for step in 0..t {
        let row = &probs[step * c..(step + 1) * c];
        // np.argmax / np.max over the classes
        let (mut idx, mut max) = (0usize, row[0]);
        for (k, &v) in row.iter().enumerate().skip(1) {
            if v > max {
                max = v;
                idx = k;
            }
        }
        let selected = prev != Some(idx) && idx != 0;
        prev = Some(idx);
        if selected {
            text.push_str(&characters[idx]);
            confs.push(npy::py_round(max as f64, 5));
        }
    }
    if confs.is_empty() {
        confs.push(0.0);
    }
    if std::env::var("POC_OCR_DEBUG").is_ok() {
        eprintln!("ctc {text:?} confs {confs:?} mean {:?}", npy::mean(&confs));
    }
    (text, npy::round(npy::mean(&confs), 5))
}

/// resize_image_within_bounds (+ reduce_max_side / increase_min_side).
fn resize_within_bounds(img: &Img, min_side: f64, max_side: f64) -> (Img, f64, f64) {
    let mut out = img.clone();
    let (mut ratio_h, mut ratio_w) = (1.0, 1.0);
    let resize = |src: &Img, ratio: f64| {
        let (h, w) = (src.h, src.w);
        let (rh, rw) = (round32(trunc(h as f64 * ratio)), round32(trunc(w as f64 * ratio)));
        let r = cv::resize_linear(src, rw as usize, rh as usize);
        (r, h as f64 / rh as f64, w as f64 / rw as f64)
    };
    if (out.h.max(out.w) as f64) > max_side {
        let ratio = if out.h > out.w { max_side / out.h as f64 } else { max_side / out.w as f64 };
        (out, ratio_h, ratio_w) = resize(&out, ratio);
    }
    if (out.h.min(out.w) as f64) < min_side {
        let ratio = if out.h < out.w { min_side / out.h as f64 } else { min_side / out.w as f64 };
        (out, ratio_h, ratio_w) = resize(&out, ratio);
    }
    (out, ratio_h, ratio_w)
}

/// get_mini_boxes: boxPoints sorted by x (stable), then tl, tr, br, bl; and min(w, h).
fn mini_box(r: &cv::RotatedRect) -> ([(f32, f32); 4], f32) {
    let mut pts = cv::box_points(r).to_vec();
    pts.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap());
    let (i1, i4) = if pts[1].1 > pts[0].1 { (0, 1) } else { (1, 0) };
    let (i2, i3) = if pts[3].1 > pts[2].1 { (2, 3) } else { (3, 2) };
    ([pts[i1], pts[i2], pts[i3], pts[i4]], r.w.min(r.h))
}

/// box_score_fast: mean of the prediction inside the box polygon.
fn box_score_fast(pred: &[f32], w: usize, h: usize, b: &[(f32, f32); 4]) -> f64 {
    let min_x = b.iter().map(|p| p.0).fold(f32::INFINITY, f32::min);
    let max_x = b.iter().map(|p| p.0).fold(f32::NEG_INFINITY, f32::max);
    let min_y = b.iter().map(|p| p.1).fold(f32::INFINITY, f32::min);
    let max_y = b.iter().map(|p| p.1).fold(f32::NEG_INFINITY, f32::max);
    let xmin = (min_x.floor() as i32).clamp(0, w as i32 - 1);
    let xmax = (max_x.ceil() as i32).clamp(0, w as i32 - 1);
    let ymin = (min_y.floor() as i32).clamp(0, h as i32 - 1);
    let ymax = (max_y.ceil() as i32).clamp(0, h as i32 - 1);
    let (mw, mh) = ((xmax - xmin + 1) as usize, (ymax - ymin + 1) as usize);
    let mut mask = vec![0u8; mw * mh];
    // box - (xmin, ymin) in float32, then astype(int32) (truncation)
    let poly: Vec<(i32, i32)> = b.iter().map(|p| ((p.0 - xmin as f32) as i32, (p.1 - ymin as f32) as i32)).collect();
    cv::fill_poly(&mut mask, mw, mh, &poly, 1);
    cv::mean_masked(pred, w, xmin as usize, ymin as usize, mw, mh, &mask)
}

unsafe extern "C" {
    fn vrct_clipper_offset_round(xy: *const i64, n: usize, delta: f64, out_points: *mut usize) -> *mut i64;
    fn vrct_clipper_free(p: *mut i64);
}

/// unclip: shapely area / length (GEOS's shoelace and segment sums in double), then pyclipper's
/// round offset of the box truncated to integers.
fn unclip(b: &[(f32, f32); 4], unclip_ratio: f64) -> Vec<(i32, i32)> {
    let ring: Vec<(f64, f64)> = b.iter().chain(std::iter::once(&b[0])).map(|p| (p.0 as f64, p.1 as f64)).collect();
    let n = ring.len();
    let x0 = ring[0].0;
    let mut sum = 0.0;
    for i in 1..n - 1 {
        sum += (ring[i].0 - x0) * (ring[i - 1].1 - ring[i + 1].1);
    }
    let area = (sum / 2.0).abs();
    let mut length = 0.0;
    for i in 1..n {
        let (dx, dy) = (ring[i].0 - ring[i - 1].0, ring[i].1 - ring[i - 1].1);
        length += (dx * dx + dy * dy).sqrt();
    }
    let distance = area * unclip_ratio / length;
    let xy: Vec<i64> = b.iter().flat_map(|p| [p.0 as i64, p.1 as i64]).collect();
    let mut n_out = 0usize;
    unsafe {
        let out = vrct_clipper_offset_round(xy.as_ptr(), 4, distance, &mut n_out);
        let pts = (0..n_out).map(|i| (*out.add(2 * i) as i32, *out.add(2 * i + 1) as i32)).collect();
        vrct_clipper_free(out);
        pts
    }
}

/// order_points_clockwise on an int32 box (argsort of 4 values is an insertion sort: stable).
fn order_points_clockwise(b: &[(i32, i32); 4]) -> [(f32, f32); 4] {
    let mut xs: Vec<(i32, i32)> = b.to_vec();
    xs.sort_by_key(|p| p.0);
    let mut left = [xs[0], xs[1]];
    let mut right = [xs[2], xs[3]];
    left.sort_by_key(|p| p.1);
    right.sort_by_key(|p| p.1);
    let f = |p: (i32, i32)| (p.0 as f32, p.1 as f32);
    [f(left[0]), f(right[0]), f(right[1]), f(left[1])]
}

/// TextDetector.sorted_boxes: stable sort by the top-left y, lines where y jumps by >= 10, then by x.
fn sorted_boxes(boxes: Vec<[(f32, f32); 4]>) -> Vec<[(f32, f32); 4]> {
    if boxes.is_empty() {
        return boxes;
    }
    let mut by_y: Vec<usize> = (0..boxes.len()).collect();
    by_y.sort_by(|&a, &b| boxes[a][0].1.partial_cmp(&boxes[b][0].1).unwrap());
    let mut line = 0;
    let mut keyed: Vec<(i32, f32, usize)> = Vec::with_capacity(by_y.len());
    for (k, &i) in by_y.iter().enumerate() {
        if k > 0 && boxes[i][0].1 - boxes[by_y[k - 1]][0].1 >= 10.0 {
            line += 1;
        }
        keyed.push((line, boxes[i][0].0, k));
    }
    // np.lexsort((x, line_ids)) is stable
    keyed.sort_by(|a, b| a.0.cmp(&b.0).then(a.1.partial_cmp(&b.1).unwrap()));
    keyed.iter().map(|&(_, _, k)| boxes[by_y[k]]).collect()
}

/// get_rotate_crop_image.
fn rotate_crop(img: &Img, b: &[(f32, f32); 4]) -> Img {
    let w = norm32(b[0], b[1]).max(norm32(b[2], b[3])) as usize;
    let h = norm32(b[0], b[3]).max(norm32(b[1], b[2])) as usize;
    let dst = [(0.0, 0.0), (w as f32, 0.0), (w as f32, h as f32), (0.0, h as f32)];
    let m = cv::get_perspective_transform(b, &dst);
    let crop = cv::warp_perspective_cubic_replicate(img, &m, w, h);
    if crop.h as f64 * 1.0 / crop.w as f64 >= 1.5 { cv::rot90(&crop) } else { crop }
}

/// resize_norm_img of the classifier (fixed width) and the recognizer: height `img_h`, width
/// ceil(img_h * ratio) capped at `img_w`, (x / 255 - 0.5) / 0.5 in float32, zero padded.
fn resize_norm(img: &Img, img_h: usize, img_w: usize, _rec: Option<usize>) -> Vec<f32> {
    let ratio = img.w as f64 / img.h as f64;
    let resized_w = if (img_h as f64 * ratio).ceil() > img_w as f64 { img_w } else { (img_h as f64 * ratio).ceil() as usize };
    let resized = cv::resize_linear(img, resized_w, img_h);
    let mut out = vec![0f32; 3 * img_h * img_w];
    for y in 0..img_h {
        for x in 0..resized_w {
            for c in 0..3 {
                let v = resized.data[(y * resized_w + x) * 3 + c] as f32 / 255.0;
                out[c * img_h * img_w + y * img_w + x] = (v - 0.5) / 0.5;
            }
        }
    }
    out
}
