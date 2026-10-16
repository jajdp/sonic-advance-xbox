@echo off
REM Carga el entorno «store» de Visual Studio y lanza la construccion UWP de Sonic Advance.
REM
REM «store» y no «desktop»: INCLUDE apunta a las cabeceras que filtran por WINAPI_FAMILY y LIB a
REM las bibliotecas que la Xbox acepta dentro de un AppContainer. Sin esto, clang con
REM --target=x86_64-pc-windows-msvc encuentra el CRT de escritorio y el binario no activa en la
REM consola (0x8027025B, «the app didn't start»).
setlocal
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat" x64 store
if errorlevel 1 exit /b 1
py -3 -X utf8 C:\sa2-uwp\construir_uwp.py %*
