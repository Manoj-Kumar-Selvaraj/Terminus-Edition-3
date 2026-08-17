use std::env;
use std::path::PathBuf;
use std::process::Command;

fn run(mut command: Command, description: &str) {
    let status = command.status().unwrap_or_else(|error| {
        panic!("failed to start {description}: {error}");
    });
    if !status.success() {
        panic!("{description} failed with {status}");
    }
}

fn main() {
    let out_dir = PathBuf::from(env::var_os("OUT_DIR").expect("OUT_DIR is set by cargo"));
    let object = out_dir.join("engine.o");
    let archive = out_dir.join("libstonevault_engine.a");

    let mut compile = Command::new("g++");
    compile.args([
        "-std=c++20",
        "-O2",
        "-Wall",
        "-Wextra",
        "-Wpedantic",
        "-pthread",
        "-Istorage",
        "-c",
        "storage/engine.cpp",
        "-o",
    ]);
    compile.arg(&object);
    run(compile, "C++ storage-engine compilation");

    let mut archive_cmd = Command::new("ar");
    archive_cmd.arg("crs").arg(&archive).arg(&object);
    run(archive_cmd, "storage-engine archive creation");

    println!("cargo:rustc-link-search=native={}", out_dir.display());
    println!("cargo:rustc-link-lib=static=stonevault_engine");
    println!("cargo:rustc-link-lib=dylib=stdc++");
    println!("cargo:rustc-link-arg=-pthread");
    println!("cargo:rerun-if-changed=storage/engine.cpp");
    println!("cargo:rerun-if-changed=storage/engine.hpp");
}
