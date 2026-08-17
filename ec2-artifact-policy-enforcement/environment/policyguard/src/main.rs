mod adapters;
mod audit;
mod cache;
mod engine;
mod exceptions;
mod model;
mod permit;
mod policy;
mod scanner;

use engine::EnginePaths;
use model::{parse_flags, Request};
use policy::Policy;
use std::env;
use std::path::{Path, PathBuf};
use std::process;

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        fail_usage("missing command");
    }
    let command = args[1].as_str();
    let tail = &args[2..];
    match command {
        "evaluate" => run_evaluate(tail),
        "verify-permit" => run_verify(tail),
        _ => fail_usage(&format!("unknown command {command}")),
    }
}

fn run_evaluate(args: &[String]) {
    let request = match Request::from_args(args) {
        Ok(value) => value,
        Err(error) => fail_usage(&error),
    };
    let flags = parse_flags(args);
    let root = root_dir();
    let policy = path_flag(&flags, "config", &root.join("config/policy.conf"));
    let scanner_db = path_flag(&flags, "scan-db", &root.join("config/scan-db.tsv"));
    let exceptions = path_flag(&flags, "exceptions", &root.join("config/exceptions.tsv"));
    let state_dir = path_flag(&flags, "state-dir", &root.join("state"));
    let paths = EnginePaths {
        policy: &policy,
        scanner_db: &scanner_db,
        exceptions: &exceptions,
        state_dir: &state_dir,
    };
    match engine::evaluate(&paths, &request) {
        Ok(decision) => {
            println!("{}", decision.to_json());
            if decision.allow {
                process::exit(0);
            }
            process::exit(42);
        }
        Err(error) => {
            eprintln!("policyguard internal error: {error}");
            process::exit(70);
        }
    }
}

fn run_verify(args: &[String]) {
    let flags = parse_flags(args);
    let required = |key: &str| -> String {
        match flags.get(key) {
            Some(value) => value.clone(),
            None => fail_usage(&format!("missing required flag --{key}")),
        }
    };
    let token = required("token");
    let instance = required("instance");
    let digest = required("digest");
    let now = match required("now").parse::<u64>() {
        Ok(value) => value,
        Err(_) => fail_usage("--now must be an unsigned epoch value"),
    };
    let root = root_dir();
    let policy_path = path_flag(&flags, "config", &root.join("config/policy.conf"));
    let policy = match Policy::load(&policy_path) {
        Ok(value) => value,
        Err(error) => {
            eprintln!("policyguard internal error: {error}");
            process::exit(70);
        }
    };
    match permit::verify(&token, &instance, &digest, now, &policy) {
        Ok(true) => {
            println!("{{\"valid\":true}}");
            process::exit(0);
        }
        Ok(false) => {
            println!("{{\"valid\":false}}");
            process::exit(43);
        }
        Err(error) => {
            eprintln!("policyguard internal error: {error}");
            process::exit(70);
        }
    }
}

fn root_dir() -> PathBuf {
    env::var_os("POLICYGUARD_ROOT")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("/app/policyguard"))
}

fn path_flag(
    flags: &std::collections::HashMap<String, String>,
    key: &str,
    default: &Path,
) -> PathBuf {
    flags
        .get(key)
        .map(PathBuf::from)
        .unwrap_or_else(|| default.to_path_buf())
}

fn fail_usage(message: &str) -> ! {
    eprintln!("policyguard usage error: {message}");
    process::exit(2)
}
