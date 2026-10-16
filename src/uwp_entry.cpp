/* Punto de entrada del port UWP de Sonic Advance 2 / Sonic Advance 1 (SAT-R/sa2).
 *
 * En escritorio el juego arranca por main() (src/platform/pret_sdl/sdl2.c) y SDL2 abre una
 * ventana Win32. En la consola no hay ventana que abrir: el sistema crea un CoreWindow y se lo
 * entrega a la aplicacion, que debe presentarse como IFrameworkView y cederle el hilo. Ese baile
 * lo hace SDL por dentro: SDL_WinRTRunApp registra su vista, llama a CoreApplication::Run y,
 * cuando el CoreWindow ya existe, invoca la funcion que se le pase como si fuera main().
 *
 * No se usa la plantilla de SDL porque es C++/CX (/ZW), que clang no habla. Lo que hace son dos
 * cosas y las dos caben en C++ normal: RoInitialize(RO_INIT_MULTITHREADED) y SDL_WinRTRunApp.
 * Receta heredada del port de Diddy Kong Racing (xbox\notas-port-uwp.md, seccion 4nonies).
 *
 * Diferencia con DKR: aqui NO hay que localizar una ROM. El pipeline del decomp expande los
 * INCBIN_U8 a literales de C con la herramienta `preproc`, asi que todos los assets viajan
 * dentro del ejecutable. El paquete es exe + SDL2.dll y nada mas.
 */
#include <windows.h>
#include <roapi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef SDL_MAIN_HANDLED
#define SDL_MAIN_HANDLED
#endif
#include <SDL.h>
#include <SDL_main.h>

/* El juego. Con -DSDL_MAIN_HANDLED el main() de sdl2.c sigue llamandose main(). */
extern "C" int main(int argc, char **argv);

/* --------------------------------------------------------------------------------------------
 * La partida guardada.
 *
 * sdl2.c hace fopen("sa2.sav", "r+b") con ruta RELATIVA, contra el directorio actual. En
 * escritorio eso es la carpeta del juego; dentro de un AppContainer el directorio actual es la
 * carpeta de instalacion, que es de SOLO LECTURA: el fopen fallaria y el juego no podria guardar.
 *
 * SDL_GetPrefPath en el backend WinRT resuelve a LocalState, que es la carpeta de escritura de
 * la aplicacion. Se calcula una vez y se cachea, porque sdl2.c la pide antes de SDL_Init (lo
 * cual vale: GetPrefPath consulta ApplicationData::Current, no el subsistema de video).
 * ----------------------------------------------------------------------------------------- */
extern "C" char *sa2_uwp_save_path(void) {
    static char cacheada[512];
    if (cacheada[0] != '\0') {
        return cacheada;
    }
    char *base = SDL_GetPrefPath("sa2", SA2_UWP_GAME_NAME);
    if (base == NULL) {
        /* Sin LocalState no hay nada mejor que intentar; que falle por la via normal. */
        snprintf(cacheada, sizeof(cacheada), "%s.sav", SA2_UWP_GAME_NAME);
        return cacheada;
    }
    snprintf(cacheada, sizeof(cacheada), "%s%s.sav", base, SA2_UWP_GAME_NAME);
    SDL_free(base);
    return cacheada;
}

/* --------------------------------------------------------------------------------------------
 * Registro.
 *
 * En la consola no hay terminal: todo lo que el juego cuenta de si mismo (los fprintf(stderr) de
 * SDL_Init, del renderizador y del audio) se perderia, y depurar un arranque fallido en una Xbox
 * sin eso es adivinar.
 *
 * Los DOS flujos se abren en modo «a». No es un detalle: con stdout en «w» y stderr en «a» cada
 * uno lleva su propia posicion sobre el mismo archivo y se pisan las escrituras; y duplicar el
 * descriptor con _dup2 deja el FILE* de stderr con su bandera de error puesta y enmudece del
 * todo. El archivo se trunca aparte para que cada arranque empiece limpio.
 * ----------------------------------------------------------------------------------------- */
static void sa2_uwp_abrir_registro(void) {
    char *base = SDL_GetPrefPath("sa2", SA2_UWP_GAME_NAME);
    if (base == NULL) {
        return;
    }
    size_t largo = strlen(base) + 32;
    char *ruta = (char *) malloc(largo);
    if (ruta != NULL) {
        snprintf(ruta, largo, "%sregistro.txt", base);
        FILE *trunca = fopen(ruta, "w");
        if (trunca != NULL) {
            fclose(trunca);
        }
        if (freopen(ruta, "a", stdout) != NULL) {
            setvbuf(stdout, NULL, _IONBF, 0);
        }
        clearerr(stderr);
        if (freopen(ruta, "a", stderr) != NULL) {
            setvbuf(stderr, NULL, _IONBF, 0);
        }
        free(ruta);
    }
    SDL_free(base);
}

/* --------------------------------------------------------------------------------------------
 * Argumentos y variables de entorno de diagnostico, leidos de LocalState\diagnostico.txt.
 *
 * En la consola no hay linea de ordenes y getenv() devuelve NULL siempre: el proceso arranca sin
 * bloque de entorno. Pero el CRT guarda su propia copia dentro del proceso, asi que _putenv_s la
 * puebla y getenv la lee. Con esto quedan al alcance las dos variables que el juego consulta en
 * su arranque (HEADLESS y SIO_PARENT) sin tocar el binario que se juega.
 * ----------------------------------------------------------------------------------------- */
#define SA2_UWP_MAX_ARGS 16

static int sa2_uwp_args_extra(char **destino, int tope) {
    char *base = SDL_GetPrefPath("sa2", SA2_UWP_GAME_NAME);
    if (base == NULL) {
        return 0;
    }
    int puestos = 0;
    size_t largo = strlen(base) + 32;
    char *ruta = (char *) malloc(largo);
    if (ruta != NULL) {
        snprintf(ruta, largo, "%sdiagnostico.txt", base);
        FILE *f = fopen(ruta, "r");
        if (f != NULL) {
            char linea[256];
            while (puestos < tope && fgets(linea, (int) sizeof(linea), f) != NULL) {
                size_t n = strlen(linea);
                while (n > 0 && (linea[n - 1] == '\n' || linea[n - 1] == '\r' ||
                                 linea[n - 1] == ' ' || linea[n - 1] == '\t')) {
                    linea[--n] = '\0';
                }
                if (n == 0) {
                    continue;
                }
                char *igual = strchr(linea, '=');
                if (igual != NULL && linea[0] != '-') {
                    *igual = '\0';
                    _putenv_s(linea, igual + 1);
                    fprintf(stderr, "[uwp] entorno %s=%s\n", linea, igual + 1);
                    continue;
                }
                char *copia = (char *) malloc(n + 1);
                if (copia == NULL) {
                    break;
                }
                memcpy(copia, linea, n + 1);
                destino[puestos++] = copia;
            }
            fclose(f);
        }
        free(ruta);
    }
    SDL_free(base);
    return puestos;
}

/* No se le pasa &main a SDL directamente: tomar la direccion de main no esta permitido en C++.
 * Este envoltorio cuesta nada y deja el codigo dentro de lo que el estandar admite. */
static int SDLCALL sa2_uwp_arranque(int argc, char **argv) {
    char *propios[1 + SA2_UWP_MAX_ARGS + 1];

    sa2_uwp_abrir_registro();
    fprintf(stderr, "[uwp] " SA2_UWP_GAME_NAME " arrancando (argc=%d)\n", argc);

    propios[0] = (argc > 0 && argv != NULL) ? argv[0] : (char *) SA2_UWP_GAME_NAME;
    int n = 1 + sa2_uwp_args_extra(&propios[1], SA2_UWP_MAX_ARGS);
    propios[n] = NULL;
    return main(n, propios);
}

int WINAPI WinMain(HINSTANCE instancia, HINSTANCE anterior, LPSTR linea, int mostrar) {
    (void) instancia;
    (void) anterior;
    (void) linea;
    (void) mostrar;

    /* Multihilo, no monohilo: CoreApplication::Run reclama un apartamento MTA. Si esto falla no
     * se sigue, porque lo siguiente seria un cuelgue sin explicacion en la consola. */
    HRESULT hr = RoInitialize(RO_INIT_MULTITHREADED);
    if (FAILED(hr) && hr != S_FALSE && hr != RPC_E_CHANGED_MODE) {
        return (int) hr;
    }

    /* El boton B del mando no cierra el juego.
     *
     * En la consola B no es solo un boton: el sistema lo traduce ademas a la navegacion «atras»
     * (SystemNavigationManager.BackRequested), y si la aplicacion no marca ese evento como
     * atendido, el shell la CIERRA. SDL ya trae el manejador registrado pero solo marca el evento
     * si se le pide con este hint, y con prioridad OVERRIDE para que nada lo rebaje despues.
     *
     * Esto no le quita el boton al juego: la pulsacion llega aparte por Windows.Gaming.Input ->
     * SDL_GameController. Salir queda en el boton Xbox. */
    SDL_SetHintWithPriority(SDL_HINT_WINRT_HANDLE_BACK_BUTTON, "1", SDL_HINT_OVERRIDE);

    return SDL_WinRTRunApp(sa2_uwp_arranque, NULL);
}
