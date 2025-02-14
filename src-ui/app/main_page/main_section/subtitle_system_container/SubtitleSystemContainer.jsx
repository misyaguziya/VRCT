import styles from "./SubtitleSystemContainer.module.scss";
import { InputFileContainer } from "./input_file_container/InputFileContainer";
import { ModeSelectorContainer } from "./mode_selector_container/ModeSelectorContainer";
import { PlayControlContainer } from "./play_control_container/PlayControlContainer";
import { CountdownContainer } from "./countdown_container/CountdownContainer";
import { SubtitlesListContainer } from "./subtitles_list_container/SubtitlesListContainer";

export const SubtitleSystemContainer = () => {
    // const [srtContent, setSrtContent] = useState("");
    // const [cues, setCues] = useState([]);
    // const [isPlaying, setIsPlaying] = useState(false);

    // 再生モード ("relative": ボタン押下から、"absolute": 指定時刻から)
    // const [playbackMode, setPlaybackMode] = useState("relative");
    // 絶対モード用の再生開始時刻（ドロップダウンで選択、HH:MM）
    // const [targetHour, setTargetHour] = useState("23");
    // const [targetMinute, setTargetMinute] = useState("00");

    // カウントダウン状態
    // // initialCountdown: 再生開始ボタン押下時に算出される元の残り秒数
    // const [initialCountdown, setInitialCountdown] = useState(null);
    // countdownAdjustment: ユーザーが上下ボタンで調整する値（秒単位）
    // const [countdownAdjustment, setCountdownAdjustment] = useState(0);
    // effectiveCountdown: (initialCountdown + countdownAdjustment) から経過秒数を差し引いた表示用の値
    // const [effectiveCountdown, setEffectiveCountdown] = useState(null);
    // cuesScheduled: 字幕タイマーが一度スケジュールされたか
    // const [cuesScheduled, setCuesScheduled] = useState(false);

    // // タイマー（setTimeout/setInterval）のID管理用
    // const timersRef = useRef([]);
    // // カウントダウンタイマー専用の ref
    // const countdownIntervalRef = useRef(null);

    return (
        <div className={styles.container}>
            <h1 className={styles.title}>字幕プレイヤー</h1>
            <InputFileContainer />
            <ModeSelectorContainer />
            <PlayControlContainer />
            <div className={styles.border}></div>
            <CountdownContainer />
            <SubtitlesListContainer />
        </div>
    );
};
