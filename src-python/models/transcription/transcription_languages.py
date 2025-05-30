"""Provides a mapping of languages and countries to their respective codes for various transcription engines (Google, Whisper)."""
from typing import Dict

transcription_lang: Dict[str, Dict[str, Dict[str, str]]] = {
    "Afrikaans": {
        "South Africa": {
            "Google": "af-ZA",
            "Whisper": "af",
        },
    },
    "Albanian": {
        "Albania": {
            "Google": "sq-AL",
            "Whisper": "sq",
        },
    },
    "Amharic": {
        "Ethiopia": {
            "Google": "am-ET",
            "Whisper": "am",
        },
    },
    "Arabic": {
        "Algeria": {"Google": "ar-DZ", "Whisper": "ar"},
        "Bahrain": {"Google": "ar-BH", "Whisper": "ar"},
        "Egypt": {"Google": "ar-EG", "Whisper": "ar"},
        "Israel": {"Google": "ar-IL", "Whisper": "ar"},
        "Iraq": {"Google": "ar-IQ", "Whisper": "ar"},
        "Jordan": {"Google": "ar-JO", "Whisper": "ar"},
        "Kuwait": {"Google": "ar-KW", "Whisper": "ar"},
        "Lebanon": {"Google": "ar-LB", "Whisper": "ar"},
        "Mauritania": {"Google": "ar-MR", "Whisper": "ar"},
        "Morocco": {"Google": "ar-MA", "Whisper": "ar"},
        "Oman": {"Google": "ar-OM", "Whisper": "ar"},
        "Qatar": {"Google": "ar-QA", "Whisper": "ar"},
        "Saudi Arabia": {"Google": "ar-SA", "Whisper": "ar"},
        "Palestine": {"Google": "ar-PS", "Whisper": "ar"},
        "Syria": {"Google": "ar-SY", "Whisper": "ar"},
        "Tunisia": {"Google": "ar-TN", "Whisper": "ar"},
        "United Arab Emirates": {"Google": "ar-AE", "Whisper": "ar"},
        "Yemen": {"Google": "ar-YE", "Whisper": "ar"},
    },
    "Armenian": {
        "Armenia": {
            "Google": "hy-AM",
            "Whisper": "hy",
        },
    },
    "Azerbaijani": {
        "Azerbaijan": {
            "Google": "az-AZ",
            "Whisper": "az",
        },
    },
    "Basque": {
        "Spain": {
            "Google": "eu-ES",
            "Whisper": "eu",
        },
    },
    "Bengali": {
        "Bangladesh": {
            "Google": "bn-BD",
            "Whisper": "bn",
        },
        "India": {
            "Google": "bn-IN",
            "Whisper": "bn",
        },
    },
    "Bosnian": {
        "Bosnia and Herzegovina": {
            "Google": "bs-BA",
            "Whisper": "bs",
        },
    },
    "Bulgarian": {
        "Bulgaria": {
            "Google": "bg-BG",
            "Whisper": "bg",
        },
    },
    "Burmese": {
        "Myanmar": {
            "Google": "my-MM",
            "Whisper": "my",
        },
    },
    "Catalan": {
        "Spain": {
            "Google": "ca-ES",
            "Whisper": "ca",
        },
    },
    "Chinese Simplified": {
        "China": {
            "Google": "cmn-Hans-CN",
            "Whisper": "zh",
        },
        "Hong Kong": {
            "Google": "cmn-Hans-HK",
            "Whisper": "zh",
        },
    },
    "Chinese Traditional": {
        "Taiwan": {
            "Google": "cmn-Hant-TW",
            "Whisper": "zh",
        },
        "Hong Kong": { # Cantonese (Yue) in Hong Kong uses Traditional characters
            "Google": "yue-Hant-HK",
            "Whisper": "yue", # Whisper has a specific model for Cantonese
        },
    },
    "Croatian": {
        "Croatia": {
            "Google": "hr-HR",
            "Whisper": "hr",
        },
    },
    "Czech": {
        "Czech Republic": {
            "Google": "cs-CZ",
            "Whisper": "cs",
        },
    },
    "Danish": {
        "Denmark": {
            "Google": "da-DK",
            "Whisper": "da",
        },
    },
    "Dutch": {
        "Belgium": {
            "Google": "nl-BE",
            "Whisper": "nl",
        },
        "Netherlands": {
            "Google": "nl-NL",
            "Whisper": "nl",
        },
    },
    "English": {
        "Australia": {"Google": "en-AU", "Whisper": "en"},
        "Canada": {"Google": "en-CA", "Whisper": "en"},
        "Ghana": {"Google": "en-GH", "Whisper": "en"},
        "Hong Kong": {"Google": "en-HK", "Whisper": "en"},
        "India": {"Google": "en-IN", "Whisper": "en"},
        "Ireland": {"Google": "en-IE", "Whisper": "en"},
        "Kenya": {"Google": "en-KE", "Whisper": "en"},
        "New Zealand": {"Google": "en-NZ", "Whisper": "en"},
        "Nigeria": {"Google": "en-NG", "Whisper": "en"},
        "Philippines": {"Google": "en-PH", "Whisper": "en"},
        "Singapore": {"Google": "en-SG", "Whisper": "en"},
        "South Africa": {"Google": "en-ZA", "Whisper": "en"},
        "Tanzania": {"Google": "en-TZ", "Whisper": "en"},
        "United Kingdom": {"Google": "en-GB", "Whisper": "en"},
        "United States": {"Google": "en-US", "Whisper": "en"},
    },
    "Estonian": {
        "Estonia": {
            "Google": "et-EE",
            "Whisper": "et",
        },
    },
    "Filipino": { # Tagalog (tl) is often used as the code for Filipino
        "Philippines": {
            "Google": "fil-PH",
            "Whisper": "tl",
        },
    },
    "Finnish": {
        "Finland": {
            "Google": "fi-FI",
            "Whisper": "fi",
        },
    },
    "French": {
        "Belgium": {"Google": "fr-BE", "Whisper": "fr"},
        "Canada": {"Google": "fr-CA", "Whisper": "fr"},
        "France": {"Google": "fr-FR", "Whisper": "fr"},
        "Switzerland": {"Google": "fr-CH", "Whisper": "fr"},
    },
    "Galician": {
        "Spain": {
            "Google": "gl-ES",
            "Whisper": "gl",
        },
    },
    "Georgian": {
        "Georgia": {
            "Google": "ka-GE",
            "Whisper": "ka",
        },
    },
    "German": {
        "Austria": {"Google": "de-AT", "Whisper": "de"},
        "Germany": {"Google": "de-DE", "Whisper": "de"},
        "Switzerland": {"Google": "de-CH", "Whisper": "de"},
    },
    "Greek": {
        "Greece": {
            "Google": "el-GR",
            "Whisper": "el",
        },
    },
    "Gujarati": {
        "India": {
            "Google": "gu-IN",
            "Whisper": "gu",
        },
    },
    "Hebrew": {
        "Israel": {
            "Google": "iw-IL", # Note: "iw" is an old code for Hebrew, "he" is current
            "Whisper": "he",
        },
    },
    "Hindi": {
        "India": {
            "Google": "hi-IN",
            "Whisper": "hi",
        },
    },
    "Hungarian": {
        "Hungary": {
            "Google": "hu-HU",
            "Whisper": "hu",
        },
    },
    "Icelandic": {
        "Iceland": {
            "Google": "is-IS",
            "Whisper": "is",
        },
    },
    "Indonesian": {
        "Indonesia": {
            "Google": "id-ID",
            "Whisper": "id",
        },
    },
    "Italian": {
        "Italy": {"Google": "it-IT", "Whisper": "it"},
        "Switzerland": {"Google": "it-CH", "Whisper": "it"},
    },
    "Japanese": {
        "Japan": {
            "Google": "ja-JP",
            "Whisper": "ja",
        },
    },
    # "Javanese": { # Example of a language that might be added
    #     "Indonesia": {
    #         "Google": "jv-ID",
    #         "Whisper": "jw", # Whisper code for Javanese is "jw"
    #     },
    # },
    "Kannada": {
        "India": {
            "Google": "kn-IN",
            "Whisper": "kn",
        },
    },
    "Kazakh": {
        "Kazakhstan": {
            "Google": "kk-KZ",
            "Whisper": "kk",
        },
    },
    "Khmer": {
        "Cambodia": {
            "Google": "km-KH",
            "Whisper": "km",
        },
    },
    # "Kinyarwanda": { # Example
    #     "Rwanda": {
    #         "Google": "rw-RW",
    #         # Whisper support might be missing or under a general code, research needed
    #     },
    # },
    "Korean": {
        "South Korea": {
            "Google": "ko-KR",
            "Whisper": "ko",
        },
    },
    "Lao": {
        "Laos": {
            "Google": "lo-LA",
            "Whisper": "lo",
        },
    },
    "Latvian": {
        "Latvia": {
            "Google": "lv-LV",
            "Whisper": "lv",
        },
    },
    "Lithuanian": {
        "Lithuania": {
            "Google": "lt-LT",
            "Whisper": "lt",
        },
    },
    "Macedonian": {
        "North Macedonia": {
            "Google": "mk-MK",
            "Whisper": "mk",
        },
    },
    "Malay": {
        "Malaysia": {
            "Google": "ms-MY",
            "Whisper": "ms",
        },
    },
    "Malayalam": {
        "India": {
            "Google": "ml-IN",
            "Whisper": "ml",
        },
    },
    "Mongolian": {
        "Mongolia": {
            "Google": "mn-MN",
            "Whisper": "mn",
        },
    },
    "Nepali": {
        "Nepal": {
            "Google": "ne-NP",
            "Whisper": "ne",
        },
    },
    "Norwegian": { # Norwegian Bokmål
        "Norway": {
            "Google": "no-NO",
            "Whisper": "no",
        },
    },
    "Persian": {
        "Iran": {
            "Google": "fa-IR",
            "Whisper": "fa",
        },
    },
    "Polish": {
        "Poland": {
            "Google": "pl-PL",
            "Whisper": "pl",
        },
    },
    "Portuguese": {
        "Brazil": {"Google": "pt-BR", "Whisper": "pt"},
        "Portugal": {"Google": "pt-PT", "Whisper": "pt"},
    },
    # "Punjabi": { # Gurmukhi script
    #     "India": {
    #         "Google": "pa-Guru-IN",
    #         "Whisper": "pa", # Whisper code "pa"
    #     },
    # },
    "Romanian": {
        "Romania": {
            "Google": "ro-RO",
            "Whisper": "ro",
        },
    },
    "Russian": {
        "Russia": {
            "Google": "ru-RU",
            "Whisper": "ru",
        },
    },
    "Serbian": {
        "Serbia": {
            "Google": "sr-RS",
            "Whisper": "sr",
        },
    },
    "Sinhala": {
        "Sri Lanka": {
            "Google": "si-LK",
            "Whisper": "si",
        },
    },
    "Slovak": {
        "Slovakia": {
            "Google": "sk-SK",
            "Whisper": "sk",
        },
    },
    "Slovenian": {
        "Slovenia": {
            "Google": "sl-SI",
            "Whisper": "sl",
        },
    },
    # "Sesotho": {
    #     "South Africa": {
    #         "Google": "st-ZA",
    #         "Whisper": "st", # Whisper code "st"
    #     },
    # },
    "Spanish": {
        "Argentina": {"Google": "es-AR", "Whisper": "es"},
        "Bolivia": {"Google": "es-BO", "Whisper": "es"},
        "Chile": {"Google": "es-CL", "Whisper": "es"},
        "Colombia": {"Google": "es-CO", "Whisper": "es"},
        "Costa Rica": {"Google": "es-CR", "Whisper": "es"},
        "Dominican Republic": {"Google": "es-DO", "Whisper": "es"},
        "Ecuador": {"Google": "es-EC", "Whisper": "es"},
        "El Salvador": {"Google": "es-SV", "Whisper": "es"},
        "Guatemala": {"Google": "es-GT", "Whisper": "es"},
        "Honduras": {"Google": "es-HN", "Whisper": "es"},
        "Mexico": {"Google": "es-MX", "Whisper": "es"},
        "Nicaragua": {"Google": "es-NI", "Whisper": "es"},
        "Panama": {"Google": "es-PA", "Whisper": "es"},
        "Paraguay": {"Google": "es-PY", "Whisper": "es"},
        "Peru": {"Google": "es-PE", "Whisper": "es"},
        "Puerto Rico": {"Google": "es-PR", "Whisper": "es"},
        "Spain": {"Google": "es-ES", "Whisper": "es"},
        "United States": {"Google": "es-US", "Whisper": "es"},
        "Uruguay": {"Google": "es-UY", "Whisper": "es"},
        "Venezuela": {"Google": "es-VE", "Whisper": "es"},
    },
    "Sundanese": {
        "Indonesia": {
            "Google": "su-ID",
            "Whisper": "su",
        },
    },
    "Swahili": {
        "Kenya": {"Google": "sw-KE", "Whisper": "sw"},
        "Tanzania": {"Google": "sw-TZ", "Whisper": "sw"},
    },
    # "Swazi": {
    #     "Eswatini": {
    #         "Google": "ss-Latn-ZA",
    #         # No direct Whisper code, might fall under 'en' or regional for Whisper
    #     },
    # },
    "Swedish": {
        "Sweden": {
            "Google": "sv-SE",
            "Whisper": "sv",
        },
    },
    "Tamil": {
        "India": {"Google": "ta-IN", "Whisper": "ta"},
        "Malaysia": {"Google": "ta-MY", "Whisper": "ta"},
        "Singapore": {"Google": "ta-SG", "Whisper": "ta"},
        "Sri Lanka": {"Google": "ta-LK", "Whisper": "ta"},
    },
    "Telugu": {
        "India": {
            "Google": "te-IN",
            "Whisper": "te",
        },
    },
    "Thai": {
        "Thailand": {
            "Google": "th-TH",
            "Whisper": "th",
        },
    },
    # "Tsonga": {
    #     "South Africa": {"Google": "ts-ZA"},
    # },
    # "Setswana": { # (Tswana)
    #     "South Africa": {
    #         "Google": "tn-Latn-ZA",
    #         "Whisper": "tn", # Whisper code "tn"
    #     },
    # },
    "Turkish": {
        "Turkey": {
            "Google": "tr-TR",
            "Whisper": "tr",
        },
    },
    "Ukrainian": {
        "Ukraine": {
            "Google": "uk-UA",
            "Whisper": "uk",
        },
    },
    "Urdu": {
        "India": {"Google": "ur-IN", "Whisper": "ur"},
        "Pakistan": {"Google": "ur-PK", "Whisper": "ur"},
    },
    "Uzbek": {
        "Uzbekistan": {
            "Google": "uz-UZ",
            "Whisper": "uz",
        },
    },
    # "Venda": {
    #     "South Africa": {
    #         "Google": "ve-ZA",
    #         "Whisper": "ve", # Whisper code "ve"
    #     },
    # },
    "Vietnamese": {
        "Vietnam": {
            "Google": "vi-VN",
            "Whisper": "vi",
        },
    },
    # "Xhosa": {
    #     "South Africa": {"Google": "xh-ZA"}, # Whisper code "xh"
    # },
    # "Zulu": {
    #     "South Africa": {"Google": "zu-ZA"}, # Whisper code "zu"
    # },
}