#pragma once
#include <cstddef>
#include <cmath>

// 比較契約の最終テンソル。PCMを渡す経路には戻さない。
inline bool valid_common_mel(const float* values, size_t count,
                             int mels, int frames, int original_samples) {
  if (!values || mels != 128 || frames != 3000 || count != 128u * 3000u
      || original_samples < 3200 || original_samples > 480000)
    return false;
  for (size_t i = 0; i < count; ++i)
    if (!std::isfinite(values[i])) return false;
  return true;
}
constexpr int common_mel_duration_ms(int original_samples) { return original_samples / 16; }
