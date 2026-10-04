// VRパネルとメインの間の emit は、Rust (serde_json::Value) を通るときにオブジェクトのキーを辞書順に並び替える。
// 一覧の並び ({名前: 名前} のフォント・デバイスなど、挿入順に意味があるもの) を保つため、
// オブジェクトを [キー, 値] の組の並びに包んで送り、受け取る側で挿入順どおりに戻す。
const MARK = "__vr_entries__";

export const encodeOrdered = (value) => {
    if (Array.isArray(value)) return value.map(encodeOrdered);
    if (value && typeof value === "object") {
        return { [MARK]: Object.entries(value).map(([key, v]) => [key, encodeOrdered(v)]) };
    }
    return value;
};

export const decodeOrdered = (value) => {
    if (Array.isArray(value)) return value.map(decodeOrdered);
    if (value && typeof value === "object") {
        const entries = value[MARK];
        if (!Array.isArray(entries)) return value;
        return Object.fromEntries(entries.map(([key, v]) => [key, decodeOrdered(v)]));
    }
    return value;
};

// VR画面がメイン経由でバックエンドへ頼める操作の範囲。VR画面はローカルの資産だけを読むが、
// アプリの終了・更新・ファイルを開く・モデルのダウンロード・認証キーの変更は VR からは頼めない
const BLOCKED_RELAY_PATHS = ["/run/shutdown", "/run/update_software", "/run/open_filepath_logs", "/run/open_filepath_config_file"];
export const isRelayAllowed = (path) => typeof path === "string"
    && /^\/(get|set|run)\//.test(path)
    && !BLOCKED_RELAY_PATHS.includes(path)
    && !path.startsWith("/run/download_")
    && !/auth_key|auth_token/.test(path);
