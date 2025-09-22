import sys
import unittest

# 初期化のため、config.jsonの削除
import os
if os.path.exists("config.json"):
    os.remove("config.json")

from mainloop import main_instance

class TestMainloop(unittest.TestCase):
    def setUp(self):
        self.main = main_instance
        self.main.startReceiver()
        self.main.startHandler()

        def stop_main():
            pass
        self.main.controller.setWatchdogCallback(stop_main)
        self.main.controller.init()

        # mappingのすべてのstatusをTrueにする
        for key in self.main.mapping.keys():
            self.main.mapping[key]["status"] = True

    def test_endpoints(self):
        print("単体動作の確認")
        # エンドポイントとテストデータの定義
        endpoints = {
            # Main Window
            "/set/enable/translation": [{"data": None, "status": 200, "result": True}],
            "/set/disable/translation": [{"data": None, "status": 200, "result": False}],
            "/set/enable/transcription_send": [{"data": None, "status": 200, "result": True}],
            "/set/disable/transcription_send": [{"data": None, "status": 200, "result": False}],
            "/set/enable/transcription_receive": [{"data": None, "status": 200, "result": True}],
            "/set/disable/transcription_receive": [{"data": None, "status": 200, "result": False}],
            "/set/enable/foreground": [{"data": None, "status": 200, "result": True}],
            "/set/disable/foreground": [{"data": None, "status": 200, "result": False}],
            "/get/data/selected_tab_no": [{"data": None, "status": 200, "result": "1"}],
            "/set/data/selected_tab_no": [
                {"data": "1", "status": 200, "result": "1"},
                {"data": "2", "status": 200, "result": "2"},
                {"data": "3", "status": 200, "result": "3"},
            ],
            "/get/data/main_window_sidebar_compact_mode": [{"data": None, "status": 200, "result": False}],
            "/set/enable/main_window_sidebar_compact_mode": [{"data": None, "status": 200, "result": True}],
            "/set/disable/main_window_sidebar_compact_mode": [{"data": None, "status": 200, "result": False}],
            "/get/data/translation_engines": [{"data": None, "status": 200, "result": ['DeepL', 'Google', 'Bing', 'Papago', 'CTranslate2']}],
            "/get/data/selectable_language_list": [
                {
                    "data": None,
                    "status": 200,
                    "result":
                        [
                            {'language': 'Afrikaans', 'country': 'South Africa'},
                            {'language': 'Albanian', 'country': 'Albania'},
                            {'language': 'Amharic', 'country': 'Ethiopia'},
                            {'language': 'Arabic', 'country': 'Algeria'},
                            {'language': 'Arabic', 'country': 'Bahrain'},
                            {'language': 'Arabic', 'country': 'Egypt'},
                            {'language': 'Arabic', 'country': 'Israel'},
                            {'language': 'Arabic', 'country': 'Iraq'},
                            {'language': 'Arabic', 'country': 'Jordan'},
                            {'language': 'Arabic', 'country': 'Kuwait'},
                            {'language': 'Arabic', 'country': 'Lebanon'},
                            {'language': 'Arabic', 'country': 'Mauritania'},
                            {'language': 'Arabic', 'country': 'Morocco'},
                            {'language': 'Arabic', 'country': 'Oman'},
                            {'language': 'Arabic', 'country': 'Qatar'},
                            {'language': 'Arabic', 'country': 'Saudi Arabia'},
                            {'language': 'Arabic', 'country': 'Palestine'},
                            {'language': 'Arabic', 'country': 'Syria'},
                            {'language': 'Arabic', 'country': 'Tunisia'},
                            {'language': 'Arabic', 'country': 'United Arab Emirates'},
                            {'language': 'Arabic', 'country': 'Yemen'},
                            {'language': 'Armenian', 'country': 'Armenia'},
                            {'language': 'Azerbaijani', 'country': 'Azerbaijan'},
                            {'language': 'Basque', 'country': 'Spain'},
                            {'language': 'Bengali', 'country': 'Bangladesh'},
                            {'language': 'Bengali', 'country': 'India'},
                            {'language': 'Bosnian', 'country': 'Bosnia and Herzegovina'},
                            {'language': 'Bulgarian', 'country': 'Bulgaria'},
                            {'language': 'Catalan', 'country': 'Spain'},
                            {'language': 'Chinese Simplified', 'country': 'China'},
                            {'language': 'Chinese Simplified', 'country': 'Hong Kong'},
                            {'language': 'Chinese Traditional', 'country': 'Taiwan'},
                            {'language': 'Chinese Traditional', 'country': 'Hong Kong'},
                            {'language': 'Croatian', 'country': 'Croatia'},
                            {'language': 'Czech', 'country': 'Czech Republic'},
                            {'language': 'Danish', 'country': 'Denmark'},
                            {'language': 'Dutch', 'country': 'Belgium'},
                            {'language': 'Dutch', 'country': 'Netherlands'},
                            {'language': 'English', 'country': 'Australia'},
                            {'language': 'English', 'country': 'Canada'},
                            {'language': 'English', 'country': 'Ghana'},
                            {'language': 'English', 'country': 'Hong Kong'},
                            {'language': 'English', 'country': 'India'},
                            {'language': 'English', 'country': 'Ireland'},
                            {'language': 'English', 'country': 'Kenya'},
                            {'language': 'English', 'country': 'New Zealand'},
                            {'language': 'English', 'country': 'Nigeria'},
                            {'language': 'English', 'country': 'Philippines'},
                            {'language': 'English', 'country': 'Singapore'},
                            {'language': 'English', 'country': 'South Africa'},
                            {'language': 'English', 'country': 'Tanzania'},
                            {'language': 'English', 'country': 'United Kingdom'},
                            {'language': 'English', 'country': 'United States'},
                            {'language': 'Estonian', 'country': 'Estonia'},
                            {'language': 'Filipino', 'country': 'Philippines'},
                            {'language': 'Finnish', 'country': 'Finland'},
                            {'language': 'French', 'country': 'Belgium'},
                            {'language': 'French', 'country': 'Canada'},
                            {'language': 'French', 'country': 'France'},
                            {'language': 'French', 'country': 'Switzerland'},
                            {'language': 'Galician', 'country': 'Spain'},
                            {'language': 'Georgian', 'country': 'Georgia'},
                            {'language': 'German', 'country': 'Austria'},
                            {'language': 'German', 'country': 'Germany'},
                            {'language': 'German', 'country': 'Switzerland'},
                            {'language': 'Greek', 'country': 'Greece'},
                            {'language': 'Gujarati', 'country': 'India'},
                            {'language': 'Hebrew', 'country': 'Israel'},
                            {'language': 'Hindi', 'country': 'India'},
                            {'language': 'Hungarian', 'country': 'Hungary'},
                            {'language': 'Icelandic', 'country': 'Iceland'},
                            {'language': 'Indonesian', 'country': 'Indonesia'},
                            {'language': 'Italian', 'country': 'Italy'},
                            {'language': 'Italian', 'country': 'Switzerland'},
                            {'language': 'Japanese', 'country': 'Japan'},
                            {'language': 'Kannada', 'country': 'India'},
                            {'language': 'Kazakh', 'country': 'Kazakhstan'},
                            {'language': 'Khmer', 'country': 'Cambodia'},
                            {'language': 'Korean', 'country': 'South Korea'},
                            {'language': 'Lao', 'country': 'Laos'},
                            {'language': 'Latvian', 'country': 'Latvia'},
                            {'language': 'Lithuanian', 'country': 'Lithuania'},
                            {'language': 'Macedonian', 'country': 'North Macedonia'},
                            {'language': 'Malay', 'country': 'Malaysia'},
                            {'language': 'Malayalam', 'country': 'India'},
                            {'language': 'Mongolian', 'country': 'Mongolia'},
                            {'language': 'Nepali', 'country': 'Nepal'},
                            {'language': 'Norwegian', 'country': 'Norway'},
                            {'language': 'Persian', 'country': 'Iran'},
                            {'language': 'Polish', 'country': 'Poland'},
                            {'language': 'Portuguese', 'country': 'Brazil'},
                            {'language': 'Portuguese', 'country': 'Portugal'},
                            {'language': 'Romanian', 'country': 'Romania'},
                            {'language': 'Russian', 'country': 'Russia'},
                            {'language': 'Serbian', 'country': 'Serbia'},
                            {'language': 'Sinhala', 'country': 'Sri Lanka'},
                            {'language': 'Slovak', 'country': 'Slovakia'},
                            {'language': 'Slovenian', 'country': 'Slovenia'},
                            {'language': 'Spanish', 'country': 'Argentina'},
                            {'language': 'Spanish', 'country': 'Bolivia'},
                            {'language': 'Spanish', 'country': 'Chile'},
                            {'language': 'Spanish', 'country': 'Colombia'},
                            {'language': 'Spanish', 'country': 'Costa Rica'},
                            {'language': 'Spanish', 'country': 'Dominican Republic'},
                            {'language': 'Spanish', 'country': 'Ecuador'},
                            {'language': 'Spanish', 'country': 'El Salvador'},
                            {'language': 'Spanish', 'country': 'Guatemala'},
                            {'language': 'Spanish', 'country': 'Honduras'},
                            {'language': 'Spanish', 'country': 'Mexico'},
                            {'language': 'Spanish', 'country': 'Nicaragua'},
                            {'language': 'Spanish', 'country': 'Panama'},
                            {'language': 'Spanish', 'country': 'Paraguay'},
                            {'language': 'Spanish', 'country': 'Peru'},
                            {'language': 'Spanish', 'country': 'Puerto Rico'},
                            {'language': 'Spanish', 'country': 'Spain'},
                            {'language': 'Spanish', 'country': 'United States'},
                            {'language': 'Spanish', 'country': 'Uruguay'},
                            {'language': 'Spanish', 'country': 'Venezuela'},
                            {'language': 'Sundanese', 'country': 'Indonesia'},
                            {'language': 'Swahili', 'country': 'Kenya'},
                            {'language': 'Swahili', 'country': 'Tanzania'},
                            {'language': 'Swedish', 'country': 'Sweden'},
                            {'language': 'Tamil', 'country': 'India'},
                            {'language': 'Tamil', 'country': 'malaysia'},
                            {'language': 'Tamil', 'country': 'Singapore'},
                            {'language': 'Tamil', 'country': 'Sri Lanka'},
                            {'language': 'Telugu', 'country': 'India'},
                            {'language': 'Thai', 'country': 'Thailand'},
                            {'language': 'Turkish', 'country': 'Turkey'},
                            {'language': 'Ukrainian', 'country': 'Ukraine'},
                            {'language': 'Urdu', 'country': 'India'},
                            {'language': 'Urdu', 'country': 'Pakistan'},
                            {'language': 'Uzbek', 'country': 'Uzbekistan'},
                            {'language': 'Vietnamese', 'country': 'Vietnam'}
                        ]}],
            "/get/data/selected_translation_engines": [{"data": None, "status": 200, "result": {'1': 'CTranslate2', '2': 'CTranslate2', '3': 'CTranslate2'}}],
            "/set/data/selected_translation_engines": [
                {
                    "data": {'1': 'DeepL', '2': 'Google', '3': 'Papago'},
                    "status": 200,
                    "result": {'1': 'DeepL', '2': 'Google', '3': 'Papago'}
                },
            ],
            "/get/data/selected_your_languages": [
                {
                    "data": None,
                    "status": 200,
                    "result": {
                        '1': {
                            '1': {
                                'language': 'Japanese',
                                'country': 'Japan',
                                'enable': True
                            }
                        },
                        '2': {
                            '1': {
                                'language': 'Japanese',
                                'country': 'Japan',
                                'enable': True
                            }
                        },
                        '3': {
                            '1': {
                                'language': 'Japanese',
                                'country': 'Japan',
                                'enable': True
                            }
                        }
                    }
                }
            ],
            "/set/data/selected_your_languages": [
                {
                    "data": {
                        '1': {
                            '1': {
                                'language': 'Japanese',
                                'country': 'Japan',
                                'enable': True
                            },
                        },
                        '2': {
                            '1': {
                                'language': 'English',
                                'country': 'United States',
                                'enable': True
                            },
                        },
                        '3': {
                            '1': {
                                'language': 'French',
                                'country': 'France',
                                'enable': True
                            }
                        }
                    },
                    "status": 200,
                    "result": {
                        '1': {
                            '1': {
                                'language': 'Japanese',
                                'country': 'Japan',
                                'enable': True
                            },
                        },
                        '2': {
                            '1': {
                                'language': 'English',
                                'country': 'United States',
                                'enable': True
                            },
                        },
                        '3': {
                            '1': {
                                'language': 'French',
                                'country': 'France',
                                'enable': True
                            }
                        }
                    }
                }
            ],
            "/get/data/selected_target_languages": [
                {
                    "data": None,
                    "status": 200,
                    "result": {
                        "1": {
                            "1": {
                                "language": "English",
                                "country": "United States",
                                "enable": True
                            },
                            "2": {
                                "language": "English",
                                "country": "United States",
                                "enable": False
                            },
                            "3": {
                                "language": "English",
                                "country": "United States",
                                "enable": False
                            }
                        },
                        "2": {
                            "1": {
                                "language": "English",
                                "country": "United States",
                                "enable": True
                            },
                            "2": {
                                "language": "English",
                                "country": "United States",
                                "enable": False
                            },
                            "3": {
                                "language": "English",
                                "country": "United States",
                                "enable": False
                            }
                        },
                        "3": {
                            "1": {
                                "language": "English",
                                "country": "United States",
                                "enable": True
                            },
                            "2": {
                                "language": "English",
                                "country": "United States",
                                "enable": False
                            },
                            "3": {
                                "language": "English",
                                "country": "United States",
                                "enable": False
                            }
                        }
                    },
                }
            ],
            "/set/data/selected_target_languages": [
                {
                    "data": {
                        "1": {
                            "1": {
                                "language": "Japanese",
                                "country": "Japan",
                                "enable": True
                            },
                            "2": {
                                "language": "English",
                                "country": "United States",
                                "enable": True
                            },
                            "3": {
                                "language": "French",
                                "country": "France",
                                "enable": True
                            }
                        },
                        "2": {
                            "1": {
                                "language": "Japanese",
                                "country": "Japan",
                                "enable": True
                            },
                            "2": {
                                "language": "English",
                                "country": "United States",
                                "enable": True
                            },
                            "3": {
                                "language": "French",
                                "country": "France",
                                "enable": True
                            }
                        },
                        "3": {
                            "1": {
                                "language": "Japanese",
                                "country": "Japan",
                                "enable": True
                            },
                            "2": {
                                "language": "English",
                                "country": "United States",
                                "enable": True
                            },
                            "3": {
                                "language": "French",
                                "country": "France",
                                "enable": True
                            }
                        }
                    },
                    "status": 200,
                    "result": {
                        "1": {
                            "1": {
                                "language": "Japanese",
                                "country": "Japan",
                                "enable": True
                            },
                            "2": {
                                "language": "English",
                                "country": "United States",
                                "enable": True
                            },
                            "3": {
                                "language": "French",
                                "country": "France",
                                "enable": True
                            }
                        },
                        "2": {
                            "1": {
                                "language": "Japanese",
                                "country": "Japan",
                                "enable": True
                            },
                            "2": {
                                "language": "English",
                                "country": "United States",
                                "enable": True
                            },
                            "3": {
                                "language": "French",
                                "country": "France",
                                "enable": True
                            }
                        },
                        "3": {
                            "1": {
                                "language": "Japanese",
                                "country": "Japan",
                                "enable": True
                            },
                            "2": {
                                "language": "English",
                                "country": "United States",
                                "enable": True
                            },
                            "3": {
                                "language": "French",
                                "country": "France",
                                "enable": True
                            }
                        }
                    },
                }
            ],
            "/get/data/transcription_engines": [{"data": None, "status": 200, "result": ['Google', 'Whisper']}],
            "/get/data/selected_transcription_engine": [{"data": None, "status": 200, "result": "Google"}],
            "/set/data/selected_transcription_engine": [
                {"data": "Google", "status": 200, "result": "Google"},
                {"data": "Whisper", "status": 200, "result": "Whisper"},
            ],
            "/run/send_message_box": [
                {
                    "data": {"id":"123456", "message":"test"},
                    "status": 200,
                    "result": {
                        'id': '123456',
                        'original': {
                            'message': 'test',
                            'transliteration': []
                            },
                        'translations': []
                    }
                }
            ],
            "/run/typing_message_box": [{"data": None, "status": 200, "result": True}],
            "/run/stop_typing_message_box": [{"data": None, "status": 200, "result": True}],
            "/run/send_text_overlay": [{"data": "test_overlay", "status": 200, "result": "test_overlay"}],
            "/run/swap_your_language_and_target_language": [{"data": None, "status": 200, "result": True}],
            # !!!Cant be tested here!!!
            # "/run/update_software": [{"data": None, "status": 200, "result": True}],
            # "/run/update_cuda_software": [{"data": None, "status": 200, "result": True}],

            # Config Window
            # Appearance
            "/get/data/version": [{"data": None, "status": 200, "result": "3.2.2"}],
            "/get/data/transparency": [{"data": None, "status": 200, "result": 100}],
            "/set/data/transparency": [
                {"data": 100, "status": 200, "result": 100},
                {"data": 80, "status": 200, "result": 80},
                {"data": 50, "status": 200, "result": 50},
                {"data": 20, "status": 200, "result": 20},
                {"data": 0, "status": 200, "result": 0},
            ],
            "/get/data/ui_scaling": [{"data": None, "status": 200, "result": 100}],
            "/set/data/ui_scaling": [
                {"data": 100, "status": 200, "result": 100},
                {"data": 80, "status": 200, "result": 80},
                {"data": 50, "status": 200, "result": 50},
                {"data": 20, "status": 200, "result": 20},
                {"data": 10, "status": 200, "result": 10},
            ],
            "/get/data/textbox_ui_scaling": [{"data": None, "status": 200, "result": 100}],
            "/set/data/textbox_ui_scaling": [
                {"data": 100, "status": 200, "result": 100},
                {"data": 80, "status": 200, "result": 80},
                {"data": 50, "status": 200, "result": 50},
                {"data": 20, "status": 200, "result": 20},
                {"data": 10, "status": 200, "result": 10},
            ],
            "/get/data/message_box_ratio": [{"data": None, "status": 200, "result": 10}],
            "/set/data/message_box_ratio": [
                {"data": 10, "status": 200, "result": 10},
                {"data": 9, "status": 200, "result": 5.5},
                {"data": 1, "status": 200, "result": 1},
            ],
            "/get/data/send_message_button_type": [{"data": None, "status": 200, "result": "show"}],
            "/set/data/send_message_button_type": [
                {"data": "show", "status": 200, "result": "show"},
                {"data": "hide", "status": 200, "result": "hide"},
                {"data": "show_and_disable_enter_key", "status": 200, "result": "show_and_disable_enter_key"},
            ],
            "/get/data/show_resend_button": [{"data": None, "status": 200, "result": False}],
            "/set/enable/show_resend_button": [{"data": None, "status": 200, "result": True}],
            "/set/disable/show_resend_button": [{"data": None, "status": 200, "result": False}],
            "/get/data/font_family": [{"data": None, "status": 200, "result": "Yu Gothic UI"}],
            "/set/data/font_family": [{"data": "Yu Gothic UI", "status": 200, "result": "Yu Gothic UI"}],
            "/get/data/ui_language": [{"data": None, "status": 200, "result": "en"}],
            "/set/data/ui_language": [
                {"data": "en", "status": 200, "result": "en"},
                {"data": "ja", "status": 200, "result": "ja"},
                {"data": "ko", "status": 200, "result": "ko"},
                {"data": "zh-Hant", "status": 200, "result": "zh-Hant"},
                {"data": "zh-Hans", "status": 200, "result": "zh-Hans"},
            ],
            "/get/data/main_window_geometry": [{"data": None, "status": 200, "result": {"x_pos": 0, "y_pos": 0, "width": 870, "height": 654}}],
            "/set/data/main_window_geometry": [
                {
                    "data": {"x_pos": 0, "y_pos": 0, "width": 870, "height": 654},
                    "status": 200,
                    "result": {"x_pos": 0, "y_pos": 0, "width": 870, "height": 654}
                },
            ],
            # Compute device
            "/get/data/compute_mode": [{"data": None, "status": 200, "result": "cpu"}],
            "/get/data/translation_compute_device_list": [{"data": None, "status": 200, "result": [{"device": "cpu", "device_index": 0, "device_name": "cpu"}]}],
            "/get/data/selected_translation_compute_device": [{"data": None, "status": 200, "result": {"device": "cpu", "device_index": 0, "device_name": "cpu"}}],
            "/set/data/selected_translation_compute_device": [
                {
                    "data": {"device": "cpu", "device_index": 0, "device_name": "cpu"},
                    "status": 200,
                    "result": {"device": "cpu", "device_index": 0, "device_name": "cpu"}
                }
            ],
            "/get/data/transcription_compute_device_list": [
                {
                    "data": None,
                    "status": 200,
                    "result": [{"device": "cpu", "device_index": 0, "device_name": "cpu"}]
                }
            ],
            "/get/data/selected_transcription_compute_device": [
                {
                    "data": None,
                    "status": 200,
                    "result": {"device": "cpu", "device_index": 0, "device_name": "cpu"}
                }
            ],
            "/set/data/selected_transcription_compute_device": [
                {
                    "data": {"device": "cpu", "device_index": 0, "device_name": "cpu"},
                    "status": 200,
                    "result": {"device": "cpu", "device_index": 0, "device_name": "cpu"}
                },
            ],
            # Translation
            "/get/data/selectable_ctranslate2_weight_type_dict": [
                {
                    "data": None,
                    "status": 200,
                    "result": {"small": True, "large": False}
                },
            ],
            "/get/data/ctranslate2_weight_type": [
                {
                    "data": "small",
                    "status": 200,
                    "result": "small"
                },
            ],
            # "/set/data/ctranslate2_weight_type": {"data": None},
            # "/run/download_ctranslate2_weight": {"data": None},
            # "/get/data/deepl_auth_key": {"data": None},
            # "/set/data/deepl_auth_key": {"data": None},
            # "/delete/data/deepl_auth_key": {"data": None},
            # "/get/data/convert_message_to_romaji": {"data": None},
            # "/set/enable/convert_message_to_romaji": {"data": None},
            # "/set/disable/convert_message_to_romaji": {"data": None},
            # "/get/data/convert_message_to_hiragana": {"data": None},
            # "/set/enable/convert_message_to_hiragana": {"data": None},
            # "/set/disable/convert_message_to_hiragana": {"data": None},
            # # Transcription
            # "/get/data/mic_host_list": {"data": None},
            # "/get/data/mic_device_list": {"data": None},
            # "/get/data/speaker_device_list": {"data": None},
            # "/get/data/auto_mic_select": {"data": None},
            # "/set/enable/auto_mic_select": {"data": None},
            # "/set/disable/auto_mic_select": {"data": None},
            # "/get/data/selected_mic_host": {"data": None},
            # "/set/data/selected_mic_host": {"data": None},
            # "/get/data/selected_mic_device": {"data": None},
            # "/set/data/selected_mic_device": {"data": None},
            # "/get/data/mic_threshold": {"data": None},
            # "/set/data/mic_threshold": {"data": None},
            # "/get/data/mic_automatic_threshold": {"data": None},
            # "/set/enable/mic_automatic_threshold": {"data": None},
            # "/set/disable/mic_automatic_threshold": {"data": None},
            # "/get/data/mic_record_timeout": {"data": None},
            # "/set/data/mic_record_timeout": {"data": None},
            # "/get/data/mic_phrase_timeout": {"data": None},
            # "/set/data/mic_phrase_timeout": {"data": None},
            # "/get/data/mic_max_phrases": {"data": None},
            # "/set/data/mic_max_phrases": {"data": None},
            # "/get/data/hotkeys": {"data": None},
            # "/set/data/hotkeys": {"data": None},
            # "/get/data/plugins_status": {"data": None},
            # "/set/data/plugins_status": {"data": None},
            # "/get/data/mic_avg_logprob": {"data": None},
            # "/set/data/mic_avg_logprob": {"data": None},
            # "/get/data/mic_no_speech_prob": {"data": None},
            # "/set/data/mic_no_speech_prob": {"data": None},
            # "/set/enable/check_mic_threshold": {"data": None},
            # "/set/disable/check_mic_threshold": {"data": None},
            # "/get/data/mic_word_filter": {"data": None},
            # "/set/data/mic_word_filter": {"data": None},
            # "/get/data/auto_speaker_select": {"data": None},
            # "/set/enable/auto_speaker_select": {"data": None},
            # "/set/disable/auto_speaker_select": {"data": None},
            # "/get/data/selected_speaker_device": {"data": None},
            # "/set/data/selected_speaker_device": {"data": None},
            # "/get/data/speaker_threshold": {"data": None},
            # "/set/data/speaker_threshold": {"data": None},
            # "/get/data/speaker_automatic_threshold": {"data": None},
            # "/set/enable/speaker_automatic_threshold": {"data": None},
            # "/set/disable/speaker_automatic_threshold": {"data": None},
            # "/get/data/speaker_record_timeout": {"data": None},
            # "/set/data/speaker_record_timeout": {"data": None},
            # "/get/data/speaker_phrase_timeout": {"data": None},
            # "/set/data/speaker_phrase_timeout": {"data": None},
            # "/get/data/speaker_max_phrases": {"data": None},
            # "/set/data/speaker_max_phrases": {"data": None},
            # "/get/data/speaker_avg_logprob": {"data": None},
            # "/set/data/speaker_avg_logprob": {"data": None},
            # "/get/data/speaker_no_speech_prob": {"data": None},
            # "/set/data/speaker_no_speech_prob": {"data": None},
            # "/set/enable/check_speaker_threshold": {"data": None},
            # "/set/disable/check_speaker_threshold": {"data": None},
            # "/get/data/selectable_whisper_weight_type_dict": {"data": None},
            # "/get/data/whisper_weight_type": {"data": None},
            # "/set/data/whisper_weight_type": {"data": None},
            # "/run/download_whisper_weight": {"data": None},
            # # VR
            # "/get/data/overlay_small_log": {"data": None},
            # "/set/enable/overlay_small_log": {"data": None},
            # "/set/disable/overlay_small_log": {"data": None},
            # "/get/data/overlay_small_log_settings": {"data": None},
            # "/set/data/overlay_small_log_settings": {"data": None},
            # "/get/data/overlay_large_log": {"data": None},
            # "/set/enable/overlay_large_log": {"data": None},
            # "/set/disable/overlay_large_log": {"data": None},
            # "/get/data/overlay_large_log_settings": {"data": None},
            # "/set/data/overlay_large_log_settings": {"data": None},
            # "/get/data/overlay_show_only_translated_messages": {"data": None},
            # "/set/enable/overlay_show_only_translated_messages": {"data": None},
            # "/set/disable/overlay_show_only_translated_messages": {"data": None},
            # # Others
            # "/get/data/send_message_format_parts": {"data": None},
            # "/set/data/send_message_format_parts": {"data": None},
            # "/get/data/received_message_format_parts": {"data": None},
            # "/set/data/received_message_format_parts": {"data": None},
            # "/get/data/auto_clear_message_box": {"data": None},
            # "/set/enable/auto_clear_message_box": {"data": None},
            # "/set/disable/auto_clear_message_box": {"data": None},
            # "/get/data/send_only_translated_messages": {"data": None},
            # "/set/enable/send_only_translated_messages": {"data": None},
            # "/set/disable/send_only_translated_messages": {"data": None},
            # "/get/data/logger_feature": {"data": None},
            # "/set/enable/logger_feature": {"data": None},
            # "/set/disable/logger_feature": {"data": None},
            # "/run/open_filepath_logs": {"data": None},
            # "/get/data/vrc_mic_mute_sync": {"data": None},
            # "/set/enable/vrc_mic_mute_sync": {"data": None},
            # "/set/disable/vrc_mic_mute_sync": {"data": None},
            # "/get/data/send_message_to_vrc": {"data": None},
            # "/set/enable/send_message_to_vrc": {"data": None},
            # "/set/disable/send_message_to_vrc": {"data": None},
            # "/get/data/send_received_message_to_vrc": {"data": None},
            # "/set/enable/send_received_message_to_vrc": {"data": None},
            # "/set/disable/send_received_message_to_vrc": {"data": None},
            # # WebSocket Settings
            # "/get/data/websocket_host": {"data": None},
            # "/set/data/websocket_host": {"data": None},
            # "/get/data/websocket_port": {"data": None},
            # "/set/data/websocket_port": {"data": None},
            # "/get/data/websocket_server": {"data": None},
            # "/set/enable/websocket_server": {"data": None},
            # "/set/disable/websocket_server": {"data": None},
            # # Advanced Settings
            # "/get/data/osc_ip_address": {"data": None},
            # "/set/data/osc_ip_address": {"data": None},
            # "/get/data/osc_port": {"data": None},
            # "/set/data/osc_port": {"data": None},
            # "/get/data/notification_vrc_sfx": {"data": None},
            # "/set/enable/notification_vrc_sfx": {"data": None},
            # "/set/disable/notification_vrc_sfx": {"data": None},
            # "/run/open_filepath_config_file": {"data": None},
            # "/run/feed_watchdog": {"data": None},
        }

        for endpoint, value in endpoints.items():
            with self.subTest(endpoint=endpoint):
                for item in value:
                    input_data = item["data"]
                    expected_status = item["status"]
                    expected_result = item["result"]
                    result, status = self.main.handleRequest(endpoint, input_data)
                    print(f"Endpoint: {endpoint}, Status: {status}, Result: {result}")
                    self.assertEqual(status, expected_status)
                    self.assertEqual(result, expected_result)

    def tearDown(self):
        self.main.stop()

if __name__ == "__main__":
    unittest.main()