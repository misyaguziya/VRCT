#pragma once

// v1.8.4 は0始まりのステップ番号で停止する。共通予算はEOTを含む生成ステップ数。
constexpr int last_decode_step(int budget) { return budget - 1; }
constexpr bool completed_within_budget(int steps, bool ends_with_eot, int budget) {
  return steps > 0 && steps <= budget && ends_with_eot;
}
