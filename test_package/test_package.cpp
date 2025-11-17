#include <cstdlib>
#include "spral.h"

int main(void) {

  int state = SPRAL_RANDOM_INITIAL_SEED;
  spral_random_real(&state, false);

  return EXIT_SUCCESS;
}
