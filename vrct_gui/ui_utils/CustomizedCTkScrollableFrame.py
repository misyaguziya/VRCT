# Override customtkinter's CTkScrollableFrame for scrolling speed up
from customtkinter import CTkScrollableFrame, CTkFont
from typing import Union, Tuple, Optional
import sys
try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

class CustomizedCTkScrollableFrame(CTkScrollableFrame):
    def __init__(
            self,
            master: any,
            width: int = 200,
            height: int = 200,
            corner_radius: Optional[Union[int, str]] = None,
            border_width: Optional[Union[int, str]] = None,

            bg_color: Union[str, Tuple[str, str]] = "transparent",
            fg_color: Optional[Union[str, Tuple[str, str]]] = None,
            border_color: Optional[Union[str, Tuple[str, str]]] = None,
            scrollbar_fg_color: Optional[Union[str, Tuple[str, str]]] = None,
            scrollbar_button_color: Optional[Union[str, Tuple[str, str]]] = None,
            scrollbar_button_hover_color: Optional[Union[str, Tuple[str, str]]] = None,
            label_fg_color: Optional[Union[str, Tuple[str, str]]] = None,
            label_text_color: Optional[Union[str, Tuple[str, str]]] = None,

            label_text: str = "",
            label_font: Optional[Union[tuple, CTkFont]] = None,
            label_anchor: str = "center",
            orientation: Literal["vertical", "horizontal"] = "vertical"
        ):

        super().__init__(
                master,
                width,
                height,
                corner_radius,
                border_width,

                bg_color,
                fg_color,
                border_color,
                scrollbar_fg_color,
                scrollbar_button_color,
                scrollbar_button_hover_color,
                label_fg_color,
                label_text_color,

                label_text,
                label_font,
                label_anchor,
                orientation,
            )

    def _mouse_wheel_all(self, event):
        if self.check_if_master_is_canvas(event.widget):
            if sys.platform.startswith("win"):
                if self._shift_pressed:
                    if self._parent_canvas.xview() != (0.0, 1.0):
                        self._parent_canvas.xview("scroll", -int(event.delta / 6), "units")
                else:
                    if self._parent_canvas.yview() != (0.0, 1.0):
                        self._parent_canvas.yview("scroll", -int(event.delta / 2), "units")

            elif sys.platform == "darwin":
                if self._shift_pressed:
                    if self._parent_canvas.xview() != (0.0, 1.0):
                        self._parent_canvas.xview("scroll", -event.delta, "units")
                else:
                    if self._parent_canvas.yview() != (0.0, 1.0):
                        self._parent_canvas.yview("scroll", -event.delta, "units")
            else:
                if self._shift_pressed:
                    if self._parent_canvas.xview() != (0.0, 1.0):
                        self._parent_canvas.xview("scroll", -event.delta, "units")
                else:
                    if self._parent_canvas.yview() != (0.0, 1.0):
                        self._parent_canvas.yview("scroll", -event.delta, "units")