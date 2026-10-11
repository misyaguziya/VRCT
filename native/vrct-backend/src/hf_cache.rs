//! Files of a Hugging Face Hub cache (`from_pretrained(repo, cache_dir=...)`), read the way
//! huggingface_hub resolves them offline: `models--{org}--{name}/refs/main` names the snapshot.
use anyhow::{Context, Result};
use std::path::{Path, PathBuf};

/// `<cache_dir>/models--org--name/snapshots/<refs/main>/`
pub fn snapshot_dir(cache_dir: &Path, repo_id: &str) -> Result<PathBuf> {
    let repo = cache_dir.join(format!("models--{}", repo_id.replace('/', "--")));
    let refs = repo.join("refs").join("main");
    let commit = std::fs::read_to_string(&refs).with_context(|| format!("{}", refs.display()))?;
    Ok(repo.join("snapshots").join(commit.trim()))
}
