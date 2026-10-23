# Included right after project(minikin) in the web build (CMAKE_PROJECT_minikin_INCLUDE).
# minikin's forced-include _stub.h (krkr_richtext) defines ssize_t itself unless SSIZE_MAX is
# already defined, and picks int when size_t is 32-bit; Emscripten's own ssize_t is long, so
# every minikin source failed with "typedef redefinition with different types".
# Defining SSIZE_MAX as <limits.h> does skips the stub's definition.
add_compile_definitions(SSIZE_MAX=LONG_MAX)
