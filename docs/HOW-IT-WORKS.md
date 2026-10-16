# How it works

*(Español: [HOW-IT-WORKS.es.md](HOW-IT-WORKS.es.md))*

## Why this repository has so little code in it

`SAT-R/sa2` has **no license at all**. That means no line of it can be redistributed — not in a
patch, not as the context lines a diff needs. So the two changes it requires are written down here
instead, precisely enough to redo them in a couple of minutes.

This is the same rule the other repositories in this family apply to unlicensed projects, and it is
why `rush2-xbox` and `mk64-xbox` look the way they do.

## The two changes, described

**1. SDL2 has to be the UWP build.** The project links SDL2 as the desktop ships it. Inside an
AppContainer those binaries are unusable: they import libraries that are not there and they have no
WinRT video backend. Point the build at an SDL2 compiled for WindowsStore — the one with the
`APPCONTAINER` bit, the `_app` CRT and the WinRT backend. If you miss this, it fails at link time
with missing SDL symbols, which is at least an honest error.

**2. One structure alignment assumption has to be relaxed.** The decompilation reproduces the Game
Boy Advance's packing, and one place relies on the compiler laying a structure out the way the
desktop build does. In this build it does not, and the failure is not a crash: the game runs and
behaves strangely. That one is worth doing carefully.

## What this repository does add

- `src/uwp_entry.cpp` — the WinRT entry point. In UWP the process starts at `CoreApplication`, not
  at `main()`: this creates the window and hands control to the game.
- `src/input_uwp.c` — the controller, read through the console's own API. The desktop input path has
  nothing to talk to here.
- `tools/` — build and packaging, with every path as a parameter and the certificate thumbprint as
  one too.

## Two games out of one project

The project also builds *Sonic Advance 1*, and the same recipe packages it: two targets, two
packages, one set of scripts. Both have been playing on two consoles since 2026-09-16.

## A note on language

The scripts are in English. Some comments in the UWP layer are in Spanish, which is where they were
written.
