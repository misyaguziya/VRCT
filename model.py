from time import sleep
from queue import Queue
from threading import Thread, Event
from requests import get as requests_get

from flashtext import KeywordProcessor
from models.translation.translation_translator import Translator
from models.transcription.transcription_utils import getInputDevices, getOutputDevices, getDefaultInputDevice, getDefaultOutputDevice
from models.osc.osc_tools import sendTyping, sendMessage, sendTestAction, receiveOscParameters
from models.transcription.transcription_recorder import SelectedMicRecorder, SelectedSpeakerRecorder
from models.transcription.transcription_recorder import SelectedMicEnergyRecorder, SelectedSpeakeEnergyRecorder
from models.transcription.transcription_transcriber import AudioTranscriber
from models.xsoverlay.notification import xsoverlayForVRCT
from config import config

class threadFnc(Thread):
    def __init__(self, fnc, daemon=True, *args, **kwargs):
        super(threadFnc, self).__init__(daemon=daemon, *args, **kwargs)
        self.fnc = fnc
        self._stop = Event()
    def stop(self):
        self._stop.set()
    def stopped(self):
        return self._stop.isSet()
    def run(self):
        while True:
            if self.stopped():
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
        self.mic_energy_recorder = None
        self.mic_energy_plot_progressbar = None
        self.speaker_energy_get_progressbar = None
        self.speaker_energy_plot_progressbar = None
        self.translator = Translator()
        self.keyword_processor = KeywordProcessor()

    def resetTranslator(self):
        del self.translator
        self.translator = Translator()

    def resetKeywordProcessor(self):
        del self.translator
        self.keyword_processor = KeywordProcessor()

    def authenticationTranslator(self, choice_translator=None, auth_key=None):
        if choice_translator == None:
            choice_translator = config.CHOICE_TRANSLATOR
        if auth_key == None:
            auth_key = config.AUTH_KEYS[choice_translator]

        result = self.translator.authentication(choice_translator, auth_key)
        if result:
            auth_keys = config.AUTH_KEYS
            auth_keys[choice_translator] = auth_key
            config.AUTH_KEYS = auth_keys
        return result

    def getTranslatorStatus(self):
        return self.translator.translator_status[config.CHOICE_TRANSLATOR]

    def getListTranslatorName(self):
        return list(self.translator.translator_status.keys())

    def getInputTranslate(self, message):
        translation = self.translator.translate(
                        translator_name=config.CHOICE_TRANSLATOR,
                        source_language=config.SOURCE_LANGUAGE,
                        target_language=config.TARGET_LANGUAGE,
                        message=message
                )
        return translation

    def getOutputTranslate(self, message):
        translation = self.translator.translate(
                        translator_name=config.CHOICE_TRANSLATOR,
                        source_language=config.OUTPUT_SOURCE_LANG,
                        target_language=config.OUTPUT_TARGET_LANG,
                        message=message
                )
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

    @staticmethod
    def checkOSCStarted():
        def checkOscReceive(address, osc_arguments):
            if config.ENABLE_OSC is False:
                config.ENABLE_OSC = True

        # start receive osc
        th_receive_osc_parameters = Thread(target=receiveOscParameters, args=(checkOscReceive,))
        th_receive_osc_parameters.daemon = True
        th_receive_osc_parameters.start()

        # check osc started
        sendTestAction()

    @staticmethod
    def checkSoftwareUpdated():
        # check update
        response = requests_get(config.GITHUB_URL)
        tag_name = response.json()["tag_name"]
        if tag_name != config.VERSION:
            config.UPDATE_FLAG = True

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
        mic_audio_queue = Queue()
        self.mic_audio_recorder = SelectedMicRecorder(
            [device for device in getInputDevices()[config.CHOICE_MIC_HOST] if device["name"] == config.CHOICE_MIC_DEVICE][0],
            config.INPUT_MIC_ENERGY_THRESHOLD,
            config.INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD,
            config.INPUT_MIC_RECORD_TIMEOUT,
        )
        self.mic_audio_recorder.recordIntoQueue(mic_audio_queue)
        mic_transcriber = AudioTranscriber(
            speaker=False,
            source=self.mic_audio_recorder.source,
            phrase_timeout=config.INPUT_MIC_PHRASE_TIMEOUT,
            max_phrases=config.INPUT_MIC_MAX_PHRASES,
        )
        def sendMicTranscript():
            mic_transcriber.transcribeAudioQueue(mic_audio_queue, config.SOURCE_LANGUAGE, config.SOURCE_COUNTRY)
            message = mic_transcriber.getTranscript()
            fnc(message)

        self.mic_print_transcript = threadFnc(sendMicTranscript)
        self.mic_print_transcript.daemon = True
        self.mic_print_transcript.start()

    def stopMicTranscript(self):
        if isinstance(self.mic_print_transcript, threadFnc):
            self.mic_print_transcript.stop()
        if self.mic_audio_recorder.stop != None:
            self.mic_audio_recorder.stop()
            self.mic_audio_recorder.stop = None

    def startCheckMicEnergy(self, fnc):
        def sendMicEnergy():
            if mic_energy_queue.empty() is False:
                energy = mic_energy_queue.get()
                fnc(energy)
            sleep(0.01)
        mic_energy_queue = Queue()
        mic_device = [device for device in getInputDevices()[config.CHOICE_MIC_HOST] if device["name"] == config.CHOICE_MIC_DEVICE][0]
        self.mic_energy_recorder = SelectedMicEnergyRecorder(mic_device)
        self.mic_energy_recorder.recordIntoQueue(mic_energy_queue)
        self.mic_energy_plot_progressbar = threadFnc(sendMicEnergy)
        self.mic_energy_plot_progressbar.daemon = True
        self.mic_energy_plot_progressbar.start()

    def stopCheckMicEnergy(self):
        if self.mic_energy_recorder != None:
            self.mic_energy_recorder.stop()
        if self.mic_energy_plot_progressbar != None:
            self.mic_energy_plot_progressbar.stop()

    def startSpeakerTranscript(self, fnc):
        spk_audio_queue = Queue()
        spk_device = [device for device in getOutputDevices() if device["name"] == config.CHOICE_SPEAKER_DEVICE][0]
        self.spk_audio_recorder = SelectedSpeakerRecorder(
            spk_device,
            config.INPUT_SPEAKER_ENERGY_THRESHOLD,
            config.INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD,
            config.INPUT_SPEAKER_RECORD_TIMEOUT,
        )
        self.spk_audio_recorder.recordIntoQueue(spk_audio_queue)
        spk_transcriber = AudioTranscriber(
            speaker=True,
            source=self.spk_audio_recorder.source,
            phrase_timeout=config.INPUT_SPEAKER_PHRASE_TIMEOUT,
            max_phrases=config.INPUT_SPEAKER_MAX_PHRASES,
        )
        def sendSpkTranscript():
            spk_transcriber.transcribeAudioQueue(spk_audio_queue, config.TARGET_LANGUAGE, config.TARGET_COUNTRY)
            message = spk_transcriber.getTranscript()
            fnc(message)

        self.spk_print_transcript = threadFnc(sendSpkTranscript)
        self.spk_print_transcript.daemon = True
        self.spk_print_transcript.start()

    def stopSpeakerTranscript(self):
        if isinstance(self.spk_print_transcript, threadFnc):
            self.spk_print_transcript.stop()
        if self.spk_audio_recorder.stop != None:
            self.spk_audio_recorder.stop()
            self.spk_audio_recorder.stop = None

    def startCheckSpeakerEnergy(self, fnc):
        def sendSpeakerEnergy():
            if speaker_energy_queue.empty() is False:
                energy = speaker_energy_queue.get()
                fnc(energy)
            sleep(0.01)

        def getSpeakerEnergy():
            with self.speaker_energy_recorder.source as source:
                energy = self.speaker_energy_recorder.recorder.listen_energy(source)
                speaker_energy_queue.put(energy)

        speaker_device = [device for device in getOutputDevices() if device["name"] == config.CHOICE_SPEAKER_DEVICE][0]
        speaker_energy_queue = Queue()
        self.speaker_energy_recorder = SelectedSpeakeEnergyRecorder(speaker_device)
        self.speaker_energy_get_progressbar = threadFnc(getSpeakerEnergy)
        self.speaker_energy_get_progressbar.daemon = True
        self.speaker_energy_get_progressbar.start()
        self.speaker_energy_plot_progressbar = threadFnc(sendSpeakerEnergy)
        self.speaker_energy_plot_progressbar.daemon = True
        self.speaker_energy_plot_progressbar.start()

    def stopCheckSpeakerEnergy(self):
        if self.speaker_energy_get_progressbar != None:
            self.speaker_energy_get_progressbar.stop()
        if self.speaker_energy_plot_progressbar != None:
            self.speaker_energy_plot_progressbar.stop()

    def notificationXSOverlay(self, message):
        xsoverlayForVRCT(content=f"{message}")

model = Model()
