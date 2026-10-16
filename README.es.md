# Sonic Advance 2 en la Xbox — el port UWP

Cómo coger la decompilación [sa2](https://github.com/SAT-R/sa2) de *Sonic Advance 2* (Game Boy
Advance, 2002) y hacerla correr **en una Xbox Series en modo desarrollador**. La misma receta
construye también *Sonic Advance 1*, que el proyecto incluye.

*(English: [README.md](README.md))*

Los dos se juegan en dos consolas desde el 2026-09-16, con partida confirmada.

## Qué es este repositorio

**Una receta, y es corta de código a propósito.** El proyecto del juego **no tiene licencia
ninguna**, así que aquí no se reproduce nada suyo: ni las líneas de contexto de un diff. Lo que hay
es nuestro: el punto de entrada de WinRT, la capa de entrada para la consola y los scripts que
compilan, empaquetan y firman. Los dos cambios que el proyecto necesita se **describen** en
[`docs/HOW-IT-WORKS.es.md`](docs/HOW-IT-WORKS.es.md), con detalle suficiente para rehacerlos, y no
se copian.

Es la misma regla que siguen los demás repositorios de esta familia con los proyectos sin licencia.

## Qué **no** es

Ninguna ROM, ningún código del juego, ningún ejecutable, ningún paquete, ningún arte. Esto no puede
dar un juego jugable por sí solo. Ver [`NOTICE.es.md`](NOTICE.es.md).

## Qué hace falta antes

| | |
|---|---|
| El proyecto del juego | [SAT-R/sa2](https://github.com/SAT-R/sa2), **compilando y corriendo antes en tu PC** |
| Tu propia ROM | Sonic Advance 2 (y Sonic Advance 1 si quieres el objetivo de regalo) |
| MSYS2 | Con el toolchain que pide el proyecto |
| Visual Studio 2022 | Para `makeappx` y `signtool` |
| Python 3 | Para los scripts de compilación y empaquetado |
| Una Xbox en modo desarrollador | Y un certificado para firmar |

## Qué hubo que resolver

| | Síntoma | Arreglo |
|---|---|---|
| 1 | En UWP el proceso no arranca por `main()` | `src/uwp_entry.cpp`: el punto de entrada de WinRT, que crea la ventana y cede el control al juego |
| 2 | Sin mando | `src/input_uwp.c`: el mando leído por la API de la consola, sustituyendo el camino de entrada de escritorio |
| 3 | La compilación daba por hecho el SDL2 de escritorio | Descrito en `docs/HOW-IT-WORKS.es.md`: el SDL2 contra el que enlaza el proyecto tiene que ser el de UWP |
| 4 | Una suposición de alineación de estructuras no se sostiene aquí | Descrita, con el síntoma que produce |

## Cómo se verificó

Los dos paquetes se construyeron con esta receta y se juegan en dos consolas desde el 2026-09-16. Lo
que publica este repositorio —el punto de entrada, la capa de entrada y los scripts— se releyó y se
saneó antes de publicarlo: ninguna ruta de esta máquina, ninguna huella de certificado (es un
parámetro), ningún arte.

Una reconstrucción desde un clon limpio **no** se vuelve a medir aquí, porque necesita el toolchain
de MSYS2 del proyecto. La afirmación es estrecha a propósito, y los dos cambios están descritos con
detalle suficiente para que los compruebes tú contra tu propia copia.

## Créditos y licencia

Las herramientas y la capa de UWP son de **Recompilaciones**, bajo la [licencia MIT](LICENSE).

*Sonic Advance 2* es © Sega / Sonic Team / Dimps. Sin afiliación con ellos, ni con Microsoft, ni con
los autores de la decompilación. El detalle está en [`NOTICE.es.md`](NOTICE.es.md); los titulares de
derechos pueden escribir a **jajdpmail@gmail.com**.
