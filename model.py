import sys
from zipfile import ZipFile
from subprocess import Popen
from os import makedirs as os_makedirs
from os import path as os_path, rename as os_rename
from shutil import rmtree
from datetime import datetime
from logging import getLogger, FileHandler, Formatter, INFO
from time import sleep
from queue import Queue
from threading import Thread, Event
from requests import get as requests_get
import webbrowser

from flashtext import KeywordProcessor
from models.translation.translation_translator import Translator
from models.transcription.transcription_utils import getInputDevices, getOutputDevices, getDefaultInputDevice, getDefaultOutputDevice
from models.osc.osc_tools import sendTyping, sendMessage, sendTestAction, receiveOscParameters
from models.transcription.transcription_recorder import SelectedMicRecorder, SelectedSpeakerRecorder
from models.transcription.transcription_recorder import SelectedMicEnergyRecorder, SelectedSpeakeEnergyRecorder
from models.transcription.transcription_transcriber import AudioTranscriber
from models.xsoverlay.notification import xsoverlayForVRCT
from models.translation.translation_languages import translatorEngine, translation_lang
from models.transcription.transcription_languages import transcription_lang
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
    # Languages available for both transcription and translation
    SUPPORTED_LANGUAGES = [
        'Afrikaans', 'Arabic', 'Basque', 'Bulgarian', 'Catalan', 'Chinese', 'Croatian',
        'Czech', 'Danish', 'Dutch', 'English', 'Filipino', 'Finnish', 'French', 'German',
        'Greek', 'Hebrew', 'Hindi', 'Hungarian', 'Indonesian', 'Italian', 'Japanese',
        'Korean', 'Lithuanian', 'Malay', 'Norwegian', 'Polish', 'Portuguese', 'Romanian',
        'Russian', 'Serbian', 'Slovak', 'Slovenian', 'Spanish', 'Swedish', 'Thai', 'Turkish',
        'Ukrainian', 'Vietnamese'
        ]
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
        self.keyword_processor = KeywordProcessor()

    def resetTranslator(self):
        del self.translator
        self.translator = Translator()

    def resetKeywordProcessor(self):
        del self.keyword_processor
        self.keyword_processor = KeywordProcessor()

    def authenticationTranslator(self, fnc, choice_translator=None, auth_key=None):
        if choice_translator == None:
            choice_translator = config.CHOICE_TRANSLATOR
        if auth_key == None:
            auth_key = config.AUTH_KEYS[choice_translator]

        result = self.translator.authentication(choice_translator, auth_key)
        if result:
            auth_keys = config.AUTH_KEYS
            auth_keys[choice_translator] = auth_key
            try:
                fnc(auth_keys)
            except:
                pass
        return result

    def startLogger(self):
        os_makedirs(os_path.join(os_path.dirname(sys.argv[0]), "logs"), exist_ok=True)
        logger = getLogger()
        logger.setLevel(INFO)
        file_name = os_path.join(os_path.dirname(sys.argv[0]), "logs", f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")
        file_handler = FileHandler(file_name, encoding="utf-8", delay=True)
        formatter = Formatter("[%(asctime)s] %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        self.logger = logger
        self.logger.disabled = False

    def stopLogger(self):
        self.logger.disabled = True
        self.logger = None

    @staticmethod
    def getListLanguageAndCountry():
        langs = []
        for lang in model.SUPPORTED_LANGUAGES:
            for country in transcription_lang[lang]:
                langs.append(f"{lang}\n({country})")
        return langs

    @staticmethod
    def getLanguageAndCountry(select):
        parts = select.split("\n")
        language = parts[0]
        country = parts[1][1:-1]
        return language, country

    @staticmethod
    def findTranslationEngine(source_lang, target_lang):
        compatible_engines = []
        for engine in translatorEngine:
            source_languages = translation_lang.get(engine, {}).get("source", {})
            target_languages = translation_lang.get(engine, {}).get("target", {})
            if source_lang in source_languages and target_lang in target_languages:
                compatible_engines.append(engine)
        engine_name = compatible_engines[0]

        if engine_name == "DeepL(web)" and config.AUTH_KEYS["DeepL(auth)"] != None:
            engine_name = "DeepL(auth)"
        return engine_name

    def getTranslatorStatus(self):
        return self.translator.translator_status[config.CHOICE_TRANSLATOR]

    def getListTranslatorName(self):
        return list(self.translator.translator_status.keys())

    def getInputTranslate(self, message):
        try:
            if config.CHOICE_TRANSLATOR == "DeepL(auth)":
                if config.TARGET_LANGUAGE == "English":
                    if config.TARGET_COUNTRY in ["United States", "Canada", "Philippines"]:
                        config.TARGET_LANGUAGE = "English American"
                    else:
                        config.TARGET_LANGUAGE = "English British"
                elif config.TARGET_LANGUAGE in ["Portuguese"]:
                    if config.TARGET_COUNTRY == "Portugal":
                        config.TARGET_LANGUAGE = "Portuguese European"
                    else:
                        config.TARGET_LANGUAGE = "Portuguese Brazilian"

            translation = self.translator.translate(
                            translator_name=config.CHOICE_TRANSLATOR,
                            source_language=config.SOURCE_LANGUAGE,
                            target_language=config.TARGET_LANGUAGE,
                            message=message
                    )
        except:
            translation = None
        return translation

    def getOutputTranslate(self, message):
        try:
            if config.CHOICE_TRANSLATOR == "DeepL(auth)":
                if config.SOURCE_LANGUAGE == "English":
                    if config.SOURCE_COUNTRY in ["United States", "Canada", "Philippines"]:
                        config.SOURCE_LANGUAGE = "English American"
                    else:
                        config.SOURCE_LANGUAGE = "English British"
                elif config.SOURCE_LANGUAGE in ["Portuguese"]:
                    if config.SOURCE_COUNTRY == "Portugal":
                        config.SOURCE_LANGUAGE = "Portuguese European"
                    else:
                        config.SOURCE_LANGUAGE = "Portuguese Brazilian"

            translation = self.translator.translate(
                            translator_name=config.CHOICE_TRANSLATOR,
                            source_language=config.TARGET_LANGUAGE,
                            target_language=config.SOURCE_LANGUAGE,
                            message=message
                    )
        except:
            translation = None
        return translation

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
    def updateSoftware(restart:bool=True):
        filename = 'download.zip'
        program_name = 'VRCT.exe'
        temporary_name = '_VRCT.exe'
        tmp_directory_name = 'tmp'
        batch_name = 'update.bat'
        current_directory = os_path.dirname(sys.argv[0])
        program_directory = os_path.dirname(__file__)

        try:
            res = requests_get(config.GITHUB_URL)
            url = res.json()['assets'][0]['browser_download_url']
            res = requests_get(url, stream=True)
            os_makedirs(os_path.join(current_directory, tmp_directory_name), exist_ok=True)
            with open(os_path.join(current_directory, tmp_directory_name, filename), 'wb') as file:
                for chunk in res.iter_content(chunk_size=1024):
                    file.write(chunk)
            with ZipFile(os_path.join(current_directory, tmp_directory_name, filename)) as zf:
                zf.extract(program_name, os_path.join(current_directory, tmp_directory_name))
            os_rename(os_path.join(current_directory, tmp_directory_name, program_name), os_path.join(current_directory, temporary_name))
            rmtree(os_path.join(current_directory, tmp_directory_name))
            command = [os_path.join(program_directory, "batch", batch_name), program_name, temporary_name, str(restart)]
            Popen(command)
        except:
            webbrowser.open(config.BOOTH_URL, new=2, autoraise=True)

    @staticmethod
    def reStartSoftware():
        program_name = 'VRCT.exe'
        batch_name = 'restart.bat'
        program_directory = os_path.dirname(__file__)
        command = [os_path.join(program_directory, "batch", batch_name), program_name]
        Popen(command)

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
    def getListOutputDevice():
        return [device["name"] for device in getOutputDevices()]

    @staticmethod
    def checkSpeakerStatus(choice=config.CHOICE_SPEAKER_DEVICE):
        speaker_device = [device for device in getOutputDevices() if device["name"] == choice][0]
        if getDefaultOutputDevice()["index"] == speaker_device["index"]:
            return True
        return False

    def startMicTranscript(self, fnc):
        if config.CHOICE_MIC_HOST == "NoHost" or config.CHOICE_MIC_DEVICE == "NoDevice":
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
            except:
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

    def startCheckMicEnergy(self, fnc, end_fnc):
        if config.CHOICE_MIC_HOST == "NoHost" or config.CHOICE_MIC_DEVICE == "NoDevice":
            return

        def sendMicEnergy():
            if mic_energy_queue.empty() is False:
                energy = mic_energy_queue.get()
                try:
                    fnc(energy)
                except:
                    pass
            # sleep(0.01)

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

    def startSpeakerTranscript(self, fnc):
        if config.CHOICE_SPEAKER_DEVICE == "NoDevice":
            return
        speaker_audio_queue = Queue()
        speaker_device = [device for device in getOutputDevices() if device["name"] == config.CHOICE_SPEAKER_DEVICE][0]

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
            except:
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

    def startCheckSpeakerEnergy(self, fnc, end_fnc):
        if config.CHOICE_SPEAKER_DEVICE == "NoDevice":
            return

        def sendSpeakerEnergy():
            if speaker_energy_queue.empty() is False:
                energy = speaker_energy_queue.get()
                try:
                    fnc(energy)
                except:
                    pass
            # sleep(0.01)

        speaker_device = [device for device in getOutputDevices() if device["name"] == config.CHOICE_SPEAKER_DEVICE][0]
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
