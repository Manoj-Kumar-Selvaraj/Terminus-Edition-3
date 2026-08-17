use std::env;
use std::path::PathBuf;
use std::process::Command;

fn run(mut command: Command, what: &str) {
    let status = command.status().unwrap_or_else(|e| panic!("cannot start {what}: {e}"));
    if !status.success() { panic!("{what} failed: {status}"); }
}

fn main() {
    let out = PathBuf::from(env::var_os("OUT_DIR").expect("OUT_DIR"));
    let mut objects = Vec::new();
    {
        let object = out.join("catalog.o");
        let mut c = Command::new("g++");
        c.args(["-std=c++20", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-pthread", "-Istorage", "-c", "storage/catalog.cpp", "-o"]);
        c.arg(&object);
        run(c, "C++ compilation");
        objects.push(object);
    }
    {
        let object = out.join("codec.o");
        let mut c = Command::new("g++");
        c.args(["-std=c++20", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-pthread", "-Istorage", "-c", "storage/codec.cpp", "-o"]);
        c.arg(&object);
        run(c, "C++ compilation");
        objects.push(object);
    }
    {
        let object = out.join("common.o");
        let mut c = Command::new("g++");
        c.args(["-std=c++20", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-pthread", "-Istorage", "-c", "storage/common.cpp", "-o"]);
        c.arg(&object);
        run(c, "C++ compilation");
        objects.push(object);
    }
    {
        let object = out.join("engine.o");
        let mut c = Command::new("g++");
        c.args(["-std=c++20", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-pthread", "-Istorage", "-c", "storage/engine.cpp", "-o"]);
        c.arg(&object);
        run(c, "C++ compilation");
        objects.push(object);
    }
    {
        let object = out.join("integrity.o");
        let mut c = Command::new("g++");
        c.args(["-std=c++20", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-pthread", "-Istorage", "-c", "storage/integrity.cpp", "-o"]);
        c.arg(&object);
        run(c, "C++ compilation");
        objects.push(object);
    }
    {
        let object = out.join("lock.o");
        let mut c = Command::new("g++");
        c.args(["-std=c++20", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-pthread", "-Istorage", "-c", "storage/lock.cpp", "-o"]);
        c.arg(&object);
        run(c, "C++ compilation");
        objects.push(object);
    }
    {
        let object = out.join("maintenance.o");
        let mut c = Command::new("g++");
        c.args(["-std=c++20", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-pthread", "-Istorage", "-c", "storage/maintenance.cpp", "-o"]);
        c.arg(&object);
        run(c, "C++ compilation");
        objects.push(object);
    }
    {
        let object = out.join("recovery.o");
        let mut c = Command::new("g++");
        c.args(["-std=c++20", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-pthread", "-Istorage", "-c", "storage/recovery.cpp", "-o"]);
        c.arg(&object);
        run(c, "C++ compilation");
        objects.push(object);
    }
    {
        let object = out.join("snapshot.o");
        let mut c = Command::new("g++");
        c.args(["-std=c++20", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-pthread", "-Istorage", "-c", "storage/snapshot.cpp", "-o"]);
        c.arg(&object);
        run(c, "C++ compilation");
        objects.push(object);
    }
    {
        let object = out.join("transactions.o");
        let mut c = Command::new("g++");
        c.args(["-std=c++20", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-pthread", "-Istorage", "-c", "storage/transactions.cpp", "-o"]);
        c.arg(&object);
        run(c, "C++ compilation");
        objects.push(object);
    }
    {
        let object = out.join("wal.o");
        let mut c = Command::new("g++");
        c.args(["-std=c++20", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-pthread", "-Istorage", "-c", "storage/wal.cpp", "-o"]);
        c.arg(&object);
        run(c, "C++ compilation");
        objects.push(object);
    }
    let archive = out.join("libstonevault_engine.a");
    let mut ar = Command::new("ar");
    ar.arg("crs").arg(&archive);
    for object in &objects { ar.arg(object); }
    run(ar, "C++ archive creation");
    println!("cargo:rustc-link-search=native={}", out.display());
    println!("cargo:rustc-link-lib=static=stonevault_engine");
    println!("cargo:rustc-link-lib=dylib=stdc++");
    println!("cargo:rustc-link-arg=-pthread");
    println!("cargo:rerun-if-changed=storage");
}
