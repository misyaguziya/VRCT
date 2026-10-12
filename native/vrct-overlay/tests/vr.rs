//! The VR UI's calculations against the Python version (native/testdata/overlay/vr.json, written by
//! native/reference/export_overlay_vr.py): poses, the layout, the masks, the tooltip's checks
use serde_json::Value;
use vrct_overlay::image::Image;
use vrct_overlay::layout::{self, Layout, PointerKind, Region, TooltipMode};
use vrct_overlay::math::{Mat34, Mat4};
use vrct_overlay::pose::{self, Vec3};

fn data() -> Value {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../testdata/overlay/vr.json");
    serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap()
}

fn f(v: &Value) -> f64 {
    v.as_f64().unwrap()
}

fn floats(v: &Value) -> Vec<f64> {
    v.as_array().unwrap().iter().map(f).collect()
}

fn vec3(v: &Value) -> Vec3 {
    floats(v).try_into().unwrap()
}

fn m4(v: &Value) -> Mat4 {
    let rows: Vec<[f64; 4]> = v.as_array().unwrap().iter().map(|r| floats(r).try_into().unwrap()).collect();
    rows.try_into().unwrap()
}

fn m34(v: &Value) -> Mat34 {
    let rows: Vec<[f64; 4]> = v.as_array().unwrap().iter().map(|r| floats(r).try_into().unwrap()).collect();
    rows.try_into().unwrap()
}

fn close(a: &[f64], b: &[f64], what: &str) {
    assert_eq!(a.len(), b.len(), "{what}");
    for (x, y) in a.iter().zip(b) {
        assert!((x - y).abs() < 1e-9, "{what}: {a:?} != {b:?}");
    }
}

fn flat(m: &Mat4) -> Vec<f64> {
    m.iter().flatten().copied().collect()
}

#[test]
fn poses_match_python() {
    let data = data();
    let c = &data["cases"];
    let each = |name: &str| c[name].as_array().unwrap().clone();
    for case in each("ray_plane_hit") {
        let hit = pose::ray_plane_hit(&m4(&case["ray"]), &m4(&case["plane"]));
        match (&hit, case["hit"].as_array()) {
            (None, None) => {}
            (Some(h), Some(e)) => close(&[h.x, h.y, h.point[0], h.point[1], h.point[2], h.distance],
                                        &[f(&e[0]), f(&e[1]), vec3(&e[2])[0], vec3(&e[2])[1], vec3(&e[2])[2], f(&e[3])], "ray_plane_hit"),
            _ => panic!("ray_plane_hit {hit:?} {case}"),
        }
    }
    for case in each("pose_facing") {
        let up = case["up"].as_array().map(|_| vec3(&case["up"]));
        close(&flat(&pose::pose_facing(vec3(&case["position"]), vec3(&case["target"]), up)), &flat(&m4(&case["pose"])), "pose_facing");
    }
    for case in each("face_head") {
        close(&flat(&pose::face_head(vec3(&case["position"]), &m4(&case["head"]))), &flat(&m4(&case["pose"])), "face_head");
    }
    for case in each("pose_on_sphere") {
        let got = pose::pose_on_sphere(vec3(&case["point"]), &m4(&case["head"]), f(&case["radius"]));
        close(&flat(&got), &flat(&m4(&case["pose"])), "pose_on_sphere");
    }
    for case in each("sphere_radius") {
        let v = floats(&case);
        close(&[pose::sphere_radius(v[0], v[1], v[2])], &[v[3]], "sphere_radius");
    }
    for case in each("is_out_of_view") {
        let got = pose::is_out_of_view(&m4(&case["head"]), vec3(&case["position"]), case["was_out"].as_bool().unwrap());
        assert_eq!(got, case["out"].as_bool().unwrap(), "is_out_of_view {case}");
    }
    for case in each("recall_pose") {
        close(&flat(&pose::recall_pose(&m4(&case["head"]))), &flat(&m4(&case["pose"])), "recall_pose");
    }
    for case in each("intro_front_pose") {
        close(&flat(&pose::intro_front_pose(&m4(&case["head"]))), &flat(&m4(&case["pose"])), "intro_front_pose");
    }
    for case in each("intro_flight_pose") {
        let got = pose::intro_flight_pose(&m4(&case["front"]), &m4(&case["target"]), f(&case["progress"]));
        close(&flat(&got), &flat(&m4(&case["pose"])), "intro_flight_pose");
    }
    for case in each("push_pull_distance") {
        let v = floats(&case);
        close(&[pose::push_pull_distance(v[0], Some((v[1], v[2])), v[3])], &[v[4]], "push_pull_distance");
    }
    for case in each("push_pull") {
        let s = floats(&case["stick"]);
        let got = pose::push_pull(&m4(&case["pose"]), Some((s[0], s[1])), f(&case["dt"]));
        close(&flat(&got), &flat(&m4(&case["result"])), "push_pull");
    }
    for case in each("launcher_looks_visible") {
        let got = pose::launcher_looks_visible(&m4(&case["launcher"]), &m4(&case["head"]), f(&case["face"]), f(&case["gaze"]));
        assert_eq!(got, case["visible"].as_bool().unwrap(), "launcher_looks_visible");
    }
    for case in each("launcher_reach") {
        let s = &case["settings"];
        let xyz = [f(&s["x_pos"]), f(&s["y_pos"]), f(&s["z_pos"])];
        assert_eq!(pose::launcher_out_of_reach(xyz, f(&s["ui_scaling"])), case["out"].as_bool().unwrap());
        let (p, w) = pose::launcher_nearest_in_reach(xyz, f(&s["ui_scaling"]));
        let n = &case["nearest"];
        // round(v, 4) is exact on both sides
        assert_eq!([p[0], p[1], p[2], w], [f(&n["x_pos"]), f(&n["y_pos"]), f(&n["z_pos"]), f(&n["ui_scaling"])]);
    }
    for case in each("matrix_to_position") {
        let got = pose::matrix_to_position(&m34(&case["base"]), &m34(&case["relative"]));
        let expected = floats(&case["position"]);
        // the angles near the gimbal lock come from asin, sensitive to the last bits
        for (i, (a, b)) in got.iter().zip(&expected).enumerate() {
            assert!((a - b).abs() < if i < 3 { 1e-9 } else { 1e-5 }, "matrix_to_position {got:?} {expected:?}");
        }
    }
    for case in each("laser_tilt") {
        close(&flat(&pose::laser_tilt(f(&case["degrees"]))), &flat(&m4(&case["pose"])), "laser_tilt");
    }
    for case in each("uv_to_pixel") {
        let v: Vec<f64> = case.as_array().unwrap()[..4].iter().map(f).collect();
        let (x, y) = pose::uv_to_pixel(v[0], v[1], v[2] as usize, v[3] as usize);
        assert_eq!([x as f64, y as f64], [floats(&case[4])[0], floats(&case[4])[1]], "uv_to_pixel {case}");
    }
}

/// Pixels differing from a run-length image (rows of [value, count])
fn differing(runs: &Value, width: usize, pixel: impl Fn(usize, usize) -> Vec<u8>) -> usize {
    let mut count = 0;
    for (y, row) in runs.as_array().unwrap().iter().enumerate() {
        let mut x = 0;
        for run in row.as_array().unwrap() {
            let value: Vec<u8> = run[0].as_array().unwrap().iter().map(|v| v.as_u64().unwrap() as u8).collect();
            let n = run[1].as_u64().unwrap() as usize;
            count += (x..x + n).filter(|&px| pixel(px, y) != value).count();
            x += n;
        }
        assert_eq!(x, width);
    }
    count
}

fn ints(v: &Value) -> Vec<u32> {
    v.as_array().unwrap().iter().map(|x| x.as_u64().unwrap() as u32).collect()
}

#[test]
fn layout_matches_python() {
    let data = data();
    for entry in data["layouts"].as_array().unwrap() {
        let panel = ints(&entry["panel"]);
        let layout = Layout::new(panel[0], panel[1]);
        assert_eq!([layout.atlas.0, layout.atlas.1].to_vec(), ints(&entry["atlas"]));
        let image = ints(&entry["image"]);
        for region in Region::ALL {
            assert_eq!(layout.region(region).to_vec(), ints(&entry["regions"][region.name()]));
            assert_eq!(layout.region_rect(region, image[0]).to_vec(), ints(&entry["rects"][region.name()]));
            // Python's bounds are OpenGL's (v up); DirectX's v = 1 - that
            let gl = floats(&entry["bounds"][region.name()]);
            let dx = layout.region_bounds(region, 1.0, 1.0);
            close(&dx.map(f64::from), &[gl[0], gl[1], 1.0 - gl[2], 1.0 - gl[3]].map(|v| v as f32 as f64), "bounds");
        }
        let (row, columns) = layout::marker_points(image[0], &layout);
        let marker = &entry["marker"];
        assert_eq!(row, marker[0].as_u64().unwrap() as u32);
        assert_eq!(columns.to_vec(), ints(&marker[1]));
        let Some(expected) = entry.get("mask") else { continue };
        let size = (image[0], image[1]);
        let mut mask = layout::mask(size, &layout);
        let at = |m: &Vec<u8>, x: usize, y: usize| vec![m[y * size.0 as usize + x]];
        // Pillow's quarter circles round a little differently at the corners: a few px each
        let off = differing(expected, size.0 as usize, |x, y| at(&mask, x, y));
        assert!(off <= 4 * 4 * 6, "mask {panel:?} {image:?}: {off} px differ");
        let state = &entry["tooltip"]["state"];
        let shown = layout::TooltipShown { region: Region::Launcher, mode: TooltipMode::Hover, button: [0.0; 4],
                                           size: floats(&state["size"]).try_into().unwrap(), arrow_x: f(&state["arrow_x"]) };
        layout::tooltip_mask(size, &layout, &shown, &mut mask);
        let off = differing(&entry["tooltip"]["mask"], size.0 as usize, |x, y| at(&mask, x, y));
        assert!(off <= 4 * 4 * 6 + 4 * 4 + 8, "tooltip mask {panel:?} {image:?}: {off} px differ");
    }
    for c in data["clamps"].as_array().unwrap() {
        let (w, h) = layout::clamp_panel_size(f(&c[0]), f(&c[1]));
        assert_eq!(vec![w, h], ints(&c[2]), "{c}");
    }
}

#[test]
fn tooltips_match_python() {
    let data = data();
    for case in data["tooltips"].as_array().unwrap() {
        let got = layout::validate_tooltip(&case["data"]);
        match (&got, case.get("error")) {
            (Err(reason), Some(expected)) => assert_eq!(*reason, expected.as_str().unwrap(), "{case}"),
            (Ok(t), None) => {
                let ok = &case["ok"];
                assert_eq!((t.epoch, t.revision), (ok["epoch"].as_u64().unwrap(), ok["revision"].as_u64().unwrap()));
                match &t.shown {
                    None => assert!(!ok["visible"].as_bool().unwrap()),
                    Some(s) => {
                        assert_eq!(s.region.name(), ok["region"].as_str().unwrap());
                        assert_eq!(s.mode == TooltipMode::Focus, ok["mode"] == "focus");
                        assert_eq!(s.button.to_vec(), floats(&ok["button"]));
                        assert_eq!(s.size.to_vec(), floats(&ok["size"]));
                        assert_eq!(s.arrow_x, f(&ok["arrow_x"]));
                    }
                }
            }
            _ => panic!("{got:?} for {case}"),
        }
    }
    let layout = Layout::new(900, 700);
    let (_, columns) = layout::marker_points(layout.atlas.0, &layout);
    for r in data["marker_rows"].as_array().unwrap() {
        let (epoch, revision) = (r["epoch"].as_u64().unwrap(), r["revision"].as_u64().unwrap());
        let row: Vec<u8> = ints(&r["row"]).into_iter().map(|v| v as u8).collect();
        let bad: Vec<u8> = ints(&r["bad"]).into_iter().map(|v| v as u8).collect();
        assert_eq!(layout::marker_row_matches(&row, &columns, epoch, revision), r["matches"].as_bool().unwrap());
        assert_eq!(layout::marker_row_matches(&bad, &columns, epoch, revision), r["bad_matches"].as_bool().unwrap());
    }
}

fn image_off(image: &Image, runs: &Value) -> usize {
    differing(runs, image.width, |x, y| image.data[(y * image.width + x) * 4..][..4].to_vec())
}

#[test]
fn images_match_python() {
    let data = data();
    for kind in PointerKind::ALL {
        let off = image_off(&layout::pointer_image(kind), &data["images"]["pointer"][kind.name()]);
        assert!(off <= 64, "pointer {}: {off} px differ", kind.name());
    }
    for g in data["images"]["ghost"].as_array().unwrap() {
        let size = ints(&g["size"]);
        let image = layout::ghost_image(size[0], size[1], g["at_limit"].as_bool().unwrap());
        let off = image_off(&image, &g["image"]);
        assert!(off <= 40, "ghost {size:?}: {off} px differ");
    }
}
