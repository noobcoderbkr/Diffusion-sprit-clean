"""Bilingual desktop interface for the preserved region compositor."""
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, ttk

from PIL import Image, ImageDraw, ImageTk

from ui_support import LANGUAGES, load_language, save_language, translate
from versions.legacy_compositor import (
    DND_FILES, TkinterDnD, LoadedImage,
    RegionCompositorApp as LegacyCompositor,
)

COLORS = {
    'background': '#F3F4F6', 'surface': '#FFFFFF', 'text': '#1D1D1F',
    'secondary': '#5D626B', 'line': '#D9DDE3', 'accent': '#0066CC',
    'accent_hover': '#0055AA', 'selected': '#E5EFFB', 'canvas': '#E9ECF0',
}


class RegionCompositorApp(LegacyCompositor):
    def __init__(self, root, language=None, preference_path=None):
        self.preference_path = preference_path
        self.language = language if language in LANGUAGES else load_language(preference_path)
        self.text_variables = {}
        self.language_var = tk.StringVar(root, LANGUAGES[self.language])
        self._status_key = None
        self._status_values = {}
        self._render_job = None
        super().__init__(root)
        root.title('RegionCompositor')
        root.geometry('1240x840')
        root.minsize(960, 640)
        root.bind('<Destroy>', self._on_destroy, add='+')
        self.apply_language()

    def _on_destroy(self, event):
        if event.widget is self.root and self._render_job is not None:
            self.root.after_cancel(self._render_job)
            self._render_job = None

    def tr(self, key, **values):
        return translate(self.language, key, **values)

    def text(self, key):
        if key not in self.text_variables:
            self.text_variables[key] = tk.StringVar(self.root, self.tr(key))
        return self.text_variables[key]

    def _configure_style(self):
        available = tkfont.families(self.root)
        self.font_family = 'Segoe UI' if 'Segoe UI' in available else 'TkDefaultFont'
        style = ttk.Style(self.root)
        style.theme_use('clam')
        c = COLORS
        style.configure('.', font=(self.font_family, 11), foreground=c['text'])
        for name, background in [('App', c['background']), ('Panel', c['surface'])]:
            style.configure(f'{name}.TFrame', background=background)
            style.configure(f'{name}.TLabel', background=background, foreground=c['text'])
        style.configure('Title.TLabel', background=c['background'], font=(self.font_family, 20, 'bold'))
        style.configure('Subtitle.TLabel', background=c['background'], foreground=c['secondary'])
        style.configure('Heading.TLabel', background=c['surface'], font=(self.font_family, 11, 'bold'))
        style.configure('Meta.TLabel', background=c['surface'], foreground=c['secondary'], font=(self.font_family, 10))
        style.configure('Value.TLabel', background=c['surface'], foreground=c['text'], font=(self.font_family, 10))
        style.configure('TButton', padding=(12, 8), background=c['surface'], bordercolor=c['line'],
                        lightcolor=c['surface'], darkcolor=c['surface'], focuscolor=c['accent'], borderwidth=1)
        style.map('TButton', background=[('pressed', c['selected']), ('active', '#F1F5FA')],
                  foreground=[('disabled', '#8A8F98')], bordercolor=[('focus', c['accent'])])
        style.configure('Compact.TButton', padding=(10, 4))
        style.configure('Primary.TButton', background=c['accent'], foreground='white',
                        font=(self.font_family, 10, 'bold'), bordercolor=c['accent'])
        style.map('Primary.TButton', background=[('disabled', '#E1E5EA'), ('active', c['accent_hover'])],
                  foreground=[('disabled', '#737983'), ('!disabled', 'white')])
        style.configure('TCheckbutton', background=c['surface'], padding=(0, 6), focuscolor=c['accent'])
        style.map('TCheckbutton', background=[('active', c['surface'])])
        style.configure('Segment.TRadiobutton', background=c['surface'], padding=(12, 7),
                        relief='flat', borderwidth=1, focuscolor=c['accent'])
        style.layout('Segment.TRadiobutton', [('Radiobutton.padding', {'children': [
            ('Radiobutton.focus', {'children': [('Radiobutton.label', {'sticky': 'nswe'})], 'sticky': 'nswe'})], 'sticky': 'nswe'})])
        style.map('Segment.TRadiobutton', background=[('selected', c['selected']), ('active', '#F3F6FA')],
                  foreground=[('selected', c['accent'])])
        style.configure('TCombobox', padding=(8, 6), fieldbackground=c['surface'], arrowsize=14)
        style.map('TCombobox', fieldbackground=[('readonly', c['surface'])],
                  foreground=[('readonly', c['text'])], selectbackground=[('readonly', c['surface'])],
                  selectforeground=[('readonly', c['text'])])
        style.configure('Horizontal.TScale', background=c['surface'], troughcolor='#E3E7ED',
                        bordercolor=c['surface'], lightcolor=c['surface'], darkcolor=c['surface'])
        thumb = Image.new('RGBA', (22, 22))
        ImageDraw.Draw(thumb).ellipse((2, 2, 19, 19), fill=c['accent'], outline='white', width=2)
        self.slider_thumb = ImageTk.PhotoImage(thumb, master=self.root)
        if 'Compositor.Scale.slider' not in style.element_names():
            style.element_create('Compositor.Scale.slider', 'image', self.slider_thumb)
        style.layout('Horizontal.TScale', [('Horizontal.Scale.trough', {'sticky': 'we', 'children': [
            ('Compositor.Scale.slider', {'side': 'left', 'sticky': ''})]})])
        style.configure('Vertical.TScrollbar', background='#CBD0D8', troughcolor=c['background'],
                        borderwidth=0, arrowsize=12)

    def label(self, parent, key, style='Panel.TLabel', **kwargs):
        return ttk.Label(parent, textvariable=self.text(key), style=style, **kwargs)

    def button(self, parent, key, command, **kwargs):
        return ttk.Button(parent, textvariable=self.text(key), command=command, **kwargs)

    def _build_ui(self):
        self.root.configure(background=COLORS['background'])
        self.root.columnconfigure(0, weight=0, minsize=340)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(1, weight=1)
        header = ttk.Frame(self.root, style='App.TFrame', padding=(24, 18, 24, 16))
        header.grid(row=0, column=0, columnspan=2, sticky='ew')
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text='RegionCompositor', style='Title.TLabel').grid(row=0, column=0, sticky='w')
        self.label(header, 'subtitle', 'Subtitle.TLabel').grid(row=1, column=0, sticky='w', pady=(3, 0))
        language_group = ttk.Frame(header, style='App.TFrame')
        language_group.grid(row=0, column=1, rowspan=2, padx=(16, 18))
        self.label(language_group, 'language', 'Subtitle.TLabel').pack(side='left', padx=(0, 8))
        self.language_selector = ttk.Combobox(language_group, textvariable=self.language_var,
                                             values=list(LANGUAGES.values()), state='readonly', width=9)
        self.language_selector.pack(side='left')
        self.language_selector.bind('<<ComboboxSelected>>', self.change_language)
        self.export_button = self.button(header, 'export', self.save_as, style='Primary.TButton')
        self.export_button.grid(row=0, column=2, rowspan=2, sticky='e')

        inspector_host = ttk.Frame(self.root, style='App.TFrame')
        inspector_host.grid(row=1, column=0, sticky='nsew', padx=(20, 14), pady=(0, 16))
        inspector_host.columnconfigure(0, weight=1)
        inspector_host.rowconfigure(0, weight=1)
        self.inspector_canvas = tk.Canvas(inspector_host, width=320, highlightthickness=0,
                                          background=COLORS['background'])
        self.inspector_canvas.grid(row=0, column=0, sticky='nsew')
        scroll = ttk.Scrollbar(inspector_host, orient='vertical', command=self.inspector_canvas.yview)
        scroll.grid(row=0, column=1, sticky='ns', padx=(3, 0))
        self.inspector_canvas.configure(yscrollcommand=scroll.set)
        self.inspector = ttk.Frame(self.inspector_canvas, style='App.TFrame')
        self.inspector_window = self.inspector_canvas.create_window((0, 0), window=self.inspector, anchor='nw')
        self.inspector.bind('<Configure>', lambda _e: self.inspector_canvas.configure(scrollregion=self.inspector_canvas.bbox('all')))
        self.inspector_canvas.bind('<Configure>', lambda e: self.inspector_canvas.itemconfigure(self.inspector_window, width=e.width))
        self._build_upload_section(self.inspector)
        self._build_region_section(self.inspector)
        self._build_blend_section(self.inspector)

        preview = ttk.Frame(self.root, style='Panel.TFrame', padding=1)
        preview.grid(row=1, column=1, sticky='nsew', padx=(0, 20), pady=(0, 16))
        preview.rowconfigure(1, weight=1)
        preview.columnconfigure(0, weight=1)
        preview_header = ttk.Frame(preview, style='Panel.TFrame', padding=(18, 12))
        preview_header.grid(row=0, column=0, sticky='ew')
        preview_header.columnconfigure(0, weight=1)
        self.label(preview_header, 'preview', 'Heading.TLabel').grid(row=0, column=0, sticky='w')
        modes = ttk.Frame(preview_header, style='Panel.TFrame')
        modes.grid(row=0, column=1, sticky='e')
        for column, mode in enumerate(('composite', 'base', 'patch')):
            ttk.Radiobutton(modes, textvariable=self.text('view_' + mode), value=mode,
                            variable=self.view_mode, command=self.render, style='Segment.TRadiobutton').grid(row=0, column=column)
        self.canvas = tk.Canvas(preview, bg=COLORS['canvas'], highlightthickness=0, cursor='crosshair', takefocus=True)
        self.canvas.grid(row=1, column=0, sticky='nsew', padx=1)
        footer = ttk.Frame(preview, style='Panel.TFrame', padding=(16, 10))
        footer.grid(row=2, column=0, sticky='ew')
        footer.columnconfigure(0, weight=1)
        self.selection_text = tk.StringVar(self.root)
        ttk.Label(footer, textvariable=self.selection_text, style='Meta.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Checkbutton(footer, textvariable=self.text('guide'), variable=self.show_guide,
                        command=self.render).grid(row=0, column=1, sticky='e')
        ttk.Label(self.root, textvariable=self.status_text, style='Subtitle.TLabel',
                  padding=(24, 0, 24, 12)).grid(row=2, column=0, columnspan=2, sticky='ew')
        self._build_menu()

    def card(self, parent, key):
        border = tk.Frame(parent, background=COLORS['line'], padx=1, pady=1)
        border.pack(fill='x', pady=(0, 12))
        frame = ttk.Frame(border, style='Panel.TFrame', padding=(14, 12))
        frame.pack(fill='both', expand=True)
        self.label(frame, key, 'Heading.TLabel').pack(anchor='w', pady=(0, 8))
        return frame

    def _build_upload_section(self, parent):
        frame = self.card(parent, 'images')
        self.base_button = self.button(frame, 'open_base', self.open_base)
        self.base_button.pack(fill='x')
        self.base_label = ttk.Label(frame, textvariable=self.base_text, style='Meta.TLabel', wraplength=270)
        self.base_label.pack(fill='x', pady=(5, 9))
        self.patch_button = self.button(frame, 'open_patch', self.open_patch)
        self.patch_button.pack(fill='x')
        self.patch_label = ttk.Label(frame, textvariable=self.patch_text, style='Meta.TLabel', wraplength=270)
        self.patch_label.pack(fill='x', pady=(5, 9))
        self.swap_button = self.button(frame, 'swap', self.swap_images, style='Compact.TButton')
        self.swap_button.pack(fill='x')
        self.drop_text = tk.StringVar(self.root)
        self.drop_hint_label = ttk.Label(frame, textvariable=self.drop_text, style='Meta.TLabel', wraplength=270)
        self.drop_hint_label.pack(fill='x', pady=(10, 0))

    def slider(self, parent, key, variable, display, upper, command, lower=0):
        row = ttk.Frame(parent, style='Panel.TFrame')
        row.pack(fill='x', pady=(0, 9))
        row.columnconfigure(1, weight=1)
        self.label(row, key, width=10).grid(row=0, column=0, sticky='w')
        ttk.Label(row, textvariable=display, style='Value.TLabel', width=6, anchor='e').grid(row=0, column=2, sticky='e')
        ttk.Scale(row, from_=lower, to=upper, variable=variable, command=lambda _v: command(), takefocus=True).grid(
            row=0, column=1, sticky='ew', padx=(4, 7))

    def _build_region_section(self, parent):
        frame = self.card(parent, 'region')
        for key in ('x', 'y', 'w', 'h'):
            self.slider(frame, key, getattr(self, key + '_var'), getattr(self, key + '_text'), 100,
                        lambda k=key: self.update_rect_from_controls(k), lower=0 if key in ('x', 'y') else 1)
        actions = ttk.Frame(frame, style='Panel.TFrame')
        actions.pack(fill='x')
        ttk.Checkbutton(actions, textvariable=self.text('lock'), variable=self.lock_aspect).pack(side='left')
        self.button(actions, 'reset', lambda: self.set_rect(.25, .25, .5, .5), style='Compact.TButton').pack(side='right')

    def _build_blend_section(self, parent):
        frame = self.card(parent, 'blend')
        self.slider(frame, 'opacity', self.opacity_var, self.opacity_text, 100, self.update_blend)
        self.slider(frame, 'feather', self.feather_var, self.feather_text, 200, self.update_blend)
        ttk.Checkbutton(frame, textvariable=self.text('edge_match'), variable=self.edge_match, command=self.render).pack(anchor='w')

    def _build_menu(self):
        menu = tk.Menu(self.root, tearoff=False)
        self.file_menu = tk.Menu(menu, tearoff=False)
        for key, action, shortcut in [('open_base', self.open_base, 'Ctrl+O'), ('open_patch', self.open_patch, 'Ctrl+Shift+O')]:
            self.file_menu.add_command(label=self.tr(key), command=action, accelerator=shortcut)
        self.file_menu.add_separator()
        self.file_menu.add_command(label=self.tr('export'), command=self.save_as, accelerator='Ctrl+S')
        self.file_menu.add_command(label=self.tr('replace'), command=self.save_png, accelerator='Ctrl+Shift+S')
        self.file_menu.add_separator()
        self.file_menu.add_command(label=self.tr('quit'), command=self.root.destroy)
        menu.add_cascade(label=self.tr('file_menu'), menu=self.file_menu)
        view = tk.Menu(menu, tearoff=False)
        for mode in ('composite', 'base', 'patch'):
            view.add_radiobutton(label=self.tr('view_' + mode), variable=self.view_mode, value=mode, command=self.render)
        view.add_separator()
        view.add_checkbutton(label=self.tr('guide'), variable=self.show_guide, command=self.render)
        menu.add_cascade(label=self.tr('view_menu'), menu=view)
        languages = tk.Menu(menu, tearoff=False)
        for code, label in LANGUAGES.items():
            languages.add_radiobutton(label=label, variable=self.language_var, value=label,
                                      command=lambda c=code: self.change_language(code=c))
        menu.add_cascade(label=self.tr('language_menu'), menu=languages)
        previous = getattr(self, 'menubar', None)
        self.root.configure(menu=menu)
        self.menubar = menu
        if previous is not None:
            previous.destroy()

    def _bind_events(self):
        super()._bind_events()
        for sequence, action in [('<Control-o>', self.open_base), ('<Control-O>', self.open_patch),
                                  ('<Control-s>', self.save_as), ('<Control-S>', self.save_png)]:
            self.root.bind(sequence, lambda _e, fn=action: (fn(), 'break')[1])
        for key, dx, dy in [('Left', -1, 0), ('Right', 1, 0), ('Up', 0, -1), ('Down', 0, 1)]:
            self.canvas.bind('<' + key + '>', lambda e, x=dx, y=dy: self.nudge(x, y, 10 if e.state & 1 else 1))
        self.root.bind('<MouseWheel>', self._scroll_inspector, add='+')

    def _scroll_inspector(self, event):
        widget = event.widget
        while widget is not None:
            if widget is self.inspector or widget is self.inspector_canvas:
                self.inspector_canvas.yview_scroll(-int(event.delta / 120), 'units')
                return 'break'
            widget = getattr(widget, 'master', None)

    def nudge(self, dx, dy, step):
        if self.base:
            x, y, w, h = self.rect
            self.set_rect(x + dx * step / self.base.image.width, y + dy * step / self.base.image.height, w, h)
        return 'break'

    def on_pointer_down(self, event):
        self.canvas.focus_set()
        super().on_pointer_down(event)

    def change_language(self, _event=None, code=None):
        code = code or next((code for code, label in LANGUAGES.items() if label == self.language_var.get()), 'ko')
        if code not in LANGUAGES:
            return
        self.language = code
        self.language_var.set(LANGUAGES[code])
        self.apply_language()
        try:
            save_language(code, self.preference_path)
        except OSError:
            self.set_status('settings_error')

    def apply_language(self):
        for key, value in self.text_variables.items():
            value.set(self.tr(key))
        self.base_text.set(self.base.label if self.base else self.tr('empty_file'))
        self.patch_text.set(self.patch.label if self.patch else self.tr('empty_file'))
        self.drop_text.set(self.tr('drop_hint' if self.drop_available else 'drop_off'))
        self._build_menu()
        self.render()

    def _setup_drop_targets(self):
        self.drop_available = bool(DND_FILES and hasattr(self.root, 'drop_target_register'))
        if self.drop_available:
            try:
                for widget, target in [(self.base_button, 'base'), (self.base_label, 'base'),
                                       (self.patch_button, 'patch'), (self.patch_label, 'patch')]:
                    self._register_drop_target(widget, target)
            except (tk.TclError, AttributeError):
                self.drop_available = False
        self.drop_text.set(self.tr('drop_hint' if self.drop_available else 'drop_off'))

    def handle_file_drop(self, event, target):
        try:
            path = next((p for p in self.parse_drop_paths(getattr(event, 'data', '')) if self.is_supported_image(p)), None)
            if path is None:
                messagebox.showinfo(self.tr('no_image'), self.tr('drop_error'), parent=self.root)
            else:
                self.load_image_path(path, target)
        except (OSError, tk.TclError) as exc:
            messagebox.showerror(self.tr('open_failed'), self.tr('open_error', error=exc), parent=self.root)
        return 'break'

    def open_base(self):
        self.open_image('base')

    def open_patch(self):
        self.open_image('patch')

    def open_image(self, target):
        path = filedialog.askopenfilename(parent=self.root, title=self.tr('open_' + target), filetypes=(
            (self.tr('image_files'), '*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff'), (self.tr('all_files'), '*.*')))
        if path:
            self.load_image_path(Path(path), target)

    def load_image_path(self, path, target):
        try:
            with Image.open(path) as image:
                loaded = LoadedImage(Path(path), image.convert('RGBA'))
            setattr(self, target, loaded)
            getattr(self, target + '_text').set(loaded.label)
            self._status_key = None
            self.render()
        except Exception as exc:
            messagebox.showerror(self.tr('open_failed'), self.tr('open_error', error=exc), parent=self.root)

    def swap_images(self):
        self.base, self.patch = self.patch, self.base
        self._status_key = None
        self.apply_language()

    def set_status(self, key, **values):
        self._status_key, self._status_values = key, values
        self.status_text.set(self.tr(key, **values))

    def render(self):
        if self._render_job is None:
            self._render_job = self.root.after_idle(self._render_now)

    def _render_now(self):
        self._render_job = None
        self.sync_controls()
        ready = bool(self.base and self.patch)
        if ready:
            self.drop_hint_label.pack_forget()
        elif not self.drop_hint_label.winfo_manager():
            self.drop_hint_label.pack(fill='x', pady=(10, 0))
        self.export_button.configure(state='normal' if ready else 'disabled')
        self.swap_button.configure(state='normal' if ready else 'disabled')
        for entry in (3, 4):
            self.file_menu.entryconfigure(entry, state='normal' if ready else 'disabled')
        self.canvas.delete('all')
        width, height = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        if not self.base:
            cx, cy = width / 2, height / 2 - 38
            self.canvas.create_rectangle(cx-40, cy-38, cx+16, cy+16, fill='#F8FAFC', outline='#BAC5D2', width=2)
            self.canvas.create_rectangle(cx-12, cy-12, cx+44, cy+42, fill='#DEE9F7', outline=COLORS['accent'], width=2)
            self.canvas.create_text(cx, cy+85, text=self.tr('empty_title'), fill=COLORS['text'], font=(self.font_family, 18, 'bold'))
            self.canvas.create_text(cx, cy+138, text=self.tr('empty_body'), fill=COLORS['secondary'],
                                    font=(self.font_family, 11), justify='center', width=max(100, width-40))
            self.selection_text.set('—')
            self.status_text.set(self.tr(self._status_key, **self._status_values) if self._status_key else self.tr('ready'))
            return
        result = self.compose(mode=self.view_mode.get())
        image_width, image_height = result.size
        scale = min(max(1, width-48) / image_width, max(1, height-48) / image_height)
        dw, dh = max(1, round(image_width*scale)), max(1, round(image_height*scale))
        ox, oy = (width-dw)/2, (height-dh)/2
        self.preview_metrics = (scale, ox, oy, dw, dh)
        self.canvas.create_rectangle(ox+4, oy+5, ox+dw+4, oy+dh+5, fill='#D3D8DF', outline='')
        for y in range(0, dh, 16):
            for x in range(0, dw, 16):
                fill = '#FFFFFF' if (x//16+y//16) % 2 == 0 else '#E9ECF0'
                self.canvas.create_rectangle(ox+x, oy+y, ox+min(dw,x+16), oy+min(dh,y+16), fill=fill, width=0)
        self.preview_photo = ImageTk.PhotoImage(result.resize((dw, dh), Image.Resampling.LANCZOS), master=self.root)
        self.canvas.create_image(ox, oy, anchor='nw', image=self.preview_photo)
        if self.show_guide.get():
            self.draw_canvas_guide()
        self.selection_text.set(self.tr('selection', width=round(self.rect[2]*image_width), height=round(self.rect[3]*image_height)))
        self.status_text.set(self.tr(self._status_key, **self._status_values) if self._status_key else
                             self.tr('dimensions', width=image_width, height=image_height) if ready else self.tr('need_patch'))

    def draw_canvas_guide(self):
        _, ox, oy, dw, dh = self.preview_metrics
        x, y, w, h = self.rect
        left, top, right, bottom = ox+x*dw, oy+y*dh, ox+(x+w)*dw, oy+(y+h)*dh
        self.canvas.create_rectangle(left, top, right, bottom, outline='white', width=4)
        self.canvas.create_rectangle(left, top, right, bottom, outline=COLORS['accent'], width=2, dash=(6, 3))
        for hx, hy in ((left, top), (right, top), (left, bottom), (right, bottom)):
            self.canvas.create_rectangle(hx-5, hy-5, hx+5, hy+5, fill='white', outline=COLORS['accent'], width=2)

    def save_as(self):
        if not (self.base and self.patch):
            messagebox.showinfo(self.tr('no_image'), self.tr('need_both'), parent=self.root)
            return
        path = filedialog.asksaveasfilename(parent=self.root, title=self.tr('export'), defaultextension='.png',
                                           initialfile=self.base.path.stem + '_composited.png',
                                           filetypes=((self.tr('png_files'), '*.png'),))
        if not path:
            return
        try:
            output = self.compose()
            self.save_image_replacing(output, Path(path))
            self.set_status('saved', name=Path(path).name)
        except Exception as exc:
            messagebox.showerror(self.tr('save_failed'), self.tr('save_error', error=exc), parent=self.root)

    def save_png(self):
        if not (self.base and self.patch):
            messagebox.showinfo(self.tr('no_image'), self.tr('need_both'), parent=self.root)
            return
        if not messagebox.askyesno(self.tr('confirm_title'), self.tr('confirm_body', path=self.base.path),
                                  parent=self.root, default='no', icon='warning'):
            return
        try:
            self.save_image_replacing(self.compose(), self.base.path)
            with Image.open(self.base.path) as image:
                self.base = LoadedImage(self.base.path, image.convert('RGBA'))
            self.set_status('replaced', name=self.base.path.name)
            self.render()
        except Exception as exc:
            messagebox.showerror(self.tr('save_failed'), self.tr('save_error', error=exc), parent=self.root)


def main():
    try:
        root = TkinterDnD.Tk() if TkinterDnD is not None else tk.Tk()
    except (tk.TclError, RuntimeError):
        root = tk.Tk()
    RegionCompositorApp(root)
    root.mainloop()
    return 0
