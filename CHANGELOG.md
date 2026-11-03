# Changelog

All notable changes to this recipe. Dates are `YYYY-MM-DD`.

## 1.0.3 — 2026-11-03

### Changed

- **This repository no longer explains itself by pointing at other repositories of this
  catalogue.** Comments and documentation introduced a decision, a trap or a default as "the same
  as in such-and-such other port of ours" — which asked anyone who came here for this game to go
  and read about a different one first. Each of those comparisons carried a fact that reads better
  stated outright, so that is what is written now.

  What is still cited is everything that is **not** ours: the upstream project, the third-party
  forks the recipe is built on, and the files taken from them under their own license.

- **The build tool no longer needs a tree of ours, and the packer no longer needs an unpublished
  tool.** `construir_uwp.py` took clang and lld from the toolkit inside another port's tree of
  this catalogue; it now reads `SA2_TOOLKIT` (and `SA2_ARBOL` for the decomp tree). In
  `empaquetar_sa2.py` the packaging folder comes from `SA2_PAQUETE`, and the visual-identity step
  is now **optional**: with `SA2_IDENTIDAD` unset it is skipped and the package keeps the name and
  tiles its own manifest and seed already carry. Before, it required a tool that is not published
  here, so it could not run anywhere else by design.

## 1.0.2 — 2026-10-20

### Changed

- **The README now says which console this was tested on, and which one it was not.** Everything here
  was built and measured on an **Xbox Series X** in Developer Mode; a **Series S has never been tried**,
  so nothing here says anything about one. The wording used to say "Xbox Series", which reads as if it
  covered both, and it does not.

## 1.0.1 — 2026-10-16

### Fixed

- **`LICENSE`: the explanatory block named the wrong project.** Everything after the MIT text had
  been copied from another repository in this catalogue and never adapted: it said this was a
  derivative of a different project altogether, denied granting rights in a game that is not this
  one, quoted "the 57 lines of the upstream project", and listed folders this repository does not
  have. The MIT grant itself was correct all along, and `NOTICE.md` always had the right figures.
  The block now names SAT-R/sa2, which has no license at all and Sonic Advance 2, and points at
  `NOTICE.md` for the measurements instead of repeating a number.

## 1.0.0 — 2026-10-14

First release. The package built this way has been on two Xbox Series X consoles since 2026-09-16.

### Included

- `src/uwp_entry.cpp` and `src/input_uwp.c`: the WinRT entry point and the console input layer.
- `tools/`: the build and packaging scripts, with every path as a parameter.
- `package/Package.appxmanifest` with `CHANGE-ME` identity, and documentation in English and
  Spanish — including the two changes the game project needs, described rather than copied.

### Verified before release

Both packages (Sonic Advance 2 and the Sonic Advance 1 bonus target) were built with this recipe
and have been playing on two consoles since 2026-09-16, with gameplay confirmed.

What this repository ships was re-read and sanitised before publication: no path from the machine it
was written on, no certificate thumbprint — it is a parameter now — and no artwork. A rebuild from a
clean clone is not re-measured, because it needs the project's MSYS2 toolchain.
