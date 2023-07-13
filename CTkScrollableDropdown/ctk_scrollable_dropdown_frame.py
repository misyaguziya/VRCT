'''
Advanced Scrollable Dropdown Frame class for customtkinter widgets
Author: Akash Bora
'''

import customtkinter
import sys

class CTkScrollableDropdownFrame(customtkinter.CTkFrame):
    
    def __init__(self, attach, x=None, y=None, button_color=None, height: int = 200, width: int = None,
                 fg_color=None, button_height: int = 20, justify="center", scrollbar_button_color=None,
                 scrollbar=True, scrollbar_button_hover_color=None, frame_border_width=2, values=[],
                 command=None, image_values=[], double_click=False, frame_corner_radius=True, resize=True, frame_border_color=None,
                 text_color=None, autocomplete=False, **button_kwargs):

        super().__init__(master=attach.winfo_toplevel(), bg_color=attach.cget("bg_color"))
        
        self.attach = attach
        self.corner = 11 if frame_corner_radius else 0
        self.padding = 0
        self.disable = True

        self.hide = True
        self.attach.bind('<Configure>', lambda e: self._withdraw() if not self.disable else None, add="+")
        self.attach.winfo_toplevel().bind("<Triple-Button-1>", lambda e: self._withdraw() if not self.disable else None, add="+")
        self.attach.winfo_toplevel().bind("<Button-3>", lambda e: self._withdraw() if not self.disable else None, add="+")
        self.attach.winfo_toplevel().bind("<Button-2>", lambda e: self._withdraw() if not self.disable else None, add="+")
        
        self.disable = False
        self.fg_color = customtkinter.ThemeManager.theme["CTkFrame"]["fg_color"] if fg_color is None else fg_color
        self.scroll_button_color = customtkinter.ThemeManager.theme["CTkScrollbar"]["button_color"] if scrollbar_button_color is None else scrollbar_button_color
        self.scroll_hover_color = customtkinter.ThemeManager.theme["CTkScrollbar"]["button_hover_color"] if scrollbar_button_hover_color is None else scrollbar_button_hover_color
        self.frame_border_color = customtkinter.ThemeManager.theme["CTkFrame"]["border_color"] if frame_border_color is None else frame_border_color
        self.button_color = customtkinter.ThemeManager.theme["CTkFrame"]["top_fg_color"] if button_color is None else button_color
        self.text_color = customtkinter.ThemeManager.theme["CTkLabel"]["text_color"] if text_color is None else text_color
        
        if scrollbar is False:
            self.scroll_button_color = self.fg_color
            self.scroll_hover_color = self.fg_color
            
        self.frame = customtkinter.CTkScrollableFrame(self, fg_color=self.fg_color, bg_color=attach.cget("bg_color"),
                                        scrollbar_button_hover_color=self.scroll_hover_color,
                                        corner_radius=self.corner, border_width=frame_border_width,
                                        scrollbar_button_color=self.scroll_button_color,
                                        border_color=self.frame_border_color)
        self.frame._scrollbar.grid_configure(padx=3)
        self.frame.pack(expand=True, fill="both")
        
        if self.corner==0:
            self.corner = 21
            
        self.dummy_entry = customtkinter.CTkEntry(self.frame, fg_color="transparent", border_width=0, height=1, width=1)
        self.no_match = customtkinter.CTkLabel(self.frame, text="No Match")
        self.height = height
        self.height_new = height
        self.width = width
        self.command = command
        self.fade = False
        self.resize = resize
        self.autocomplete = autocomplete
        self.var_update = customtkinter.StringVar()
        self.appear = False
        
        if justify.lower()=="left":
            self.justify = "w"
        elif justify.lower()=="right":
            self.justify = "e"
        else:
            self.justify = "c"
            
        self.button_height = button_height
        self.values = values
        self.button_num = len(self.values)
        self.image_values = None if len(image_values)!=len(self.values) else image_values
        
        self._init_buttons(**button_kwargs)

        # Add binding for different ctk widgets
        if double_click or self.attach.winfo_name().startswith("!ctkentry") or self.attach.winfo_name().startswith("!ctkcombobox"):
            self.attach.bind('<Double-Button-1>', lambda e: self._iconify(), add="+")
            self.attach._entry.bind('<FocusOut>', lambda e: self._withdraw() if not self.disable else None, add="+")
        else:
            self.attach.bind('<Button-1>', lambda e: self._iconify(), add="+")

        if self.attach.winfo_name().startswith("!ctkcombobox"):
            self.attach._canvas.tag_bind("right_parts", "<Button-1>", lambda e: self._iconify())
            self.attach._canvas.tag_bind("dropdown_arrow", "<Button-1>", lambda e: self._iconify())
      
            if self.command is None:
                self.command = self.attach.set
              
        if self.attach.winfo_name().startswith("!ctkoptionmenu"):
            self.attach._canvas.bind("<Button-1>", lambda e: self._iconify())
            self.attach._text_label.bind("<Button-1>", lambda e: self._iconify())
            if self.command is None:
                self.command = self.attach.set
        
        self.x = x
        self.y = y

        if self.autocomplete:
            self.bind_autocomplete()
        
    def _withdraw(self):
        if self.hide is False: self.place_forget()
        self.hide = True

    def _update(self, a, b, c):
        self.live_update(self.attach._entry.get())
        
    def bind_autocomplete(self, ):
        def appear(x):
            self.appear = True
            
        if self.attach.winfo_name().startswith("!ctkcombobox"):
            self.attach._entry.configure(textvariable=self.var_update)
            self.attach.set(self.values[0])
            self.attach._entry.bind("<Key>", appear)
            self.var_update.trace_add('write', self._update)
            
        if self.attach.winfo_name().startswith("!ctkentry"):
            self.attach.configure(textvariable=self.var_update)
            self.attach.bind("<Key>", appear)
            self.var_update.trace_add('write', self._update)
            
    def _init_buttons(self, **button_kwargs):
        self.i = 0
        self.widgets = {}
        for row in self.values:                                
            self.widgets[self.i] = customtkinter.CTkButton(self.frame,
                                                          text=row,
                                                          height=self.button_height,
                                                          fg_color=self.button_color,
                                                          text_color=self.text_color,
                                                          image=self.image_values[i] if self.image_values is not None else None,
                                                          anchor=self.justify,
                                                          command=lambda k=row: self._attach_key_press(k), **button_kwargs)
            self.widgets[self.i].pack(fill="x", pady=2, padx=(self.padding, 0))
            self.i+=1
             
        self.hide = False
            
    def destroy_popup(self):
        self.destroy()
        self.disable = True

    def place_dropdown(self):
        self.x_pos = self.attach.winfo_x() if self.x is None else self.x + self.attach.winfo_rootx()
        self.y_pos = self.attach.winfo_y() + self.attach.winfo_reqheight() + 5 if self.y is None else self.y + self.attach.winfo_rooty()
        self.width_new = self.attach.winfo_width()-45+self.corner if self.width is None else self.width
        
        if self.resize:
            if self.button_num==1:      
                self.height_new = self.button_height * self.button_num + 45
            else:
                self.height_new = self.button_height * self.button_num + 35
            if self.height_new>self.height:
                self.height_new = self.height
 
        self.frame.configure(width=self.width_new, height=self.height_new)
        self.place(x=self.x_pos, y=self.y_pos)
        
        if sys.platform.startswith("darwin"):
            self.dummy_entry.pack()
            self.after(100, self.dummy_entry.pack_forget())
            
        self.lift()
        self.attach.focus()
   
    def _iconify(self):
        if self.disable: return
        if self.hide:       
            self.hide = False
            self.place_dropdown()
        else:
            self.place_forget()
            self.hide = True
            
    def _attach_key_press(self, k):
        self.fade = True
        if self.command:
            self.command(k)
        self.fade = False
        self.place_forget()
        self.hide = True
            
    def live_update(self, string=None):
        if not self.appear: return
        if self.disable: return
        if self.fade: return
        if string:
            self._deiconify()
            i=1
            for key in self.widgets.keys():
                s = self.widgets[key].cget("text")
                if not s.startswith(string):
                    self.widgets[key].pack_forget()
                else:
                    self.widgets[key].pack(fill="x", pady=2, padx=(self.padding, 0))
                    i+=1
                    
            if i==1:
                self.no_match.pack(fill="x", pady=2, padx=(self.padding, 0))
            else:
                self.no_match.pack_forget()
            self.button_num = i
            self.place_dropdown()
            
        else:
            self.no_match.pack_forget()
            self.button_num = len(self.values)
            for key in self.widgets.keys():
                self.widgets[key].destroy()
            self._init_buttons()
            self.place_dropdown()
            
        self.frame._parent_canvas.yview_moveto(0.0)
        self.appear = False
        
    def insert(self, value, **kwargs):
        self.widgets[self.i] = customtkinter.CTkButton(self.frame,
                                                       text=value,
                                                       height=self.button_height,
                                                       fg_color=self.button_color,
                                                       text_color=self.text_color,
                                                       anchor=self.justify,
                                                       command=lambda k=value: self._attach_key_press(k), **kwargs)
        self.widgets[self.i].pack(fill="x", pady=2, padx=(self.padding, 0))
        self.i+=1
        self.values.append(value)
        
    def _deiconify(self):
        if len(self.values)>0:
            self.pack_forget()

    def popup(self, x=None, y=None):
        self.x = x
        self.y = y
        self.hide = True
        self._iconify()
        
    def configure(self, **kwargs):
        if "height" in kwargs:
            self.height = kwargs.pop("height")
            self.height_new = self.height
            
        if "alpha" in kwargs:
            self.alpha = kwargs.pop("alpha")
            
        if "width" in kwargs:
            self.width = kwargs.pop("width")
            
        if "fg_color" in kwargs:
            self.frame.configure(fg_color=kwargs.pop("fg_color"))
            
        if "values" in kwargs:
            self.values = kwargs.pop("values")
            self.image_values = None
            for key in self.widgets.keys():
                self.widgets[key].destroy()
            self._init_buttons()
            
        if "image_values" in kwargs:
            self.image_values = kwargs.pop("image_values")
            self.image_values = None if len(self.image_values)!=len(self.values) else self.image_values
            if self.image_values is not None:
                i=0
                for key in self.widgets.keys():
                    self.widgets[key].configure(image=self.image_values[i])
                    i+=1
                    
        if "button_color" in kwargs:
            for key in self.widgets.keys():
                self.widgets[key].configure(fg_color=kwargs.pop("button_color"))
                
        for key in self.widgets.keys():
            self.widgets[key].configure(**kwargs)
