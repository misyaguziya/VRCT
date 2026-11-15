//! The VR keyboard's dictionaries (RIME's shared data), downloaded when the VR UI is first on: each
//! project's archive at a fixed commit from GitHub, only the files used taken out and checked by
//! their SHA-256 (an archive's own bytes are not stable). Nothing is redistributed by VRCT.
//!
//! <root>/ime/shared: the schemas and dictionaries, OpenCC's data (bundled in _internal), the
//! projects' licenses; .vrct-ime names the set it holds, written last: a folder without it (a
//! stopped download) is made again. (Not made elsewhere and renamed in: Windows refuses to rename
//! a folder while a file just written in it is still open, as virus scanners hold them.)
use crate::net::Http;
use anyhow::{bail, Context, Result};
use sha2::{Digest, Sha256};
use std::io::Read;
use std::path::{Path, PathBuf};

/// One project's files at a commit: (name in its archive, SHA-256)
pub struct Source {
    pub repo: &'static str,
    pub commit: &'static str,
    /// about the archive's size (GitHub does not tell it): what the progress counts against
    pub size: u64,
    pub files: &'static [(&'static str, &'static str)],
}

/// Japanese (rime-jaroomaji, Apache-2.0; Mozc's dictionary BSD-3, JMdict and KANJIDIC2 CC BY-SA 4.0),
/// Chinese (luna_pinyin with essay and prelude; Zhuyin (bopomofo, with terra_pinyin), Cangjie
/// (cangjie5) and Quick (quick5): LGPL-3.0)
pub const SOURCES: &[Source] = &[
    Source {
        repo: "rime/rime-prelude",
        commit: "082425ea0684bca36474415d4a0e8db9b016487e",
        size: 20_307,
        files: &[("default.yaml", "0628ada16651d56c4cdfcb8e45ddba23d4d585cc8be0580a62c4e077c0bcc141"),
                 ("key_bindings.yaml", "ee2476598b4cae89068b823868196eb07b5f72007a600814fe5804b39008b3ed"),
                 ("punctuation.yaml", "d6f89592149098f0a2d0ed3e5c83f49adb6226cdf1d967b0bc0d293f4e5c496a"),
                 ("symbols.yaml", "6d08969525bd66c67abf1791c99928079356bd0e673386c49c1959d2a52fdbba"),
                 ("LICENSE", "da7eabb7bafdf7d3ae5e9f223aa5bdc1eece45ac569dc21b3b037520b4464768")],
    },
    Source {
        repo: "rime/rime-essay",
        commit: "054920de4f54c9e5994276a96a4fc2a35cb51aa3",
        size: 2_577_894,
        files: &[("essay.txt", "3e8512ebaa6657e35961b1f5762060717c647e3bf471d5e3b86e783b4e934ffb"),
                 ("LICENSE", "da7eabb7bafdf7d3ae5e9f223aa5bdc1eece45ac569dc21b3b037520b4464768")],
    },
    Source {
        repo: "rime/rime-luna-pinyin",
        commit: "56b934b099dfbeab842320f13aa8b461a6ab3e42",
        size: 398_121,
        files: &[("luna_pinyin.schema.yaml", "668b4d4957e4cc8f9cea32ed3f08f0ecf4a7be8cdba058700507487bd96dd5c7"),
                 ("luna_pinyin.dict.yaml", "75bcf6eb3ff62b129882ed89cc22b2d80a5347aa72bcfa2ccc839bac298e7314"),
                 ("pinyin.yaml", "caa220b05172bf35775db07fed6ead7719c742e6139232d9797040dbe65f746c"),
                 ("LICENSE", "da7eabb7bafdf7d3ae5e9f223aa5bdc1eece45ac569dc21b3b037520b4464768")],
    },
    Source {
        repo: "rime/rime-terra-pinyin",
        commit: "723e51bc266cf9464530c1ddedb856aa18e3da34",
        size: 732_915,
        files: &[("terra_pinyin.dict.yaml", "2f881a239e09a61e5993e79257655f98f81c3789dc8aeea5f33477f710345b27"),
                 ("LICENSE", "da7eabb7bafdf7d3ae5e9f223aa5bdc1eece45ac569dc21b3b037520b4464768")],
    },
    Source {
        repo: "rime/rime-bopomofo",
        commit: "6085c9a38a4a728047862b33d67eee18aa86f3b9",
        size: 12_487,
        files: &[("bopomofo.schema.yaml", "21301f17f799c4779516d69bb9d80a343c1cc36f06cdcb8607860c80394bb8cc"),
                 ("zhuyin.yaml", "77931ab77952fdb2535f8addebc0918453e0220a50ca176380971203f14c48be"),
                 ("LICENSE", "da7eabb7bafdf7d3ae5e9f223aa5bdc1eece45ac569dc21b3b037520b4464768")],
    },
    Source {
        repo: "rime/rime-cangjie",
        commit: "52d90a1b1312e74042b38c1cbc8142defbc53171",
        size: 403_479,
        files: &[("cangjie5.schema.yaml", "93b3e81787447b9002885b38fb4024d36e4135741e9e765bd847268efb81aac1"),
                 ("cangjie5.dict.yaml", "1514afcfb56dc347db596a6602c8dfefee798fa504e35d10eaa1e11536648d3a"),
                 ("cangjie5.base.dict.yaml", "8690f2ad8aafd38780846881aa916b5779e6d9247a351a1da426d3f3257afca4"),
                 ("cangjie5.stem.dict.yaml", "a15208351dbc33d5ade8d16ece75907ef2a7310e3962f4e54003dab9bbd49b8a"),
                 ("cangjie5.extended.dict.yaml", "a6a0b06427c599d9fa7fc1e02a618bf234eb1dc9fc9b6b92f3292fc02213b3cd"),
                 ("LICENSE", "da7eabb7bafdf7d3ae5e9f223aa5bdc1eece45ac569dc21b3b037520b4464768")],
    },
    Source {
        repo: "rime/rime-quick",
        commit: "5dcdb9e353d314239e9c8cddc0f42d52da4837bb",
        size: 40_231,
        files: &[("quick5.schema.yaml", "0eed4b8b10cd50132a691c8027cb774f481eb571c9d5c0b901d54bc7c5867c53"),
                 ("quick5.dict.yaml", "47dee37657c75afce60b3c65e650dbcbd4df39e4a7aecba7153ab56649632cd0"),
                 ("quick5.supplement.dict.yaml", "c7e38622084f4be1c64a240f64e41ec5571da22563e60ea14028945e3f76a4b7"),
                 ("LICENSE", "da7eabb7bafdf7d3ae5e9f223aa5bdc1eece45ac569dc21b3b037520b4464768")],
    },
    Source {
        repo: "lazyfoxchan/rime-jaroomaji",
        commit: "9848e630a8218d77c3636622427d332796abe8f4",
        size: 25_393_619,
        files: &[("jaroomaji.schema.yaml", "c5602acc778686861f200d397259d0c93cacc2cbfc98391d33c10471c6cbbbd8"),
                 ("jaroomaji.dict.yaml", "bd7053825bb00e7a4839a3aed3f14ffa5ddb847553d802068a0e9a1ec1744f1e"),
                 ("jaroomaji.mozc.dict.yaml", "5bfcd8c81e89d4c6d4dfed6468988f51f4d1ce1537c14fbb9110dcc880f8209a"),
                 ("jaroomaji.jmdict.dict.yaml", "0a7d7c0f725c5f6b037c3532c65a67a482f2ad24257750a91e3e69866c8c1897"),
                 ("jaroomaji.kanjidic2.dict.yaml", "6433cd8c4706f285e18e7b59b0e375e905a31f98001135ce8cb8d6a2c0afaf30"),
                 ("jaroomaji.mozcemoji.dict.yaml", "f48c7e91207a5a9058cd9ffac387a80437b2ac7b2ad871ad824fb11b72c96aca"),
                 ("jaroomaji.kana_kigou.dict.yaml", "b615f1b902e60953516c9212e2d8a8c18b92c65e74bacc21e854d4dc65c1fc32"),
                 ("jaroomaji.user.dict.yaml", "4986e940ccff1760a1700f24e52cea5f0369e5eeeef40c364fe676e797d2a631"),
                 ("LICENSE", "1ad7585641ef7b7f3468b2b954c281061b7c35a470efe63d07b9b35627bda662")],
    },
];

pub const GITHUB_ARCHIVES: &str = "https://codeload.github.com";
const MARKER: &str = ".vrct-ime";

/// What `<root>/ime/shared` must hold for `sources`: the commits, in order
fn set_id(sources: &[Source]) -> String {
    sources.iter().map(|s| format!("{}@{}\n", s.repo, s.commit)).collect()
}

pub fn shared_dir(root: &Path) -> PathBuf {
    root.join("ime").join("shared")
}

/// The data for `sources` is there, complete
pub fn ready(root: &Path, sources: &[Source]) -> bool {
    std::fs::read_to_string(shared_dir(root).join(MARKER)).is_ok_and(|id| id == set_id(sources))
}

fn sha256(data: &[u8]) -> String {
    format!("{:x}", Sha256::digest(data))
}

/// The files of `source` out of its archive into `dest` (LICENSE as licenses/<project>.txt)
fn unpack(archive: &Path, source: &Source, dest: &Path) -> Result<()> {
    let mut zip = zip::ZipArchive::new(std::fs::File::open(archive)?)?;
    let project = source.repo.rsplit('/').next().unwrap_or(source.repo);
    // GitHub's archives hold everything under "<project>-<commit>/"
    let prefix = format!("{project}-{}/", source.commit);
    for (name, expected) in source.files {
        let mut member = zip.by_name(&format!("{prefix}{name}")).with_context(|| format!("{} has no {name}", source.repo))?;
        let mut data = Vec::with_capacity(member.size() as usize);
        member.read_to_end(&mut data)?;
        let actual = sha256(&data);
        if actual != *expected {
            bail!("{}/{name}: sha256 {actual}, expected {expected}", source.repo);
        }
        let out = if *name == "LICENSE" { dest.join("licenses").join(format!("{project}.txt")) } else { dest.join(name) };
        std::fs::write(out, data)?;
    }
    Ok(())
}

/// Downloads and sets up the data unless it is there (`progress` 0..1 over the archives, by
/// their sizes). `opencc`: OpenCC's data to copy beside it (rime/opencc in _internal).
pub fn prepare(http: &Http, root: &Path, sources: &[Source], base_url: &str, opencc: &Path,
               progress: &dyn Fn(f64), log: &dyn Fn(&str, &str)) -> Result<()> {
    if ready(root, sources) {
        return Ok(());
    }
    let ime = root.join("ime");
    let shared = shared_dir(root);
    let downloads = ime.join("download");
    // (shared.part: where older builds made it)
    let _ = std::fs::remove_dir_all(ime.join("shared.part"));
    for dir in [&shared, &downloads] {
        if dir.exists() {
            std::fs::remove_dir_all(dir).with_context(|| format!("remove {}", dir.display()))?;
        }
    }
    std::fs::create_dir_all(shared.join("licenses")).with_context(|| format!("create {}", shared.display()))?;
    std::fs::create_dir_all(&downloads).with_context(|| format!("create {}", downloads.display()))?;
    let all: u64 = sources.iter().map(|s| s.size.max(1)).sum();
    let mut done = 0;
    for source in sources {
        let url = format!("{base_url}/{}/zip/{}", source.repo, source.commit);
        let archive = downloads.join(format!("{}.zip", source.repo.replace('/', "_")));
        let size = source.size.max(1);
        let share = |f: f64| progress((done as f64 + f * size as f64) / all as f64);
        if !crate::weights::download_file(http, &url, &archive, Some(&share), Some(size), "keyboard dictionary", log) {
            bail!("download {url} failed");
        }
        done += size;
        unpack(&archive, source, &shared).with_context(|| format!("unpack {}", archive.display()))?;
        let _ = std::fs::remove_file(&archive);
        progress(done as f64 / all as f64);
    }
    let to = shared.join("opencc");
    std::fs::create_dir_all(&to)?;
    for entry in std::fs::read_dir(opencc).with_context(|| format!("{}: OpenCC's data is missing", opencc.display()))? {
        let path = entry?.path();
        if path.is_file() {
            std::fs::copy(&path, to.join(path.file_name().unwrap())).with_context(|| format!("copy {}", path.display()))?;
        }
    }
    std::fs::write(shared.join(MARKER), set_id(sources))?;
    let _ = std::fs::remove_dir_all(&downloads);
    progress(1.0);
    Ok(())
}
