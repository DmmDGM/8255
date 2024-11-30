<p align = "center">
    <picture>
        <source media = "(prefers-color-scheme: dark)" srcset = ".github/logo_dark.png">
        <source media = "(prefers-color-scheme: light)" srcset = ".github/logo_light.png">
        <img alt = "8255 logo" src = "/.github/logo_dark.png">
    </picture>
    <hr>
</p>

A programming language.

## Installation

```bash
git clone git@github.com:iiPythonx/8255
cd 8255
python3 -m 8255 SOME_FILE.8255
```

## Syntax

<!-- Using JS for syntax highlighting since its the closest I can find. -->

```js
PROGRAM "Program Name"              // Optional, to be used later
SIZE 8K BINARY                      // Give this program a 8192 byte stack to work with
START                               // Required for execution to begin
  010   out "Hello, world."         // Basic print to the screen
  020   alc &something :[1]         // Allocate 1 byte to the "something" register
  030   set &something 251          // Put the number 251 into the "something" register
  040   out "Number: $something."   // Write the number to the screen
.                                   // Stop execution, not required
```

- The `START` keyword must always come before the "code block", ie where the lines of code are stored.
- The `.` keyword should always be present at the end of the file to denote execution end, however it is optional.
    - If you do provide `.`, it **must** be at the end of the file (excluding blank lines).
- The `PROGRAM` directive should be at the top of the file, however it is currently unused and not enforced.
- The `SIZE` directive controls how much space to allocate to the stack.  
    - Available values are `1K`, `2K`, `4K`, `8K`, `16K`, `32K`, `64K`, & `128K`.
    - You must specify whether you want to use `BINARY` (1024) or `DECIMAL` (1000) for your byte sizes.
- Line numbers must start at `10` and go up by increments of `10`. Failure to do so will lead to a `SyntaxError`.  
    - They are not required to be zero padded, however you can pad them if you so wish.

The language has no set tab or spacing rules, it is up to you to implement spacing however you see fit.

## Reserved registers

```js
&slx    // ERROR CODE OF LAST RAN LINE, 0 IF SUCCESS
&sly    // RESERVED
&slz    // RESERVED
```

## Inspiration

8255 is inspired by the look and feel of [Pascal](https://en.wikipedia.org/wiki/Pascal_(programming_language)), [BASIC](https://en.wikipedia.org/wiki/BASIC), & [Assembly](https://en.wikipedia.org/wiki/Assembly_language).

## Copyright

© 2024-2025 Benjamin "iiPython" O'Brien, see [LICENSE.txt](LICENSE.txt) for details.
