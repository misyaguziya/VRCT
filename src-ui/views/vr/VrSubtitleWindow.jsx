import clsx from "clsx";
import { MessageWithTransliteration } from "../app/main_page/main_section/message_container/log_box/message_container/MessageContainer";

import win from "./VrWindow.module.scss";
import styles from "./VrSubtitleWindow.module.scss";

// ログ窓の字幕の形。オーバーレイの small (1 行) / large (複数行) と同じ見た目の不透明な板。
// 表示・消える演出はオーバーレイの不透明度だけで行う (ここに transition / animation を置かない)。
// ロックを外している間だけ、角の取っ手を出す (当たり判定と大きさの変更は vrct-overlay)
export const VrSubtitleWindow = ({ form, entries, is_locked }) => (
    <div className={clsx(win.window, styles.board, styles[form])} data-vr-hoverable={is_locked ? undefined : ""}>
        <div className={styles.entries}>
            {entries.map(entry => (
                <div key={entry.id} className={clsx(styles.entry, styles[entry.category])}>
                    {form === "multi_line" && (
                        <p className={styles.info}>
                            <span className={styles.time}>{entry.created_at}</span>
                            <span className={styles.kind}>{entry.category === "sent" ? "Send" : "Receive"}</span>
                        </p>
                    )}
                    {entry.small && <MessageWithTransliteration item={entry.small} className={styles.small} />}
                    {entry.large.map((item, index) => <MessageWithTransliteration key={index} item={item} className={styles.large} />)}
                </div>
            ))}
        </div>
        {!is_locked && ["top_left", "bottom_left", "bottom_right"].map(corner => (
            <span key={corner} className={`${win.resize_handle} ${win[corner]}`} data-vr-hoverable="" />
        ))}
    </div>
);
