// 押している途中で止められたとき (vrct-overlay の Mouse::cancel)、窓には (-30000, -30000) の up が届く。
// 表示倍率で縮んでも見分けられるように遠い左上を見る。パネルの外で離しただけの up は止めたことにしない
export const isInteractionCancel = (event) => event.clientX < -1000 && event.clientY < -1000;
