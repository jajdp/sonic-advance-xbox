# Sonic Advance 2 on Xbox — the UWP port

How to take the [sa2](https://github.com/SAT-R/sa2) decompilation of *Sonic Advance 2* (Game Boy
Advance, 2002) and run it **on an Xbox Series X in Developer Mode**. The same recipe also builds
*Sonic Advance 1*, which the project includes.

*(Español: [README.es.md](README.es.md))*

Both have been playing on two consoles since 2026-09-16, with gameplay confirmed.

## Which console this was tested on

**An Xbox Series X**, in Developer Mode. Both of the consoles this was built and tested on are Series X,
so that is the only hardware anything claimed here covers.

**A Series S has never been tried — not once.** It is a different machine: less memory available to a
game and a weaker GPU. This may work on one, it may run slower, or it may not start at all; nothing here
has been measured on it. If you run it on a Series S, what you get is not what this README reports, and
none of the numbers here are a promise about that console.

## What this repository is

**A recipe, and it is deliberately short on code.** The game project has **no license at all**, so
nothing of it is reproduced here — not even the context lines of a diff. What is here is ours: the
WinRT entry point, the input layer for the console, and the scripts that build, package and sign.
The two changes the project needs are **described** in [`docs/HOW-IT-WORKS.md`](docs/HOW-IT-WORKS.md),
precisely enough to redo them, and not copied.

That is the same rule the other repositories in this family follow for projects without a license.

## What this repository is **not**

No ROM, no game code, no built executable, no package, no artwork. It cannot produce a playable game
on its own. See [`NOTICE.md`](NOTICE.md).

## What you need first

| | |
|---|---|
| The game project | [SAT-R/sa2](https://github.com/SAT-R/sa2), **building and running on your PC first** |
| Your own ROM | Sonic Advance 2 (and Sonic Advance 1 if you want the bonus target) |
| MSYS2 | With the toolchain the project asks for |
| Visual Studio 2022 | For `makeappx` and `signtool` |
| Python 3 | For the build and packaging scripts |
| An Xbox in Developer Mode | And a certificate to sign with |

## What it had to solve

| | Symptom | Fix |
|---|---|---|
| 1 | In UWP the process does not start at `main()` | `src/uwp_entry.cpp`: the WinRT entry point, which creates the window and hands control to the game |
| 2 | No controller | `src/input_uwp.c`: the pad read through the console's own API, replacing the desktop input path |
| 3 | The build assumed SDL2 as the desktop ships it | Described in `docs/HOW-IT-WORKS.md`: the SDL2 the project links has to be the UWP one |
| 4 | A structure alignment assumption does not hold here | Described, with the symptom it produces |

## How it was verified

Both packages were built with this recipe and have been playing on two consoles since 2026-09-16.
What this repository ships — the entry point, the input layer and the scripts — was re-read and
sanitised before publication: no path from this machine, no certificate thumbprint (it is a
parameter), no artwork.

A rebuild from a clean clone is **not** re-measured here, because that needs the project's MSYS2
toolchain. The claim is narrow on purpose, and the two changes are described well enough that you
can check them yourself against your own checkout.

## Credits and license

**Almost none of what makes this work is ours.** This repository is a recipe that glues together other people's work; without any one of these pieces there would be no port at all.

| What it does | Who made it | License |
|---|---|---|
| **[sa2](https://github.com/SAT-R/sa2)** — decompiles *Sonic Advance 1 & 2* | **SAT-R** | none declared |
| **[SDL](https://github.com/libsdl-org/SDL)** — window, input and audio | **Sam Lantinga** and the SDL contributors | zlib |

**The packaging recipe, the tooling and this documentation** are by **Recompilaciones**.


Tooling and the UWP layer by **Recompilaciones**, under the [MIT License](LICENSE).

*Sonic Advance 2* is © Sega / Sonic Team / Dimps. Not affiliated with them, with Microsoft or with
the authors of the decompilation. Details in [`NOTICE.md`](NOTICE.md); rights holders can write to
**jajdpmail@gmail.com**.
