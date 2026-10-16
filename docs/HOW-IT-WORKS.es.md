# Cómo funciona

*(English: [HOW-IT-WORKS.md](HOW-IT-WORKS.md))*

## Por qué este repositorio tiene tan poco código

`SAT-R/sa2` **no tiene licencia ninguna**. Eso significa que no se puede redistribuir ni una línea
suya: ni en un parche, ni como las líneas de contexto que necesita un diff. Así que los dos cambios
que hacen falta están escritos aquí, con detalle suficiente para rehacerlos en un par de minutos.

Es la misma regla que los demás repositorios de esta familia aplican a los proyectos sin licencia, y
es por lo que `rush2-xbox` y `mk64-xbox` son como son.

## Los dos cambios, descritos

**1. El SDL2 tiene que ser el de UWP.** El proyecto enlaza el SDL2 de escritorio. Dentro de un
AppContainer esos binarios no sirven: importan bibliotecas que no están y no tienen backend de vídeo
de WinRT. Apunta la compilación a un SDL2 compilado para WindowsStore —el que lleva el bit
`APPCONTAINER`, el CRT «_app» y el backend de WinRT—. Si se te pasa, falla al enlazar con símbolos
de SDL que faltan, que al menos es un error honesto.

**2. Hay que relajar una suposición de alineación de estructuras.** La decompilación reproduce el
empaquetado de la Game Boy Advance, y en un sitio se apoya en que el compilador coloque una
estructura como lo hace la compilación de escritorio. En esta no lo hace, y el fallo no es un cierre:
el juego corre y se comporta de forma rara. Ese conviene hacerlo con cuidado.

## Qué añade este repositorio

- `src/uwp_entry.cpp` — el punto de entrada de WinRT. En UWP el proceso arranca en
  `CoreApplication`, no en `main()`: esto crea la ventana y cede el control al juego.
- `src/input_uwp.c` — el mando, leído por la API de la consola. El camino de entrada de escritorio
  no tiene aquí con quién hablar.
- `tools/` — compilación y empaquetado, con cada ruta como parámetro y la huella del certificado
  también.

## Dos juegos de un proyecto

El proyecto compila además *Sonic Advance 1*, y la misma receta lo empaqueta: dos objetivos, dos
paquetes, un solo juego de scripts. Los dos se juegan en dos consolas desde el 2026-09-16.

## Sobre el idioma

Los scripts están en inglés. Algunos comentarios de la capa de UWP están en español, que es donde se
escribieron.
