# Instalación — del proyecto del juego al juego en la consola

*(English: [INSTALL.md](INSTALL.md))*

## 1. Haz que sa2 compile primero en tu PC

[SAT-R/sa2](https://github.com/SAT-R/sa2), con su toolchain de MSYS2 y tu propia ROM. Sonic
Advance 1 se construye del mismo proyecto si tienes también esa ROM. Si la compilación de escritorio
no funciona, nada de aquí lo hará.

## 2. Los dos cambios que el proyecto necesita

Están **descritos**, no incluidos: el proyecto no tiene licencia, así que este repositorio no
reproduce nada de su código, ni como contexto de un diff. Los dos son pequeños y
[`HOW-IT-WORKS.es.md`](HOW-IT-WORKS.es.md) dice exactamente qué hacer y qué se rompe si no:

1. el SDL2 contra el que enlaza tiene que ser el de UWP, no el de escritorio;
2. una suposición de alineación de estructuras no se sostiene en esta compilación y hay que
   relajarla.

## 3. Añadir la capa de UWP y compilar

Copia `src/uwp_entry.cpp` y `src/input_uwp.c` al proyecto, y luego:

```powershell
python tools\construir_uwp.py <ruta-a-tu-copia>
```

`uwp_entry.cpp` es el punto de entrada de WinRT —en UWP el proceso arranca en `CoreApplication`, no
en `main()`— e `input_uwp.c` lee el mando por la API de la consola.

## 4. Empaquetar, firmar e instalar

```powershell
python tools\empaquetar_sa2.py --exe <exe compilado> --tiles <tus mosaicos> --certificate <huella>
```

Tus propios mosaicos ([`ASSETS.es.md`](ASSETS.es.md)); este repositorio no trae ninguno. El
`Publisher` del manifiesto tiene que ser **exactamente** el sujeto de tu certificado.

Instala por el Device Portal (`https://<ip de la consola>:11443`, con el usuario y la
contraseña de Dev Home) con el appx de `Microsoft.VCLibs.140.00` para x64 como dependencia, y
**un usuario conectado** en la consola.

## 5. Cuando algo sale mal

| Lo que ves | Qué es |
|---|---|
| Errores de enlazado con símbolos de SDL | El SDL2 que enlazaste es el de escritorio (apartado 2) |
| El juego arranca y se comporta de forma rara | Falta el cambio de alineación (apartado 2) |
| El paquete se instala y no hace nada | No hay usuario conectado en la consola |
| Se instala pero el juego es el viejo | No subió la versión del paquete |
| Sin mando | `input_uwp.c` no entró en la compilación |
