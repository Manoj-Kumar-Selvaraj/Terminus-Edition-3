use std::env;
use std::path::{Path, PathBuf};

pub const DEFAULT_DATA_DIR: &str = "/app/stonevault/data";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RuntimeConfig {
    pub data_dir: PathBuf,
}

impl RuntimeConfig {
    pub fn from_process() -> Result<Self, String> {
        Self::from_iter(env::args().skip(1), env::var_os("STONEVAULT_DATA"))
    }

    pub fn from_iter<I, S>(args: I, env_data_dir: Option<std::ffi::OsString>) -> Result<Self, String>
    where
        I: IntoIterator<Item = S>,
        S: Into<String>,
    {
        let mut data_dir: Option<PathBuf> = None;
        let mut iter = args.into_iter().map(Into::into).peekable();
        while let Some(arg) = iter.next() {
            match arg.as_str() {
                "--data-dir" => {
                    if data_dir.is_some() {
                        return Err("--data-dir may be specified only once".to_string());
                    }
                    let value = iter
                        .next()
                        .ok_or_else(|| "--data-dir requires a path".to_string())?;
                    if value.is_empty() {
                        return Err("--data-dir requires a non-empty path".to_string());
                    }
                    data_dir = Some(PathBuf::from(value));
                }
                "--help" | "-h" => {
                    return Err("usage: stonevault [--data-dir PATH]".to_string());
                }
                value if value.starts_with("--data-dir=") => {
                    if data_dir.is_some() {
                        return Err("--data-dir may be specified only once".to_string());
                    }
                    let value = &value["--data-dir=".len()..];
                    if value.is_empty() {
                        return Err("--data-dir requires a non-empty path".to_string());
                    }
                    data_dir = Some(PathBuf::from(value));
                }
                _ => return Err(format!("unknown argument: {arg}")),
            }
        }

        let selected = if let Some(path) = env_data_dir {
            if path.is_empty() {
                PathBuf::from(DEFAULT_DATA_DIR)
            } else {
                PathBuf::from(path)
            }
        } else if let Some(path) = data_dir {
            path
        } else {
            PathBuf::from(DEFAULT_DATA_DIR)
        };

        validate_path(&selected)?;
        Ok(Self { data_dir: selected })
    }
}

fn validate_path(path: &Path) -> Result<(), String> {
    if path.as_os_str().is_empty() {
        return Err("data directory must not be empty".to_string());
    }
    if path.as_os_str().to_string_lossy().contains('\0') {
        return Err("data directory contains an invalid byte".to_string());
    }
    Ok(())
}
