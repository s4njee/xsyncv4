fn main() {
    // The C++ xs hashes with XXH3 and compresses with zstd. Linking the same
    // system libraries keeps the bytes identical without vendoring crates.
    println!("cargo:rustc-link-lib=dylib=xxhash");
    println!("cargo:rustc-link-lib=dylib=zstd");
}
