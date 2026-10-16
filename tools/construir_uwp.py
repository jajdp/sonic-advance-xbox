# -*- coding: utf-8 -*-
"""Construye Sonic Advance 2 (o 1) para UWP: recompila con ABI de MSVC y enlaza con ld.lld.

El metodo es el del port de Diddy Kong Racing (another port of this family
xbox\\notas-port-uwp.md, seccion 4nonies): NO se toca el sistema de compilacion del repo ni se
mantiene un segundo arbol. Se captura la build real -- alli con compile_commands.json, aqui con
`make -n`, que para un Makefile es lo mismo -- y se traduce cada orden al dialecto UWP.

La cadena del repo tiene tres pasos por archivo y se replican los tres:

  .c   cpp -> preproc -> gcc -S -> as          =>   clang -E -> preproc -> clang -c
  .s   preproc -> cpp -> as                    =>   preproc -> clang -E -> clang -c -x assembler

`preproc` es la herramienta del decomp y NO se puede saltar: es la que expande los INCBIN_U8 a
literales de C (asi es como los assets del juego acaban DENTRO del ejecutable, sin ROM que
acompanar) y la que resuelve los `.include` de los archivos de datos y canciones.

Se lanza desde construir-uwp.bat, que antes carga el entorno «store» de Visual Studio: sin el,
INCLUDE y LIB apuntarian a las bibliotecas de escritorio y el binario no valdria para la consola.
"""
import os
import re
import shlex
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# --- herramientas -------------------------------------------------------------------------------
# clang y lld salen del toolkit de Mario Kart Wii, igual que en DKR: no hay que instalar nada.
MKW = Path(r"<tree>"
           r"\Recompilaciones sin IA\Wii\Mario Kart Wii")
TOOLKIT = MKW / r"pc\WiiCompiled\Install\Toolkit\llvm-mingw\bin"
CLANG = TOOLKIT / "clang.exe"
CLANGXX = TOOLKIT / "clang++.exe"
LLD = TOOLKIT / "ld.lld.exe"
LLVMLIB = TOOLKIT / "llvm-lib.exe"
RESOURCE_DIR = TOOLKIT.parent / "lib" / "clang" / "22"

# SDL2 compilado para WinRT en la sesion de DKR (proyecto oficial VisualC-WinRT, v143).
SDL2_UWP = Path(r"C:\sdl2-uwp\SDL2-2.32.10")
SDL2_INC = SDL2_UWP / "include"
SDL2_LIB = SDL2_UWP / r"VisualC-WinRT\x64\Release\SDL-UWP"

# El ensamblador de los datos y las canciones sigue siendo el de MinGW, a proposito. Ver la nota
# en compila_s().
MINGW = Path(r"C:\msys64\mingw64\bin")
MGW_CPP = MINGW / "cpp.exe"
MGW_AS = MINGW / "as.exe"

SRC = Path(r"<tree>")
# Un arbol de objetos por juego: los dos comparten los MISMOS nombres de objeto (src/core.o...)
# compilados con -D GAME distinto, asi que en una sola carpeta se pisarian.
OUT = SRC / "build-uwp" / os.environ.get("SA2_JUEGO", "sa2")
PREPROC = SRC / "tools" / "preproc" / "preproc.exe"
TARGET = "x86_64-pc-windows-msvc"
JUEGO = os.environ.get("SA2_JUEGO", "sa2")      # sa2 | sa1
# Las ordenes se capturan una vez por juego con `make -n sdl_win32 GAME_NAME=<juego> PREFIX=`:
# ahi va la unica diferencia real entre los dos, que es -D GAME=GAME_SA1 y que cambia la lista de
# objetos (cada uno ignora las fuentes del otro).
ORDENES = Path(rf"C:\sa2-uwp\ordenes-{JUEGO}.txt")
PLATAFORMA = "sdl_win32"                         # el nombre que preproc espera

# --- lo que se le anade a TODA unidad -------------------------------------------------------------
DEFS_UWP = [
    "-DWINAPI_FAMILY=WINAPI_FAMILY_APP",   # las cabeceras esconden lo que un AppContainer no puede
    "-D_WIN32_WINNT=0x0A00",
    "-D_CRT_SECURE_NO_WARNINGS",
    "-D__WINRT__",                         # SDL2 lo usa para elegir su backend WinRT
    "-DSDL_MAIN_HANDLED",                  # el WinMain lo pone uwp/uwp_entry.cpp, no SDL2main
    "-DSA2_UWP=1",                         # deja fuera lo que solo vale en escritorio
    # SDL_endian.h define _m_prefetch a mano «hasta que arreglen el problema de Clang 11»; en
    # clang 22 eso ya es un builtin y redefinirlo es error duro en C++. SDL protege su parche con
    # la guarda de la cabecera de clang, asi que basta declararla. Misma trampa que en DKR.
    "-D__PRFCHWINTRIN_H",
]

# Banderas que no significan nada con ABI de MSVC o que solo estorban.
#   -Werror se cae a proposito: interesa ver TODOS los errores de una pasada.
#   -masm=intel es para la salida en ensamblador (-S), que aqui no se usa: se compila a objeto.
FUERA = {"-Werror", "-masm=intel", "-x", "c", "-S", "-w", "-mwin32"}

# Fuentes que en UWP se sustituyen enteras en vez de parchearse.
#   input.c lee el mando con XInput directo, que no existe dentro de un AppContainer.
SUSTITUIR = {
    "src/platform/shared/input.c": "uwp/input_uwp.c",
}


def norm(p):
    return str(p).replace("\\", "/")


def lee_ordenes():
    """Devuelve (cppflags, ccflags, objetos) leidos del volcado de `make -n`."""
    lineas = ORDENES.read_text(encoding="utf-8", errors="replace").splitlines()

    cppflags, ccflags, objetos = None, None, None
    for ln in lineas:
        s = ln.strip()
        if cppflags is None and s.startswith("cpp ") and " -o " in s:
            toks = shlex.split(s, posix=False)
            flags, i = [], 1
            while i < len(toks):
                t = toks[i]
                if t == "-o":
                    i += 2
                    continue
                if t.endswith((".c", ".cc")):
                    i += 1
                    continue
                # El -I de SDL2 apunta al paquete MinGW del repo; lo sustituye el de UWP.
                if t.startswith("-I") and "SDL2" in t:
                    i += 1
                    continue
                flags.append(t)
                i += 1
            cppflags = flags
        if ccflags is None and "| gcc " in s and " -S " in s:
            toks = shlex.split(s.split("| gcc ", 1)[1], posix=False)
            flags, i = [], 0
            while i < len(toks):
                t = toks[i]
                if t == "-o":
                    i += 2
                    continue
                if t in FUERA or t == "-":
                    i += 1
                    continue
                flags.append(t)
                i += 1
            ccflags = flags
        if objetos is None and s.startswith("cd build/") and " && gcc " in s:
            objetos = [t for t in shlex.split(s, posix=False) if t.endswith(".o")]

    if not (cppflags and ccflags and objetos):
        raise SystemExit("no pude leer las ordenes del volcado de make -n")
    return cppflags, ccflags, objetos


def fuente_de(obj):
    """build/<plat>/<juego>/src/foo.o -> src/foo.c ; data|sound/... -> .s"""
    rel = norm(obj)
    if rel.startswith("src/"):
        c = SRC / (rel[:-2] + ".c")
        if c.exists():
            return c, "c"
        cc = SRC / (rel[:-2] + ".cc")
        if cc.exists():
            return cc, "cc"
        return None, None
    s = SRC / (rel[:-2] + ".s")
    if s.exists():
        return s, "s"
    return None, None


def syscalls():
    """La lista SYSCALLS del Makefile de libagbsyscall (una linea por continuacion)."""
    lineas = (SRC / "libagbsyscall" / "Makefile").read_text(encoding="utf-8",
                                                            errors="replace").splitlines()
    i = next(n for n, l in enumerate(lineas) if l.startswith("SYSCALLS"))
    nombres = []
    while True:
        l = lineas[i]
        sigue = l.rstrip().endswith("\\")
        nombres += l.rstrip().rstrip("\\").split(":=")[-1].split()
        i += 1
        if not sigue:
            break
    return nombres


def corre(argv, entrada=None):
    return subprocess.run(argv, input=entrada, capture_output=True, cwd=str(SRC))


def compila_c(fuente, obj, cppflags, ccflags):
    """clang -E  ->  preproc  ->  clang -c"""
    i = OUT / (obj[:-2] + ".i")
    i.parent.mkdir(parents=True, exist_ok=True)
    salida = OUT / obj
    salida.parent.mkdir(parents=True, exist_ok=True)

    argv = ([str(CLANG), f"--target={TARGET}", "-E"] + cppflags + DEFS_UWP
            + ["-I", str(SDL2_INC), "-I", str(SRC / "uwp")]
            + incs_sistema() + [str(fuente), "-o", str(i)])
    r = corre(argv)
    if r.returncode != 0:
        return r.returncode, r.stderr.decode("utf-8", "replace"), salida

    r = corre([str(PREPROC), norm(i), PLATAFORMA, ""])
    if r.returncode != 0:
        return r.returncode, r.stderr.decode("utf-8", "replace"), salida

    argv = ([str(CLANG), f"--target={TARGET}", "-fms-runtime-lib=dll", "-g", "-gcodeview"]
            + ccflags + DEFS_UWP + ["-c", "-x", "c", "-", "-o", str(salida)])
    r2 = corre(argv, entrada=r.stdout)
    return r2.returncode, r2.stderr.decode("utf-8", "replace"), salida


def compila_s(fuente, obj, cppflags):
    """preproc  ->  cpp  ->  as     (la MISMA cadena del repo, con las herramientas de MinGW)

    Los datos y las canciones son ensamblador GNU de PUROS DATOS (.incbin, .byte, .quad): ni una
    instruccion de ARM, que es lo que hace viable este port. Aun asi NO los ensambla clang, y la
    razon es concreta:

    cada cancion abre con `.equ mus_X_grp, voicegroup007`, o sea un alias a un simbolo que vive en
    OTRO objeto, y luego emite un puntero a ese alias. El ensamblador integrado de clang escribe
    ese simbolo en la seccion 0 (indefinida) de COFF y lld lo rechaza en el enlace:
    «mus_1_up_grp should not refer to special section 0». El `as` de MinGW lo resuelve como
    relocalizacion normal, que es lo que corresponde.

    No hay contrapartida: son objetos sin codigo ni CRT, el x86-64 de Windows no decora los
    simbolos y lld-link los come igual que los de clang. Ademas asi son BYTE A BYTE los mismos que
    los del lane de PC.
    """
    salida = OUT / obj
    salida.parent.mkdir(parents=True, exist_ok=True)

    r = corre([str(PREPROC), norm(fuente), PLATAFORMA, ""])
    if r.returncode != 0:
        return r.returncode, r.stderr.decode("utf-8", "replace"), salida

    # El preprocesado lo hace clang y no el cpp de MinGW: ese, alimentado por tuberia, devuelve 1
    # con la salida y el error VACIOS (con un archivo de verdad funciona). No merece pelearse, y
    # en modo assembler-with-cpp los dos hacen lo mismo: expandir los #if y los #define.
    argv = ([str(CLANG), f"--target={TARGET}", "-E", "-x", "assembler-with-cpp"]
            + cppflags + DEFS_UWP + ["-"])
    r = corre(argv, entrada=r.stdout)
    if r.returncode != 0:
        return r.returncode, r.stderr.decode("utf-8", "replace"), salida

    # -I sound: las canciones hacen `.include "MPlayDef.s"` relativo a esa carpeta.
    argv = [str(MGW_AS), "-I", "sound", "-o", str(salida), "-"]
    r2 = corre(argv, entrada=r.stdout)
    return r2.returncode, r2.stderr.decode("utf-8", "replace"), salida


def compila_extra(fuente, obj, cppflags, ccflags, defines=(), extra=()):
    """Compilacion directa, sin preproc.

    Vale para dos cosas: las fuentes propias del port (no tienen INCBIN ni charmap que expandir) y
    los .cc del juego, que en el Makefile tampoco pasan por preproc -- su regla llama al
    compilador de C++ derecho.
    """
    salida = OUT / obj
    salida.parent.mkdir(parents=True, exist_ok=True)
    es_cxx = Path(fuente).suffix in (".cpp", ".cc")
    argv = ([str(CLANGXX if es_cxx else CLANG), f"--target={TARGET}", "-fms-runtime-lib=dll",
             "-g", "-gcodeview"]
            + [f for f in ccflags if f != "-Wimplicit"] + cppflags + DEFS_UWP + list(defines)
            + list(extra)
            + ["-I", str(SDL2_INC), "-I", str(SRC / "uwp")]
            + incs_sistema()
            + ["-c", str(fuente), "-o", str(salida)])
    r = corre(argv)
    return r.returncode, r.stderr.decode("utf-8", "replace"), salida


_INCS = None


def incs_sistema():
    """Las cabeceras de clang van DELANTE de las de Visual Studio.

    No es cosmetica: el emmintrin.h de MSVC solo DECLARA las intrinsecas SSE2 (su compilador las
    resuelve en el backend) mientras que el de clang las DEFINE. Si gana el de MSVC salen cientos
    de referencias sin dueno en el enlace. Con clang-cl esto lo arregla -imsvc, que este driver no
    acepta; el orden explicito hace lo mismo. Lo aprendio DKR (seccion 4nonies de sus notas).
    """
    global _INCS
    if _INCS is None:
        _INCS = ["-isystem", str(RESOURCE_DIR / "include")]
        for d in os.environ.get("INCLUDE", "").split(";"):
            if d.strip():
                _INCS += ["-isystem", d.strip()]
    return _INCS


def main():
    if not os.environ.get("INCLUDE"):
        print("ERROR: falta el entorno «store». Lanza construir-uwp.bat, no este .py a pelo.")
        return 2

    cppflags, ccflags, objetos = lee_ordenes()
    print(f"=== construccion UWP de {JUEGO} ===")
    print(f"  objetos del enlace : {len(objetos)}")

    trabajos = []
    sin_fuente = []
    for obj in objetos:
        rel = norm(obj)
        sust = SUSTITUIR.get(rel[:-2] + ".c")
        if sust:
            trabajos.append(("extra", SRC / sust, rel))
            continue
        fuente, tipo = fuente_de(obj)
        if fuente is None:
            sin_fuente.append(rel)
        elif tipo == "cc":
            trabajos.append(("cxx", fuente, rel))
        else:
            trabajos.append(("c" if tipo == "c" else "s", fuente, rel))

    # Fuentes propias del port + la biblioteca de syscalls del GBA, que en el repo es un .a aparte
    # y se enlazaba con -lagbsyscall.
    #
    # Ojo con como esta hecha: es UN solo .c que se compila UNA VEZ POR LLAMADA, cada pasada con
    # -D L_<nombre>=1, porque el cuerpo de cada funcion vive tras su propio #if. Compilarlo de una
    # sola vez produce un objeto vacio -- literalmente, el nuestro solo tenia @feat.00 -- y el
    # enlace se cae por ArcTan2, CpuSet, Sqrt y companyia.
    trabajos.append(("extra", SRC / "uwp" / "uwp_entry.cpp", "uwp/uwp_entry.o"))
    for nombre in syscalls():
        trabajos.append(("syscall", SRC / "libagbsyscall" / "libagbsyscall.c",
                         f"libagbsyscall/{nombre}.o"))

    print(f"  sin fuente conocida: {len(sin_fuente)}  {sin_fuente[:6]}")
    print(f"  a compilar         : {len(trabajos)}")
    print(f"  salida             : {OUT}")
    print()

    defs_juego = [f'-DSA2_UWP_GAME_NAME="{JUEGO}"']

    def haz(t):
        clase, fuente, obj = t
        if clase == "c":
            rc, err, sal = compila_c(fuente, obj, cppflags, ccflags)
        elif clase == "s":
            rc, err, sal = compila_s(fuente, obj, cppflags)
        elif clase == "syscall":
            # El nombre del objeto ES el de la llamada: libagbsyscall/ArcTan2.o -> -D L_ArcTan2=1
            rc, err, sal = compila_extra(fuente, obj, cppflags, ccflags, defs_juego,
                                         (f"-DL_{Path(obj).stem}=1",))
        elif clase == "cxx":
            # Las mismas que el Makefile: CXXFLAGS := CC1FLAGS + CPPFLAGS + estas tres.
            rc, err, sal = compila_extra(fuente, obj, cppflags, ccflags, defs_juego,
                                         ("-fno-rtti", "-fno-exceptions", "-std=c++11"))
        else:
            rc, err, sal = compila_extra(fuente, obj, cppflags, ccflags, defs_juego,
                                         ("-std=c++17",) if Path(fuente).suffix == ".cpp" else ())
        return (obj, str(fuente), rc, err, sal)

    t0 = time.time()
    resultados = []
    with ThreadPoolExecutor(max_workers=min(16, (os.cpu_count() or 4))) as ex:
        for n, res in enumerate(ex.map(haz, trabajos), 1):
            resultados.append(res)
            if n % 50 == 0:
                print(f"  {n:4}/{len(trabajos)}   fallan {sum(1 for x in resultados if x[2])}")

    ok = [r for r in resultados if r[2] == 0]
    mal = [r for r in resultados if r[2] != 0]
    print()
    print(f"=== compilacion: {len(ok)} bien, {len(mal)} mal  ({time.time()-t0:.0f} s) ===")

    if mal:
        todo = "\n".join(r[3] for r in mal)
        Path(r"C:\sa2-uwp\errores-uwp.txt").write_text(todo, encoding="utf-8")
        print("\n=== archivos que fallan ===")
        for r in mal[:30]:
            print(f"  {Path(r[1]).name}")
        if len(mal) > 30:
            print(f"  ... y {len(mal)-30} mas")
        msgs = [re.sub(r"'[^']*'", "'X'", m) for m in re.findall(r"error: (.+)", todo)]
        print("\n=== errores mas repetidos ===")
        for m, n in Counter(msgs).most_common(15):
            print(f"  {n:4}  {m[:110]}")
        for etiqueta, patron in (("simbolos sin declarar", r"call to undeclared function '([^']+)'"),
                                 ("cabeceras que faltan", r"'([^']+)' file not found")):
            v = sorted(set(re.findall(patron, todo)))
            if v:
                print(f"\n=== {etiqueta} ===")
                for n in v:
                    print(f"   {n}")
        print("\n  detalle en C:\\sa2-uwp\\errores-uwp.txt")

    (OUT / "objetos.txt").write_text("\n".join(str(r[4]) for r in ok), encoding="utf-8")

    if "--enlazar" in sys.argv and not mal:
        return enlaza([r[4] for r in ok])
    if "--enlazar" in sys.argv:
        print("\n  no se enlaza: hay objetos que no compilan")
    return 0 if not mal else 1


def archiva_syscalls(objs):
    """Empaqueta libagbsyscall en un .lib, que es como lo enlazaba el repo (era un .a).

    No es un capricho de formato: esos 43 objetos CHOCAN entre si y con el juego -- VBlankIntrWait
    lo define tambien sdl2.c, ArcTan aparece en ArcTan.o y en ArcTan2.o, sineTable en los dos
    objetos de afines. En una biblioteca el enlazador solo saca el miembro que hace falta y esas
    colisiones no existen; sueltos en la linea de enlace, son siete «duplicate symbol».
    """
    lib = OUT / "libagbsyscall.lib"
    r = subprocess.run([str(LLVMLIB), f"/OUT:{lib}"] + [str(o) for o in objs],
                       capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        print("  fallo al archivar libagbsyscall:", (r.stdout or "") + (r.stderr or ""))
        return None
    return lib


def enlaza(todos):
    print("\n=== enlace con ld.lld contra el CRT «store» ===")
    objs = [o for o in todos if "libagbsyscall" not in str(o)]
    lib = archiva_syscalls([o for o in todos if "libagbsyscall" in str(o)])
    if lib is None:
        return 1
    exe = OUT / f"{JUEGO}.exe"
    opciones = ["/nologo", "/machine:x64", "/subsystem:windows",
                "/APPCONTAINER",              # el bit que exige la consola
                "/manifest:no", "/opt:ref",
                "/DEBUG", f"/PDB:{exe.with_suffix('.pdb')}",
                f"/out:{exe}"]
    rutas = [d.strip() for d in os.environ.get("LIB", "").split(";") if d.strip()]
    rutas.append(str(SDL2_LIB))
    # Ojo a la barra final: dentro de comillas, ...\store\" escaparia la comilla y se comeria el
    # argumento siguiente. Las rutas de LIB vienen JUSTO asi.
    opciones += [f"/libpath:{d.rstrip(chr(92))}" for d in rutas]
    opciones += [str(o) for o in objs]
    opciones += [
        str(lib),
        "SDL2.lib",
        "WindowsApp.lib", "OneCore.lib", "runtimeobject.lib",
        # CRT «store»: el _app es el unico que la consola acepta dentro de un AppContainer
        "msvcrt.lib", "msvcprt.lib", "vcruntime.lib", "ucrt.lib",
    ]

    # Archivo de respuesta: 565 objetos pasan de los 32 KB que admite una linea de ordenes de
    # Windows (WinError 206). El enlazador lo lee igual, una opcion por linea.
    respuesta = OUT / "enlace.rsp"
    respuesta.write_text("\n".join('"%s"' % o if " " in o else o for o in opciones),
                         encoding="utf-8")
    argv = [str(LLD), "-flavor", "link", f"@{respuesta}"]
    r = subprocess.run(argv, capture_output=True, text=True, errors="replace")
    salida = (r.stdout or "") + (r.stderr or "")
    Path(r"C:\sa2-uwp\enlace-uwp.txt").write_text(salida, encoding="utf-8")
    if r.returncode == 0:
        print(f"  ENLAZA. {exe}  ({exe.stat().st_size/1048576:.1f} MB)")
        return 0
    faltan = sorted(set(re.findall(r"undefined symbol: (.+)", salida)))
    print(f"  NO enlaza ({len(faltan)} simbolos sin resolver)")
    for s in faltan[:40]:
        print(f"   {s}")
    if len(faltan) > 40:
        print(f"   ... y {len(faltan)-40} mas")
    print("  detalle en C:\\sa2-uwp\\enlace-uwp.txt")
    return 1


if __name__ == "__main__":
    sys.exit(main())
