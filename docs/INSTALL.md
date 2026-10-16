# Install — from the game project to the game on the console

*(Español: [INSTALL.es.md](INSTALL.es.md))*

## 1. Get sa2 building on your PC first

[SAT-R/sa2](https://github.com/SAT-R/sa2), with its MSYS2 toolchain and your own ROM. Sonic
Advance 1 builds from the same project if you have that ROM too. If the desktop build does not work,
nothing here will.

## 2. The two changes the project needs

They are **described**, not shipped: the project has no license, so this repository reproduces none
of its code — not even as diff context. Both are small and
[`HOW-IT-WORKS.md`](HOW-IT-WORKS.md) says exactly what to do and what breaks if you do not:

1. the SDL2 it links has to be the UWP build, not the desktop one;
2. one structure alignment assumption does not hold in this build and has to be relaxed.

## 3. Add the UWP layer and build

Copy `src/uwp_entry.cpp` and `src/input_uwp.c` into the project, then:

```powershell
python tools\construir_uwp.py <path-to-your-checkout>
```

`uwp_entry.cpp` is the WinRT entry point — in UWP the process starts at `CoreApplication`, not at
`main()` — and `input_uwp.c` reads the controller through the console's own API.

## 4. Package, sign and install

```powershell
python tools\empaquetar_sa2.py --exe <built exe> --tiles <your tiles> --certificate <thumbprint>
```

Your own tiles ([`ASSETS.md`](ASSETS.md)); this repository ships none. `Publisher` in the manifest
must be **exactly** your certificate's subject.

Install through the Device Portal (`https://<console ip>:11443`, with your Dev Home username
and password) with the `Microsoft.VCLibs.140.00` x64 appx as a dependency, and **a user signed
in** on the console.

## 5. When something goes wrong

| What you see | What it is |
|---|---|
| Link errors about SDL symbols | The SDL2 you linked is the desktop one (section 2) |
| The game starts and misbehaves in odd ways | The alignment change is missing (section 2) |
| The package installs and does nothing | No user signed in on the console |
| It installs but the game is the old build | The package version did not go up |
| No controller | `input_uwp.c` is not in the build |
