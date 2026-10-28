//! Build only the original standalone V8 IEEE math used by the JS geometry facade.
//! No Node/V8 runtime, rendering code or GPU objects are included.
fn main() {
    // Inputs are pinned source files; no units/return, build errors abort compilation.
    // Disable contraction/reassociation to retain the original f64 expression sequence.
    let mut build=cc::Build::new();
    build.cpp(true).std("c++17").include("vendor/v8")
        .file("vendor/v8/src/base/ieee754.cc").file("vendor/v8/wrapper.cpp")
        .flag_if_supported("-ffp-contract=off").flag_if_supported("-fno-fast-math")
        .flag_if_supported("/fp:strict");
    let compiler=build.get_compiler();
    let log=std::path::PathBuf::from(std::env::var_os("OUT_DIR").unwrap()).join("dom-math-build.txt");
    std::fs::write(log,format!("path={:?}\nargs={:?}\n",compiler.path(),compiler.args())).unwrap();
    build.compile("canvas_dom_ieee754");
    let mut number=cc::Build::new();
    number.cpp(true).std("c++17").include("vendor/v8-numbers")
        .file("vendor/v8-numbers/format.cpp").flag_if_supported("-ffp-contract=off")
        .flag_if_supported("-fno-fast-math").flag_if_supported("/fp:strict");
    for name in ["bignum","bignum-dtoa","cached-powers","diy-fp","dtoa","fast-dtoa","fixed-dtoa"] {
        number.file(format!("vendor/v8-numbers/src/base/numbers/{name}.cc"));
    }
    number.compile("canvas_number_string");
    println!("cargo:rerun-if-changed=vendor/v8-numbers");
    println!("cargo:rerun-if-changed=vendor/v8");
}
