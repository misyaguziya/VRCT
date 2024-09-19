import gc
import tempfile
from zipfile import ZipFile
from subprocess import Popen
from os import makedirs as os_makedirs
from os import path as os_path
from shutil import copyfile
from datetime import datetime
from logging import getLogger, FileHandler, Formatter, INFO
from time import sleep
from queue import Queue
from threading import Thread
from requests import get as requests_get
import webbrowser

from typing import Callable
from flashtext import KeywordProcessor
from pykakasi import kakasi
from models.translation.translation_translator import Translator
from models.transcription.transcription_utils import device_manager
from models.osc.osc_tools import sendTyping, sendMessage, receiveOscParameters, getOSCParameterValue
from models.transcription.transcription_recorder import SelectedMicEnergyAndAudioRecorder, SelectedSpeakerEnergyAndAudioRecorder
from models.transcription.transcription_recorder import SelectedMicEnergyRecorder, SelectedSpeakerEnergyRecorder
from models.transcription.transcription_transcriber import AudioTranscriber
from models.translation.translation_languages import translation_lang
from models.transcription.transcription_languages import transcription_lang
from models.translation.translation_utils import checkCTranslate2Weight, downloadCTranslate2Weight
from models.transcription.transcription_whisper import checkWhisperWeight, downloadWhisperWeight
from models.overlay.overlay import Overlay
from models.overlay.overlay_image import OverlayImage

from config import config

class threadFnc(Thread):
    def __init__(self, fnc, end_fnc=None, daemon=True, *args, **kwargs):
        super(threadFnc, self).__init__(daemon=daemon, target=fnc, *args, **kwargs)
        self.fnc = fnc
        self.end_fnc = end_fnc
        self.loop = True
        self._pause = False

    def stop(self):
        self.loop = False

    def pause(self):
        self._pause = True

    def resume(self):
        self._pause = False

    def run(self):
        while self.loop:
            self.fnc(*self._args, **self._kwargs)
            while self._pause:
                sleep(0.1)

        if callable(self.end_fnc):
            self.end_fnc()
        return

class Model:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Model, cls).__new__(cls)
            cls._instance.init()
        return cls._instance

    def init(self):
        self.logger = None
        self.th_check_device = None
        self.mic_print_transcript = None
        self.mic_audio_recorder = None
        self.mic_energy_recorder = None
        self.mic_energy_plot_progressbar = None
        self.speaker_print_transcript = None
        self.speaker_audio_recorder = None
        self.speaker_energy_recorder = None
        self.speaker_energy_plot_progressbar = None
        self.previous_send_message = ""
        self.previous_receive_message = ""
        self.translator = Translator()
        self.keyword_processor = KeywordProcessor()
        self.overlay = Overlay(
            config.OVERLAY_SMALL_LOG_SETTINGS["x_pos"],
            config.OVERLAY_SMALL_LOG_SETTINGS["y_pos"],
            config.OVERLAY_SMALL_LOG_SETTINGS["z_pos"],
            config.OVERLAY_SMALL_LOG_SETTINGS["x_rotation"],
            config.OVERLAY_SMALL_LOG_SETTINGS["y_rotation"],
            config.OVERLAY_SMALL_LOG_SETTINGS["x_rotation"],
            config.OVERLAY_SMALL_LOG_SETTINGS["display_duration"],
            config.OVERLAY_SMALL_LOG_SETTINGS["fadeout_duration"],
            config.OVERLAY_SETTINGS["opacity"],
            config.OVERLAY_SETTINGS["ui_scaling"],
        )
        self.overlay_image = OverlayImage()
        self.pre_overlay_message = None
        self.th_overlay = None
        self.mic_audio_queue = None
        self.mic_mute_status = None
        self.mic_mute_status_check = None
        self.kks = kakasi()

    def checkCTranslatorCTranslate2ModelWeight(self):
        return checkCTranslate2Weight(config.PATH_LOCAL, config.CTRANSLATE2_WEIGHT_TYPE)

    def changeTranslatorCTranslate2Model(self):
        self.translator.changeCTranslate2Model(config.PATH_LOCAL, config.CTRANSLATE2_WEIGHT_TYPE)

    def downloadCTranslate2ModelWeight(self, callbackFunc=None):
        return downloadCTranslate2Weight(config.PATH_LOCAL, config.CTRANSLATE2_WEIGHT_TYPE, callbackFunc)

    def isLoadedCTranslate2Model(self):
        return self.translator.isLoadedCTranslate2Model()

    def checkTranscriptionWhisperModelWeight(self):
        return checkWhisperWeight(config.PATH_LOCAL, config.WHISPER_WEIGHT_TYPE)

    def downloadWhisperModelWeight(self, callbackFunc=None):
        return downloadWhisperWeight(config.PATH_LOCAL, config.WHISPER_WEIGHT_TYPE, callbackFunc)

    def resetKeywordProcessor(self):
        del self.keyword_processor
        self.keyword_processor = KeywordProcessor()

    def authenticationTranslatorDeepLAuthKey(self, auth_key):
        result = self.translator.authenticationDeepLAuthKey(auth_key)
        return result

    def startLogger(self):
        os_makedirs(config.PATH_LOGS, exist_ok=True)
        logger = getLogger()
        logger.setLevel(INFO)
        file_name = os_path.join(config.PATH_LOGS, f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")
        file_handler = FileHandler(file_name, encoding="utf-8", delay=True)
        formatter = Formatter("[%(asctime)s] %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        self.logger = logger
        self.logger.disabled = False

    def stopLogger(self):
        self.logger.disabled = True
        self.logger = None

    def getListLanguageAndCountry(self):
        transcription_langs = list(transcription_lang.keys())
        translation_langs = []
        for tl_key in translation_lang.keys():
            for lang in translation_lang[tl_key]["source"]:
                translation_langs.append(lang)
        translation_langs = list(set(translation_langs))
        supported_langs = list(filter(lambda x: x in transcription_langs, translation_langs))

        languages = []
        for language in supported_langs:
            for country in transcription_lang[language]:
                languages.append(
                    {
                        "language" : language,
                        "country" : country,
                    }
                )
        languages = sorted(languages, key=lambda x: x['language'])
        return languages

    def findTranslationEngines(self, source_lang, target_lang, multi_language_translation=False):
        compatible_engines = []
        for engine in list(translation_lang.keys()):
            languages = translation_lang.get(engine, {}).get("source", {})

            if multi_language_translation is True:
                source_langs = [e["language"] for e in list(source_lang.values())]
                target_langs = [e["language"] for e in list(target_lang.values())]
            else:
                source_langs = [source_lang["primary"]["language"]]
                target_langs = [target_lang["primary"]["language"]]
            language_list = list(languages.keys())

            if all(e in language_list for e in source_langs) and all(e in language_list for e in target_langs):
                compatible_engines.append(engine)
        if "DeepL_API" in compatible_engines:
            if config.AUTH_KEYS["DeepL_API"] is None:
                compatible_engines.remove('DeepL_API')
        return compatible_engines

    def getTranslate(self, translator_name, source_language, target_language, target_country, message):
        success_flag = False
        translation = self.translator.translate(
                        translator_name=translator_name,
                        source_language=source_language,
                        target_language=target_language,
                        target_country=target_country,
                        message=message
                )

        # 翻訳失敗時のフェールセーフ処理
        if isinstance(translation, str):
            success_flag = True
        else:
            while True:
                translation = self.translator.translate(
                                    translator_name="CTranslate2",
                                    source_language=source_language,
                                    target_language=target_language,
                                    target_country=target_country,
                                    message=message
                            )
                if translation is not False:
                    break
                sleep(0.1)
        return translation, success_flag

    def getInputTranslate(self, message):
        translator_name=config.SELECTED_TRANSLATOR_ENGINES[config.SELECTED_TAB_NO]
        source_language=config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["primary"]["language"]
        target_languages=config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO]

        translations = []
        success_flags = []
        for key in target_languages.keys():
            if key == "primary" or config.MULTI_LANGUAGE_TRANSLATION is True:
                target_language = target_languages[key]["language"]
                target_country = target_languages[key]["country"]
                if target_language is not None or target_country is not None:
                    translation, success_flag = self.getTranslate(
                        translator_name,
                        source_language,
                        target_language,
                        target_country,
                        message
                        )
                    translations.append(translation)
                    success_flags.append(success_flag)

        return translations, success_flags

    def getOutputTranslate(self, message):
        translator_name=config.SELECTED_TRANSLATOR_ENGINES[config.SELECTED_TAB_NO]
        source_language=config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO]["primary"]["language"]
        target_language=config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["primary"]["language"]
        target_country=config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["primary"]["country"]

        translation, success_flag = self.getTranslate(
            translator_name,
            source_language,
            target_language,
            target_country,
            message
            )
        return [translation], success_flag

    def addKeywords(self):
        for f in config.MIC_WORD_FILTER:
            self.keyword_processor.add_keyword(f)

    def checkKeywords(self, message):
        return len(self.keyword_processor.extract_keywords(message)) != 0

    def detectRepeatSendMessage(self, message):
        repeat_flag = False
        if self.previous_send_message == message:
            repeat_flag = True
        self.previous_send_message = message
        return repeat_flag

    def detectRepeatReceiveMessage(self, message):
        repeat_flag = False
        if self.previous_receive_message == message:
            repeat_flag = True
        self.previous_receive_message = message
        return repeat_flag

    def convertMessageToTransliteration(self, message: str) -> str:
        data_list = self.kks.convert(message)
        keys_to_keep = {"orig", "hira", "hepburn"}
        filtered_list = []
        for item in data_list:
            filtered_item = {key: value for key, value in item.items() if key in keys_to_keep}
            filtered_list.append(filtered_item)
        return filtered_list

    @staticmethod
    def oscStartSendTyping():
        sendTyping(True, config.OSC_IP_ADDRESS, config.OSC_PORT)

    @staticmethod
    def oscStopSendTyping():
        sendTyping(False, config.OSC_IP_ADDRESS, config.OSC_PORT)

    @staticmethod
    def oscSendMessage(message):
        sendMessage(message, config.OSC_IP_ADDRESS, config.OSC_PORT)

    @staticmethod
    def getMuteSelfStatus():
        return getOSCParameterValue(address="/avatar/parameters/MuteSelf")

    def startCheckMuteSelfStatus(self):
        def checkMuteSelfStatus():
            if self.mic_mute_status is not None:
                self.changeMicTranscriptStatus()
                self.stopCheckMuteSelfStatus()

            status = self.getMuteSelfStatus()
            if status is not None:
                self.mic_mute_status = status
                self.changeMicTranscriptStatus()
                self.stopCheckMuteSelfStatus()

        if not isinstance(self.mic_mute_status_check, threadFnc):
            self.mic_mute_status_check = threadFnc(checkMuteSelfStatus)
            self.mic_mute_status_check.daemon = True
            self.mic_mute_status_check.start()

    def stopCheckMuteSelfStatus(self):
        if isinstance(self.mic_mute_status_check, threadFnc):
            self.mic_mute_status_check.stop()
            self.mic_mute_status_check = None

    def startReceiveOSC(self):
        osc_parameter_prefix = "/avatar/parameters/"
        param_MuteSelf = "MuteSelf"

        def change_handler_mute(address, osc_arguments):
            if osc_arguments is True and self.mic_mute_status is False:
                self.mic_mute_status = osc_arguments
                self.changeMicTranscriptStatus()
            elif osc_arguments is False and self.mic_mute_status is True:
                self.mic_mute_status = osc_arguments
                self.changeMicTranscriptStatus()

        dict_filter_and_target = {
            osc_parameter_prefix + param_MuteSelf: change_handler_mute,
        }

        th_osc_server = Thread(target=receiveOscParameters, args=(dict_filter_and_target,))
        th_osc_server.daemon = True
        th_osc_server.start()

    @staticmethod
    def checkSoftwareUpdated():
        # check update
        update_flag = False
        response = requests_get(config.GITHUB_URL)
        new_version = response.json()["name"]
        if new_version != config.VERSION:
            update_flag = True
        return update_flag

    @staticmethod
    def updateSoftware(restart:bool=True, download=None, update=None):
        def updateSoftwareTask():
            filename = 'VRCT.zip'
            program_name = 'VRCT.exe'
            folder_name = '_internal'
            tmp_directory_name = 'tmp'
            batch_name = 'update.bat'
            current_directory = config.PATH_LOCAL

            try:
                res = requests_get(config.GITHUB_URL)
                assets = res.json()['assets']
                url = [i["browser_download_url"] for i in assets if i["name"] == filename][0]
                with tempfile.TemporaryDirectory() as tmp_path:
                    res = requests_get(url, stream=True)
                    file_size = int(res.headers.get('content-length', 0))
                    total_chunk = 0
                    with open(os_path.join(tmp_path, filename), 'wb') as file:
                        for chunk in res.iter_content(chunk_size=1024*5):
                            file.write(chunk)
                            total_chunk += len(chunk)
                            if isinstance(download, Callable):
                                download(total_chunk/file_size)
                            print(f"downloaded {total_chunk}/{file_size}")

                    with ZipFile(os_path.join(tmp_path, filename)) as zf:
                        total_files = len(zf.infolist())
                        extracted_files = 0
                        for file_info in zf.infolist():
                            extracted_files += 1
                            zf.extract(file_info, os_path.join(current_directory, tmp_directory_name))
                            if isinstance(update, Callable):
                                update(extracted_files/total_files)
                            print(f"extracted {extracted_files}/{total_files}")

                copyfile(os_path.join(current_directory, folder_name, "batch", batch_name), os_path.join(current_directory, batch_name))
                command = [os_path.join(current_directory, batch_name), program_name, folder_name, tmp_directory_name, str(restart)]
                Popen(command, cwd=current_directory)
            except Exception:
                import traceback
                with open('error.log', 'a') as f:
                    traceback.print_exc(file=f)
                webbrowser.open(config.BOOTH_URL, new=2, autoraise=True)
        th_update_software = Thread(target=updateSoftwareTask)
        th_update_software.daemon = True
        th_update_software.start()

    @staticmethod
    def reStartSoftware():
        program_name = 'VRCT.exe'
        folder_name = '_internal'
        batch_name = 'restart.bat'
        current_directory = config.PATH_LOCAL
        copyfile(os_path.join(current_directory, folder_name, "batch", batch_name), os_path.join(current_directory, batch_name))
        command = [os_path.join(current_directory, batch_name), program_name]
        Popen(command, cwd=current_directory)

    def getListInputHost(self):
        result = [host for host in device_manager.getInputDevices().keys()]
        return result

    def getInputDefaultDevice(self):
        result = device_manager.getInputDevices().get(config.SELECTED_MIC_HOST, [{"name": "NoDevice"}])[0]["name"]
        return result

    def getListInputDevice(self):
        result = [device["name"] for device in device_manager.getInputDevices().get(config.SELECTED_MIC_HOST, [{"name": "NoDevice"}])]
        return result

    def getListOutputDevice(self):
        result = [device["name"] for device in device_manager.getOutputDevices()]
        return result

    def startMicTranscript(self, fnc):
        if config.AUTO_MIC_SELECT is True:
            default_device = device_manager.getDefaultInputDevice()
            mic_host_name = default_device["host"]["name"]
            mic_device_name = default_device["device"]["name"]
        else:
            mic_host_name = config.SELECTED_MIC_HOST
            mic_device_name = config.SELECTED_MIC_DEVICE

        mic_device_list = device_manager.getInputDevices().get(mic_host_name, [{"name": "NoDevice"}])
        selected_mic_device = [device for device in mic_device_list if device["name"] == mic_device_name]

        if len(selected_mic_device) == 0:
            return False

        self.mic_audio_queue = Queue()
        # self.mic_energy_queue = Queue()

        mic_device = selected_mic_device[0]
        record_timeout = config.MIC_RECORD_TIMEOUT
        phrase_timeout = config.MIC_PHRASE_TIMEOUT
        if record_timeout > phrase_timeout:
            record_timeout = phrase_timeout

        self.mic_audio_recorder = SelectedMicEnergyAndAudioRecorder(
            device=mic_device,
            energy_threshold=config.MIC_ENERGY_THRESHOLD,
            dynamic_energy_threshold=config.MIC_DYNAMIC_ENERGY_THRESHOLD,
            record_timeout=record_timeout,
        )
        # self.mic_audio_recorder.recordIntoQueue(self.mic_audio_queue, mic_energy_queue)
        self.mic_audio_recorder.recordIntoQueue(self.mic_audio_queue, None)
        self.mic_transcriber = AudioTranscriber(
            speaker=False,
            source=self.mic_audio_recorder.source,
            phrase_timeout=phrase_timeout,
            max_phrases=config.MIC_MAX_PHRASES,
            transcription_engine=config.SELECTED_TRANSCRIPTION_ENGINE,
            root=config.PATH_LOCAL,
            whisper_weight_type=config.WHISPER_WEIGHT_TYPE,
        )
        def sendMicTranscript():
            try:
                res = self.mic_transcriber.transcribeAudioQueue(
                    self.mic_audio_queue,
                    config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["primary"]["language"],
                    config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["primary"]["country"],
                    config.MIC_AVG_LOGPROB,
                    config.MIC_NO_SPEECH_PROB
                )
                if res:
                    message = self.mic_transcriber.getTranscript()
                    fnc(message)
            except Exception:
                pass

        def endMicTranscript():
            while not self.mic_audio_queue.empty():
                self.mic_audio_queue.get()
            # while not self.mic_energy_queue.empty():
            #     self.mic_energy_queue.get()
            del self.mic_transcriber
            gc.collect()

        # def sendMicEnergy():
        #     if mic_energy_queue.empty() is False:
        #         energy = mic_energy_queue.get()
        #         # print("mic energy:", energy)
        #         try:
        #             fnc(energy)
        #         except Exception:
        #             pass
        #     sleep(0.01)

        self.mic_print_transcript = threadFnc(sendMicTranscript, end_fnc=endMicTranscript)
        self.mic_print_transcript.daemon = True
        self.mic_print_transcript.start()

        # self.mic_get_energy = threadFnc(sendMicEnergy)
        # self.mic_get_energy.daemon = True
        # self.mic_get_energy.start()

        self.changeMicTranscriptStatus()

    def resumeMicTranscript(self):
        # キューをクリア
        if isinstance(self.mic_audio_queue, Queue):
            while not self.mic_audio_queue.empty():
                self.mic_audio_queue.get()

        # 文字起こしを再開
        # if isinstance(self.mic_print_transcript, threadFnc):
        #     self.mic_print_transcript.resume()

        # 音声のレコードを再開
        if isinstance(self.mic_audio_recorder, SelectedMicEnergyAndAudioRecorder):
            self.mic_audio_recorder.resume()

    def pauseMicTranscript(self):
        # 文字起こしを一時停止
        # if isinstance(self.mic_print_transcript, threadFnc):
        #     self.mic_print_transcript.pause()

        # 音声のレコードを一時停止
        if isinstance(self.mic_audio_recorder, SelectedMicEnergyAndAudioRecorder):
            self.mic_audio_recorder.pause()

    def changeMicTranscriptStatus(self):
        if config.VRC_MIC_MUTE_SYNC is True:
            if self.mic_mute_status is True:
                self.pauseMicTranscript()
            elif self.mic_mute_status is False:
                self.resumeMicTranscript()
            else:
                pass
        else:
            self.resumeMicTranscript()

    def stopMicTranscript(self):
        if isinstance(self.mic_print_transcript, threadFnc):
            self.mic_print_transcript.stop()
            self.mic_print_transcript.join()
            self.mic_print_transcript = None
        if isinstance(self.mic_audio_recorder, SelectedMicEnergyAndAudioRecorder):
            self.mic_audio_recorder.resume()
            self.mic_audio_recorder.stop()
            self.mic_audio_recorder = None
        # if isinstance(self.mic_get_energy, threadFnc):
        #     self.mic_get_energy.stop()
        #     self.mic_get_energy = None

    def startCheckMicEnergy(self, fnc:Callable[[float], None]=None) -> None:
        if isinstance(fnc, Callable):
            self.check_mic_energy_fnc = fnc

        if config.AUTO_MIC_SELECT is True:
            default_device = device_manager.getDefaultInputDevice()
            mic_host_name = default_device["host"]["name"]
            mic_device_name = default_device["device"]["name"]
        else:
            mic_host_name = config.SELECTED_MIC_HOST
            mic_device_name = config.SELECTED_MIC_DEVICE

        mic_device_list = device_manager.getInputDevices().get(mic_host_name, [{"name": "NoDevice"}])
        selected_mic_device = [device for device in mic_device_list if device["name"] == mic_device_name]

        if len(selected_mic_device) == 0:
            return False

        def sendMicEnergy():
            if mic_energy_queue.empty() is False:
                energy = mic_energy_queue.get()
                try:
                    self.check_mic_energy_fnc(energy)
                except Exception:
                    pass
            sleep(0.01)

        mic_energy_queue = Queue()
        mic_device = selected_mic_device[0]
        self.mic_energy_recorder = SelectedMicEnergyRecorder(mic_device)
        self.mic_energy_recorder.recordIntoQueue(mic_energy_queue)
        self.mic_energy_plot_progressbar = threadFnc(sendMicEnergy)
        self.mic_energy_plot_progressbar.daemon = True
        self.mic_energy_plot_progressbar.start()

    def stopCheckMicEnergy(self):
        if isinstance(self.mic_energy_plot_progressbar, threadFnc):
            self.mic_energy_plot_progressbar.stop()
            self.mic_energy_plot_progressbar.join()
            self.mic_energy_plot_progressbar = None
        if isinstance(self.mic_energy_recorder, SelectedMicEnergyRecorder):
            self.mic_energy_recorder.resume()
            self.mic_energy_recorder.stop()
            self.mic_energy_recorder = None

    def startSpeakerTranscript(self, fnc):
        if config.AUTO_SPEAKER_SELECT is True:
            default_device = device_manager.getDefaultOutputDevice()
            speaker_device_name = default_device["device"]["name"]
        else:
            speaker_device_name = config.SELECTED_SPEAKER_DEVICE

        speaker_device_list = device_manager.getOutputDevices()
        selected_speaker_device = [device for device in speaker_device_list if device["name"] == speaker_device_name]

        if len(selected_speaker_device) == 0:
            return False

        speaker_audio_queue = Queue()
        # speaker_energy_queue = Queue()
        speaker_device = selected_speaker_device[0]
        record_timeout = config.SPEAKER_RECORD_TIMEOUT
        phrase_timeout = config.SPEAKER_PHRASE_TIMEOUT
        if record_timeout > phrase_timeout:
            record_timeout = phrase_timeout

        self.speaker_audio_recorder = SelectedSpeakerEnergyAndAudioRecorder(
            device=speaker_device,
            energy_threshold=config.SPEAKER_ENERGY_THRESHOLD,
            dynamic_energy_threshold=config.SPEAKER_DYNAMIC_ENERGY_THRESHOLD,
            record_timeout=record_timeout,
        )
        # self.speaker_audio_recorder.recordIntoQueue(speaker_audio_queue, speaker_energy_queue)
        self.speaker_audio_recorder.recordIntoQueue(speaker_audio_queue, None)
        self.speaker_transcriber = AudioTranscriber(
            speaker=True,
            source=self.speaker_audio_recorder.source,
            phrase_timeout=phrase_timeout,
            max_phrases=config.SPEAKER_MAX_PHRASES,
            transcription_engine=config.SELECTED_TRANSCRIPTION_ENGINE,
            root=config.PATH_LOCAL,
            whisper_weight_type=config.WHISPER_WEIGHT_TYPE,
        )
        def sendSpeakerTranscript():
            try:
                res = self.speaker_transcriber.transcribeAudioQueue(
                    speaker_audio_queue,
                    config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO]["primary"]["language"],
                    config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO]["primary"]["country"],
                    config.SPEAKER_AVG_LOGPROB,
                    config.SPEAKER_NO_SPEECH_PROB
                )
                if res:
                    message = self.speaker_transcriber.getTranscript()
                    fnc(message)
            except Exception:
                pass

        def endSpeakerTranscript():
            speaker_audio_queue.queue.clear()
            # speaker_energy_queue.queue.clear()
            del self.speaker_transcriber
            gc.collect()

        # def sendSpeakerEnergy():
        #     if speaker_energy_queue.empty() is False:
        #         energy = speaker_energy_queue.get()
        #         # print("speaker energy:", energy)
        #         try:
        #             fnc(energy)
        #         except Exception:
        #             pass
        #     sleep(0.01)

        self.speaker_print_transcript = threadFnc(sendSpeakerTranscript, end_fnc=endSpeakerTranscript)
        self.speaker_print_transcript.daemon = True
        self.speaker_print_transcript.start()

        # self.speaker_get_energy = threadFnc(sendSpeakerEnergy)
        # self.speaker_get_energy.daemon = True
        # self.speaker_get_energy.start()

    def stopSpeakerTranscript(self):
        if isinstance(self.speaker_print_transcript, threadFnc):
            self.speaker_print_transcript.stop()
            self.speaker_print_transcript.join()
            self.speaker_print_transcript = None
        if isinstance(self.speaker_audio_recorder, SelectedSpeakerEnergyAndAudioRecorder):
            self.speaker_audio_recorder.stop()
            self.speaker_audio_recorder = None
        # if isinstance(self.speaker_get_energy, threadFnc):
        #     self.speaker_get_energy.stop()
        #     self.speaker_get_energy = None

    def startCheckSpeakerEnergy(self, fnc:Callable[[float], None]=None) -> None:
        if isinstance(fnc, Callable):
            self.check_speaker_energy_fnc = fnc

        if config.AUTO_SPEAKER_SELECT is True:
            default_device = device_manager.getDefaultOutputDevice()
            speaker_device_name = default_device["device"]["name"]
        else:
            speaker_device_name = config.SELECTED_SPEAKER_DEVICE

        speaker_device_list = device_manager.getOutputDevices()
        selected_speaker_device = [device for device in speaker_device_list if device["name"] == speaker_device_name]

        if len(selected_speaker_device) == 0:
            return False

        def sendSpeakerEnergy():
            if speaker_energy_queue.empty() is False:
                energy = speaker_energy_queue.get()
                try:
                    self.check_speaker_energy_fnc(energy)
                except Exception:
                    pass
            sleep(0.01)

        speaker_energy_queue = Queue()
        speaker_device = selected_speaker_device[0]
        self.speaker_energy_recorder = SelectedSpeakerEnergyRecorder(speaker_device)
        self.speaker_energy_recorder.recordIntoQueue(speaker_energy_queue)
        self.speaker_energy_plot_progressbar = threadFnc(sendSpeakerEnergy)
        self.speaker_energy_plot_progressbar.daemon = True
        self.speaker_energy_plot_progressbar.start()

    def stopCheckSpeakerEnergy(self):
        if isinstance(self.speaker_energy_plot_progressbar, threadFnc):
            self.speaker_energy_plot_progressbar.stop()
            self.speaker_energy_plot_progressbar.join()
            self.speaker_energy_plot_progressbar = None
        if isinstance(self.speaker_energy_recorder, SelectedSpeakerEnergyRecorder):
            self.speaker_energy_recorder.resume()
            self.speaker_energy_recorder.stop()
            self.speaker_energy_recorder = None

    def createOverlayImageShort(self, message, translation):
        your_language = config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO]["primary"]["language"]
        target_language = config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["primary"]["language"]
        ui_type = config.OVERLAY_UI_TYPE
        self.pre_overlay_message = {
            "message" : message,
            "your_language" : your_language,
            "translation" : translation,
            "target_language" : target_language,
            "ui_type" : ui_type,
        }
        return self.overlay_image.createOverlayImageShort(message, your_language, translation, target_language, ui_type)

    def clearOverlayImage(self):
        self.overlay.clearImage()

    def updateOverlay(self, img):
        self.overlay.updateImage(img)

    def startOverlay(self):
        self.overlay.startOverlay()

    def updateOverlayPosition(self):
        self.overlay.updatePosition(
            config.OVERLAY_SMALL_LOG_SETTINGS["x_pos"],
            config.OVERLAY_SMALL_LOG_SETTINGS["y_pos"],
            config.OVERLAY_SMALL_LOG_SETTINGS["z_pos"],
            config.OVERLAY_SMALL_LOG_SETTINGS["x_rotation"],
            config.OVERLAY_SMALL_LOG_SETTINGS["y_rotation"],
            config.OVERLAY_SMALL_LOG_SETTINGS["z_rotation"],
        )

    def updateOverlayTimes(self):
        display_duration = config.OVERLAY_SMALL_LOG_SETTINGS["display_duration"]
        self.overlay.updateDisplayDuration(display_duration)
        fadeout_duration = config.OVERLAY_SMALL_LOG_SETTINGS["fadeout_duration"]
        self.overlay.updateFadeoutDuration(fadeout_duration)

    def updateOverlayImageOpacity(self):
        opacity = config.OVERLAY_SETTINGS["opacity"]
        self.overlay.updateOpacity(opacity, with_fade=True)

    def updateOverlayImageUiScaling(self):
        ui_scaling = config.OVERLAY_SETTINGS["ui_scaling"]
        self.overlay.updateUiScaling(ui_scaling)

    def shutdownOverlay(self):
        self.overlay.shutdownOverlay()

model = Model()