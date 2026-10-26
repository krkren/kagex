# Included at the end of a platform kit's CMakeLists.txt (in the CI checkout) on the web, Android
# and iOS, where every plugin is built into the engine. scnfile and xp3crypt each compile their
# own copy of Monocypher, and static plugins are linked whole (--whole-archive / -force_load),
# so both copies' crypto_* functions were in the one binary: duplicate symbols. scnfile's copy
# is renamed for its own sources (scnfile-monocypher-names.h, force-included); xp3crypt's keeps
# the plain names. On the desktops scnfile is a plugin library of its own, with its symbols
# hidden, so nothing clashes there.
if(TARGET scnfile AND TARGET xp3crypt)
  get_target_property(_kagex_scn_type scnfile TYPE)
  if(_kagex_scn_type STREQUAL "STATIC_LIBRARY")
    target_compile_options(scnfile PRIVATE
      "SHELL:-include \"${CMAKE_CURRENT_LIST_DIR}/scnfile-monocypher-names.h\"")
    message(STATUS "kagex: scnfile's Monocypher renamed (xp3crypt is built in too)")
  endif()
endif()
