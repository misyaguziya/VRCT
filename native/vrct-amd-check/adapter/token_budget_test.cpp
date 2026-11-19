#include "token_budget.h"

// 本文127+EOTの正常完了と、EOTなしの打切りを区別する回帰テスト。
static_assert(last_decode_step(128) == 127);
static_assert(last_decode_step(1) == 0);
static_assert(completed_within_budget(128, true, 128));
static_assert(completed_within_budget(1, true, 128));
static_assert(!completed_within_budget(128, false, 128));
static_assert(!completed_within_budget(129, true, 128));
static_assert(!completed_within_budget(0, true, 128));
int main() { return 0; }
