// Out-of-class definitions of in-class "static const" members of Effekseer's runtime that an
// unoptimized build odr-uses (std::min and BinaryReader::Read take them by reference); an
// optimized build folds them, so only Android's debug APK failed to link without these
// ("undefined symbol: Effekseer::Gradient::KeyMax"). krkreffekseer-kit.cmake adds this file to
// the efk_core target in the CI checkout; Effekseer and krkrz_dev stay as they are.
#include "Effekseer/Effekseer.Base.Pre.h"
#include "Effekseer/Material/Effekseer.MaterialFile.h"

const int Effekseer::Gradient::KeyMax;
const int32_t Effekseer::MaterialFile::LatestSupportVersion;
const int32_t Effekseer::MaterialFile::OldestSupportVersion;
