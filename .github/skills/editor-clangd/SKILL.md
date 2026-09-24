---
name: editor-clangd
description: "Use when VS Code misreports PicAmpControl firmware rather than XC8 doing it: the Problems panel or IntelliSense showing 'xc.h' file not found, undeclared registers (LATCbits, ADCON1, ADPCH, ADRES, PIR1bits, NVMCON1bits), 'Unknown argument' or 'Unsupported argument' for -mdfp= or -mcpu=, a stale compile_commands.json, clangd or the C/C++ extension failing to resolve XC8 device headers, or when editing .clangd, .vscode/settings.json, c_cpp_properties.json, or the include/macro options that feed them."

# PicAmpControl Editor and Toolchain (VS Code, clangd, C/C++ extension)

This skill covers **making the editor understand XC8/PIC code**. The build and the tests never use any
of it - they invoke XC8 directly - so a problem in here can never make the firmware wrong, and a green
build says nothing about whether this is correct. Two separate failure domains, hence two skills.

**For building, running tests, reading verdicts or debugging firmware behaviour, read
`.github/skills/build-test/SKILL.md`** - and note its standing rule that every simulator
run goes through the watchdog wrapper, no exceptions.

## The one-line summary

XC8's driver flags (`-mcpu=<part>`, `-mdfp=<pack>`) mean nothing to clangd or the C/C++ extension, and
XC8's headers are gated behind macros that only XC8 itself defines. So the compile database has to
carry, for the editor's benefit: three include directories, three family macros, and - for clangd -
a handful of XC8-specific types mapped to host equivalents. Get any one of them wrong and the symptom
is identical: `<xc.h>` not found, or every register undeclared, burying the real diagnostic.

**Full forensic detail, in the order the diagnostics mislead you, with the commands that proved each
step: [`references/xc8-headers.md`](references/xc8-headers.md).**

## Rules

- **The compile database must be a fresh configure of the directory the editor reads.** `.clangd` and
  `.vscode/settings.json` both use `_build/My_Pic_Project/release/compile_commands.json`. If that
  directory holds an old configure, the panel reports the *old* device - after the Q10 switch it named
  the 16F pack path (`Unknown argument: '-mdfp=.../PIC16F1xxxx_DFP/...'`). Do not "fix" that by
  editing flags: re-configure that directory, because the device now defaults to the Q10 in
  `device.cmake`.
- **Never hand-add `-mcpu=` to `.clangd`.** clang has no such CPU and replies
  `Unsupported argument '18F47Q10' to option '-mcpu='`; the part reaches clangd as the `__18F47Q10__`
  define already in the database.
- **The include paths and the family macros belong in `user.cmake`, not in `.clangd`.** CMake derives
  them per machine and per OS (the compiler include from `${CMAKE_C_COMPILER}`, the pack include from
  `${PICAMP_DFP_PATH}`, which `device.cmake` resolves), and writes them into the database as plain
  `-I`/`-D` flags that every consumer understands. Nothing OS-specific gets committed, and Windows
  resolves its own. `.clangd` keeps only what is portably true.
- **XC8-only types are mapped in `.clangd` alone - never in the CMake options.** `__int24`,
  `__uint24`, `__bit`, `__far`, `__at(...)` and the function-like `__interrupt(...)`. Redefining a
  compiler type for the real XC8 build would be a genuine risk to the firmware; for indexing it is
  free.
- **Do not set `C_Cpp.default.compileCommands`.** With it set, the C/C++ extension **ignores**
  `includePath`/`defines` and parses the XC8 command line instead - where `-mdfp` means nothing to it.
  Left unset, `c_cpp_properties.json`'s per-OS pack include path (Mac-XC8 / Windows-XC8) is what
  resolves the device headers.
- **Two build directories exist and only one holds the editor's database.** `.clangd` and
  `.vscode/settings.json` point at `_build/My_Pic_Project/release`, while the Q10 build tasks also
  write `_build/My_Pic_Project/q10_release`. Building in one leaves the other's database stale.

## Diagnosing this class of problem

Use clangd's own check, not the panel:

```
clangd --check=<file> --compile-commands-dir=<build dir>
```

Read its `E[...]` lines. **The panel caches**, and it will keep showing errors that this check no
longer produces: on 2026-09-23 it still reported `-mdfp`/`xc.h` problems through two restarts, because
`.clangd` had been changed again in between. `.clangd` and settings changes need a language-server
restart (or a window reload) before they apply - which reads as "the fix did not work" when it did.

`tweak: ... ==> FAIL` lines in that log are clangd's internal code-action noise, not diagnostics about
your code. Count the real ones: `[pp_file_not_found]`, `[undeclared_var_use]`, `[unknown_typename]`.
