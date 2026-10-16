/* Mando para el port UWP: sustituye a src/platform/shared/input.c.
 *
 * El port de escritorio lee el mando con XInput directo (XInputGetState). Dentro de un
 * AppContainer ese camino no esta: en la consola los mandos llegan por Windows.Gaming.Input, que
 * es justo lo que el backend WinRT de SDL2 usa por dentro. Asi que se reimplementa la MISMA
 * funcion -- GetXInputKeys(), que devuelve la mascara de teclas del GBA -- sobre
 * SDL_GameController, y ni sdl2.c ni el juego se enteran del cambio.
 *
 * El mapeo replica el del port de escritorio (input.c), para que lo documentado en el manual
 * valga en las dos plataformas, con UNA anadidura: en escritorio la B del mando no hace nada
 * (el boton B del GBA esta en la X), y en una consola eso desconcierta, asi que aqui B y X
 * hacen las dos el B del GBA. Es un superconjunto: no quita nada.
 */
#include <SDL.h>
#include "gba/types.h"
#include "gba/io_reg.h"
#include "platform/shared/input.h"

#define STICK_THRESHOLD 0.5f

/* El gatillo derecho acelera el juego (KEY_SPEEDUP). El port de escritorio compara el valor de
 * XInput (0-255) contra 170; SDL da el eje en 0-32767, asi que el umbral equivalente es
 * 170/255 * 32767. */
#define TRIGGER_SPEEDUP 21845

static SDL_GameController *sMando = NULL;

/* Contador de FPS con R3. Lo define sdl2.c, que es quien lo pinta. */
extern int gMostrarFps;

/* Abre el primer mando que el sistema reconozca. Se reintenta mientras no haya ninguno, porque
 * en la consola el mando puede emparejarse despues de arrancar el juego. */
static void AbrirMando(void)
{
    int i, n;

    if (sMando != NULL) {
        if (SDL_GameControllerGetAttached(sMando)) {
            return;
        }
        SDL_GameControllerClose(sMando);
        sMando = NULL;
    }

    /* sdl2.c inicializa VIDEO|AUDIO|JOYSTICK, no GAMECONTROLLER: hay que pedirlo aqui. */
    if (!SDL_WasInit(SDL_INIT_GAMECONTROLLER)) {
        if (SDL_InitSubSystem(SDL_INIT_GAMECONTROLLER) < 0) {
            return;
        }
    }

    n = SDL_NumJoysticks();
    for (i = 0; i < n; i++) {
        if (SDL_IsGameController(i)) {
            sMando = SDL_GameControllerOpen(i);
            if (sMando != NULL) {
                fprintf(stderr, "[uwp] mando: %s\n", SDL_GameControllerName(sMando));
                return;
            }
        }
    }
}

SharedKeys GetXInputKeys(void)
{
    SharedKeys keys = 0;
    Sint16 xAxisRaw, yAxisRaw;
    float xAxis, yAxis;

    AbrirMando();
    if (sMando == NULL) {
        return 0;
    }

    /* El bucle de eventos del juego ya bombea (SDL_PollEvent), pero esta llamada deja el estado
     * fresco tambien si alguna vuelta no paso por ahi. */
    SDL_GameControllerUpdate();

    if (SDL_GameControllerGetButton(sMando, SDL_CONTROLLER_BUTTON_A)) {
        keys |= A_BUTTON;
    }
    if (SDL_GameControllerGetButton(sMando, SDL_CONTROLLER_BUTTON_X)
        || SDL_GameControllerGetButton(sMando, SDL_CONTROLLER_BUTTON_B)) {
        keys |= B_BUTTON;
    }
    if (SDL_GameControllerGetButton(sMando, SDL_CONTROLLER_BUTTON_START)) {
        keys |= START_BUTTON;
    }
    if (SDL_GameControllerGetButton(sMando, SDL_CONTROLLER_BUTTON_BACK)) {
        keys |= SELECT_BUTTON;
    }
    if (SDL_GameControllerGetButton(sMando, SDL_CONTROLLER_BUTTON_LEFTSHOULDER)) {
        keys |= L_BUTTON;
    }
    if (SDL_GameControllerGetButton(sMando, SDL_CONTROLLER_BUTTON_RIGHTSHOULDER)) {
        keys |= R_BUTTON;
    }
    if (SDL_GameControllerGetButton(sMando, SDL_CONTROLLER_BUTTON_DPAD_UP)) {
        keys |= DPAD_UP;
    }
    if (SDL_GameControllerGetButton(sMando, SDL_CONTROLLER_BUTTON_DPAD_DOWN)) {
        keys |= DPAD_DOWN;
    }
    if (SDL_GameControllerGetButton(sMando, SDL_CONTROLLER_BUTTON_DPAD_LEFT)) {
        keys |= DPAD_LEFT;
    }
    if (SDL_GameControllerGetButton(sMando, SDL_CONTROLLER_BUTTON_DPAD_RIGHT)) {
        keys |= DPAD_RIGHT;
    }

    /* Palanca izquierda, con el mismo umbral que el port de escritorio. */
    xAxisRaw = SDL_GameControllerGetAxis(sMando, SDL_CONTROLLER_AXIS_LEFTX);
    yAxisRaw = SDL_GameControllerGetAxis(sMando, SDL_CONTROLLER_AXIS_LEFTY);
    xAxis = (float) xAxisRaw / 32767.0f;
    yAxis = (float) yAxisRaw / 32767.0f;

    if (xAxis < -STICK_THRESHOLD) {
        keys |= DPAD_LEFT;
    } else if (xAxis > STICK_THRESHOLD) {
        keys |= DPAD_RIGHT;
    }
    /* Ojo al signo: en SDL el eje Y crece hacia ABAJO, al reves que el sThumbLY de XInput. */
    if (yAxis < -STICK_THRESHOLD) {
        keys |= DPAD_UP;
    } else if (yAxis > STICK_THRESHOLD) {
        keys |= DPAD_DOWN;
    }

    if (SDL_GameControllerGetAxis(sMando, SDL_CONTROLLER_AXIS_TRIGGERRIGHT) > TRIGGER_SPEEDUP) {
        keys |= KEY_SPEEDUP;
    }

    /* Contador de FPS con R3. R3 no esta asignado a nada del juego, asi que se lee aparte y no
     * entra en `keys`: el GBA emulado no llega a verlo. */
    {
        static int r3Pulsado = 0;
        const int r3 = SDL_GameControllerGetButton(sMando, SDL_CONTROLLER_BUTTON_RIGHTSTICK);

        if (r3 && !r3Pulsado) {
            gMostrarFps = !gMostrarFps;
        }
        r3Pulsado = r3;
    }

    return keys;
}
