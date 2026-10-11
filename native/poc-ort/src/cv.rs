//! The OpenCV operations RapidOCR uses, ported so the results match opencv-python 4.11.0 on Windows
//! bit for bit (fixed-point tables, rounding, float/double mixes and evaluation order kept as written).
//!
//! Ported from OpenCV 4.11.0 (https://github.com/opencv/opencv): imgproc/src/resize.cpp,
//! imgwarp.cpp, imgwarp.sse4_1.cpp, contours_new.cpp, contours_common.hpp, convhull.cpp,
//! rotcalipers.cpp, drawing.cpp, morph; core/src/types.cpp, lapack.cpp, matrix_decomp.cpp,
//! mean.dispatch.cpp, sum.simd.hpp.
//! Copyright (C) 2000-2022, Intel Corporation, OpenCV Foundation, and other contributors.
//! Licensed under the Apache License, Version 2.0 (see LICENSE-APACHE-2.0 in this crate);
//! this file is a modified, translated version of those sources.
//!
//! opencv-python 4.11.0 for Windows is built with MSVC 19.0, /fp:precise, SSE3 baseline, no
//! LAPACK, and IPP disabled for the functions used here (warp/remap by OpenCV, 8-bit linear resize
//! by ipp_resize's own check, mean by OPENCV_IPP_MEAN being off).

/// HWC 8-bit image.
#[derive(Clone)]
pub struct Img {
    pub w: usize,
    pub h: usize,
    pub c: usize,
    pub data: Vec<u8>,
}

impl Img {
    pub fn new(w: usize, h: usize, c: usize) -> Img {
        Img { w, h, c, data: vec![0; w * h * c] }
    }
}

/// saturate_cast<int>(double) / cvRound: round half to even (cvtsd2si with the default MXCSR).
fn cv_round(v: f64) -> i32 {
    let r = v.round_ties_even();
    r.clamp(i32::MIN as f64, i32::MAX as f64) as i32
}

fn sat_short(v: i32) -> i16 {
    v.clamp(i16::MIN as i32, i16::MAX as i32) as i16
}

// ------------------------------------------------------------------------------------ resize

const INTER_RESIZE_COEF_SCALE: f32 = 2048.0;

/// cv::resize(src, (nw, nh), INTER_LINEAR) for 8-bit images (hal::resize, resizeGeneric_ with
/// HResizeLinear / VResizeLinearVec_32s8u, or resizeAreaFast_ for an exact 2x reduction).
pub fn resize_linear(src: &Img, nw: usize, nh: usize) -> Img {
    let (w, h, cn) = (src.w, src.h, src.c);
    if nw == w && nh == h {
        return src.clone();
    }
    let inv_scale_x = nw as f64 / w as f64;
    let inv_scale_y = nh as f64 / h as f64;
    let (scale_x, scale_y) = (1.0 / inv_scale_x, 1.0 / inv_scale_y);
    let (iscale_x, iscale_y) = (cv_round(scale_x), cv_round(scale_y));
    let is_area_fast =
        (scale_x - iscale_x as f64).abs() < f64::EPSILON && (scale_y - iscale_y as f64).abs() < f64::EPSILON;
    let mut dst = Img::new(nw, nh, cn);
    if is_area_fast && iscale_x == 2 && iscale_y == 2 {
        // INTER_LINEAR with scale 2 becomes INTER_AREA (fast): (a + b + c + d + 2) >> 2
        for dy in 0..nh {
            let (s0, s1) = (&src.data[(2 * dy) * w * cn..], &src.data[(2 * dy + 1) * w * cn..]);
            for dx in 0..nw {
                for k in 0..cn {
                    let i = dx * 2 * cn + k;
                    let v = s0[i] as i32 + s0[i + cn] as i32 + s1[i] as i32 + s1[i + cn] as i32 + 2;
                    dst.data[(dy * nw + dx) * cn + k] = (v >> 2) as u8;
                }
            }
        }
        return dst;
    }
    // x taps: sx clamped with fx = 0 at the borders; dx >= xmax uses S[sx] * ONE only
    let mut xofs = vec![0usize; nw];
    let mut ialpha = vec![[0i32; 2]; nw];
    let mut xmax = nw;
    for dx in 0..nw {
        let mut fx = ((dx as f64 + 0.5) * scale_x - 0.5) as f32;
        let mut sx = fx.floor() as i64;
        fx -= sx as f32;
        if sx < 0 {
            fx = 0.0;
            sx = 0;
        }
        if sx + 1 >= w as i64 {
            xmax = xmax.min(dx);
            if sx >= w as i64 - 1 {
                fx = 0.0;
                sx = w as i64 - 1;
            }
        }
        xofs[dx] = sx as usize;
        ialpha[dx] = [
            cv_round(((1.0 - fx) * INTER_RESIZE_COEF_SCALE) as f64),
            cv_round((fx * INTER_RESIZE_COEF_SCALE) as f64),
        ];
    }
    let hrow = |y: usize, row: &mut [i32]| {
        let s = &src.data[y * w * cn..(y + 1) * w * cn];
        for dx in 0..nw {
            let sx = xofs[dx] * cn;
            for k in 0..cn {
                row[dx * cn + k] = if dx < xmax {
                    s[sx + k] as i32 * ialpha[dx][0] + s[sx + cn + k] as i32 * ialpha[dx][1]
                } else {
                    s[sx + k] as i32 * 2048
                };
            }
        }
    };
    let width = nw * cn;
    let (mut row0, mut row1) = (vec![0i32; width], vec![0i32; width]);
    for dy in 0..nh {
        // y is not clamped: the rows are, the betas are not
        let fy0 = ((dy as f64 + 0.5) * scale_y - 0.5) as f32;
        let sy = fy0.floor() as i64;
        let fy = fy0 - sy as f32;
        let b0 = cv_round(((1.0 - fy) * INTER_RESIZE_COEF_SCALE) as f64) as i16 as i32;
        let b1 = cv_round((fy * INTER_RESIZE_COEF_SCALE) as f64) as i16 as i32;
        let clip = |v: i64| v.clamp(0, h as i64 - 1) as usize;
        hrow(clip(sy), &mut row0);
        hrow(clip(sy + 1), &mut row1);
        let out = &mut dst.data[dy * width..(dy + 1) * width];
        for i in 0..width {
            // VResizeLinearVec_32s8u and its scalar tail: ((b0*(S0>>4))>>16) + ((b1*(S1>>4))>>16) + 2 >> 2
            let v = (((b0 * (row0[i] >> 4)) >> 16) + ((b1 * (row1[i] >> 4)) >> 16) + 2) >> 2;
            out[i] = v.clamp(0, 255) as u8;
        }
    }
    dst
}

/// cv::copyMakeBorder(BORDER_CONSTANT, 0) on the top and bottom.
pub fn pad_vertical(src: &Img, top: usize, bottom: usize) -> Img {
    let mut dst = Img::new(src.w, src.h + top + bottom, src.c);
    let row = src.w * src.c;
    dst.data[top * row..(top + src.h) * row].copy_from_slice(&src.data);
    dst
}

/// cv::rotate(img, ROTATE_180).
pub fn rotate_180(src: &Img) -> Img {
    let mut dst = Img::new(src.w, src.h, src.c);
    let n = src.w * src.h;
    for i in 0..n {
        dst.data[i * src.c..(i + 1) * src.c].copy_from_slice(&src.data[(n - 1 - i) * src.c..(n - i) * src.c]);
    }
    dst
}

/// np.rot90(img): 90 degrees counter-clockwise, out[i][j] = in[j][w-1-i].
pub fn rot90(src: &Img) -> Img {
    let mut dst = Img::new(src.h, src.w, src.c);
    for i in 0..src.w {
        for j in 0..src.h {
            let s = (j * src.w + (src.w - 1 - i)) * src.c;
            let d = (i * src.h + j) * src.c;
            dst.data[d..d + src.c].copy_from_slice(&src.data[s..s + src.c]);
        }
    }
    dst
}

/// cv::dilate with the 2x2 kernel of ones (anchor (1,1)): max of (y-1..y, x-1..x).
pub fn dilate_2x2(src: &[u8], w: usize, h: usize) -> Vec<u8> {
    let mut dst = vec![0u8; w * h];
    for y in 0..h {
        for x in 0..w {
            let mut m = src[y * w + x];
            if x > 0 {
                m = m.max(src[y * w + x - 1]);
            }
            if y > 0 {
                m = m.max(src[(y - 1) * w + x]);
                if x > 0 {
                    m = m.max(src[(y - 1) * w + x - 1]);
                }
            }
            dst[y * w + x] = m;
        }
    }
    dst
}

// ------------------------------------------------------------------------------ findContours

const CHAIN_DELTAS: [(i32, i32); 8] = [(1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1)];
const MASK8_RIGHT: i8 = -128; // 0x80
const MASK8_NEW: i8 = 2;
const MASK8_FLAGS: i8 = -2; // 0xFE

/// cv::findContours(bitmap, RETR_LIST, CHAIN_APPROX_SIMPLE) (contours_new.cpp). `bitmap` is
/// 0 / non-zero. Contours come out in the order OpenCV returns them (last found first).
pub fn find_contours_list_simple(bitmap: &[u8], w: usize, h: usize) -> Vec<Vec<(i32, i32)>> {
    // copyMakeBorder 1px + threshold to 0/1, read as schar
    let (pw, ph) = (w + 2, h + 2);
    let mut img = vec![0i8; pw * ph];
    for y in 0..h {
        for x in 0..w {
            img[(y + 1) * pw + x + 1] = (bitmap[y * w + x] != 0) as i8;
        }
    }
    let step = pw as isize;
    let delta = |s: i8| -> isize {
        let (dx, dy) = CHAIN_DELTAS[(s % 8) as usize];
        dx as isize + dy as isize * step
    };
    let mut found = Vec::new();
    let (width, height) = (pw - 1, ph - 1);
    let (mut x, mut y) = (1usize, 1usize);
    let mut prev: i32 = img[y * pw + x - 1] as i32;
    'scan: while y < height {
        let mut p: i32 = 0;
        while x < width {
            // findNextX
            while x < width {
                p = img[y * pw + x] as i32;
                if p != prev {
                    break;
                }
                x += 1;
            }
            if x >= width {
                break;
            }
            // contourScan (RETR_LIST: every contour's parent is the root)
            let is_hole = if prev == 0 && p == 1 {
                Some(false)
            } else if p != 0 || prev < 1 {
                None
            } else {
                Some(true)
            };
            if let Some(is_hole) = is_hole {
                let start = (x - is_hole as usize, y);
                found.push(fetch_contour(&mut img, pw, start, is_hole, &delta));
                // the scanner resumes at x + 1 with prev re-read from the (now marked) image
                x += 1;
                prev = img[y * pw + x - 1] as i32;
                continue 'scan;
            }
            prev = p;
            x += 1;
        }
        y += 1;
        x = 1;
        prev = 0;
    }
    let _ = MASK8_FLAGS;
    found.reverse();
    found
}

/// icvFetchContourEx<schar> for CHAIN_APPROX_SIMPLE with the scanner offset (-1, -1).
fn fetch_contour(img: &mut [i8], pw: usize, start: (usize, usize), is_hole: bool, delta: &dyn Fn(i8) -> isize) -> Vec<(i32, i32)> {
    let mut pts = Vec::new();
    let i0 = (start.1 * pw + start.0) as isize;
    let mut pt = (start.0 as i32 - 1, start.1 as i32 - 1);
    let s_end0: i8 = if is_hole { 0 } else { 4 };
    let mut s = s_end0;
    let mut i1;
    loop {
        s = (s - 1) & 7;
        i1 = i0 + delta(s);
        if img[i1 as usize] != 0 || s == s_end0 {
            break;
        }
    }
    if s == s_end0 {
        img[i0 as usize] = MASK8_NEW | MASK8_RIGHT;
        pts.push(pt);
        return pts;
    }
    let mut i3 = i0;
    let mut prev_s = s ^ 4;
    loop {
        let s_end = s;
        s = s.min(15);
        let mut i4 = i3;
        while s < 15 {
            s += 1;
            i4 = i3 + delta(s);
            if img[i4 as usize] != 0 {
                break;
            }
        }
        s &= 7;
        if ((s as i32 - 1) as u32) < (s_end as i32 as u32) {
            img[i3 as usize] = MASK8_NEW | MASK8_RIGHT;
        } else if img[i3 as usize] == 1 {
            img[i3 as usize] = MASK8_NEW;
        }
        if s != prev_s {
            pts.push(pt);
        }
        prev_s = s;
        pt.0 += CHAIN_DELTAS[s as usize].0;
        pt.1 += CHAIN_DELTAS[s as usize].1;
        if i4 == i0 && i3 == i1 {
            break;
        }
        i3 = i4;
        s = (s + 4) & 7;
    }
    pts
}

// --------------------------------------------------------------------------------- convexHull

fn sign(v: i64) -> i32 {
    (v > 0) as i32 - (v < 0) as i32
}

/// Sklansky_<int, int64> over indices into `p` (sorted points).
fn sklansky(p: &[(i32, i32)], start: usize, end: usize, stack: &mut [usize], nsign: i32, sign2: i32) -> usize {
    let incr: isize = if end > start { 1 } else { -1 };
    let (mut pprev, mut pcur) = (start as isize, start as isize + incr);
    let mut pnext = pcur + incr;
    let mut stacksize = 3usize;
    if start == end || (p[start].0 == p[end].0 && p[start].1 == p[end].1) {
        stack[0] = start;
        return 1;
    }
    stack[0] = pprev as usize;
    stack[1] = pcur as usize;
    stack[2] = pnext as usize;
    let end = end as isize + incr;
    while pnext != end {
        let cury = p[pcur as usize].1;
        let nexty = p[pnext as usize].1;
        let by = nexty - cury;
        if sign(by as i64) != nsign {
            let ax = p[pcur as usize].0 - p[pprev as usize].0;
            let bx = p[pnext as usize].0 - p[pcur as usize].0;
            let ay = cury - p[pprev as usize].1;
            let convexity = ay as i64 * bx as i64 - ax as i64 * by as i64;
            if sign(convexity) == sign2 && (ax != 0 || ay != 0) {
                pprev = pcur;
                pcur = pnext;
                pnext += incr;
                stack[stacksize] = pnext as usize;
                stacksize += 1;
            } else if pprev == start as isize {
                pcur = pnext;
                stack[1] = pcur as usize;
                pnext += incr;
                stack[2] = pnext as usize;
            } else {
                stack[stacksize - 2] = pnext as usize;
                pcur = pprev;
                pprev = stack[stacksize - 4] as isize;
                stacksize -= 1;
            }
        } else {
            pnext += incr;
            stack[stacksize - 1] = pnext as usize;
        }
    }
    stacksize - 1
}

/// cv::convexHull(points, clockwise=false, returnPoints=true) for integer points.
pub fn convex_hull(points: &[(i32, i32)]) -> Vec<(i32, i32)> {
    let total = points.len();
    if total == 0 {
        return vec![];
    }
    // sort by x, y, then position (the comparator breaks ties on the pointer)
    let mut order: Vec<usize> = (0..total).collect();
    order.sort_by(|&a, &b| (points[a].0, points[a].1, a).cmp(&(points[b].0, points[b].1, b)));
    let p: Vec<(i32, i32)> = order.iter().map(|&i| points[i]).collect();
    let (mut miny_ind, mut maxy_ind) = (0usize, 0usize);
    for i in 1..total {
        let y = p[i].1;
        if p[miny_ind].1 > y {
            miny_ind = i;
        }
        if p[maxy_ind].1 < y {
            maxy_ind = i;
        }
    }
    let mut hullbuf: Vec<usize> = Vec::with_capacity(total);
    let mut stack = vec![0usize; total + 2];
    if p[0] == p[total - 1] {
        hullbuf.push(0);
    } else {
        // upper half
        let n_left = sklansky(&p, 0, maxy_ind, &mut stack, -1, 1);
        let left = stack[..n_left].to_vec();
        let n_right = sklansky(&p, total - 1, maxy_ind, &mut stack[n_left..], -1, -1);
        let right = stack[n_left..n_left + n_right].to_vec();
        // !clockwise: the two halves swap roles
        let (tl_stack, tl_count, tr_stack, tr_count) = (right, n_right, left, n_left);
        for &i in &tl_stack[..tl_count - 1] {
            hullbuf.push(i);
        }
        for i in (1..tr_count).rev() {
            hullbuf.push(tr_stack[i]);
        }
        let stop_idx: isize = if tr_count > 2 {
            tr_stack[1] as isize
        } else if tl_count > 2 {
            tl_stack[tl_count - 2] as isize
        } else {
            -1
        };
        // lower half
        let mut bl_count = sklansky(&p, 0, miny_ind, &mut stack, 1, -1);
        let bl_stack: Vec<usize> = stack[..bl_count].to_vec();
        let mut br_count = sklansky(&p, total - 1, miny_ind, &mut stack[bl_count..], 1, 1);
        let br_stack: Vec<usize> = stack[bl_count..bl_count + br_count].to_vec();
        if stop_idx >= 0 {
            let check_idx: isize = if bl_count > 2 {
                bl_stack[1] as isize
            } else if bl_count + br_count > 2 {
                br_stack[2 - bl_count] as isize
            } else {
                -1
            };
            if check_idx == stop_idx
                || (check_idx >= 0 && p[check_idx as usize] == p[stop_idx as usize])
            {
                bl_count = bl_count.min(2);
                br_count = br_count.min(2);
            }
        }
        for &i in &bl_stack[..bl_count - 1] {
            hullbuf.push(i);
        }
        for i in (1..br_count).rev() {
            hullbuf.push(br_stack[i]);
        }
        // cyclic shift so that the (original) indices are monotonic, if possible
        let nout = hullbuf.len();
        if nout >= 3 {
            let orig = |k: usize| order[hullbuf[k]];
            let (mut min_idx, mut max_idx, mut lt) = (0usize, 0usize, 0usize);
            let mut i = 1;
            while i < nout {
                let idx = orig(i);
                lt += (orig(i - 1) < idx) as usize;
                if lt > 1 && lt + 2 <= i {
                    break;
                }
                if idx < orig(min_idx) {
                    min_idx = i;
                }
                if idx > orig(max_idx) {
                    max_idx = i;
                }
                i += 1;
            }
            let mmdist = (max_idx as isize - min_idx as isize).unsigned_abs();
            if (mmdist == 1 || mmdist == nout - 1) && (lt <= 1 || lt + 2 >= nout) {
                let ascending = (max_idx + 1) % nout == min_idx;
                let i0 = if ascending { min_idx } else { max_idx };
                let mut j = i0;
                if i0 > 0 {
                    let mut shifted = Vec::with_capacity(nout);
                    let mut i = 0;
                    while i < nout {
                        let curr = hullbuf[j];
                        shifted.push(curr);
                        let next_j = if j + 1 < nout { j + 1 } else { 0 };
                        let next = hullbuf[next_j];
                        if i < nout - 1 && (ascending != (order[curr] < order[next])) {
                            break;
                        }
                        j = next_j;
                        i += 1;
                    }
                    if i == nout {
                        hullbuf = shifted;
                    }
                }
            }
        }
    }
    hullbuf.iter().map(|&i| p[i]).collect()
}

// ------------------------------------------------------------------- minAreaRect / boxPoints

#[derive(Clone, Copy, Debug)]
pub struct RotatedRect {
    pub cx: f32,
    pub cy: f32,
    pub w: f32,
    pub h: f32,
    pub angle: f32,
}

/// rotatingCalipers(CALIPERS_MINAREARECT): corner, vector1, vector2.
fn rotating_calipers(pts: &[(f32, f32)]) -> [(f32, f32); 3] {
    let n = pts.len();
    let mut vect = vec![(0f32, 0f32); n];
    let mut inv_len = vec![0f32; n];
    let (mut left, mut bottom, mut right, mut top) = (0usize, 0usize, 0usize, 0usize);
    let mut pt0 = pts[0];
    let (mut left_x, mut right_x, mut top_y, mut bottom_y) = (pt0.0, pt0.0, pt0.1, pt0.1);
    for i in 0..n {
        if pt0.0 < left_x {
            left_x = pt0.0;
            left = i;
        }
        if pt0.0 > right_x {
            right_x = pt0.0;
            right = i;
        }
        if pt0.1 > top_y {
            top_y = pt0.1;
            top = i;
        }
        if pt0.1 < bottom_y {
            bottom_y = pt0.1;
            bottom = i;
        }
        let pt = pts[if i + 1 < n { i + 1 } else { 0 }];
        let dx = (pt.0 - pt0.0) as f64;
        let dy = (pt.1 - pt0.1) as f64;
        vect[i] = (dx as f32, dy as f32);
        inv_len[i] = (1.0 / (dx * dx + dy * dy).sqrt()) as f32;
        pt0 = pt;
    }
    let mut orientation = 0f32;
    {
        let (mut ax, mut ay) = (vect[n - 1].0 as f64, vect[n - 1].1 as f64);
        for v in &vect {
            let (bx, by) = (v.0 as f64, v.1 as f64);
            let convexity = ax * by - ay * bx;
            if convexity != 0.0 {
                orientation = if convexity > 0.0 { 1.0 } else { -1.0 };
                break;
            }
            ax = bx;
            ay = by;
        }
        assert!(orientation != 0.0);
    }
    // the calipers' base starts as (orientation, 0) but every iteration sets it before use
    let (mut base_a, mut base_b): (f32, f32);
    let mut seq = [bottom, right, top, left];
    let mut minarea = f32::MAX;
    let mut buf: (usize, f32, f32, f32, f32, usize) = (0, 0.0, 0.0, 0.0, 0.0, 0);
    let first_vec_is_right = |v1: (f32, f32), v2: (f32, f32)| (v1.1 * v2.0 + (-v1.0) * v2.1) < 0.0;
    for _ in 0..n {
        let mut main_element = 0usize;
        let rot = [
            vect[seq[0]],
            (vect[seq[1]].1, -vect[seq[1]].0),
            (-vect[seq[2]].0, -vect[seq[2]].1),
            (-vect[seq[3]].1, vect[seq[3]].0),
        ];
        for i in 1..4 {
            if first_vec_is_right(rot[i], rot[main_element]) {
                main_element = i;
            }
        }
        let pindex = seq[main_element];
        let lead_x = vect[pindex].0 * inv_len[pindex];
        let lead_y = vect[pindex].1 * inv_len[pindex];
        match main_element {
            0 => (base_a, base_b) = (lead_x, lead_y),
            1 => (base_a, base_b) = (lead_y, -lead_x),
            2 => (base_a, base_b) = (-lead_x, -lead_y),
            _ => (base_a, base_b) = (-lead_y, lead_x),
        }
        seq[main_element] += 1;
        if seq[main_element] == n {
            seq[main_element] = 0;
        }
        let dx = pts[seq[1]].0 - pts[seq[3]].0;
        let dy = pts[seq[1]].1 - pts[seq[3]].1;
        let width = dx * base_a + dy * base_b;
        let dx = pts[seq[2]].0 - pts[seq[0]].0;
        let dy = pts[seq[2]].1 - pts[seq[0]].1;
        let height = -dx * base_b + dy * base_a;
        let area = width * height;
        if area <= minarea {
            minarea = area;
            buf = (seq[3], base_a, width, base_b, height, seq[0]);
        }
    }
    let (a1, b1) = (buf.1, buf.3);
    let (a2, b2) = (-buf.3, buf.1);
    let c1 = a1 * pts[buf.0].0 + pts[buf.0].1 * b1;
    let c2 = a2 * pts[buf.5].0 + pts[buf.5].1 * b2;
    let idet = 1.0f32 / (a1 * b2 - a2 * b1);
    let px = (c1 * b2 - c2 * b1) * idet;
    let py = (a1 * c2 - a2 * c1) * idet;
    [(px, py), (a1 * buf.2, b1 * buf.2), (a2 * buf.4, b2 * buf.4)]
}

/// cv::minAreaRect for integer points.
pub fn min_area_rect(points: &[(i32, i32)]) -> RotatedRect {
    let hull: Vec<(f32, f32)> = convex_hull(points).iter().map(|&(x, y)| (x as f32, y as f32)).collect();
    let n = hull.len();
    let mut r = RotatedRect { cx: 0.0, cy: 0.0, w: 0.0, h: 0.0, angle: 0.0 };
    if n > 2 {
        let out = rotating_calipers(&hull);
        r.cx = out[0].0 + (out[1].0 + out[2].0) * 0.5;
        r.cy = out[0].1 + (out[1].1 + out[2].1) * 0.5;
        r.w = ((out[1].0 as f64) * out[1].0 as f64 + (out[1].1 as f64) * out[1].1 as f64).sqrt() as f32;
        r.h = ((out[2].0 as f64) * out[2].0 as f64 + (out[2].1 as f64) * out[2].1 as f64).sqrt() as f32;
        r.angle = (out[1].1 as f64).atan2(out[1].0 as f64) as f32;
    } else if n == 2 {
        r.cx = (hull[0].0 + hull[1].0) * 0.5;
        r.cy = (hull[0].1 + hull[1].1) * 0.5;
        let dx = (hull[1].0 - hull[0].0) as f64;
        let dy = (hull[1].1 - hull[0].1) as f64;
        r.w = (dx * dx + dy * dy).sqrt() as f32;
        r.angle = dy.atan2(dx) as f32;
    } else if n == 1 {
        r.cx = hull[0].0;
        r.cy = hull[0].1;
    }
    r.angle = ((r.angle * 180.0) as f64 / std::f64::consts::PI) as f32;
    r
}

/// cv::boxPoints (RotatedRect::points).
pub fn box_points(r: &RotatedRect) -> [(f32, f32); 4] {
    let angle = r.angle as f64 * std::f64::consts::PI / 180.0;
    let b = angle.cos() as f32 * 0.5;
    let a = angle.sin() as f32 * 0.5;
    let p0 = (r.cx - a * r.h - b * r.w, r.cy + b * r.h - a * r.w);
    let p1 = (r.cx + a * r.h - b * r.w, r.cy - b * r.h - a * r.w);
    [p0, p1, (2.0 * r.cx - p0.0, 2.0 * r.cy - p0.1), (2.0 * r.cx - p1.0, 2.0 * r.cy - p1.1)]
}

// ---------------------------------------------------------------------------------- fillPoly

/// clipLine(Size2l, Point2l&, Point2l&).
fn clip_line(w: i64, h: i64, p1: &mut (i64, i64), p2: &mut (i64, i64)) -> bool {
    let (right, bottom) = (w - 1, h - 1);
    if w <= 0 || h <= 0 {
        return false;
    }
    let code = |p: (i64, i64)| (p.0 < 0) as i32 + (p.0 > right) as i32 * 2 + (p.1 < 0) as i32 * 4 + (p.1 > bottom) as i32 * 8;
    let (mut c1, mut c2) = (code(*p1), code(*p2));
    if (c1 & c2) == 0 && (c1 | c2) != 0 {
        if c1 & 12 != 0 {
            let a = if c1 < 8 { 0 } else { bottom };
            p1.0 += ((a - p1.1) as f64 * (p2.0 - p1.0) as f64 / (p2.1 - p1.1) as f64) as i64;
            p1.1 = a;
            c1 = (p1.0 < 0) as i32 + (p1.0 > right) as i32 * 2;
        }
        if c2 & 12 != 0 {
            let a = if c2 < 8 { 0 } else { bottom };
            p2.0 += ((a - p2.1) as f64 * (p2.0 - p1.0) as f64 / (p2.1 - p1.1) as f64) as i64;
            p2.1 = a;
            c2 = (p2.0 < 0) as i32 + (p2.0 > right) as i32 * 2;
        }
        if (c1 & c2) == 0 && (c1 | c2) != 0 {
            if c1 != 0 {
                let a = if c1 == 1 { 0 } else { right };
                p1.1 += ((a - p1.0) as f64 * (p2.1 - p1.1) as f64 / (p2.0 - p1.0) as f64) as i64;
                p1.0 = a;
                c1 = 0;
            }
            if c2 != 0 {
                let a = if c2 == 1 { 0 } else { right };
                p2.1 += ((a - p2.0) as f64 * (p2.1 - p1.1) as f64 / (p2.0 - p1.0) as f64) as i64;
                p2.0 = a;
                c2 = 0;
            }
        }
    }
    (c1 | c2) == 0
}

/// Line(img, pt1, pt2, color, 8): LineIterator with leftToRight, connectivity 8.
fn draw_line(mask: &mut [u8], w: usize, h: usize, p1: (i64, i64), p2: (i64, i64), color: u8) {
    let (mut p1, mut p2) = ((p1.0 as i32 as i64, p1.1 as i32 as i64), (p2.0 as i32 as i64, p2.1 as i32 as i64));
    if p1.0 < 0 || p1.0 >= w as i64 || p2.0 < 0 || p2.0 >= w as i64 || p1.1 < 0 || p1.1 >= h as i64 || p2.1 < 0 || p2.1 >= h as i64 {
        if !clip_line(w as i64, h as i64, &mut p1, &mut p2) {
            return;
        }
    }
    let (mut delta_x, mut delta_y) = (1i64, 1i64);
    let mut dx = p2.0 - p1.0;
    let mut dy = p2.1 - p1.1;
    if dx < 0 {
        dx = -dx;
        dy = -dy;
        p1 = p2;
    }
    if dy < 0 {
        dy = -dy;
        delta_y = -1;
    }
    let vert = dy > dx;
    if vert {
        std::mem::swap(&mut dx, &mut dy);
        std::mem::swap(&mut delta_x, &mut delta_y);
    }
    let mut err = dx - (dy + dy);
    let plus_delta = dx + dx;
    let minus_delta = -(dy + dy);
    let (mut minus_shift, mut plus_shift, mut minus_step, mut plus_step) = (delta_x, 0i64, 0i64, delta_y);
    let count = dx + 1;
    if vert {
        std::mem::swap(&mut plus_step, &mut plus_shift);
        std::mem::swap(&mut minus_step, &mut minus_shift);
    }
    let mut p = p1;
    for _ in 0..count {
        mask[p.1 as usize * w + p.0 as usize] = color;
        let m = if err < 0 { -1i64 } else { 0 };
        err += minus_delta + (plus_delta & m);
        p.0 += minus_shift + (plus_shift & m);
        p.1 += minus_step + (plus_step & m);
    }
}

struct PolyEdge {
    y0: i32,
    y1: i32,
    x: i64,
    dx: i64,
    next: usize, // index into edges, usize::MAX = none
}

const XY_SHIFT: i64 = 16;
const XY_ONE: i64 = 1 << XY_SHIFT;

/// cv::fillPoly(mask, [pts], color) with lineType 8 and shift 0.
pub fn fill_poly(mask: &mut [u8], w: usize, h: usize, v: &[(i32, i32)], color: u8) {
    let n = v.len();
    if n == 0 {
        return;
    }
    let mut edges: Vec<PolyEdge> = Vec::new();
    let mut pt0 = ((v[n - 1].0 as i64) << XY_SHIFT, v[n - 1].1 as i64);
    for i in 0..n {
        let pt1 = ((v[i].0 as i64) << XY_SHIFT, v[i].1 as i64);
        let (mut pt0c, mut pt1c) = (pt0, pt1);
        let mut t0 = ((pt0.0 + (XY_ONE >> 1)) >> XY_SHIFT, pt0.1);
        let mut t1 = ((pt1.0 + (XY_ONE >> 1)) >> XY_SHIFT, pt1.1);
        draw_line(mask, w, h, t0, t1, color);
        if t0.0 < 0 || t0.0 >= w as i64 || t1.0 < 0 || t1.0 >= w as i64 || t0.1 < 0 || t0.1 >= h as i64 || t1.1 < 0 || t1.1 >= h as i64 {
            clip_line(w as i64, h as i64, &mut t0, &mut t1);
            if t0.1 != t1.1 {
                pt0c.1 = t0.1;
                pt1c.1 = t1.1;
            }
        }
        pt0c.0 = t0.0 << XY_SHIFT;
        pt1c.0 = t1.0 << XY_SHIFT;
        if pt0.1 != pt1.1 {
            let dx = (pt1c.0 - pt0c.0) / (pt1c.1 - pt0c.1);
            let edge = if pt0.1 < pt1.1 {
                PolyEdge { y0: pt0.1 as i32, y1: pt1.1 as i32, x: pt0c.0 + (pt0.1 - pt0c.1) * dx, dx, next: usize::MAX }
            } else {
                PolyEdge { y0: pt1.1 as i32, y1: pt0.1 as i32, x: pt1c.0 + (pt1.1 - pt1c.1) * dx, dx, next: usize::MAX }
            };
            edges.push(edge);
        }
        pt0 = pt1;
    }
    fill_edge_collection(mask, w, h, edges, color);
}

fn fill_edge_collection(mask: &mut [u8], w: usize, h: usize, mut edges: Vec<PolyEdge>, color: u8) {
    let total = edges.len();
    if total < 2 {
        return;
    }
    let (mut y_max, mut y_min) = (i32::MIN, i32::MAX);
    let (mut x_max, mut x_min) = (-1i64, i64::MAX);
    for e in &edges {
        let x1 = e.x + (e.y1 - e.y0) as i64 * e.dx;
        y_min = y_min.min(e.y0);
        y_max = y_max.max(e.y1);
        x_min = x_min.min(e.x).min(x1);
        x_max = x_max.max(e.x).max(x1);
    }
    if y_max < 0 || y_min >= h as i32 || x_max < 0 || x_min >= (w as i64) << XY_SHIFT {
        return;
    }
    edges.sort_by(|a, b| {
        if a.y0 != b.y0 {
            a.y0.cmp(&b.y0)
        } else if a.x != b.x {
            a.x.cmp(&b.x)
        } else {
            a.dx.cmp(&b.dx)
        }
    });
    // sentinel, and "tmp" (the active list head) as index total + 1
    edges.push(PolyEdge { y0: i32::MAX, y1: 0, x: 0, dx: 0, next: usize::MAX });
    let tmp = total + 1;
    edges.push(PolyEdge { y0: 0, y1: 0, x: 0, dx: 0, next: usize::MAX });
    const NONE: usize = usize::MAX;
    let mut i = 0usize;
    let mut e = 0usize;
    let y_max = y_max.min(h as i32);
    let delta = XY_ONE - 1;
    let mut y = edges[e].y0;
    while y < y_max {
        let mut draw = 0;
        let clipline = y < 0;
        let mut prelast = tmp;
        let mut last = edges[tmp].next;
        while last != NONE || edges[e].y0 == y {
            if last != NONE && edges[last].y1 == y {
                edges[prelast].next = edges[last].next;
                last = edges[last].next;
                continue;
            }
            let keep_prelast = prelast;
            if last != NONE && (edges[e].y0 > y || edges[last].x < edges[e].x) {
                prelast = last;
                last = edges[last].next;
            } else if i < total {
                edges[prelast].next = e;
                edges[e].next = last;
                prelast = e;
                i += 1;
                e = i;
            } else {
                break;
            }
            if draw != 0 {
                if !clipline {
                    let (x1, x2) = if edges[keep_prelast].x > edges[prelast].x {
                        (((edges[prelast].x + delta) >> XY_SHIFT) as i32, (edges[keep_prelast].x >> XY_SHIFT) as i32)
                    } else {
                        (((edges[keep_prelast].x + delta) >> XY_SHIFT) as i32, (edges[prelast].x >> XY_SHIFT) as i32)
                    };
                    if x1 < w as i32 && x2 >= 0 {
                        let (x1, x2) = (x1.max(0), x2.min(w as i32 - 1));
                        for x in x1..=x2 {
                            mask[y as usize * w + x as usize] = color;
                        }
                    }
                }
                let d = edges[keep_prelast].dx;
                edges[keep_prelast].x += d;
                let d = edges[prelast].dx;
                edges[prelast].x += d;
            }
            draw ^= 1;
        }
        // bubble sort of the active list by x
        let mut keep_prelast = NONE;
        loop {
            prelast = tmp;
            last = edges[tmp].next;
            let mut last_exchange = NONE;
            while last != keep_prelast && edges[last].next != NONE {
                let te = edges[last].next;
                if edges[last].x > edges[te].x {
                    edges[prelast].next = te;
                    edges[last].next = edges[te].next;
                    edges[te].next = last;
                    prelast = te;
                    last_exchange = prelast;
                } else {
                    prelast = last;
                    last = te;
                }
            }
            if last_exchange == NONE {
                break;
            }
            keep_prelast = last_exchange;
            if keep_prelast == edges[tmp].next || keep_prelast == tmp {
                break;
            }
        }
        y += 1;
    }
}

/// cv::mean(src, mask)[0] for a float32 single-channel region (rows summed in order in double,
/// then multiplied by 1/count).
pub fn mean_masked(src: &[f32], stride: usize, x0: usize, y0: usize, w: usize, h: usize, mask: &[u8]) -> f64 {
    let mut s = 0f64;
    let mut nz = 0usize;
    for y in 0..h {
        for x in 0..w {
            if mask[y * w + x] != 0 {
                s += src[(y0 + y) * stride + x0 + x] as f64;
                nz += 1;
            }
        }
    }
    s * if nz != 0 { 1.0 / nz as f64 } else { 0.0 }
}

// ------------------------------------------------------------------- perspective transforms

/// hal::LU64f (LUImpl, eps = DBL_EPSILON * 100) solving a * x = b in place in b.
fn lu_solve(a: &mut [[f64; 8]; 8], b: &mut [f64; 8]) -> bool {
    let m = 8;
    let eps = f64::EPSILON * 100.0;
    for i in 0..m {
        let mut k = i;
        for j in i + 1..m {
            if a[j][i].abs() > a[k][i].abs() {
                k = j;
            }
        }
        if a[k][i].abs() < eps {
            return false;
        }
        if k != i {
            for j in i..m {
                let t = a[i][j];
                a[i][j] = a[k][j];
                a[k][j] = t;
            }
            b.swap(i, k);
        }
        let d = -1.0 / a[i][i];
        for j in i + 1..m {
            let alpha = a[j][i] * d;
            for k in i + 1..m {
                a[j][k] += alpha * a[i][k];
            }
            b[j] += alpha * b[i];
        }
    }
    for i in (0..m).rev() {
        let mut s = b[i];
        for k in i + 1..m {
            s -= a[i][k] * b[k];
        }
        b[i] = s / a[i][i];
    }
    true
}

/// cv::getPerspectiveTransform(src, dst) (DECOMP_LU) as a row-major 3x3.
pub fn get_perspective_transform(src: &[(f32, f32); 4], dst: &[(f32, f32); 4]) -> [f64; 9] {
    let mut a = [[0f64; 8]; 8];
    let mut b = [0f64; 8];
    for i in 0..4 {
        a[i][0] = src[i].0 as f64;
        a[i + 4][3] = src[i].0 as f64;
        a[i][1] = src[i].1 as f64;
        a[i + 4][4] = src[i].1 as f64;
        a[i][2] = 1.0;
        a[i + 4][5] = 1.0;
        a[i][6] = (-src[i].0 * dst[i].0) as f64;
        a[i][7] = (-src[i].1 * dst[i].0) as f64;
        a[i + 4][6] = (-src[i].0 * dst[i].1) as f64;
        a[i + 4][7] = (-src[i].1 * dst[i].1) as f64;
        b[i] = dst[i].0 as f64;
        b[i + 4] = dst[i].1 as f64;
    }
    lu_solve(&mut a, &mut b);
    [b[0], b[1], b[2], b[3], b[4], b[5], b[6], b[7], 1.0]
}

/// cv::invert for a 3x3 double matrix (the n == 3 branch).
fn invert3(m: &[f64; 9]) -> [f64; 9] {
    let s = |y: usize, x: usize| m[y * 3 + x];
    let det = s(0, 0) * (s(1, 1) * s(2, 2) - s(1, 2) * s(2, 1)) - s(0, 1) * (s(1, 0) * s(2, 2) - s(1, 2) * s(2, 0))
        + s(0, 2) * (s(1, 0) * s(2, 1) - s(1, 1) * s(2, 0));
    if det == 0.0 {
        return [0.0; 9];
    }
    let d = 1.0 / det;
    [
        (s(1, 1) * s(2, 2) - s(1, 2) * s(2, 1)) * d,
        (s(0, 2) * s(2, 1) - s(0, 1) * s(2, 2)) * d,
        (s(0, 1) * s(1, 2) - s(0, 2) * s(1, 1)) * d,
        (s(1, 2) * s(2, 0) - s(1, 0) * s(2, 2)) * d,
        (s(0, 0) * s(2, 2) - s(0, 2) * s(2, 0)) * d,
        (s(0, 2) * s(1, 0) - s(0, 0) * s(1, 2)) * d,
        (s(1, 0) * s(2, 1) - s(1, 1) * s(2, 0)) * d,
        (s(0, 1) * s(2, 0) - s(0, 0) * s(2, 1)) * d,
        (s(0, 0) * s(1, 1) - s(0, 1) * s(1, 0)) * d,
    ]
}

const INTER_BITS: i32 = 5;
const INTER_TAB_SIZE: i32 = 1 << INTER_BITS;
const INTER_REMAP_COEF_BITS: i32 = 15;
const INTER_REMAP_COEF_SCALE: i32 = 1 << INTER_REMAP_COEF_BITS;

/// BicubicTab_i of initInterTab2D(INTER_CUBIC, fixpt=true): [32*32][16].
fn bicubic_tab() -> Vec<[i32; 16]> {
    fn cubic(x: f32) -> [f32; 4] {
        const A: f32 = -0.75;
        let c0 = ((A * (x + 1.0) - 5.0 * A) * (x + 1.0) + 8.0 * A) * (x + 1.0) - 4.0 * A;
        let c1 = ((A + 2.0) * x - (A + 3.0)) * x * x + 1.0;
        let c2 = ((A + 2.0) * (1.0 - x) - (A + 3.0)) * (1.0 - x) * (1.0 - x) + 1.0;
        [c0, c1, c2, 1.0 - c0 - c1 - c2]
    }
    let scale = 1.0f32 / INTER_TAB_SIZE as f32;
    let tab1: Vec<[f32; 4]> = (0..INTER_TAB_SIZE).map(|i| cubic(i as f32 * scale)).collect();
    let mut out = Vec::with_capacity((INTER_TAB_SIZE * INTER_TAB_SIZE) as usize);
    for i in 0..INTER_TAB_SIZE as usize {
        for j in 0..INTER_TAB_SIZE as usize {
            let mut itab = [0i32; 16];
            let mut isum = 0;
            for k1 in 0..4 {
                let vy = tab1[i][k1];
                for k2 in 0..4 {
                    let v = vy * tab1[j][k2];
                    let iv = sat_short(cv_round((v * INTER_REMAP_COEF_SCALE as f32) as f64)) as i32;
                    itab[k1 * 4 + k2] = iv;
                    isum += iv;
                }
            }
            if isum != INTER_REMAP_COEF_SCALE {
                let diff = isum - INTER_REMAP_COEF_SCALE;
                let (mut mk1, mut mk2, mut big1, mut big2) = (2usize, 2usize, 2usize, 2usize);
                for k1 in 2..4 {
                    for k2 in 2..4 {
                        if itab[k1 * 4 + k2] < itab[mk1 * 4 + mk2] {
                            mk1 = k1;
                            mk2 = k2;
                        } else if itab[k1 * 4 + k2] > itab[big1 * 4 + big2] {
                            big1 = k1;
                            big2 = k2;
                        }
                    }
                }
                if diff < 0 {
                    itab[big1 * 4 + big2] = (itab[big1 * 4 + big2] - diff) as i16 as i32;
                } else {
                    itab[mk1 * 4 + mk2] = (itab[mk1 * 4 + mk2] - diff) as i16 as i32;
                }
            }
            out.push(itab);
        }
    }
    out
}

/// cv::warpPerspective(src, M, (dw, dh), flags=INTER_CUBIC, borderMode=BORDER_REPLICATE) for
/// 8-bit images: invert M, per 32x32-ish block compute the fixed-point source coordinates
/// (WarpPerspectiveLine_SSE4), then remapBicubic with FixedPtCast<int, uchar, 15>.
pub fn warp_perspective_cubic_replicate(src: &Img, m: &[f64; 9], dw: usize, dh: usize) -> Img {
    let m = invert3(m);
    let tab = bicubic_tab();
    let cn = src.c;
    let mut dst = Img::new(dw, dh, cn);
    if dw == 0 || dh == 0 {
        return dst;
    }
    let bh0 = 16.min(dh);
    let bw0 = (1024 / bh0).min(dw);
    let (sw, sh) = (src.w as i32, src.h as i32);
    let (width1, height1) = ((sw - 3).max(0) as u32, (sh - 3).max(0) as u32);
    for y in 0..dh {
        let mut x0 = 0;
        while x0 < dw {
            let bw = bw0.min(dw - x0);
            let xd = x0 as f64;
            let yd = y as f64;
            let big_x0 = m[0] * xd + m[1] * yd + m[2];
            let big_y0 = m[3] * xd + m[4] * yd + m[5];
            let w0 = m[6] * xd + m[7] * yd + m[8];
            for x1 in 0..bw {
                let x1d = x1 as f64;
                let mut wv = w0 + m[6] * x1d;
                wv = if wv != 0.0 { INTER_TAB_SIZE as f64 / wv } else { 0.0 };
                let fx = (i32::MIN as f64).max((i32::MAX as f64).min((big_x0 + m[0] * x1d) * wv));
                let fy = (i32::MIN as f64).max((i32::MAX as f64).min((big_y0 + m[3] * x1d) * wv));
                let (ix, iy) = (cv_round(fx), cv_round(fy));
                let xs = sat_short(ix >> INTER_BITS) as i32;
                let ys = sat_short(iy >> INTER_BITS) as i32;
                let alpha = ((iy & (INTER_TAB_SIZE - 1)) * INTER_TAB_SIZE + (ix & (INTER_TAB_SIZE - 1))) as usize;
                let w = &tab[alpha];
                let (sx, sy) = (xs - 1, ys - 1);
                let d = &mut dst.data[(y * dw + x0 + x1) * cn..(y * dw + x0 + x1 + 1) * cn];
                if (sx as u32) < width1 && (sy as u32) < height1 {
                    for k in 0..cn {
                        let at = |r: i32, c: i32| src.data[((sy + r) as usize * src.w + (sx + c) as usize) * cn + k] as i32;
                        let mut sum = at(0, 0) * w[0] + at(0, 1) * w[1] + at(0, 2) * w[2] + at(0, 3) * w[3];
                        sum += at(1, 0) * w[4] + at(1, 1) * w[5] + at(1, 2) * w[6] + at(1, 3) * w[7];
                        sum += at(2, 0) * w[8] + at(2, 1) * w[9] + at(2, 2) * w[10] + at(2, 3) * w[11];
                        sum += at(3, 0) * w[12] + at(3, 1) * w[13] + at(3, 2) * w[14] + at(3, 3) * w[15];
                        d[k] = ((sum + (1 << (INTER_REMAP_COEF_BITS - 1))) >> INTER_REMAP_COEF_BITS).clamp(0, 255) as u8;
                    }
                } else {
                    // BORDER_REPLICATE: clamp the taps; cval = 0 so sum starts at 0
                    let xi: [usize; 4] = std::array::from_fn(|i| (sx + i as i32).clamp(0, sw - 1) as usize);
                    let yi: [usize; 4] = std::array::from_fn(|i| (sy + i as i32).clamp(0, sh - 1) as usize);
                    for k in 0..cn {
                        let mut sum = 0i32;
                        for i in 0..4 {
                            for j in 0..4 {
                                sum += src.data[(yi[i] * src.w + xi[j]) * cn + k] as i32 * w[i * 4 + j];
                            }
                        }
                        d[k] = ((sum + (1 << (INTER_REMAP_COEF_BITS - 1))) >> INTER_REMAP_COEF_BITS).clamp(0, 255) as u8;
                    }
                }
            }
            x0 += bw0;
        }
    }
    dst
}
