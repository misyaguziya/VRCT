from types import SimpleNamespace

from .Themes import _darkTheme, _lightTheme

class ColorThemeManager():
    def __init__(self, theme):
        self.base_color = SimpleNamespace(

            PRIMARY_100_COLOR = "#b7ded8",
            PRIMARY_200_COLOR = "#8acac0",
            PRIMARY_300_COLOR = "#61b4a7",
            PRIMARY_400_COLOR = "#48a495",
            PRIMARY_450_COLOR = "#429c8c",
            PRIMARY_500_COLOR = "#3b9483",
            PRIMARY_600_COLOR = "#368777",
            PRIMARY_650_COLOR = "#347f6f",
            PRIMARY_700_COLOR = "#317767",
            PRIMARY_750_COLOR = "#2F6F60",
            PRIMARY_800_COLOR = "#2c6759",
            PRIMARY_900_COLOR = "#214b3f",


            DARK_100_COLOR = "#f5f7fb",
            DARK_200_COLOR = "#f1f2f6",
            DARK_300_COLOR = "#e9eaee",
            DARK_350_COLOR = "#d8d9dd",
            DARK_400_COLOR = "#c7c8cc",
            DARK_450_COLOR = "#b8b9bd",
            DARK_500_COLOR = "#a9aaae",
            DARK_600_COLOR = "#7f8084",
            DARK_650_COLOR = "#75767a",
            DARK_700_COLOR = "#6a6c6f",
            DARK_725_COLOR = "#636467",
            DARK_750_COLOR = "#5b5c5f",
            DARK_775_COLOR = "#535457",
            DARK_800_COLOR = "#4b4c4f",
            DARK_825_COLOR = "#434447",
            DARK_850_COLOR = "#3a3b3e",
            DARK_863_COLOR = "#36373a",
            DARK_875_COLOR = "#323336",
            DARK_888_COLOR = "#2e2f32",
            DARK_900_COLOR = "#292a2d",
            DARK_925_COLOR = "#242528",
            DARK_950_COLOR = "#1f2022",
            DARK_975_COLOR = "#1a1b1d",
            DARK_1000_COLOR = "#151517", # THE DARKEST COLOR


            LIGHT_100_COLOR = "#f2f2f2", # THE LIGHTEST COLOR,
            LIGHT_200_COLOR = "#e9e9e9",
            LIGHT_250_COLOR = "#e1e1e1",
            LIGHT_300_COLOR = "#d9d9d9",
            LIGHT_325_COLOR = "#d0d0d0",
            LIGHT_350_COLOR = "#c7c7c7",
            LIGHT_375_COLOR = "#bebebe",
            LIGHT_400_COLOR = "#b5b5b5",
            LIGHT_450_COLOR = "#a5a5a5",
            LIGHT_500_COLOR = "#959595",
            LIGHT_600_COLOR = "#6d6d6d",
            LIGHT_700_COLOR = "#5a5a5a",
            LIGHT_750_COLOR = "#515151",
            LIGHT_800_COLOR = "#3b3b3b",
            LIGHT_850_COLOR = "#323232",
            LIGHT_875_COLOR = "#2b2b2b",
            LIGHT_900_COLOR = "#1b1b1b",
            # LIGHT_925_COLOR = "#121212",
            # LIGHT_950_COLOR = "#0c0c0c",
            # LIGHT_975_COLOR = "#070707",
            LIGHT_1000_COLOR = "#010101",
        )


        # It's actually meaningless to separate it from __init__. but it's just set to use the dark theme by default, so I did it just in case to change the default theme.
        selected_color_theme = _darkTheme(self.base_color)
        for each_key in selected_color_theme.__dict__.keys():
            setattr(self, each_key, getattr(selected_color_theme, each_key))


        if theme == "Dark":
            pass

        elif theme == "Light":
            selected_color_theme = _lightTheme(self.base_color)
            self._colorThemeDictsMerger(selected_color_theme)





    def _colorThemeDictsMerger(self, selected_color_theme):
        # Each section(main, selectable_language_window, config_window...) marge to default theme.
        for selected_theme_section_key in selected_color_theme.__dict__.keys():
            # Get same section data by section key from default theme.
            default_theme_target_section_data = getattr(self, selected_theme_section_key)

            selected_theme_section_data = getattr(selected_color_theme, selected_theme_section_key)
            self._mergeNestedDicts(default_theme_target_section_data.__dict__, selected_theme_section_data.__dict__)



    def _mergeNestedDicts(self, d1, d2):
        for key, value in d2.items():
            if key in d1 and isinstance(d1[key], dict) and isinstance(value, dict):
                self._mergeNestedDicts(d1[key], value)
            else:
                d1[key] = value

        return d1
