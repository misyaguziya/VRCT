//! The log images (models/overlay/overlay_image.py): the small log (one message and its
//! translations under the view) and the large log (the last 5 messages), with romaji / hiragana
//! above each token when transliteration is on. Same sizes as the Python version (the text widths
//! are FreeType's hinted advances: each glyph's advance rounded to whole pixels, as Pillow 10's
//! basic layout measures them); the pixels only need to look the same (design §6.7).
use ab_glyph::{Font, FontVec, PxScale, ScaleFont};
use std::collections::HashMap;
use std::path::{Path, PathBuf};

pub type Rgb = (u8, u8, u8);

/// A font per language; Default for the others
const LANGUAGES: [(&str, &str); 5] = [
    ("Default", "NotoSansJP-Regular.ttf"),
    ("Japanese", "NotoSansJP-Regular.ttf"),
    ("Korean", "NotoSansKR-Regular.ttf"),
    ("Chinese Simplified", "NotoSansSC-Regular.ttf"),
    ("Chinese Traditional", "NotoSansTC-Regular.ttf"),
];

fn font_file(language: &str) -> &'static str {
    LANGUAGES.iter().find(|(l, _)| *l == language).unwrap_or(&LANGUAGES[0]).1
}

/// An RGBA image with straight alpha (Pillow's "RGBA")
#[derive(Clone, Debug, PartialEq)]
pub struct Image {
    pub width: usize,
    pub height: usize,
    pub data: Vec<u8>,
}

impl Image {
    pub fn new(width: usize, height: usize, color: [u8; 4]) -> Self {
        Self { width, height, data: color.repeat(width * height) }
    }

    /// Image.paste(other, (x, y)): the pixels replaced (alpha too), clipped to this image
    fn paste(&mut self, other: &Image, x: usize, y: usize) {
        for row in 0..other.height.min(self.height.saturating_sub(y)) {
            let n = other.width.min(self.width.saturating_sub(x)) * 4;
            let src = row * other.width * 4;
            let dst = ((y + row) * self.width + x) * 4;
            self.data[dst..dst + n].copy_from_slice(&other.data[src..src + n]);
        }
    }

    /// concatenateImagesVertically: `other` under this one, `margin` apart (this one's width)
    fn concat_vertical(&self, other: &Image, margin: usize) -> Image {
        let mut out = Image::new(self.width, self.height + other.height + margin, [0; 4]);
        out.paste(self, 0, 0);
        out.paste(other, 0, self.height + margin);
        out
    }

    /// addImageMargin with a transparent margin on every side
    fn with_margin(&self, margin: usize) -> Image {
        let mut out = Image::new(self.width + 2 * margin, self.height + 2 * margin, [0; 4]);
        out.paste(self, margin, margin);
        out
    }

    /// The image on a rounded rectangle of `color` (draw.rounded_rectangle, which has no
    /// anti-aliasing, then Image.alpha_composite)
    fn on_rounded_rectangle(&self, radius: usize, color: Rgb) -> Image {
        let (w, h, r) = (self.width as f64, self.height as f64, radius as f64);
        let mut out = Image::new(self.width, self.height, [0; 4]);
        for y in 0..self.height {
            for x in 0..self.width {
                // the pixel centre against the corner circles
                let (px, py) = (x as f64 + 0.5, y as f64 + 0.5);
                let cx = px.clamp(r, w - r);
                let cy = py.clamp(r, h - r);
                let inside = (px - cx).powi(2) + (py - cy).powi(2) <= r * r;
                let i = (y * self.width + x) * 4;
                let bg = if inside { [color.0, color.1, color.2, 255] } else { [0; 4] };
                out.data[i..i + 4].copy_from_slice(&composite(bg, self.data[i..i + 4].try_into().unwrap()));
            }
        }
        out
    }
}

/// Image.alpha_composite for one pixel: `fg` over `bg`, straight alpha
fn composite(bg: [u8; 4], fg: [u8; 4]) -> [u8; 4] {
    let (fa, ba) = (fg[3] as f32 / 255.0, bg[3] as f32 / 255.0);
    let out_a = fa + ba * (1.0 - fa);
    if out_a <= 0.0 {
        return [0; 4];
    }
    let c = |i: usize| ((fg[i] as f32 * fa + bg[i] as f32 * ba * (1.0 - fa)) / out_a).round() as u8;
    [c(0), c(1), c(2), (out_a * 255.0).round() as u8]
}

#[derive(Clone, Copy, PartialEq)]
enum Align {
    Left,
    Center,
    Right,
}

/// A font at one pixel size
struct Sized<'f> {
    font: &'f FontVec,
    size: f32,
}

impl Sized<'_> {
    fn scaled(&self) -> ab_glyph::PxScaleFont<&FontVec> {
        self.font.as_scaled(PxScale::from(self.size * self.font.height_unscaled() / self.font.units_per_em().unwrap_or(1000.0)))
    }

    /// draw.textlength: the hinted (whole-pixel) advances
    fn length(&self, text: &str) -> f64 {
        let scaled = self.scaled();
        text.chars().map(|c| scaled.h_advance(scaled.glyph_id(c)).round() as f64).sum()
    }

    /// The baseline for a vertical "m" anchor at `y`: the middle of the ascender and descender
    fn baseline_for_middle(&self, y: f64) -> f64 {
        let s = self.scaled();
        y + (s.ascent().round() + s.descent().round()) as f64 / 2.0
    }

    /// One line, the left of its first glyph at `x`, its baseline at `baseline`
    fn draw_line(&self, image: &mut Image, x: f64, baseline: f64, text: &str, color: Rgb) {
        let scaled = self.scaled();
        let mut pen = x.floor();
        for c in text.chars() {
            let id = scaled.glyph_id(c);
            let glyph = id.with_scale_and_position(scaled.scale(), ab_glyph::point(pen as f32, baseline.floor() as f32));
            if let Some(outlined) = scaled.outline_glyph(glyph) {
                let bounds = outlined.px_bounds();
                outlined.draw(|gx, gy, coverage| {
                    let (px, py) = (bounds.min.x as i64 + gx as i64, bounds.min.y as i64 + gy as i64);
                    if px < 0 || py < 0 || px as usize >= image.width || py as usize >= image.height {
                        return;
                    }
                    // draw_bitmap: the ink blended in by the glyph's coverage (alpha too)
                    let i = (py as usize * image.width + px as usize) * 4;
                    let a = coverage.clamp(0.0, 1.0);
                    for (k, ink) in [color.0, color.1, color.2, 255].into_iter().enumerate() {
                        image.data[i + k] = (image.data[i + k] as f32 * (1.0 - a) + ink as f32 * a).round() as u8;
                    }
                });
            }
            pen += scaled.h_advance(id).round() as f64;
        }
    }

    /// draw.text / draw.multiline_text with a vertical "m" anchor and horizontal anchor `anchor`
    /// ("l", "m" or "r"), lines `align`ed (spacing 4)
    #[allow(clippy::too_many_arguments)] // Pillow's arguments
    fn draw(&self, image: &mut Image, x: f64, y: f64, anchor: Align, align: Align, text: &str, color: Rgb) {
        let lines: Vec<&str> = text.split('\n').collect();
        let widths: Vec<f64> = lines.iter().map(|l| self.length(l)).collect();
        let max_width = widths.iter().cloned().fold(0.0, f64::max);
        // textbbox("A")[3] + spacing: the bottom of "A" under the top of the ascender
        let line_spacing = self.scaled().ascent().round() as f64 + 4.0;
        let mut top = y - (lines.len() - 1) as f64 * line_spacing / 2.0;
        for (line, width) in lines.iter().zip(&widths) {
            let mut left = x;
            let difference = max_width - width;
            match anchor {
                Align::Center => left -= difference / 2.0,
                Align::Right => left -= difference,
                Align::Left => {}
            }
            match align {
                Align::Center => left += difference / 2.0,
                Align::Right => left += difference,
                Align::Left => {}
            }
            // the anchor of the line itself
            let start = match anchor {
                Align::Left => left,
                Align::Center => left - width / 2.0,
                Align::Right => left - width,
            };
            self.draw_line(image, start, self.baseline_for_middle(top), line, color);
            top += line_spacing;
        }
    }
}

/// One token of the transliteration (orig / hira / hepburn)
#[derive(Clone, Debug, Default)]
pub struct Token {
    pub orig: String,
    pub hira: String,
    pub hepburn: String,
}

/// A message of the large log
#[derive(Clone, Debug)]
struct LogEntry {
    message_type: String,
    message: Option<String>,
    your_language: String,
    translation: Vec<String>,
    target_language: Vec<String>,
    transliteration_message: Vec<Token>,
    transliteration_translation: Vec<Vec<Token>>,
    datetime: String,
}

const SMALL_WIDTH: usize = 3840;
const SMALL_FONT_SIZE: usize = 92;
const COLOR_BACKGROUND: Rgb = (41, 42, 45);
const COLOR_TEXT: Rgb = (223, 223, 223);
const LARGE_WIDTH: usize = 960;
const LARGE_FONT_LARGE: usize = 30;
const LARGE_FONT_SMALL: usize = 20;
const LARGE_MARGIN: usize = 25;
const LARGE_RADIUS: usize = 25;
const LARGE_PADDING: usize = 10;
const LARGE_CLAUSE_MARGIN: usize = 20;
const COLOR_TEXT_SMALL: Rgb = (190, 190, 190);
const COLOR_SEND: Rgb = (97, 151, 180);
const COLOR_RECEIVE: Rgb = (168, 97, 180);
const COLOR_TIME: Rgb = (120, 120, 120);
const RUBY_FONT_SCALE: f64 = 0.5;
const RUBY_LINE_SPACING: usize = 4;
const RUBY_ORIGINAL_SPACING: usize = 2;
const OUTER_PADDING: usize = 10;

/// OverlayImage: the fonts, and the large log's messages
pub struct OverlayImage {
    fonts_dir: PathBuf,
    fonts: HashMap<&'static str, FontVec>,
    message_log: Vec<LogEntry>,
}

/// A token measured: (orig, hira, hepburn, width)
type Measured = (String, String, String, usize);

impl OverlayImage {
    /// `fonts_dir`: the folder with the Noto Sans fonts
    pub fn new(fonts_dir: &Path) -> Self {
        Self { fonts_dir: fonts_dir.into(), fonts: HashMap::new(), message_log: vec![] }
    }

    fn font(&mut self, language: &str) -> std::io::Result<&FontVec> {
        let file = font_file(language);
        if !self.fonts.contains_key(file) {
            let bytes = std::fs::read(self.fonts_dir.join(file))?;
            let font = FontVec::try_from_vec(bytes).map_err(|e| std::io::Error::other(e.to_string()))?;
            self.fonts.insert(file, font);
        }
        Ok(&self.fonts[file])
    }

    /// createTextboxSmallLog: the text wrapped by character count and centred
    fn textbox_small(&mut self, text: &str, language: &str, color: Rgb) -> std::io::Result<Image> {
        let font = Sized { font: self.font(language)?, size: SMALL_FONT_SIZE as f32 };
        let chars: Vec<char> = text.chars().collect();
        let text_width = if chars.is_empty() { 1.0 } else { font.length(text) };
        let character_width = (text_width / chars.len().max(1) as f64).floor().max(1.0);
        let per_line = ((SMALL_WIDTH as f64 / character_width).floor() - 12.0) as i64;
        let text = if per_line > 0 && chars.len() as i64 > per_line {
            chars.chunks(per_line as usize).map(|c| c.iter().collect::<String>()).collect::<Vec<_>>().join("\n")
        } else {
            text.to_string()
        };
        let lines = if text.is_empty() { 1 } else { text.split('\n').count() };
        let height = SMALL_FONT_SIZE * (lines + 1) + 20;
        let mut image = Image::new(SMALL_WIDTH, height, [0; 4]);
        font.draw(&mut image, (SMALL_WIDTH / 2) as f64, (height / 2) as f64, Align::Center, Align::Center, &text, color);
        Ok(image)
    }

    /// The tokens with the width each takes (the widest of the original and its ruby)
    fn measure(&mut self, tokens: &[Token], language: &str, size: usize) -> std::io::Result<(Vec<Measured>, usize)> {
        let ruby_size = ((size as f64 * RUBY_FONT_SCALE) as usize).max(1);
        let font = self.font(language)?;
        let (orig_font, ruby_font) = (Sized { font, size: size as f32 }, Sized { font, size: ruby_size as f32 });
        let measured = tokens.iter().filter(|t| !t.orig.is_empty()).map(|t| {
            let orig_w = (orig_font.length(&t.orig) as usize).max(1);
            let hira_w = if t.hira.is_empty() { 0 } else { ruby_font.length(&t.hira) as usize };
            let romaji_w = if t.hepburn.is_empty() { 0 } else { ruby_font.length(&t.hepburn) as usize };
            (t.orig.clone(), t.hira.clone(), t.hepburn.clone(), orig_w.max(hira_w).max(romaji_w))
        }).collect();
        Ok((measured, ruby_size))
    }

    /// The tokens in lines of at most 90% of `width`
    fn wrap(tokens: Vec<Measured>, width: usize) -> Vec<Vec<Measured>> {
        let max = width as f64 * 0.9;
        let mut lines: Vec<Vec<Measured>> = vec![];
        let mut current: Vec<Measured> = vec![];
        let mut current_width = 0;
        for token in tokens {
            let w = token.3;
            if (current_width + w) as f64 > max && !current.is_empty() {
                lines.push(std::mem::take(&mut current));
                current_width = 0;
            }
            current_width += w;
            current.push(token);
        }
        if !current.is_empty() {
            lines.push(current);
        }
        lines
    }

    /// The lines of tokens, each with romaji and hiragana above it, `start_x` giving each line's left
    #[allow(clippy::too_many_arguments)]
    fn ruby_lines(&mut self, lines: &[Vec<Measured>], language: &str, size: usize, ruby_size: usize, width: usize, color: Rgb,
                  original_spacing: usize, start_x: &dyn Fn(usize) -> usize) -> std::io::Result<Image> {
        let font = self.font(language)?;
        let (orig_font, ruby_font) = (Sized { font, size: size as f32 }, Sized { font, size: ruby_size as f32 });
        let mut images = vec![];
        for line in lines {
            let line_width: usize = line.iter().map(|t| t.3).sum();
            let has_romaji = line.iter().any(|t| !t.2.is_empty());
            let has_hira = line.iter().any(|t| !t.1.is_empty());
            let ruby_lines = has_romaji as usize + has_hira as usize;
            let ruby_height = ruby_lines * ruby_size + if ruby_lines == 2 { RUBY_LINE_SPACING } else { 0 };
            let height = OUTER_PADDING + ruby_height + original_spacing + size + OUTER_PADDING;
            let mut image = Image::new(width, height, [0; 4]);
            let first = OUTER_PADDING + ruby_size / 2;
            let romaji_y = has_romaji.then_some(first);
            let hira_y = match (has_romaji, has_hira) {
                (true, true) => Some(first + ruby_size + RUBY_LINE_SPACING),
                (false, true) => Some(first),
                _ => None,
            };
            let orig_y = OUTER_PADDING + ruby_height + original_spacing + size / 2;
            let mut cursor = start_x(line_width);
            for (orig, hira, romaji, w) in line {
                let centre = (cursor + w / 2) as f64;
                if let (Some(y), false) = (romaji_y, romaji.is_empty()) {
                    ruby_font.draw(&mut image, centre, y as f64, Align::Center, Align::Left, romaji, color);
                }
                if let (Some(y), false) = (hira_y, hira.is_empty()) {
                    ruby_font.draw(&mut image, centre, y as f64, Align::Center, Align::Left, hira, color);
                }
                orig_font.draw(&mut image, centre, orig_y as f64, Align::Center, Align::Left, orig, color);
                cursor += w;
            }
            images.push(image);
        }
        Ok(images.iter().skip(1).fold(images[0].clone(), |acc, i| acc.concat_vertical(i, 0)))
    }

    /// createTextboxSmallLogWithRubyTokens
    fn textbox_small_ruby(&mut self, message: &str, tokens: &[Token], language: &str, color: Rgb) -> std::io::Result<Image> {
        if message.is_empty() || tokens.is_empty() {
            return self.textbox_small(message, language, color);
        }
        let (measured, ruby_size) = self.measure(tokens, language, SMALL_FONT_SIZE)?;
        if measured.is_empty() {
            return self.textbox_small(message, language, color);
        }
        let lines = Self::wrap(measured, SMALL_WIDTH);
        self.ruby_lines(&lines, language, SMALL_FONT_SIZE, ruby_size, SMALL_WIDTH, color, RUBY_ORIGINAL_SPACING,
                        &|line_width| (SMALL_WIDTH.saturating_sub(line_width)) / 2)
    }

    /// createOverlayImageSmallLog: the message (and its translations) on a rounded panel.
    /// The translations go with their transliterations as zip() pairs them.
    pub fn small_log(&mut self, message: &str, your_language: &str, translation: &[String], target_language: &[String],
                     transliteration_message: &[Token], transliteration_translation: &[Vec<Token>]) -> std::io::Result<Image> {
        let mut boxes = vec![];
        if !translation.is_empty() && !target_language.is_empty() {
            if !message.is_empty() {
                boxes.push(self.textbox_small(message, your_language, COLOR_TEXT)?);
            }
            for ((trans, language), tokens) in translation.iter().zip(target_language).zip(transliteration_translation) {
                boxes.push(self.textbox_small_ruby(trans, tokens, language, COLOR_TEXT)?);
            }
        } else if !message.is_empty() && !transliteration_message.is_empty() {
            boxes.push(self.textbox_small_ruby(message, transliteration_message, your_language, COLOR_TEXT)?);
        } else {
            boxes.push(self.textbox_small(message, your_language, COLOR_TEXT)?);
        }
        // Python raises here (nothing to show: translations without languages to pair with)
        let Some(first) = boxes.first() else { return Err(std::io::Error::other("no text for the small log")) };
        let image = boxes.iter().skip(1).fold(first.clone(), |acc, b| acc.concat_vertical(b, 0));
        Ok(image.with_margin(50).on_rounded_rectangle(50, COLOR_BACKGROUND))
    }

    /// createTextImageLargeLog: wrapped by character count, to the left (receive) or right (send)
    fn text_large(&mut self, message_type: &str, large: bool, text: &str, language: &str) -> std::io::Result<Image> {
        let size = if large { LARGE_FONT_LARGE } else { LARGE_FONT_SMALL };
        let color = if large { COLOR_TEXT } else { COLOR_TEXT_SMALL };
        let receive = message_type == "receive";
        let font = Sized { font: self.font(language)?, size: size as f32 };
        let chars: Vec<char> = text.chars().collect();
        let text_width = text.split('\n').map(|l| font.length(l)).fold(0.0, f64::max);
        // ponytail: Python divides by len(text) and fails on an empty message; one character here
        let character_width = (text_width / chars.len().max(1) as f64).floor().max(1.0);
        let per_line = ((LARGE_WIDTH as f64 / character_width).floor() - 1.0) as i64;
        let text = if per_line > 0 && chars.len() as i64 > per_line {
            chars.chunks(per_line as usize).map(|c| c.iter().collect::<String>()).collect::<Vec<_>>().join("\n")
        } else {
            text.to_string()
        };
        let height = size * text.split('\n').count() + LARGE_PADDING;
        let mut image = Image::new(LARGE_WIDTH, height, [0; 4]);
        let (x, side) = if receive { (0.0, Align::Left) } else { (LARGE_WIDTH as f64, Align::Right) };
        font.draw(&mut image, x, (height / 2) as f64, side, side, &text, color);
        Ok(image)
    }

    /// createTextboxLargeLogWithRubyTokens
    fn textbox_large_ruby(&mut self, message_type: &str, large: bool, message: &str, tokens: &[Token], language: &str)
                          -> std::io::Result<Image> {
        if message.is_empty() || tokens.is_empty() {
            return self.text_large(message_type, large, message, language);
        }
        let size = if large { LARGE_FONT_LARGE } else { LARGE_FONT_SMALL };
        let color = if large { COLOR_TEXT } else { COLOR_TEXT_SMALL };
        let (measured, ruby_size) = self.measure(tokens, language, size)?;
        if measured.is_empty() {
            return self.text_large(message_type, large, message, language);
        }
        let lines = Self::wrap(measured, LARGE_WIDTH);
        let receive = message_type == "receive";
        self.ruby_lines(&lines, language, size, ruby_size, LARGE_WIDTH, color, 0,
                        &|line_width| if receive { 0 } else { LARGE_WIDTH.saturating_sub(line_width) })
    }

    /// createTextImageMessageType: the time and "Send" / "Receive"
    fn message_type_line(&mut self, message_type: &str, date_time: &str) -> std::io::Result<Image> {
        let receive = message_type == "receive";
        let font = Sized { font: self.font("Default")?, size: LARGE_FONT_SMALL as f32 };
        let height = LARGE_FONT_SMALL + LARGE_PADDING;
        let text_width = font.length(date_time);
        let character_width = (text_width / date_time.chars().count().max(1) as f64).floor();
        let mut image = Image::new(LARGE_WIDTH, height, [0; 4]);
        let y = (height / 2) as f64;
        let (time_x, label_x, side) = if receive {
            (0.0, text_width + character_width, Align::Left)
        } else {
            (LARGE_WIDTH as f64 - (text_width + character_width), LARGE_WIDTH as f64, Align::Right)
        };
        font.draw(&mut image, time_x, y, side, Align::Left, date_time, COLOR_TIME);
        let (label, color) = if receive { ("Receive", COLOR_RECEIVE) } else { ("Send", COLOR_SEND) };
        font.draw(&mut image, label_x, y, side, Align::Left, label, color);
        Ok(image)
    }

    /// createTextboxLargeLog: one message of the large log
    fn textbox_large(&mut self, entry: &LogEntry) -> std::io::Result<Image> {
        let mut images = vec![self.message_type_line(&entry.message_type, &entry.datetime)?];
        let kind = entry.message_type.as_str();
        if !entry.translation.is_empty() && !entry.target_language.is_empty() {
            if let Some(message) = &entry.message {
                images.push(self.text_large(kind, false, message, &entry.your_language)?);
            }
            for ((trans, language), tokens) in entry.translation.iter().zip(&entry.target_language).zip(&entry.transliteration_translation) {
                images.push(self.textbox_large_ruby(kind, true, trans, tokens, language)?);
            }
        } else {
            let message = entry.message.clone().unwrap_or_default();
            images.push(self.textbox_large_ruby(kind, true, &message, &entry.transliteration_message, &entry.your_language)?);
        }
        Ok(images.iter().skip(1).fold(images[0].clone(), |acc, i| acc.concat_vertical(i, 0)))
    }

    /// createOverlayImageLargeLog: this message added to the last 5, on a rounded panel
    #[allow(clippy::too_many_arguments)]
    pub fn large_log(&mut self, message_type: &str, message: Option<&str>, your_language: &str, translation: &[String],
                     target_language: &[String], transliteration_message: &[Token], transliteration_translation: &[Vec<Token>])
                     -> std::io::Result<Image> {
        self.message_log.push(LogEntry {
            message_type: message_type.into(),
            message: message.map(String::from),
            your_language: your_language.into(),
            translation: translation.to_vec(),
            target_language: target_language.to_vec(),
            transliteration_message: transliteration_message.to_vec(),
            transliteration_translation: transliteration_translation.to_vec(),
            datetime: chrono::Local::now().format("%H:%M").to_string(),
        });
        if self.message_log.len() > 5 {
            self.message_log.remove(0);
        }
        let entries = self.message_log.clone();
        let images = entries.iter().map(|e| self.textbox_large(e)).collect::<std::io::Result<Vec<_>>>()?;
        let image = images.iter().skip(1).fold(images[0].clone(), |acc, i| acc.concat_vertical(i, LARGE_CLAUSE_MARGIN));
        Ok(image.with_margin(LARGE_MARGIN).on_rounded_rectangle(LARGE_RADIUS, COLOR_BACKGROUND))
    }
}
