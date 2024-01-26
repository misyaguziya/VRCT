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

from tqdm import tqdm
from typing import Callable
from flashtext import KeywordProcessor
from models.translation.translation_translator import Translator
from models.transcription.transcription_utils import getInputDevices, getDefaultOutputDevice
from models.osc.osc_tools import sendTyping, sendMessage, sendTestAction, receiveOscParameters
from models.transcription.transcription_recorder import SelectedMicRecorder, SelectedSpeakerRecorder
from models.transcription.transcription_recorder import SelectedMicEnergyRecorder, SelectedSpeakeEnergyRecorder
from models.transcription.transcription_transcriber import AudioTranscriber
from models.xsoverlay.notification import xsoverlayForVRCT
from models.translation.translation_languages import translation_lang
from models.transcription.transcription_languages import transcription_lang
from models.translation.utils import checkCTranslate2Weight
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
        return self._stop.isSet()
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
        self.translator = Translator()
        if config.USE_TRANSLATION_FEATURE is True:
            self.translator.changeCTranslate2Model(config.PATH_LOCAL, config.WEIGHT_TYPE)
        self.keyword_processor = KeywordProcessor()

    def checkCTranslatorCTranslate2ModelWeight(self):
        return checkCTranslate2Weight(config.PATH_LOCAL, config.WEIGHT_TYPE)

    def changeTranslatorCTranslate2Model(self):
        self.translator.changeCTranslate2Model(config.PATH_LOCAL, config.WEIGHT_TYPE)

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
        tl_keys = translation_lang.keys()
        translation_langs = []
        for tl_key in tl_keys:
            for lang in translation_lang[tl_key]["source"]:
                translation_langs.append(lang)
        translation_langs = list(set(translation_langs))
        supported_langs = list(filter(lambda x: x in transcription_langs, translation_langs))

        langs = []
        for lang in supported_langs:
            for country in transcription_lang[lang]:
                langs.append(f"{lang}\n({country})")
        return sorted(langs)

    @staticmethod
    def getLanguageAndCountry(select):
        parts = select.split("\n")
        language = parts[0]
        country = parts[1][1:-1]
        return language, country

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
                pbar = tqdm(total=file_size, unit="B", unit_scale=True)
                total_chunk = 0
                with open(os_path.join(tmp_path, filename), 'wb') as file:
                    for chunk in res.iter_content(chunk_size=1024*5):
                        file.write(chunk)
                        pbar.update(len(chunk))
                        if isinstance(func, Callable):
                            total_chunk += len(chunk)
                            func(total_chunk/file_size)
                    pbar.close()

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
    def getInputDefaultDevice():
        return [device["name"] for device in getInputDevices()[config.CHOICE_MIC_HOST]][0]

    @staticmethod
    def getOutputDefaultDevice():
        return getDefaultOutputDevice()["name"]

    def startMicTranscript(self, fnc, error_fnc=None):
        if config.CHOICE_MIC_HOST == "NoHost" or config.CHOICE_MIC_DEVICE == "NoDevice":
            try:
                error_fnc()
            except Exception:
                pass
            return

        mic_audio_queue = Queue()
        device = [device for device in getInputDevices()[config.CHOICE_MIC_HOST] if device["name"] == config.CHOICE_MIC_DEVICE][0]
        record_timeout = config.INPUT_MIC_RECORD_TIMEOUT
        phase_timeout = config.INPUT_MIC_PHRASE_TIMEOUT
        if record_timeout > phase_timeout:
            record_timeout = phase_timeout

        self.mic_audio_recorder = SelectedMicRecorder(
            device=device,
            energy_threshold=config.INPUT_MIC_ENERGY_THRESHOLD,
            dynamic_energy_threshold=config.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD,
            record_timeout=record_timeout,
        )
        self.mic_audio_recorder.recordIntoQueue(mic_audio_queue)
        mic_transcriber = AudioTranscriber(
            speaker=False,
            source=self.mic_audio_recorder.source,
            phrase_timeout=phase_timeout,
            max_phrases=config.INPUT_MIC_MAX_PHRASES,
        )
        def sendMicTranscript():
            mic_transcriber.transcribeAudioQueue(mic_audio_queue, config.SOURCE_LANGUAGE, config.SOURCE_COUNTRY)
            message = mic_transcriber.getTranscript()
            try:
                fnc(message)
            except Exception:
                pass

        self.mic_print_transcript = threadFnc(sendMicTranscript)
        self.mic_print_transcript.daemon = True
        self.mic_print_transcript.start()

    def stopMicTranscript(self):
        if isinstance(self.mic_print_transcript, threadFnc):
            self.mic_print_transcript.stop()
            self.mic_print_transcript = None
        if isinstance(self.mic_audio_recorder, SelectedMicRecorder):
            self.mic_audio_recorder.stop()
            self.mic_audio_recorder = None

    def startCheckMicEnergy(self, fnc, end_fnc, error_fnc=None):
        if config.CHOICE_MIC_HOST == "NoHost" or config.CHOICE_MIC_DEVICE == "NoDevice":
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
        mic_device = [device for device in getInputDevices()[config.CHOICE_MIC_HOST] if device["name"] == config.CHOICE_MIC_DEVICE][0]
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
            self.mic_energy_recorder.stop()
            self.mic_energy_recorder = None

    def startSpeakerTranscript(self, fnc, error_fnc=None):
        speaker_device = getDefaultOutputDevice()
        if speaker_device["name"] == "NoDevice":
            try:
                error_fnc()
            except Exception:
                pass
            return

        speaker_audio_queue = Queue()
        record_timeout = config.INPUT_SPEAKER_RECORD_TIMEOUT
        phase_timeout = config.INPUT_SPEAKER_PHRASE_TIMEOUT
        if record_timeout > phase_timeout:
            record_timeout = phase_timeout

        self.speaker_audio_recorder = SelectedSpeakerRecorder(
            device=speaker_device,
            energy_threshold=config.INPUT_SPEAKER_ENERGY_THRESHOLD,
            dynamic_energy_threshold=config.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD,
            record_timeout=record_timeout,
        )
        self.speaker_audio_recorder.recordIntoQueue(speaker_audio_queue)
        speaker_transcriber = AudioTranscriber(
            speaker=True,
            source=self.speaker_audio_recorder.source,
            phrase_timeout=phase_timeout,
            max_phrases=config.INPUT_SPEAKER_MAX_PHRASES,
        )
        def sendSpeakerTranscript():
            speaker_transcriber.transcribeAudioQueue(speaker_audio_queue, config.TARGET_LANGUAGE, config.TARGET_COUNTRY)
            message = speaker_transcriber.getTranscript()
            try:
                fnc(message)
            except Exception:
                pass

        self.speaker_print_transcript = threadFnc(sendSpeakerTranscript)
        self.speaker_print_transcript.daemon = True
        self.speaker_print_transcript.start()

    def stopSpeakerTranscript(self):
        if isinstance(self.speaker_print_transcript, threadFnc):
            self.speaker_print_transcript.stop()
            self.speaker_print_transcript = None
        if isinstance(self.speaker_audio_recorder, SelectedSpeakerRecorder):
            self.speaker_audio_recorder.stop()
            self.speaker_audio_recorder = None

    def startCheckSpeakerEnergy(self, fnc, end_fnc, error_fnc=None):
        speaker_device = getDefaultOutputDevice()
        if speaker_device["name"] == "NoDevice":
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
        self.speaker_energy_recorder = SelectedSpeakeEnergyRecorder(speaker_device)
        self.speaker_energy_recorder.recordIntoQueue(speaker_energy_queue)
        self.speaker_energy_plot_progressbar = threadFnc(sendSpeakerEnergy, end_fnc=end_fnc)
        self.speaker_energy_plot_progressbar.daemon = True
        self.speaker_energy_plot_progressbar.start()

    def stopCheckSpeakerEnergy(self):
        if isinstance(self.speaker_energy_plot_progressbar, threadFnc):
            self.speaker_energy_plot_progressbar.stop()
            self.speaker_energy_plot_progressbar = None
        if isinstance(self.speaker_energy_recorder, SelectedSpeakeEnergyRecorder):
            self.speaker_energy_recorder.stop()
            self.speaker_energy_recorder = None

    def notificationXSOverlay(self, message):
        xsoverlayForVRCT(content=f"{message}")

model = Model()