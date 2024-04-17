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
from threading import Thread, Event
from requests import get as requests_get
import webbrowser

from typing import Callable
from flashtext import KeywordProcessor
from models.translation.translation_translator import Translator
from models.transcription.transcription_utils import getInputDevices, getOutputDevices
from models.osc.osc_tools import sendTyping, sendMessage, sendTestAction, receiveOscParameters
from models.transcription.transcription_recorder import SelectedMicEnergyAndAudioRecorder, SelectedSpeakerEnergyAndAudioRecorder
from models.transcription.transcription_recorder import SelectedMicEnergyRecorder, SelectedSpeakerEnergyRecorder
from models.transcription.transcription_transcriber import AudioTranscriber
from models.xsoverlay.notification import xsoverlayForVRCT
from models.translation.translation_languages import translation_lang
from models.transcription.transcription_languages import transcription_lang
from models.translation.translation_utils import checkCTranslate2Weight
from models.transcription.transcription_whisper import checkWhisperWeight
from models.overlay.overlay import Overlay
from models.overlay.overlay_image import OverlayImage

from config import config

class threadFnc(Thread):
    def __init__(self, fnc, end_fnc=None, daemon=True, *args, **kwargs):
        super(threadFnc, self).__init__(daemon=daemon, *args, **kwargs)
        self.fnc = fnc
        self.end_fnc = end_fnc
        self._stop = Event()
    def stop(self):
        self._stop.set()
    def stopped(self):
        return self._stop.is_set()
    def run(self):
        while True:
            if self.stopped():
                if callable(self.end_fnc):
                    self.end_fnc()
                return
            self.fnc(*self._args, **self._kwargs)

class Model:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Model, cls).__new__(cls)
            cls._instance.init()
        return cls._instance

    def init(self):
        self.logger = None
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
        self.overlay = Overlay()
        self.overlay_image = OverlayImage()
        self.th_overlay = None

    def checkCTranslatorCTranslate2ModelWeight(self):
        return checkCTranslate2Weight(config.PATH_LOCAL, config.CTRANSLATE2_WEIGHT_TYPE)

    def changeTranslatorCTranslate2Model(self):
        self.translator.changeCTranslate2Model(config.PATH_LOCAL, config.CTRANSLATE2_WEIGHT_TYPE)

    def clearTranslatorCTranslate2Model(self):
        self.translator.clearCTranslate2Model()

    def checkTranscriptionWhisperModelWeight(self):
        return checkWhisperWeight(config.PATH_LOCAL, config.WHISPER_WEIGHT_TYPE)

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

    def findTranslationEngines(self, source_lang, target_lang):
        compatible_engines = []
        for engine in list(translation_lang.keys()):
            languages = translation_lang.get(engine, {}).get("source", {})
            if source_lang in languages and target_lang in languages:
                compatible_engines.append(engine)
        if "DeepL_API" in compatible_engines:
            if config.AUTH_KEYS["DeepL_API"] is None:
                compatible_engines.remove('DeepL_API')
        return compatible_engines

    def getInputTranslate(self, message):
        translation_success_flag = True
        translator_name=config.CHOICE_INPUT_TRANSLATOR
        source_language=config.SOURCE_LANGUAGE
        target_language=config.TARGET_LANGUAGE
        target_country = config.TARGET_COUNTRY

        translation = self.translator.translate(
                        translator_name=translator_name,
                        source_language=source_language,
                        target_language=target_language,
                        target_country=target_country,
                        message=message
                )

        # 翻訳失敗時のフェールセーフ処理
        if translation is False:
            translation_success_flag = False
            translation = self.translator.translate(
                                translator_name="CTranslate2",
                                source_language=source_language,
                                target_language=target_language,
                                target_country=target_country,
                                message=message
                        )
        return translation, translation_success_flag

    def getOutputTranslate(self, message):
        translation_success_flag = True
        translator_name=config.CHOICE_OUTPUT_TRANSLATOR
        source_language=config.TARGET_LANGUAGE
        target_language=config.SOURCE_LANGUAGE
        target_country=config.SOURCE_COUNTRY

        translation = self.translator.translate(
                        translator_name=translator_name,
                        source_language=source_language,
                        target_language=target_language,
                        target_country=target_country,
                        message=message
                )

        # 翻訳失敗時のフェールセーフ処理
        if translation is False:
            translation_success_flag = False
            translation = self.translator.translate(
                                translator_name="CTranslate2",
                                source_language=source_language,
                                target_language=target_language,
                                target_country=target_country,
                                message=message
                        )
        return translation, translation_success_flag

    def addKeywords(self):
        for f in config.INPUT_MIC_WORD_FILTER:
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

    @staticmethod
    def oscStartSendTyping():
        sendTyping(True, config.OSC_IP_ADDRESS, config.OSC_PORT)

    @staticmethod
    def oscStopSendTyping():
        sendTyping(False, config.OSC_IP_ADDRESS, config.OSC_PORT)

    @staticmethod
    def oscSendMessage(message):
        sendMessage(message, config.OSC_IP_ADDRESS, config.OSC_PORT)

    def checkOSCStarted(self, fnc):
        self.is_valid_osc = False
        def checkOscReceive(address, osc_arguments):
            if self.is_valid_osc is False:
                self.is_valid_osc = True

        self.listening_server = receiveOscParameters(checkOscReceive)
        def oscListener():
            self.listening_server.serve_forever()

        def sendTestActionLoop():
            for _ in range(10):
                sendTestAction()
                if self.is_valid_osc is True:
                    break
                sleep(0.1)
            self.listening_server.shutdown()

        # start receive osc
        th_receive_osc_parameters = Thread(target=oscListener)
        th_receive_osc_parameters.daemon = True
        th_receive_osc_parameters.start()

        # check osc started
        th_send_osc_test_action = Thread(target=sendTestActionLoop)
        th_send_osc_test_action.daemon = True
        th_send_osc_test_action.start()

        th_receive_osc_parameters.join()
        th_send_osc_test_action.join()

        if self.is_valid_osc is False:
            fnc()

    @staticmethod
    def checkSoftwareUpdated():
        # check update
        update_flag = False
        response = requests_get(config.GITHUB_URL)
        new_version = response.json()["name"]
        if new_version != config.VERSION:
            update_flag = True
        print("software version", "now:", config.VERSION, "new:", new_version)
        return update_flag

    @staticmethod
    def updateSoftware(restart:bool=True, func=None):
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
                        if isinstance(func, Callable):
                            total_chunk += len(chunk)
                            func(total_chunk/file_size)

                with ZipFile(os_path.join(tmp_path, filename)) as zf:
                    zf.extractall(os_path.join(current_directory, tmp_directory_name))
            copyfile(os_path.join(current_directory, folder_name, "batch", batch_name), os_path.join(current_directory, batch_name))
            command = [os_path.join(current_directory, batch_name), program_name, folder_name, tmp_directory_name, str(restart)]
            Popen(command, cwd=current_directory)
        except Exception:
            webbrowser.open(config.BOOTH_URL, new=2, autoraise=True)

    @staticmethod
    def reStartSoftware():
        program_name = 'VRCT.exe'
        folder_name = '_internal'
        batch_name = 'restart.bat'
        current_directory = config.PATH_LOCAL
        copyfile(os_path.join(current_directory, folder_name, "batch", batch_name), os_path.join(current_directory, batch_name))
        command = [os_path.join(current_directory, batch_name), program_name]
        Popen(command, cwd=current_directory)

    @staticmethod
    def getListInputHost():
        return [host for host in getInputDevices().keys()]

    @staticmethod
    def getListInputDevice():
        return [device["name"] for device in getInputDevices()[config.CHOICE_MIC_HOST]]

    @staticmethod
    def getListOutputDevice():
        return [device["name"] for device in getOutputDevices()]

    def startMicTranscript(self, fnc, error_fnc=None):
        mic_device_list = getInputDevices().get(config.CHOICE_MIC_HOST, [{"name": "NoDevice"}])
        choice_mic_device = [device for device in mic_device_list if device["name"] == config.CHOICE_MIC_DEVICE]
        if len(choice_mic_device) == 0:
            try:
                error_fnc()
            except Exception:
                pass
            return

        mic_audio_queue = Queue()
        # mic_energy_queue = Queue()
        mic_device = choice_mic_device[0]
        record_timeout = config.INPUT_MIC_RECORD_TIMEOUT
        phase_timeout = config.INPUT_MIC_PHRASE_TIMEOUT
        if record_timeout > phase_timeout:
            record_timeout = phase_timeout

        self.mic_audio_recorder = SelectedMicEnergyAndAudioRecorder(
            device=mic_device,
            energy_threshold=config.INPUT_MIC_ENERGY_THRESHOLD,
            dynamic_energy_threshold=config.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD,
            record_timeout=record_timeout,
        )
        # self.mic_audio_recorder.recordIntoQueue(mic_audio_queue, mic_energy_queue)
        self.mic_audio_recorder.recordIntoQueue(mic_audio_queue, None)
        self.mic_transcriber = AudioTranscriber(
            speaker=False,
            source=self.mic_audio_recorder.source,
            phrase_timeout=phase_timeout,
            max_phrases=config.INPUT_MIC_MAX_PHRASES,
            transcription_engine=config.SELECTED_TRANSCRIPTION_ENGINE,
            root=config.PATH_LOCAL,
            whisper_weight_type=config.WHISPER_WEIGHT_TYPE,
        )
        def sendMicTranscript():
            try:
                self.mic_transcriber.transcribeAudioQueue(mic_audio_queue, config.SOURCE_LANGUAGE, config.SOURCE_COUNTRY)
                message = self.mic_transcriber.getTranscript()
                fnc(message)
            except Exception:
                pass

        def endMicTranscript():
            mic_audio_queue.queue.clear()
            # mic_energy_queue.queue.clear()
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

    def stopMicTranscript(self):
        if isinstance(self.mic_print_transcript, threadFnc):
            self.mic_print_transcript.stop()
            self.mic_print_transcript = None
        if isinstance(self.mic_audio_recorder, SelectedMicEnergyAndAudioRecorder):
            self.mic_audio_recorder.stop(wait_for_stop=False)
            self.mic_audio_recorder = None
        # if isinstance(self.mic_get_energy, threadFnc):
        #     self.mic_get_energy.stop()
        #     self.mic_get_energy = None

    def startCheckMicEnergy(self, fnc, end_fnc, error_fnc=None):
        mic_device_list = getInputDevices().get(config.CHOICE_MIC_HOST, [{"name": "NoDevice"}])
        choice_mic_device = [device for device in mic_device_list if device["name"] == config.CHOICE_MIC_DEVICE]
        if len(choice_mic_device) == 0:
            try:
                error_fnc()
            except Exception:
                pass
            return

        def sendMicEnergy():
            if mic_energy_queue.empty() is False:
                energy = mic_energy_queue.get()
                try:
                    fnc(energy)
                except Exception:
                    pass
            sleep(0.01)

        mic_energy_queue = Queue()
        mic_device = choice_mic_device[0]
        self.mic_energy_recorder = SelectedMicEnergyRecorder(mic_device)
        self.mic_energy_recorder.recordIntoQueue(mic_energy_queue)
        self.mic_energy_plot_progressbar = threadFnc(sendMicEnergy, end_fnc=end_fnc)
        self.mic_energy_plot_progressbar.daemon = True
        self.mic_energy_plot_progressbar.start()

    def stopCheckMicEnergy(self):
        if isinstance(self.mic_energy_plot_progressbar, threadFnc):
            self.mic_energy_plot_progressbar.stop()
            self.mic_energy_plot_progressbar = None
        if isinstance(self.mic_energy_recorder, SelectedMicEnergyRecorder):
            self.mic_energy_recorder.stop(wait_for_stop=False)
            self.mic_energy_recorder = None

    def startSpeakerTranscript(self, fnc, error_fnc=None):
        speaker_device_list = getOutputDevices()
        choice_speaker_device = [device for device in speaker_device_list if device["name"] == config.CHOICE_SPEAKER_DEVICE]
        if len(choice_speaker_device) == 0:
            try:
                error_fnc()
            except Exception:
                pass
            return

        speaker_audio_queue = Queue()
        # speaker_energy_queue = Queue()
        speaker_device = choice_speaker_device[0]
        record_timeout = config.INPUT_SPEAKER_RECORD_TIMEOUT
        phase_timeout = config.INPUT_SPEAKER_PHRASE_TIMEOUT
        if record_timeout > phase_timeout:
            record_timeout = phase_timeout

        self.speaker_audio_recorder = SelectedSpeakerEnergyAndAudioRecorder(
            device=speaker_device,
            energy_threshold=config.INPUT_SPEAKER_ENERGY_THRESHOLD,
            dynamic_energy_threshold=config.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD,
            record_timeout=record_timeout,
        )
        # self.speaker_audio_recorder.recordIntoQueue(speaker_audio_queue, speaker_energy_queue)
        self.speaker_audio_recorder.recordIntoQueue(speaker_audio_queue ,None)
        self.speaker_transcriber = AudioTranscriber(
            speaker=True,
            source=self.speaker_audio_recorder.source,
            phrase_timeout=phase_timeout,
            max_phrases=config.INPUT_SPEAKER_MAX_PHRASES,
            transcription_engine=config.SELECTED_TRANSCRIPTION_ENGINE,
            root=config.PATH_LOCAL,
            whisper_weight_type=config.WHISPER_WEIGHT_TYPE,
        )
        def sendSpeakerTranscript():
            try:
                self.speaker_transcriber.transcribeAudioQueue(speaker_audio_queue, config.TARGET_LANGUAGE, config.TARGET_COUNTRY)
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
            self.speaker_print_transcript = None
        if isinstance(self.speaker_audio_recorder, SelectedSpeakerEnergyAndAudioRecorder):
            self.speaker_audio_recorder.stop(wait_for_stop=False)
            self.speaker_audio_recorder = None
        # if isinstance(self.speaker_get_energy, threadFnc):
        #     self.speaker_get_energy.stop()
        #     self.speaker_get_energy = None

    def startCheckSpeakerEnergy(self, fnc, end_fnc, error_fnc=None):
        speaker_device_list = getOutputDevices()
        choice_speaker_device = [device for device in speaker_device_list if device["name"] == config.CHOICE_SPEAKER_DEVICE]
        if len(choice_speaker_device) == 0:
            try:
                error_fnc()
            except Exception:
                pass
            return

        def sendSpeakerEnergy():
            if speaker_energy_queue.empty() is False:
                energy = speaker_energy_queue.get()
                try:
                    fnc(energy)
                except Exception:
                    pass
            sleep(0.01)

        speaker_energy_queue = Queue()
        speaker_device = choice_speaker_device[0]
        self.speaker_energy_recorder = SelectedSpeakerEnergyRecorder(speaker_device)
        self.speaker_energy_recorder.recordIntoQueue(speaker_energy_queue)
        self.speaker_energy_plot_progressbar = threadFnc(sendSpeakerEnergy, end_fnc=end_fnc)
        self.speaker_energy_plot_progressbar.daemon = True
        self.speaker_energy_plot_progressbar.start()

    def stopCheckSpeakerEnergy(self):
        if isinstance(self.speaker_energy_plot_progressbar, threadFnc):
            self.speaker_energy_plot_progressbar.stop()
            self.speaker_energy_plot_progressbar = None
        if isinstance(self.speaker_energy_recorder, SelectedSpeakerEnergyRecorder):
            self.speaker_energy_recorder.stop(wait_for_stop=False)
            self.speaker_energy_recorder = None

    def notificationXSOverlay(self, message):
        xsoverlayForVRCT(content=f"{message}")

    def createOverlayImageShort(self, message, translation):
        your_language = config.TARGET_LANGUAGE
        target_language = config.SOURCE_LANGUAGE
        ui_type = config.OVERLAY_UI_TYPE
        return self.overlay_image.createOverlayImageShort(message, your_language, translation, target_language, ui_type)

    def createOverlayImageLong(self, message_type, message, translation):
        your_language = config.TARGET_LANGUAGE if message_type == "receive" else config.SOURCE_LANGUAGE
        target_language = config.SOURCE_LANGUAGE if message_type == "receive" else config.TARGET_LANGUAGE
        return self.overlay_image.create_overlay_image_long(message_type, message, your_language, translation, target_language)

    def setOverlayImage(self, img):
        if self.overlay.initFlag is True:
            self.overlay.uiMan.uiUpdate(img)

    def startOverlay(self):
        if self.overlay.initFlag is False:
            self.overlay.init()
        if self.overlay.initFlag is True:
            self.th_overlay = threadFnc(self.overlay.startOverlay)
            self.th_overlay.daemon = True
            self.th_overlay.start()

    def stopOverlay(self):
        if isinstance(self.th_overlay, threadFnc):
            self.th_overlay.stop()
            self.th_overlay = None

model = Model()