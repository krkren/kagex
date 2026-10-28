#---------------------------------------------------------------------------
# kagex-lipsync: the mouths' vowels for the voices a game picks (README.md)
#
# Built with kagex-release (../release/CMakeLists.txt adds this folder), into the same folder:
# kagex-lipsync(.exe) and lipsync/, the models and the dictionary it reads at run time.
#
# It aligns each voice to its line with existing libraries, at fixed commits:
#   PocketSphinx (BSD-2-Clause, https://github.com/cmusphinx/pocketsphinx): forced alignment with
#     its US English acoustic model and pronunciation dictionary (CMUdict)
#   OpenJTalk (Modified BSD, https://github.com/r9y9/open_jtalk, with MeCab and NAIST-jdic, BSD):
#     a Japanese line's phonemes from its text, kanji included
# Set FETCHCONTENT_SOURCE_DIR_KAGEX_POCKETSPHINX / _KAGEX_OPENJTALK to use checkouts already here.
#---------------------------------------------------------------------------
include(FetchContent)
FetchContent_Declare(kagex_pocketsphinx
    GIT_REPOSITORY https://github.com/cmusphinx/pocketsphinx
    GIT_TAG f20ff1b7a5db64c5e892a798479e20df86e79a35
    # its own CMakeLists.txt only works as the top project: the library is built below
    SOURCE_SUBDIR kagex-none)
FetchContent_Declare(kagex_openjtalk
    GIT_REPOSITORY https://github.com/r9y9/open_jtalk
    GIT_TAG 462fc38e7520aa89e4d32b2611749208528c901e
    SOURCE_SUBDIR kagex-none)
FetchContent_MakeAvailable(kagex_pocketsphinx kagex_openjtalk)
set(_ps "${kagex_pocketsphinx_SOURCE_DIR}")
set(_ojt "${kagex_openjtalk_SOURCE_DIR}/src")

#--- PocketSphinx: the library's sources, as its src/CMakeLists.txt lists them -------------------
file(READ "${_ps}/src/CMakeLists.txt" _ps_list)
string(REGEX MATCH "add_library\\(pocketsphinx[^)]*\\)" _ps_list "${_ps_list}")
string(REGEX MATCHALL "[A-Za-z0-9_/]+\\.c" _ps_files "${_ps_list}")
list(TRANSFORM _ps_files PREPEND "${_ps}/src/")
add_library(kagex_pocketsphinx STATIC ${_ps_files})
include(CheckIncludeFile)
include(CheckSymbolExists)
include(CheckTypeSize)
check_include_file(unistd.h HAVE_UNISTD_H)
check_include_file(sys/types.h HAVE_SYS_TYPES_H)
check_include_file(sys/stat.h HAVE_SYS_STAT_H)
check_include_file(stdint.h HAVE_STDINT_H)
check_symbol_exists(snprintf stdio.h HAVE_SNPRINTF)
check_type_size(long SIZEOF_LONG)
check_type_size("long long" SIZEOF_LONG_LONG)
set(HAVE_LONG_LONG 1)
set(DEFAULT_RADIX 12)
set(PACKAGE_NAME "PocketSphinx")
set(PACKAGE_VERSION "5.0.4")
set(_psgen "${CMAKE_CURRENT_BINARY_DIR}/pocketsphinx")
configure_file("${_ps}/config.h.in" "${_psgen}/config.h")
configure_file("${_ps}/sphinx_config.h.in" "${_psgen}/include/pocketsphinx/sphinx_config.h")
target_include_directories(kagex_pocketsphinx PRIVATE "${_psgen}" "${_ps}/src" PUBLIC "${_ps}/include" "${_psgen}/include")
target_compile_definitions(kagex_pocketsphinx PRIVATE HAVE_CONFIG_H POCKETSPHINX_EXPORTS SPHINXBASE_EXPORTS)
if(MSVC)
    target_compile_options(kagex_pocketsphinx PRIVATE /W0)
else()
    target_compile_options(kagex_pocketsphinx PRIVATE -w)
    find_library(_libm m)
    if(_libm)
        target_link_libraries(kagex_pocketsphinx PUBLIC ${_libm})
    endif()
endif()

#--- OpenJTalk's front end (its own CMakeLists.txt, which works as a sub-project) ---------------
add_subdirectory("${_ojt}" openjtalk EXCLUDE_FROM_ALL)
if(MSVC)
    # OpenJTalk asks cl for /source-charset:UTF-8 and /execution-charset:UTF-8 itself, which cl
    # refuses next to the /utf-8 (the same two) every target here starts with (tools/release)
    get_target_property(_ojt_opts openjtalk COMPILE_OPTIONS)
    if(_ojt_opts)
        list(REMOVE_ITEM _ojt_opts /utf-8)
        set_target_properties(openjtalk PROPERTIES COMPILE_OPTIONS "${_ojt_opts}")
    endif()
endif()
set(_ojt_inc jpcommon mecab/src mecab2njd njd njd2jpcommon njd_set_accent_phrase njd_set_accent_type njd_set_digit
    njd_set_long_vowel njd_set_pronunciation njd_set_unvoiced_vowel text2mecab)
list(TRANSFORM _ojt_inc PREPEND "${_ojt}/")
set(_ojt_defs CHARSET_UTF_8 MECAB_CHARSET=utf-8 MECAB_UTF8_USE_ONLY HAVE_CONFIG_H DIC_VERSION=102
    MECAB_DEFAULT_RC="dummy" MECAB_WITHOUT_SHARE_DIC PACKAGE="open_jtalk" VERSION="1.11")

# MeCab's dictionary compiler, to build NAIST-jdic from its sources when building the tool
add_executable(kagex_mecab_dict_index "${_ojt}/mecab/src/mecab-dict-index.cpp")
target_include_directories(kagex_mecab_dict_index PRIVATE ${_ojt_inc})
target_compile_definitions(kagex_mecab_dict_index PRIVATE ${_ojt_defs})
target_link_libraries(kagex_mecab_dict_index PRIVATE openjtalk)
set(_dicsrc "${_ojt}/mecab-naist-jdic")
set(_dic "${CMAKE_CURRENT_BINARY_DIR}/open_jtalk_dic")
set(_dicfiles char.bin matrix.bin sys.dic unk.dic left-id.def rewrite.def pos-id.def right-id.def)
list(TRANSFORM _dicfiles PREPEND "${_dic}/" OUTPUT_VARIABLE _dicouts)
add_custom_command(OUTPUT ${_dicouts}
    COMMAND ${CMAKE_COMMAND} -E make_directory "${_dic}"
    COMMAND ${CMAKE_COMMAND} -E copy "${_dicsrc}/_left-id.def" "${_dic}/left-id.def"
    COMMAND ${CMAKE_COMMAND} -E copy "${_dicsrc}/_rewrite.def" "${_dic}/rewrite.def"
    COMMAND ${CMAKE_COMMAND} -E copy "${_dicsrc}/_pos-id.def" "${_dic}/pos-id.def"
    COMMAND ${CMAKE_COMMAND} -E copy "${_dicsrc}/_right-id.def" "${_dic}/right-id.def"
    COMMAND kagex_mecab_dict_index -d "${_dicsrc}" -o "${_dic}" -f UTF-8 -t utf-8
    DEPENDS kagex_mecab_dict_index "${_dicsrc}/naist-jdic.csv"
    COMMENT "Building the OpenJTalk dictionary (NAIST-jdic)"
    VERBATIM)
add_custom_target(kagex_lipsync_dictionary DEPENDS ${_dicouts})

#--- the tool --------------------------------------------------------------------------------
add_executable(kagex-lipsync
    src/main.cpp
    src/Voices.cpp
    src/Align.cpp
)
target_include_directories(kagex-lipsync PRIVATE src ${_ojt_inc})
target_compile_definitions(kagex-lipsync PRIVATE ${_ojt_defs})
target_link_libraries(kagex-lipsync PRIVATE kagex_release_core kagex_pocketsphinx openjtalk)
# beside kagex-release (build/<preset>/Release/)
set_target_properties(kagex-lipsync PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}")
if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    target_link_options(kagex-lipsync PRIVATE -static-libstdc++ -static-libgcc)
endif()
add_dependencies(kagex-lipsync kagex_lipsync_dictionary)

# lipsync/ beside the tool: the models, the dictionary and their licenses
set(_data "$<TARGET_FILE_DIR:kagex-lipsync>/lipsync")
add_custom_command(TARGET kagex-lipsync POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E make_directory "${_data}/pocketsphinx" "${_data}/open_jtalk" "${_data}/licenses"
    COMMAND ${CMAKE_COMMAND} -E copy_directory "${_ps}/model/en-us/en-us" "${_data}/pocketsphinx/en-us"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different "${_ps}/model/en-us/cmudict-en-us.dict" "${_data}/pocketsphinx/"
    COMMAND ${CMAKE_COMMAND} -E copy_directory "${_dic}" "${_data}/open_jtalk"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different "${_ps}/LICENSE" "${_data}/licenses/pocketsphinx.txt"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different "${_ojt}/COPYING" "${_data}/licenses/open_jtalk.txt"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different "${_ojt}/mecab/COPYING" "${_data}/licenses/mecab.txt"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different "${_dicsrc}/COPYING" "${_data}/licenses/naist-jdic.txt"
    VERBATIM)

# The screen: appserve's client library and web/, zipped into the exe
set(_stage "${CMAKE_CURRENT_BINARY_DIR}/web")
file(REMOVE_RECURSE "${_stage}")
file(GLOB_RECURSE _web RELATIVE "${CMAKE_CURRENT_SOURCE_DIR}/web" CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/web/*")
foreach(_f IN LISTS _web)
    configure_file("${CMAKE_CURRENT_SOURCE_DIR}/web/${_f}" "${_stage}/${_f}" COPYONLY)
endforeach()
set(_lib "${KRKRZ_TOOLS_DIR}/external/appserve/web/lib")
file(GLOB_RECURSE _libfiles RELATIVE "${_lib}" CONFIGURE_DEPENDS "${_lib}/*")
foreach(_f IN LISTS _libfiles)
    configure_file("${_lib}/${_f}" "${_stage}/lib/${_f}" COPYONLY)
endforeach()
appserve_embed_web(kagex-lipsync WEB_DIR "${_stage}" NAME kagex_lipsync_web)
