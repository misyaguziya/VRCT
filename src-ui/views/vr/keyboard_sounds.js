// VRキーボードのキーの音: 実際のキーボードの1打ずつの録音 (出典は assets/sounds/keyboard/SOURCE.md)。
// Enter・BackSpace・Space・半/全 は決まった音、それ以外は残りから選ぶ (同じキーを続けて押した時は同じ音)。
// 鳴らせない環境では何もしない (入力は続ける)
const KEYPRESS_URLS = import.meta.glob("../assets/sounds/keyboard/keypress-*.wav", { eager: true, query: "?url", import: "default" });
const keypressUrl = (number) => KEYPRESS_URLS[`../assets/sounds/keyboard/keypress-${number}.wav`];
const FIXED_KEY_SOUNDS = { enter: keypressUrl("031"), backspace: keypressUrl("019"), space: keypressUrl("028"), toggle: keypressUrl("029") };
const SCATTERED_KEY_SOUNDS = Object.values(KEYPRESS_URLS).filter((url) => !Object.values(FIXED_KEY_SOUNDS).includes(url));
// 文字を打たない Shift と、半/全・◀ ▶・一覧などは控えめに
const KEY_SOUND_GAIN = { shift: 0.05, soft: 0.05, toggle: 0.05 };
const KEY_SOUND_GAIN_DEFAULT = 0.1;

let audio_context = null;
const key_buffers = {};
// 最後に鳴らしたキーとその音
let last_key_sound = { id: undefined, url: null };
const keyBuffer = (url) => key_buffers[url] ??= fetch(url).then((response) => response.arrayBuffer())
    .then((data) => audio_context.decodeAudioData(data));

// 最初の1打が遅れないよう、開いた時に読んでおく
export const loadKeySounds = () => {
    try {
        audio_context ??= new AudioContext();
        Object.values(KEYPRESS_URLS).forEach((url) => keyBuffer(url).catch(() => delete key_buffers[url]));
    } catch {
        // 音が出せなくても入力は続ける
    }
};

// name: 音の種類 (enter・backspace・space・toggle は決まった音、shift・soft は控えめ、ほかは文字のキー)。
// id: どのキーか (同じキーを続けて押した時は同じ音にする)
export const playKeySound = (name, id) => {
    try {
        audio_context ??= new AudioContext();
        if (audio_context.state === "suspended") audio_context.resume();
        const same_key = id !== undefined && id === last_key_sound.id;
        const url = FIXED_KEY_SOUNDS[name]
            ?? (same_key ? last_key_sound.url : SCATTERED_KEY_SOUNDS[Math.floor(Math.random() * SCATTERED_KEY_SOUNDS.length)]);
        last_key_sound = { id, url };
        keyBuffer(url).then((buffer) => {
            const source = audio_context.createBufferSource();
            source.buffer = buffer;
            source.playbackRate.value = 0.95 + Math.random() * 0.1; // 連打で同じ音に聞こえないよう少しずらす
            const gain = audio_context.createGain();
            gain.gain.value = KEY_SOUND_GAIN[name] ?? KEY_SOUND_GAIN_DEFAULT;
            source.connect(gain).connect(audio_context.destination);
            source.start();
        }).catch(() => delete key_buffers[url]);
    } catch {
        // 音が出せなくても入力は続ける
    }
};
