# Why the editor sees `xc.h` not found, or every register undeclared (2026-09-23)

The forensic record behind `../SKILL.md`. Five independent causes, and **each one on its own is enough
to keep the cascade alive** - so fixing four of them still shows the same ~20 errors. They are listed
in the order the diagnostics mislead you, which is also roughly the order they are worth checking.

The whole cascade started as: `'xc.h' file not found`, then `use of undeclared identifier 'LATCbits'`
(and `LATBbits`, `PORTCbits`, `PORTBbits`, `PIR4bits`, `PIR1bits`, `ADRES`, `ADCON0bits`, `FVRCON`,
`ANSELA`, `ANSELB`, `ADCON1`, `ADPCH`), then `too many errors emitted, stopping now` - 23 errors in
all, with the two real ones buried underneath.

## 1. `clangd --query-driver` cannot work with XC8 at all

clangd discovers a toolchain's system includes by running the driver with the translation unit's
flags. For this toolchain it runs:

```
xc8-cc -E -v -x c -
```

which answers:

```
(2042) no target device specified; use the -mcpu option to specify a target device
```

XC8 needs `-mcpu=`/`-mdfp=` for even that query, and clangd does not forward flags it does not
understand. clangd's log says it plainly:

```
E[...] System include extraction: driver execution failed with return code: 1 - ''
```

**Consequence:** adding `--query-driver=**/xc8-cc` (which looks like the right fix, and was tried)
changes nothing. The include paths have to be stated explicitly instead. `--query-driver` was removed
from `.vscode/settings.json`.

## 2. The include paths belong in CMake, not in `.clangd`

They are machine- and OS-specific, and `.clangd`'s own rule is that it stays free of machine paths
(it must work unchanged on macOS and Windows). `user.cmake` can *derive* them at configure time -
`${CMAKE_C_COMPILER}` for the compiler's include, `${PICAMP_DFP_PATH}` for the pack, and
`device.cmake` already resolves the pack per OS - and writes them into `compile_commands.json` as
plain `-I` flags that any consumer understands.

## 3. Three include directories, and one is easy to miss

```
<pack>/xc8/pic/include          pic18.h, pic18_chip_select.h
<pack>/xc8/pic/include/proc     the device header itself: pic18f47q10.h
<xc8>/pic/include               xc.h and the C library
```

`proc` is the surprising one: `pic18_chip_select.h` includes the device header as
`#include <pic18f47q10.h>` with **no** `proc/` prefix, because XC8's own `-mdfp` handling puts that
directory on the search path. Without it the device header is never found - and with the rest of the
chain intact, the failure surfaces as undeclared *registers* rather than a missing file, because
`pic18.h` itself loaded fine.

## 4. The root cause: three macros only XC8 defines

Even with every header found, `xc.h` expanded to **nothing**. Reading it explains why:

| Macro | Gate it controls |
|---|---|
| `__XC8` | `xc.h`'s entire body is `#ifdef __XC8` - undefined, `xc.h` is empty |
| `__PICC18__` | `xc.h` reaches `pic18.h` only under `#if defined(__PICC18__)` |
| `_18F47Q10` | `pic18_chip_select.h` tests this before including the device header |

Note the spelling of the last one: **single underscores**. `__18F47Q10__` (which is what
`device.cmake` defines, and what everything else uses) is *not* what the chip-select header looks for.

XC8 defines all three itself, so a build never needs them passed. A language server does. Without
them the symptom is the confusing one: **every header found, every register undeclared** - which reads
like a configuration problem and is a preprocessor problem.

Prove it without the LSP, by preprocessing directly and grepping for a register name:

```
clang -E -D__XC8 -D__PICC18__ -D_18F47Q10 \
  -I<pack>/xc8/pic/include -I<pack>/xc8/pic/include/proc \
  -I<xc8>/pic/include -I<xc8>/pic/include/c99 -x c file.c | grep -c LATCbits
```

`0` means the device header never loaded; a positive count means it did.

## 5. XC8's own C99 header uses types clang has never heard of

`c99/bits/alltypes.h` uses the 24-bit types `__int24`/`__uint24`, and the device headers use `__bit`
plus the `__far`/`__at(...)` qualifiers. clang aborts the parse at the first one
(`unknown type name '__int24'`), which by itself produces "too many errors emitted".

Mapped in `.clangd`'s `Add` list:

```
-D__int24=long
-D__uint24=unsigned long
-D__bit=unsigned char
-D__far=
-D__at(x)=
-D__interrupt(...)=
```

Two details worth keeping:

- `__interrupt` is **function-like** (`void __interrupt() isr(void)`), so it needs a variadic
  function-like macro. An object-like `-D__interrupt=` leaves `void () isr(void)` behind and clang
  reports `expected identifier or '('` at the function.
- The 24-bit mappings are cosmetically wrong (24 vs 64 bits on the host) and harmless for indexing.
  **Keep all of these out of the CMake options**: redefining a compiler type for the real XC8 build
  would be a risk to the firmware, whereas for indexing it costs nothing.

The remaining cast warning at the `offsetof(...)` table is answered by
`-Wno-pointer-to-int-cast`, because XC8's `offsetof` is not clang's on a 64-bit host.

## What the fixed configuration consists of

`user.cmake`, derived at configure time (nothing OS-specific committed):

```cmake
get_filename_component(_picamp_xc8_bin "${CMAKE_C_COMPILER}" DIRECTORY)
get_filename_component(_picamp_xc8_include "${_picamp_xc8_bin}/../pic/include" ABSOLUTE)
target_compile_options(<compile target> PRIVATE
    "-D__XC8" "-D__PICC18__" "-D_18F47Q10"
    "-I${PICAMP_DFP_PATH}/pic/include"
    "-I${PICAMP_DFP_PATH}/pic/include/proc"
    "-I${PICAMP_DFP_PATH}/pic/include/c99"
    "-I${_picamp_xc8_include}"
    "-I${_picamp_xc8_include}/c99")
```

`.clangd`: the XC8 type mappings above, `-Wno-pointer-to-int-cast`, and both `-mcpu=*` and `-mdfp=*`
in `Remove` - the latter is safe **only because** the `-I` flags above exist. Removing `-mdfp` before
them is what turned one diagnostic into the whole cascade.

`.vscode/settings.json`: `clangd.arguments` points at
`${workspaceFolder}/_build/My_Pic_Project/release`; no `--query-driver`; and **no**
`C_Cpp.default.compileCommands`.

Result: `clangd --check` on `firmware/src/main.c` went from 23 errors to 0 (only clangd's internal
`tweak` noise remains). The build was unaffected throughout - it passed both before and after this
work, and XC8 defines everything it needs itself.
