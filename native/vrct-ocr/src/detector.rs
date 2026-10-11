//! ocr_bubble_detector.BubbleDetector: letterbox (BGR, 0-255, top-left, canvas rounded up to 32),
//! the YOLOX graph (decoding is inside it), score threshold, NMS, back to frame coordinates and
//! the padded crop. numpy's float32 arithmetic and argsort order are kept.
use crate::cv::{self, Img};
use crate::{R, npy};
use ort::session::Session;
use ort::value::Tensor;
use std::path::Path;

pub const MODEL_FILE_NAME: &str = "chatbox_yolox_tiny.onnx";
const IMAGE_SIZE: f64 = 1280.0;
const CONFIDENCE: f32 = 0.7;
const NMS_IOU: f32 = 0.65;
const PAD_COLOR: f32 = 114.0;
const SIZE_MULTIPLE: usize = 32;
const CROP_PADDING: i64 = 4;

/// (x, y, w, h) in the frame
pub type BBox = [i64; 4];

pub struct BubbleDetector {
    session: Session,
    input_name: String,
}

impl BubbleDetector {
    pub fn new(model_path: &Path) -> R<Self> {
        let session = crate::cpu_session(model_path)?;
        let input_name = session.inputs()[0].name().to_string();
        Ok(Self { session, input_name })
    }

    /// detect(frame): the bubbles, most confident first, with their crops.
    pub fn detect(&mut self, frame: &Img) -> R<Vec<(BBox, Img)>> {
        let (w, h) = (frame.w, frame.h);
        if w == 0 || h == 0 {
            return Ok(vec![]);
        }
        let (tensor, shape, scale) = letterbox(frame);
        let out = self.session.run(ort::inputs![self.input_name.as_str() => Tensor::from_array((shape, tensor))?])?;
        let predictions = out[0].try_extract_tensor::<f32>()?.1;
        let mut boxes = vec![];
        let mut scores = vec![];
        for p in predictions.chunks_exact(6) {
            let score = p[4] * p[5];
            if score >= CONFIDENCE {
                let (half_w, half_h) = (p[2] / 2.0, p[3] / 2.0);
                boxes.push([p[0] - half_w, p[1] - half_h, p[0] + half_w, p[1] + half_h]);
                scores.push(score);
            }
        }
        let mut results = vec![];
        for index in non_max_suppression(&boxes, &scores, NMS_IOU) {
            // int(round(np.float32 / float)): float64, half to even
            let to = |v: f32| (v as f64 / scale).round_ties_even() as i64;
            let b = boxes[index];
            let x0 = (to(b[0]) - CROP_PADDING).max(0);
            let y0 = (to(b[1]) - CROP_PADDING).max(0);
            let x1 = (to(b[2]) + CROP_PADDING).min(w as i64);
            let y1 = (to(b[3]) + CROP_PADDING).min(h as i64);
            if x1 - x0 < 2 || y1 - y0 < 2 {
                continue;
            }
            results.push(([x0, y0, x1 - x0, y1 - y0], crop(frame, x0 as usize, y0 as usize, x1 as usize, y1 as usize)));
        }
        Ok(results)
    }
}

fn crop(frame: &Img, x0: usize, y0: usize, x1: usize, y1: usize) -> Img {
    let c = frame.c;
    let mut out = Img::new(x1 - x0, y1 - y0, c);
    for y in y0..y1 {
        let src = &frame.data[(y * frame.w + x0) * c..(y * frame.w + x1) * c];
        out.data[(y - y0) * out.w * c..(y - y0 + 1) * out.w * c].copy_from_slice(src);
    }
    out
}

/// BubbleDetector._letterbox: (tensor, shape, scale)
fn letterbox(frame: &Img) -> (Vec<f32>, [usize; 4], f64) {
    let (w, h) = (frame.w, frame.h);
    let scale = (IMAGE_SIZE / w as f64).min(IMAGE_SIZE / h as f64);
    let nw = ((w as f64 * scale) as usize).max(1);
    let nh = ((h as f64 * scale) as usize).max(1);
    let resized = cv::resize_linear(frame, nw, nh);
    let cw = nw.div_ceil(SIZE_MULTIPLE) * SIZE_MULTIPLE;
    let ch = nh.div_ceil(SIZE_MULTIPLE) * SIZE_MULTIPLE;
    let mut tensor = vec![PAD_COLOR; 3 * ch * cw];
    for y in 0..nh {
        for x in 0..nw {
            for c in 0..3 {
                tensor[c * ch * cw + y * cw + x] = resized.data[(y * nw + x) * 3 + c] as f32;
            }
        }
    }
    (tensor, [1, 3, ch, cw], scale)
}

/// nonMaxSuppression: `scores.argsort()[::-1]` order, float32 overlap ratios.
fn non_max_suppression(boxes: &[[f32; 4]], scores: &[f32], threshold: f32) -> Vec<usize> {
    let mut order = npy::argsort(&scores.iter().map(|&s| s as f64).collect::<Vec<_>>());
    order.reverse();
    let area = |b: &[f32; 4]| (b[2] - b[0]) * (b[3] - b[1]);
    let mut keep = vec![];
    while let Some((&current, rest)) = order.split_first() {
        keep.push(current);
        let c = boxes[current];
        order = rest
            .iter()
            .copied()
            .filter(|&r| {
                let b = boxes[r];
                let overlap = (c[2].min(b[2]) - c[0].max(b[0])).max(0.0) * (c[3].min(b[3]) - c[1].max(b[1])).max(0.0);
                let union = area(&c) + area(&b) - overlap;
                overlap / union.max(1e-6) <= threshold
            })
            .collect();
    }
    keep
}
