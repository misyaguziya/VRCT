#include "mel_input.h"
#include <limits>
#include <vector>

static_assert(common_mel_duration_ms(3200) == 200);
static_assert(common_mel_duration_ms(3201) == 200);
static_assert(common_mel_duration_ms(479999) == 29999);
static_assert(common_mel_duration_ms(480000) == 30000);
int main() {
  std::vector<float> values(128 * 3000, 0.0f);
  const auto valid = [&](int n) { return valid_common_mel(values.data(), values.size(), 128, 3000, n); };
  if (valid(3199) || !valid(3200) || !valid(480000) || valid(480001)) return 1;
  if (valid_common_mel(nullptr, values.size(), 128, 3000, 3200)) return 2;
  if (valid_common_mel(values.data(), values.size()-1, 128, 3000, 3200)) return 3;
  if (valid_common_mel(values.data(), values.size(), 80, 3000, 3200)) return 4;
  if (valid_common_mel(values.data(), values.size(), 128, 2999, 3200)) return 5;
  values[0] = std::numeric_limits<float>::quiet_NaN();
  if (valid(3200)) return 6;
  values[0] = std::numeric_limits<float>::infinity();
  if (valid(3200)) return 7;
  return 0;
}
