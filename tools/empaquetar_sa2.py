# -*- coding: utf-8 -*-
"""Arma el .msix del port UWP de Sonic Advance 2 (o 1) y lo firma.

Mismo patron que el de Diddy Kong Racing (C:\\dkr-msvc\\empaquetar_dkr.py), con una diferencia
que simplifica todo: **aqui no hay ROM que acompanar**. La cadena del decomp expande los
INCBIN_U8 a literales de C, asi que los graficos, los mapas y la musica viajan DENTRO del
ejecutable. El paquete es el exe, SDL2.dll y los mosaicos.

El NOMBRE y los MOSAICOS no se deciden aqui: salen de `identidad-visual.xlsx` y de la carpeta
`<your files>\\Display Images\\<variante>\\` del subproyecto, y los aplica la herramienta
central `another port of this family.py --aplicar-a`, the same way as the other ports here.
en Paper Mario. Este arbol produce DOS paquetes del mismo repo, asi que la fila del Excel se
elige con `--variante sa1` / `--variante sa2`; cada variante tiene su propia carpeta de arte.
El CRT no va dentro: llega por la dependencia Microsoft.VCLibs.140.00 que declara el manifiesto.

Uso:  py -3 empaquetar_sa2.py [version]          (sa2, el de por defecto)
      SA2_JUEGO=sa1 py -3 empaquetar_sa2.py 0.1.0.2
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

SDK_BIN = Path(r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64")
MAKEAPPX = SDK_BIN / "makeappx.exe"
SIGNTOOL = SDK_BIN / "signtool.exe"
HUELLA = "CHANGE-ME"   # CN=Decompilaciones

SDL2_UWP_BIN = Path(r"C:\sdl2-uwp\SDL2-2.32.10\VisualC-WinRT\x64\Release\SDL-UWP")
SUBPROYECTO = Path(r"<tree>"
                   r"\Game Boy Advance\Sonic Advance 2")
PAQUETE = SUBPROYECTO / "xbox" / "paquete"
IDENTIDAD = SUBPROYECTO.parents[1] / "herramientas" / "identidad-visual.py"
JUEGO_EXCEL = "Sonic Advance 2"          # la columna `juego` del Excel = la carpeta

# Los dos juegos salen del MISMO arbol (el repo SAT-R/sa2 trae la decomp de los dos) y por eso
# comparten subproyecto: Sonic Advance 1 es el «bonus» que ya estaba en el lane de PC. En el
# Excel cada uno es una fila con su `variante`, que es este mismo codigo.
JUEGO = os.environ.get("SA2_JUEGO", "sa2")       # sa2 | sa1
NOMBRE_MSIX, MANIFIESTO = {
    "sa2": ("SonicAdvance2", "Package.appxmanifest"),
    "sa1": ("SonicAdvance1", "Package-sa1.appxmanifest"),
}[JUEGO]

EXE = Path(r"<tree>") / JUEGO / f"{JUEGO}.exe"


def aplicar_identidad(manifiesto):
    """Nombre para mostrar y mosaicos, desde el Excel y Display Images\\<variante>\\.

    Se aplica sobre la copia de trabajo del paquete, no sobre el manifiesto fuente: los dos
    manifiestos de este subproyecto viven en la misma carpeta y referencian `Assets\\`, asi que
    aplicarlo alli haria que una variante pisara los mosaicos de la otra."""
    r = subprocess.run([sys.executable, str(IDENTIDAD), "--aplicar-a", JUEGO_EXCEL,
                        str(manifiesto), "--variante", JUEGO])
    return r.returncode


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else "0.1.0.0"
    salida = PAQUETE / f"{NOMBRE_MSIX}_{version}_x64.msix"
    raiz = PAQUETE / f"contenido-{JUEGO}"
    sdl = SDL2_UWP_BIN / "SDL2.dll"
    semilla = PAQUETE / f"Assets-{JUEGO}"

    faltan = [str(p) for p in [EXE, sdl, semilla, PAQUETE / MANIFIESTO, IDENTIDAD]
              if not p.exists()]
    if faltan:
        print("=== falta material ===")
        for f in faltan:
            print(f"  {f}")
        return 2

    if raiz.exists():
        shutil.rmtree(raiz)          # carpeta de trabajo propia y regenerable
    raiz.mkdir(parents=True)

    shutil.copy2(EXE, raiz / f"{JUEGO}.exe")
    shutil.copy2(sdl, raiz / "SDL2.dll")
    # La semilla asegura que ningun PNG del manifiesto falte; identidad-visual.py reescribe
    # encima los que tengan arte en Display Images y deja los demas como estaban.
    shutil.copytree(semilla, raiz / "Assets")

    manifiesto = (PAQUETE / MANIFIESTO).read_text(encoding="utf-8")
    manifiesto = manifiesto.replace('Version="0.1.0.0"', f'Version="{version}"')
    (raiz / "AppxManifest.xml").write_text(manifiesto, encoding="utf-8")

    rc = aplicar_identidad(raiz / "AppxManifest.xml")
    if rc != 0:
        print(f"identidad-visual.py fallo (codigo {rc}).")
        return rc

    archivos = [p for p in raiz.rglob("*") if p.is_file()]
    print(f"  contenido: {len(archivos)} archivos, "
          f"{sum(p.stat().st_size for p in archivos)/1048576:.1f} MB")

    if salida.exists():
        salida.unlink()
    r = subprocess.run([str(MAKEAPPX), "pack", "/o", "/d", str(raiz), "/p", str(salida)],
                       capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        print("=== makeappx ===")
        print(r.stdout[-2500:])
        print(r.stderr[-1500:])
        return r.returncode

    r = subprocess.run([str(SIGNTOOL), "sign", "/fd", "SHA256", "/sha1", HUELLA, "/s", "My",
                        str(salida)], capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        print("=== signtool ===")
        print(r.stdout[-1500:])
        print(r.stderr[-1000:])
        return r.returncode

    print(f"  FIRMADO: {salida.name}  ({salida.stat().st_size/1048576:.1f} MB)")
    print(f"  {salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
