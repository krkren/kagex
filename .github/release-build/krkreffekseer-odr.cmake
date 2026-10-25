# Given to krkrz_dev's Linux configure as CMAKE_PROJECT_INCLUDE, with KAGEX_EFK_ODR set to the
# release commit's .github/platforms/krkreffekseer-odr.cpp (krkrz_dev stays as it is). Effekseer
# declares in-class "static const" members that an unoptimized build odr-uses, and a shared
# object links with them undefined: the Debug package's libkrkreffekseer.so wouldn't load
# ("undefined symbol: Effekseer::MaterialFile::LatestSupportVersion"; 0.3.1's had the same
# fault). The file defines them in efk_core, as Android's debug APK needs (krkreffekseer-kit.cmake);
# an optimized build doesn't need them, and they do no harm there.
# CMAKE_PROJECT_INCLUDE runs after every project(); the change waits for the end of the top
# directory, when the plugins' targets exist.
get_property(_kagex_efk_odr GLOBAL PROPERTY KAGEX_EFK_ODR_DONE)
if(NOT _kagex_efk_odr)
  set_property(GLOBAL PROPERTY KAGEX_EFK_ODR_DONE TRUE)
  function(kagex_efk_odr)
    if(NOT EXISTS "${KAGEX_EFK_ODR}")
      message(FATAL_ERROR "kagex: KAGEX_EFK_ODR (${KAGEX_EFK_ODR}) doesn't exist")
    elseif(TARGET efk_core)
      target_sources(efk_core PRIVATE "${KAGEX_EFK_ODR}")
      message(STATUS "kagex: Effekseer's static members are defined in efk_core")
    else()
      message(WARNING "kagex: no efk_core target (krkreffekseer isn't built)")
    endif()
  endfunction()
  cmake_language(DEFER DIRECTORY "${CMAKE_SOURCE_DIR}" CALL kagex_efk_odr)
endif()
