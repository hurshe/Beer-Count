"""
main.py — Beer Count v5
- 3-column layout: Stan kegów | Sprzedaż POS | Korekty
- Wynik dnia below
- Dark/Light theme toggle
- Warning when START=0 (diff not meaningful)
- Fixed history crash, fixed settings add/remove
"""
import tkinter as tk
from tkinter import messagebox, filedialog
import database as db
import export_excel as xl
import pos_import
from datetime import date, timedelta, datetime
import os
import sys


def resource_path(filename):
    """Resolve a path to a bundled resource (e.g. icon.ico) that works
    both when running main.py directly AND when frozen into a PyInstaller
    .exe (where bundled data files live under sys._MEIPASS instead of
    next to the script)."""
    if hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, filename)

# ════════════════════════════════════════════════════
#  THEMES — calm, low-contrast palettes
# ════════════════════════════════════════════════════
LIGHT = {
    "GOLD":     "#b85c38", "GOLD_LT": "#d68a64", "GOLD_BG": "#f7e6dd",
    "GREEN":    "#2a7a45", "GREEN_BG": "#eaf6ee",
    "RED":      "#b83232", "RED_BG":  "#fdeaea",
    "AMBER":    "#a06010", "AMBER_BG": "#fff4e0",
    "ORANGE":   "#c05000", "ORANGE_BG": "#fff0e0",
    "BG":       "#eef1f4", "SURFACE": "#ffffff",
    "BORDER":   "#dde3ea", "MUTED":   "#64748b", "TEXT": "#1e2530",
    "PREV_BG":  "#e7ebef",
    "INFO_BG":  "#e8f4fd", "INFO_FG": "#1a5276",
    "DELIVERY_BG": "#fdecd9",
}

DARK = {
    "GOLD":     "#f0b272", "GOLD_LT": "#ffc98c", "GOLD_BG": "#4a3420",
    "GREEN":    "#7ee0a8", "GREEN_BG": "#1a3326",
    "RED":      "#ff8a80", "RED_BG":  "#3d1f1f",
    "AMBER":    "#ffcf7a", "AMBER_BG": "#4a3a18",
    "ORANGE":   "#ff9d5c", "ORANGE_BG": "#3d2614",
    "BG":       "#15171a", "SURFACE": "#1f2228",
    "BORDER":   "#383d46", "MUTED":   "#aab0bb", "TEXT": "#f2f3f5",
    "PREV_BG":  "#2a2e36",
    "INFO_BG":  "#16263a", "INFO_FG": "#9cd0f5",
    "DELIVERY_BG": "#3d2e1a",
}

THEME = dict(LIGHT)
CURRENT_MODE = "light"


def C(key):
    return THEME[key]


DIFF_KEYS = {
    "ok":   ("GREEN",  "GREEN_BG"),
    "warn": ("AMBER",  "AMBER_BG"),
    "over": ("ORANGE", "ORANGE_BG"),
    "bad":  ("RED",    "RED_BG"),
}
DIFF_ICONS = {"ok":"✅","warn":"🟡","over":"🟠","bad":"🔴"}
DIFF_TEXTS = {
    "ok":   "Norma (±2L)",
    "warn": "+2/+5L — Sprawdź",
    "over": ">+5L — Sprzedaż poza POS?",
    "bad":  "<−5L — Straty/spille",
}


def diff_colors(status):
    fg_key, bg_key = DIFF_KEYS[status]
    return C(fg_key), C(bg_key)


class ScrollFrame(tk.Frame):
    def __init__(self, parent, bg=None, **kw):
        bg = bg or C("BG")
        super().__init__(parent, bg=bg, **kw)
        self._canvas = tk.Canvas(self, bg=bg, highlightthickness=0,
                                  borderwidth=0)
        self._sb = tk.Scrollbar(self, orient="vertical",
                                 command=self._canvas.yview)
        self._inner = tk.Frame(self._canvas, bg=bg)
        self._win = self._canvas.create_window(
            (0, 0), window=self._inner, anchor="nw")
        self._canvas.configure(yscrollcommand=self._sb.set)
        self._sb.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)
        self._inner.bind("<Configure>", self._on_inner)
        self._canvas.bind("<Configure>", self._on_canvas)
        self.bind_all("<MouseWheel>", self._on_wheel)

    def _on_inner(self, e):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas(self, e):
        self._canvas.itemconfig(self._win, width=e.width)

    def _on_wheel(self, e):
        self._canvas.yview_scroll(int(-1*(e.delta/120)), "units")

    def recolor(self, bg):
        self.configure(bg=bg)
        self._canvas.configure(bg=bg)
        self._inner.configure(bg=bg)

    @property
    def inner(self):
        return self._inner


def make_entry(parent, var, width=8, bg=None, font=("Calibri", 10)):
    bg = bg or C("SURFACE")
    e = tk.Entry(parent, textvariable=var, width=width,
                 font=font, bg=bg, fg=C("TEXT"),
                 relief="solid", bd=1,
                 insertbackground=C("TEXT"),
                 highlightthickness=1,
                 highlightcolor=C("GOLD"),
                 highlightbackground=C("BORDER"))
    return e


def make_btn(parent, text, cmd, bg=None, fg="white",
             font=("Segoe UI", 10, "bold"), padx=12, pady=6):
    bg = bg or C("GOLD")
    return tk.Button(parent, text=text, command=cmd,
                     bg=bg, fg=fg, font=font,
                     relief="flat", cursor="hand2",
                     padx=padx, pady=pady,
                     activebackground=C("GOLD_LT"),
                     activeforeground="white",
                     bd=0)


class App(tk.Tk):
    def _set_window_icon(self):
        """Try two independent strategies to set the taskbar/titlebar
        icon, since Tk's native iconbitmap() can silently fail on some
        Windows setups depending on exactly how the .ico was produced.
        PIL's iconphoto path is more forgiving because it decodes the
        image itself instead of relying on the native ICO loader."""
        ico_path = resource_path("icon.ico")
        if not os.path.exists(ico_path):
            return  # nothing bundled — keep default Tk icon, no error

        # Strategy 1: native .ico via iconbitmap (works most reliably
        # for the actual window/taskbar icon on Windows)
        try:
            self.iconbitmap(ico_path)
            return
        except Exception:
            pass

        # Strategy 2: decode via PIL and set as iconphoto. This covers
        # cases where the .ico file, while valid, isn't structured the
        # exact way Tk's native loader expects.
        try:
            from PIL import Image, ImageTk
            img = Image.open(ico_path)
            self._icon_photo = ImageTk.PhotoImage(img)  # keep a ref!
            self.iconphoto(True, self._icon_photo)
        except Exception:
            pass  # fall back to default Tk icon — cosmetic only

    def __init__(self):
        super().__init__()
        global CURRENT_MODE, THEME
        db.init_db()
        CURRENT_MODE = db.get_theme()
        THEME = dict(DARK if CURRENT_MODE == "dark" else LIGHT)

        self.title("🍺 Beer Count")
        self._set_window_icon()
        self.geometry("1200x780")
        self.minsize(900, 600)
        self.configure(bg=C("BG"))

        self._themed_scrollframes = []

        self._build_header()
        self._build_nav()
        self._tabs = {}
        self._tab_frames = {}
        for key in ("wizard","entry","history","report","settings"):
            sf = ScrollFrame(self, bg=C("BG"))
            self._tabs[key] = sf
            self._tab_frames[key] = sf.inner
            self._themed_scrollframes.append(sf)
        self._build_entry()
        self._build_history()
        self._build_report()
        self._build_settings()
        self._build_loading_overlay()
        if not db.get_months() and not db.load_day(str(date.today())):
            self._build_wizard()
            self._show("wizard")
        else:
            self.show_tab("entry")

    # ── Header ────────────────────────────────────
    def _build_header(self):
        h = tk.Frame(self, bg=C("SURFACE"), height=50)
        h.pack(fill="x"); h.pack_propagate(False)
        self._header_frame = h
        self._header_sep = tk.Frame(h, bg=C("GOLD_LT"), height=2)
        self._header_sep.pack(side="bottom", fill="x")
        self._title_lbl = tk.Label(h, text="🍺  Beer Count", font=("Segoe UI",14,"bold"),
                 fg=C("GOLD"), bg=C("SURFACE"))
        self._title_lbl.pack(side="left", padx=(16,4))
        self._subtitle_lbl = tk.Label(h, text="System kontroli piwa",
                 font=("Segoe UI",10), fg=C("MUTED"), bg=C("SURFACE"))
        self._subtitle_lbl.pack(side="left")

        # Theme toggle drawn on a small Canvas instead of relying on an
        # emoji glyph (🌙/☀️) — those often render as a tiny garbled box
        # on older Windows fonts (esp. Windows 7) instead of a proper
        # icon, since Tk text labels can't do colored emoji rendering.
        self._theme_canvas = tk.Canvas(
            h, width=28, height=28, bg=C("SURFACE"),
            highlightthickness=0, cursor="hand2")
        self._theme_canvas.pack(side="right", padx=(0,12), pady=8)
        self._theme_canvas.bind("<Button-1>", lambda e: self._toggle_theme())
        self._draw_theme_icon()

        self._date_lbl = tk.Label(h, text=date.today().strftime("%A, %d.%m.%Y"),
                 font=("Segoe UI",10), fg=C("MUTED"), bg=C("GOLD_BG"),
                 padx=10, pady=3, relief="flat")
        self._date_lbl.pack(side="right", padx=16, pady=12)

    def _draw_keg_icon(self, cv):
        """Draw a simple beer keg silhouette on the given Canvas — used
        in the About dialog so it matches the app's own branding
        instead of falling back to a generic emoji mug glyph."""
        cv.delete("all")
        w, h = 48, 48
        body_x0, body_y0 = 10, 8
        body_x1, body_y1 = 38, 42
        # Keg body
        cv.create_rectangle(body_x0, body_y0, body_x1, body_y1,
                             fill=C("GOLD"), outline=C("GOLD_LT"), width=1)
        # Top cap
        cv.create_rectangle(body_x0+8, body_y0-4, body_x1-8, body_y0,
                             fill=C("GOLD_LT"), outline="")
        # Horizontal ribs (the metal bands on a real keg)
        for ry in (16, 24, 32):
            cv.create_line(body_x0, ry, body_x1, ry,
                            fill=C("GOLD_BG"), width=2)
        # Side handle cutout
        cv.create_oval(body_x0-3, 18, body_x0+3, 26,
                        fill=C("GOLD_BG"), outline="")

    def _draw_theme_icon(self):
        """Draw a simple sun (light mode active -> click for dark) or
        moon (dark mode active -> click for light) icon as basic
        Canvas shapes, so it always looks crisp regardless of font/OS."""
        cv = self._theme_canvas
        cv.configure(bg=C("SURFACE"))
        cv.delete("all")
        cx, cy = 14, 14
        if CURRENT_MODE == "light":
            # Show a moon (what you'll switch TO)
            cv.create_oval(6, 5, 22, 21, fill=C("MUTED"), outline="")
            # Carve a crescent by overlaying a surface-colored circle
            cv.create_oval(10, 3, 26, 19, fill=C("SURFACE"), outline="")
        else:
            # Show a sun (what you'll switch TO)
            cv.create_oval(8, 8, 20, 20, fill=C("GOLD"), outline="")
            for ang in range(0, 360, 45):
                import math
                rad = math.radians(ang)
                x1 = cx + 9 * math.cos(rad)
                y1 = cy + 9 * math.sin(rad)
                x2 = cx + 13 * math.cos(rad)
                y2 = cy + 13 * math.sin(rad)
                cv.create_line(x1, y1, x2, y2, fill=C("GOLD"), width=2)

    def _toggle_theme(self):
        global CURRENT_MODE, THEME
        CURRENT_MODE = "dark" if CURRENT_MODE == "light" else "light"
        THEME = dict(DARK if CURRENT_MODE == "dark" else LIGHT)
        db.save_theme(CURRENT_MODE)
        self._apply_theme_everywhere()

    def _apply_theme_everywhere(self):
        self._start_loading_overlay()
        self.update_idletasks()

        self.configure(bg=C("BG"))

        self._header_frame.configure(bg=C("SURFACE"))
        self._header_sep.configure(bg=C("GOLD_LT"))
        self._title_lbl.configure(fg=C("GOLD"), bg=C("SURFACE"))
        self._subtitle_lbl.configure(fg=C("MUTED"), bg=C("SURFACE"))
        self._draw_theme_icon()
        self._date_lbl.configure(fg=C("MUTED"), bg=C("GOLD_BG"))

        self._nav_frame.configure(bg=C("SURFACE"))
        self._nav_sep.configure(bg=C("BORDER"))
        current = self._current_tab
        for k, b in self._nav_btns.items():
            if k == current:
                b.configure(bg=C("GOLD_BG"), fg=C("GOLD"))
            else:
                b.configure(bg=C("SURFACE"), fg=C("MUTED"))
            b.configure(activebackground=C("GOLD_BG"), activeforeground=C("GOLD"))

        for sf in self._themed_scrollframes:
            sf.recolor(C("BG"))

        self._overlay.configure(bg=C("BG"))
        self._overlay_canvas.configure(bg=C("BG"))
        self._overlay_label.configure(fg=C("MUTED"), bg=C("BG"))

        self._build_entry_inner_only()
        self._build_history()
        self._build_report()
        self._build_settings()
        loader = getattr(self, f"_load_{current}", None)
        if loader: loader()
        self._show(current)
        self.update_idletasks()

    def _build_entry_inner_only(self):
        f = self._tab_frames["entry"]
        for w in f.winfo_children():
            w.destroy()
        self._build_entry_body(f)

    # ── Nav ───────────────────────────────────────
    def _build_nav(self):
        self._nav_frame = tk.Frame(self, bg=C("SURFACE"), height=40)
        self._nav_frame.pack(fill="x"); self._nav_frame.pack_propagate(False)
        self._nav_sep = tk.Frame(self, bg=C("BORDER"), height=1)
        self._nav_sep.pack(fill="x")
        self._nav_btns = {}
        self._current_tab = "entry"
        for key, lbl in [("entry","📋  Wpis dnia"),("history","📅  Historia"),
                          ("report","📊  Raport"),("settings","⚙️  Ustawienia")]:
            b = tk.Button(self._nav_frame, text=lbl, font=("Segoe UI",10),
                          fg=C("MUTED"), bg=C("SURFACE"), relief="flat",
                          bd=0, padx=16, pady=10, cursor="hand2",
                          activebackground=C("GOLD_BG"), activeforeground=C("GOLD"),
                          command=lambda k=key: self.show_tab(k))
            b.pack(side="left")
            self._nav_btns[key] = b

    def _build_loading_overlay(self):
        """A small animated 'pouring beer' overlay shown briefly while
        a tab's content is being constructed, so the user sees a nice
        animation instead of a half-built blank frame for a split
        second on slower machines (e.g. Windows 7)."""
        self._overlay = tk.Frame(self, bg=C("BG"))
        self._overlay_canvas = tk.Canvas(
            self._overlay, width=220, height=220,
            bg=C("BG"), highlightthickness=0)
        self._overlay_canvas.pack(expand=True)
        self._overlay_label = tk.Label(
            self._overlay, text="Ładowanie…",
            font=("Segoe UI", 11), fg=C("MUTED"), bg=C("BG"))
        self._overlay_label.pack(pady=(0, 30))
        self._overlay_job = None
        self._overlay_frame_n = 0

    # Total animation length: TOTAL_FRAMES * _OVERLAY_FRAME_MS ms.
    # 12 frames * 40ms = 480ms — short enough not to feel like a delay,
    # long enough to read as an intentional, polished transition.
    _OVERLAY_TOTAL_FRAMES = 12
    _OVERLAY_FRAME_MS = 40

    def _draw_pour_frame(self, n):
        """Draw one frame of a single-pass glass-filling-with-foam
        animation using basic Canvas primitives (no external image
        assets needed, so it works identically in the frozen .exe).
        Returns True once this was the final frame of the cycle."""
        cv = self._overlay_canvas
        cv.delete("all")
        cv.configure(bg=C("BG"))

        glass_x0, glass_y0 = 70, 40
        glass_x1, glass_y1 = 150, 170
        cv.create_polygon(
            glass_x0+6, glass_y0, glass_x1-6, glass_y0,
            glass_x1, glass_y1, glass_x0, glass_y1,
            outline=C("BORDER"), width=2, fill="")

        total = self._OVERLAY_TOTAL_FRAMES
        n = min(n, total - 1)
        progress = n / (total - 1)  # 0.0 -> 1.0, single pass, no wraparound
        fill_h = int((glass_y1 - glass_y0 - 10) * min(progress * 1.15, 1.0))
        fill_top = glass_y1 - fill_h

        if fill_h > 4:
            cv.create_rectangle(
                glass_x0+3, fill_top, glass_x1-3, glass_y1-2,
                fill=C("GOLD_LT"), outline="")
            # Foam appears while pouring, settles to a thin head by the
            # final frame — mirrors a real pour finishing cleanly.
            foam_h = 10 if progress < 0.75 else max(3, int(10 * (1 - progress)) + 3)
            if foam_h > 0:
                import random
                rnd = random.Random(n)
                for i in range(5):
                    ox = glass_x0 + 8 + i * 16 + rnd.randint(-2, 2)
                    oy = fill_top - 4 + rnd.randint(-2, 2)
                    cv.create_oval(
                        ox-9, oy-7, ox+9, oy+7,
                        fill="#ffffff", outline="")

        # Droplet only while actively pouring, gone before the end
        if progress < 0.7:
            drop_y = glass_y0 - 25 + int((n % 4) * 6)
            cv.create_oval(106, drop_y, 114, drop_y+10,
                            fill=C("GOLD_LT"), outline="")

        return n >= total - 1

    def _start_loading_overlay(self):
        """Start the pour animation and let it run exactly one full
        fill cycle, then hide itself automatically. We don't tie the
        hide timing to how long content-building took — the animation
        always completes its own arc (empty -> full -> foam settles),
        so it never looks like it was cut off mid-pour, regardless of
        whether the underlying tab loads in 5ms or 150ms."""
        self._overlay.place(x=0, y=0, relwidth=1, relheight=1)
        self._overlay.lift()
        self._overlay_frame_n = 0
        self._animate_overlay()

    def _animate_overlay(self):
        finished = self._draw_pour_frame(self._overlay_frame_n)
        self._overlay_frame_n += 1
        if finished:
            self._overlay_job = None
            self._overlay.place_forget()
        else:
            self._overlay_job = self.after(self._OVERLAY_FRAME_MS,
                                            self._animate_overlay)

    def _stop_loading_overlay(self):
        """Kept for safety/compatibility — forces the overlay away
        immediately. Normal flow lets the animation finish itself via
        _animate_overlay's own 'finished' check instead of calling this."""
        if self._overlay_job:
            self.after_cancel(self._overlay_job)
            self._overlay_job = None
        self._overlay.place_forget()

    def show_tab(self, key):
        self._current_tab = key
        for k, b in self._nav_btns.items():
            if k == key:
                b.configure(bg=C("GOLD_BG"), fg=C("GOLD"),
                            font=("Segoe UI",10,"bold"))
            else:
                b.configure(bg=C("SURFACE"), fg=C("MUTED"),
                            font=("Segoe UI",10))
        # Start the pour animation — it will run its own short, fixed
        # cycle and hide itself when done. Content is built underneath
        # while it plays, so the tab is fully ready by the time the
        # animation finishes, regardless of build speed.
        self._start_loading_overlay()
        self.update_idletasks()
        loader = getattr(self, f"_load_{key}", None)
        if loader: loader()
        self._show(key)

    def _show(self, key):
        for k, sf in self._tabs.items():
            if k != key:
                sf.pack_forget()
        self._tabs[key].pack(fill="both", expand=True)

    # ── Card helper ───────────────────────────────
    def _card(self, parent, title, side=None, fill="both",
              expand=False, padx=6, pady=6):
        outer = tk.Frame(parent, bg=C("SURFACE"), bd=1, relief="solid",
                         highlightbackground=C("BORDER"),
                         highlightthickness=1)
        if side:
            outer.pack(side=side, fill=fill, expand=expand,
                       padx=padx, pady=pady)
        else:
            outer.pack(fill=fill, expand=expand, padx=padx, pady=pady)
        th = tk.Frame(outer, bg=C("GOLD_BG"))
        th.pack(fill="x")
        tk.Label(th, text=title, font=("Segoe UI",10,"bold"),
                 fg=C("GOLD"), bg=C("GOLD_BG"), anchor="w",
                 padx=10, pady=5).pack(fill="x")
        tk.Frame(outer, bg=C("BORDER"), height=1).pack(fill="x")
        body = tk.Frame(outer, bg=C("SURFACE"))
        body.pack(fill="both", expand=True, padx=8, pady=8)
        return body

    def _sec(self, parent, title):
        tk.Label(parent, text=title, font=("Segoe UI",10,"bold"),
                 fg=C("GOLD"), bg=C("BG"), anchor="w").pack(
            fill="x", padx=12, pady=(10,2))
        tk.Frame(parent, bg=C("BORDER"), height=1).pack(fill="x", padx=12)

    # ══════════════════════════════════════════════
    #  WIZARD
    # ══════════════════════════════════════════════
    def _build_wizard(self):
        f = self._tab_frames["wizard"]
        for w in f.winfo_children(): w.destroy()

        wf = tk.Frame(f, bg=C("GREEN_BG"), bd=1, relief="solid",
                      highlightbackground=C("GREEN"), highlightthickness=1)
        wf.pack(fill="x", padx=20, pady=(20,10))
        tk.Label(wf, text="🍺  Witaj w Beer Count!",
                 font=("Segoe UI",16,"bold"), fg=C("GOLD"), bg=C("GREEN_BG")).pack(pady=(14,4))
        tk.Label(wf,
                 text="Aby zacząć, podaj aktualny stan beczek.\n"
                      "To jest potrzebne tylko raz — potem każdy dzień\n"
                      "będzie się uzupełniał automatycznie z poprzedniego.\n\n"
                      "⚠️ Bez tego kroku Różnica w pierwszym dniu będzie\n"
                      "nieprawidłowa, bo aplikacja nie będzie znać stanu START.",
                 font=("Segoe UI",11), fg=C("MUTED"), bg=C("GREEN_BG"),
                 justify="center").pack(pady=(0,14))

        dc = self._card(f, "📅  Data stanu początkowego",
                        fill="x", padx=20, pady=(0,8))
        dfr = tk.Frame(dc, bg=C("SURFACE"))
        dfr.pack(anchor="w")
        tk.Label(dfr, text="Data:", font=("Segoe UI",10),
                 fg=C("MUTED"), bg=C("SURFACE")).pack(side="left", padx=(0,6))
        self._wiz_date = tk.StringVar(value=str(date.today()))
        tk.Entry(dfr, textvariable=self._wiz_date, width=14,
                 font=("Calibri",11), relief="solid", bd=1,
                 bg=C("SURFACE"), fg=C("TEXT"),
                 insertbackground=C("TEXT")).pack(side="left")
        tk.Label(dfr,
                 text="  Wpisz datę ostatniego liczenia beczek",
                 font=("Segoe UI",9), fg=C("MUTED"), bg=C("SURFACE")).pack(side="left")

        bc = self._card(f, "🛢  Aktualny stan beczek",
                        fill="x", padx=20, pady=(0,8))
        tk.Label(bc, text="Tara: 30L=11kg | 20L=7kg",
                 font=("Segoe UI",9), fg=C("MUTED"), bg=C("SURFACE")).pack(anchor="w", pady=(0,6))

        hf = tk.Frame(bc, bg=C("GOLD_BG"))
        hf.pack(fill="x")
        for col, w in [("Piwo",14),("Pełne (szt.)",10),
                       ("Otw.kg#1",10),("Otw.kg#2",10),
                       ("Otw.kg#3",10),("Razem (L)",10)]:
            tk.Label(hf, text=col, font=("Segoe UI",9,"bold"),
                     fg=C("GOLD"), bg=C("GOLD_BG"), width=w,
                     anchor="center").pack(side="left", padx=4, pady=4)

        self._wiz_rows = []
        for beer in db.get_beers():
            rf = tk.Frame(bc, bg=C("SURFACE"))
            rf.pack(fill="x", pady=2)
            tk.Label(rf, text=f"{beer['name']} ({beer['keg']}L)",
                     font=("Segoe UI",10,"bold"), fg=C("TEXT"),
                     bg=C("SURFACE"), width=14, anchor="w").pack(side="left", padx=4)
            rv = {"beer": beer}
            rv["full"] = tk.StringVar()
            make_entry(rf, rv["full"], width=10).pack(side="left", padx=4)
            rv["open"] = []
            for _ in range(3):
                ov = tk.StringVar()
                make_entry(rf, ov, width=10).pack(side="left", padx=4)
                rv["open"].append(ov)
            res = tk.Label(rf, text="0.00 L", font=("Calibri",10),
                           fg=C("GOLD"), bg=C("SURFACE"), width=10, anchor="center")
            res.pack(side="left", padx=4)
            rv["res"] = res

            def upd(rv=rv):
                tara = db.TARA.get(rv["beer"]["keg"], 7)
                full_l = int(rv["full"].get() or 0) * rv["beer"]["keg"]
                open_l = sum(
                    max(float(v.get()) - tara, 0)
                    for v in rv["open"]
                    if self._is_float(v.get()))
                rv["res"].configure(text=f"{full_l+open_l:.2f} L")

            rv["full"].trace_add("write", lambda *_, u=upd: u())
            for ov in rv["open"]:
                ov.trace_add("write", lambda *_, u=upd: u())
            self._wiz_rows.append(rv)

        bf = tk.Frame(f, bg=C("BG"))
        bf.pack(fill="x", padx=20, pady=12)
        make_btn(bf, "✅  Zapisz stan początkowy i zacznij!",
                 self._save_wizard).pack(side="left")
        make_btn(bf, "Pomiń →",
                 lambda: self.show_tab("entry"),
                 bg=C("SURFACE"), fg=C("MUTED"), font=("Segoe UI",10)).pack(
            side="left", padx=10)

    def _save_wizard(self):
        d = self._wiz_date.get().strip()
        if not d: self._error("Błąd","Wpisz datę!"); return
        try:
            datetime.strptime(d, "%Y-%m-%d")
        except ValueError:
            self._error("Błąd","Nieprawidłowy format daty. Użyj: RRRR-MM-DD")
            return
        sizes = db.get_sizes()
        beers = db.get_beers()
        data = {
            "kegs": [],
            "pos":  [{"name":b["name"],
                      "sizes":[{"liters":sz["liters"],"qty":"0"}
                                for sz in sizes]}
                     for b in beers],
            "corr": [{"name":b["name"],"spill":"0",
                      "void_":"0","open_bar":"0"} for b in beers],
        }
        for rv in self._wiz_rows:
            data["kegs"].append({
                "name":     rv["beer"]["name"],
                "keg":      rv["beer"]["keg"],
                "start_l":  0.0,
                "delivery": "0",
                "full_end": rv["full"].get() or "0",
                "open_end": [v.get() or None for v in rv["open"]],
            })
        db.save_day(d, data)
        self._info("Zapisano",
            f"Stan początkowy na {d} zapisany ✓\n\n"
            "Możesz teraz zacząć wpisywać codzienne dane!\n"
            "Jutro przy wpisie dnia START uzupełni się automatycznie.")
        self.show_tab("entry")

    def _is_float(self, s):
        try: float(s); return True
        except: return False

    # ══════════════════════════════════════════════
    #  ENTRY TAB — 3-column layout
    # ══════════════════════════════════════════════
    def _build_entry(self):
        f = self._tab_frames["entry"]
        self._build_entry_body(f)

    def _build_entry_body(self, f):
        banner = tk.Frame(f, bg=C("GREEN_BG"), bd=1, relief="solid",
                          highlightbackground=C("GREEN"),
                          highlightthickness=1)
        banner.pack(fill="x", padx=12, pady=(10,4))
        tk.Label(banner,
                 text="✅  START ładuje się automatycznie z poprzedniego dnia"
                      " — wpisujesz tylko END na koniec zmiany + POS.",
                 font=("Segoe UI",9), fg=C("GREEN"), bg=C("GREEN_BG"),
                 anchor="w", padx=10, pady=6).pack(fill="x")

        self._start_warning = tk.Frame(f, bg=C("AMBER_BG"), bd=1, relief="solid",
                                        highlightbackground=C("AMBER"),
                                        highlightthickness=1)
        self._start_warning_lbl = tk.Label(
            self._start_warning,
            text="⚠️  Brak danych z poprzedniego dnia dla niektórych piw (START=0)."
                 " Różnica dla nich NIE jest miarodajna — uzupełnij stan początkowy"
                 " w Kreatorze (zakładka Ustawienia).",
            font=("Segoe UI",9), fg=C("AMBER"), bg=C("AMBER_BG"),
            anchor="w", padx=10, pady=6, wraplength=1100, justify="left")
        self._start_warning_lbl.pack(fill="x")

        dfr = tk.Frame(f, bg=C("BG"))
        dfr.pack(fill="x", padx=12, pady=(0,6))
        tk.Label(dfr, text="Data:", font=("Segoe UI",10),
                 fg=C("MUTED"), bg=C("BG")).pack(side="left", padx=(0,6))
        self.ev_date = tk.StringVar(value=str(date.today()))
        tk.Entry(dfr, textvariable=self.ev_date, width=14,
                 font=("Calibri",11), relief="solid", bd=1,
                 bg=C("SURFACE"), fg=C("TEXT"),
                 insertbackground=C("TEXT")).pack(side="left")

        # These shift the CURRENTLY ENTERED date by one day each click,
        # so the user can keep paging forward/backward through many
        # days in a row — not just jump to "today ± 1" every time.
        make_btn(dfr, "◀ Poprzedni dzień",
                 lambda: self._shift_date(-1),
                 bg=C("GOLD_BG"), fg=C("GOLD"),
                 font=("Segoe UI",9), padx=8, pady=4).pack(
            side="left", padx=(5,0))
        make_btn(dfr, "Dziś",
                 lambda: self.ev_date.set(str(date.today())),
                 bg=C("GOLD_BG"), fg=C("GOLD"),
                 font=("Segoe UI",9), padx=8, pady=4).pack(
            side="left", padx=5)
        make_btn(dfr, "Następny dzień ▶",
                 lambda: self._shift_date(1),
                 bg=C("GOLD_BG"), fg=C("GOLD"),
                 font=("Segoe UI",9), padx=8, pady=4).pack(
            side="left", padx=(0,5))

        self.ev_date.trace_add("write", lambda *_: self._load_prev_starts())
        make_btn(dfr, "📂 Importuj POS (xlsx)",
                 self._import_pos_xlsx,
                 bg=C("INFO_BG"), fg=C("INFO_FG"),
                 font=("Segoe UI",9), padx=8, pady=4).pack(
            side="left", padx=(14,0))

        cols = tk.Frame(f, bg=C("BG"))
        cols.pack(fill="both", expand=True, padx=6)

        self._kegs_card = self._card(cols, "🛢  Stan kegów",
                                      side="left", fill="both",
                                      expand=True, padx=4, pady=4)
        tk.Label(self._kegs_card,
                 text="szare=START auto | żółte=dostawa | Tara: 30L=11kg, 20L=7kg",
                 font=("Segoe UI",8), fg=C("MUTED"),
                 bg=C("SURFACE")).pack(anchor="w", pady=(0,4))
        self._kegs_frame = tk.Frame(self._kegs_card, bg=C("SURFACE"))
        self._kegs_frame.pack(fill="both", expand=True)

        self._pos_card = self._card(cols, "💻  Sprzedaż POS",
                                     side="left", fill="both",
                                     expand=True, padx=4, pady=4)
        self._pos_total_lbl = tk.Label(self._pos_card,
                                        text="Łącznie: 0.00 L",
                                        font=("Segoe UI",9), fg=C("MUTED"),
                                        bg=C("SURFACE"), anchor="e")
        self._pos_total_lbl.pack(fill="x", pady=(0,4))
        self._pos_frame = tk.Frame(self._pos_card, bg=C("SURFACE"))
        self._pos_frame.pack(fill="both", expand=True)

        self._corr_card = self._card(cols, "⚠️  Korekty",
                                      side="left", fill="both",
                                      expand=True, padx=4, pady=4)
        self._corr_total_lbl = tk.Label(self._corr_card,
                                         text="Łącznie: 0.00 L",
                                         font=("Segoe UI",9), fg=C("MUTED"),
                                         bg=C("SURFACE"), anchor="e")
        self._corr_total_lbl.pack(fill="x", pady=(0,4))
        self._corr_frame = tk.Frame(self._corr_card, bg=C("SURFACE"))
        self._corr_frame.pack(fill="both", expand=True)

        self._sum_card = self._card(f, "📊  Wynik dnia",
                                     fill="x", padx=10, pady=(0,6))
        self._sum_frame = tk.Frame(self._sum_card, bg=C("SURFACE"))
        self._sum_frame.pack(fill="x")

        leg = tk.Frame(f, bg=C("BG"))
        leg.pack(fill="x", padx=12, pady=(0,6))
        for status in ("ok","warn","over","bad"):
            col, bgc = diff_colors(status)
            lf = tk.Frame(leg, bg=bgc, bd=1, relief="solid",
                          highlightbackground=col, highlightthickness=0)
            lf.pack(side="left", padx=(0,8))
            tk.Label(lf, text=f" {DIFF_ICONS[status]} {DIFF_TEXTS[status]} ",
                     font=("Segoe UI",9), fg=col, bg=bgc).pack(padx=4, pady=2)

        bf = tk.Frame(f, bg=C("BG"))
        bf.pack(fill="x", padx=12, pady=(0,14))
        make_btn(bf, "💾  Zapisz dzień",
                 self._save_day).pack(side="left", padx=(0,8))
        make_btn(bf, "🔄  Przelicz", self._recalc,
                 bg=C("GOLD_BG"), fg=C("GOLD"),
                 font=("Segoe UI",10)).pack(side="left", padx=(0,8))
        make_btn(bf, "🗑  Wyczyść", self._clear,
                 bg=C("SURFACE"), fg=C("MUTED"),
                 font=("Segoe UI",10)).pack(side="left")

        self._kw = []; self._pw = []; self._cw = []

    def _load_entry(self):
        beers = db.get_beers()
        sizes = db.get_sizes()
        self._all_entries = []
        self._build_keg_inputs(beers)
        self._build_pos_inputs(beers, sizes)
        self._build_corr_inputs(beers)
        self._init_summary_rows(beers)
        self._bind_enter_navigation()
        self._load_prev_starts()
        self._recalc()

    def _bind_enter_navigation(self):
        entries = self._all_entries
        for i, e in enumerate(entries):
            next_e = entries[i+1] if i+1 < len(entries) else entries[0]
            e.bind("<Return>", lambda ev, n=next_e: n.focus_set())
            e.bind("<KP_Enter>", lambda ev, n=next_e: n.focus_set())

    def _build_keg_inputs(self, beers):
        f = self._kegs_frame
        for w in f.winfo_children(): w.destroy()
        self._kw = []
        self._all_entries = []

        hdrs = ["Piwo","START","DOSTAWA","PEŁNE","kg#1","kg#2","kg#3","END(L)"]
        for ci, h in enumerate(hdrs):
            tk.Label(f, text=h, font=("Segoe UI",8,"bold"),
                     fg=C("GOLD"), bg=C("GOLD_BG"), anchor="center").grid(
                row=0, column=ci, sticky="ew", padx=2, pady=3, ipadx=4)
        for ci in range(len(hdrs)):
            f.grid_columnconfigure(ci, weight=1)

        for ri, beer in enumerate(beers, 1):
            rv = {"beer": beer, "_start_l": 0.0}
            tk.Label(f, text=f"{beer['name']} ({beer['keg']}L)",
                     font=("Segoe UI",9,"bold"), fg=C("TEXT"),
                     bg=C("SURFACE"), anchor="w").grid(
                row=ri, column=0, sticky="ew", padx=2, pady=2)
            rv["start_lbl"] = tk.Label(f, text="—",
                                        font=("Calibri",9), fg=C("GOLD"),
                                        bg=C("PREV_BG"), anchor="center")
            rv["start_lbl"].grid(row=ri, column=1, sticky="ew", padx=2, pady=2)

            rv["delivery"] = tk.StringVar()
            e_del = make_entry(f, rv["delivery"], bg=C("DELIVERY_BG"))
            e_del.grid(row=ri, column=2, sticky="ew", padx=2, pady=2)
            e_del.bind("<KeyRelease>", lambda _: self._recalc())
            self._all_entries.append(e_del)

            rv["full_end"] = tk.StringVar()
            e_full = make_entry(f, rv["full_end"])
            e_full.grid(row=ri, column=3, sticky="ew", padx=2, pady=2)
            e_full.bind("<KeyRelease>", lambda _: self._recalc())
            self._all_entries.append(e_full)

            rv["open_end"] = []
            for j in range(3):
                ov = tk.StringVar()
                oe = make_entry(f, ov)
                oe.grid(row=ri, column=4+j, sticky="ew", padx=2, pady=2)
                oe.bind("<KeyRelease>", lambda _: self._recalc())
                self._all_entries.append(oe)
                rv["open_end"].append(ov)

            rv["end_lbl"] = tk.Label(f, text="—",
                                      font=("Calibri",9,"bold"),
                                      fg=C("GOLD"), bg=C("SURFACE"), anchor="center")
            rv["end_lbl"].grid(row=ri, column=7, sticky="ew", padx=2, pady=2)
            self._kw.append(rv)

    def _build_pos_inputs(self, beers, sizes):
        f = self._pos_frame
        for w in f.winfo_children(): w.destroy()
        self._pw = []
        tk.Label(f, text="Piwo", font=("Segoe UI",8,"bold"),
                 fg=C("GOLD"), bg=C("GOLD_BG"), anchor="w").grid(
            row=0, column=0, sticky="ew", padx=2, pady=3, ipadx=4)
        for si, sz in enumerate(sizes):
            tk.Label(f, text=sz["label"], font=("Segoe UI",8,"bold"),
                     fg=C("GOLD"), bg=C("GOLD_BG"), anchor="center").grid(
                row=0, column=si+1, sticky="ew", padx=2, pady=3, ipadx=4)
        tk.Label(f, text="Razem", font=("Segoe UI",8,"bold"),
                 fg=C("GOLD"), bg=C("GOLD_BG"), anchor="center").grid(
            row=0, column=len(sizes)+1, sticky="ew", padx=2, pady=3, ipadx=4)
        for ci in range(len(sizes)+2):
            f.grid_columnconfigure(ci, weight=1)
        for ri, beer in enumerate(beers, 1):
            tk.Label(f, text=beer["name"], font=("Segoe UI",9,"bold"),
                     fg=C("TEXT"), bg=C("SURFACE"), anchor="w").grid(
                row=ri, column=0, sticky="ew", padx=2, pady=2)
            svars = []
            for si, sz in enumerate(sizes):
                sv = tk.StringVar()
                e = make_entry(f, sv)
                e.grid(row=ri, column=si+1, sticky="ew", padx=2, pady=2)
                e.bind("<KeyRelease>", lambda _: self._recalc())
                self._all_entries.append(e)
                svars.append({"var": sv, "liters": sz["liters"], "label": sz["label"]})
            lbl = tk.Label(f, text="0.00L", font=("Calibri",9,"bold"),
                           fg=C("GOLD"), bg=C("SURFACE"), anchor="center")
            lbl.grid(row=ri, column=len(sizes)+1, sticky="ew", padx=2, pady=2)
            self._pw.append({"name": beer["name"], "sizes": svars, "lbl": lbl})

    def _build_corr_inputs(self, beers):
        f = self._corr_frame
        for w in f.winfo_children(): w.destroy()
        self._cw = []
        for ci, h in enumerate(["Piwo","Spill","Void","Open Bar","Razem"]):
            tk.Label(f, text=h, font=("Segoe UI",8,"bold"),
                     fg=C("GOLD"), bg=C("GOLD_BG"), anchor="center").grid(
                row=0, column=ci, sticky="ew", padx=2, pady=3, ipadx=4)
        for ci in range(5):
            f.grid_columnconfigure(ci, weight=1)
        for ri, beer in enumerate(beers, 1):
            tk.Label(f, text=beer["name"], font=("Segoe UI",9,"bold"),
                     fg=C("TEXT"), bg=C("SURFACE"), anchor="w").grid(
                row=ri, column=0, sticky="ew", padx=2, pady=2)
            cv = {"name": beer["name"]}
            for ci, field in enumerate(["spill","void_","open_bar"], 1):
                v = tk.StringVar()
                e = make_entry(f, v)
                e.grid(row=ri, column=ci, sticky="ew", padx=2, pady=2)
                e.bind("<KeyRelease>", lambda _: self._recalc())
                self._all_entries.append(e)
                cv[field] = v
            lbl = tk.Label(f, text="−0.00", font=("Calibri",9,"bold"),
                           fg=C("RED"), bg=C("SURFACE"), anchor="center")
            lbl.grid(row=ri, column=4, sticky="ew", padx=2, pady=2)
            cv["lbl"] = lbl
            self._cw.append(cv)

    def _shift_date(self, days):
        """Move the currently entered date by `days` (can be called
        repeatedly to page through many days forward or backward,
        unlike a fixed 'yesterday/today' jump anchored to the real
        current date)."""
        current = self.ev_date.get().strip()
        try:
            base = datetime.strptime(current, "%Y-%m-%d").date()
        except ValueError:
            # Invalid/empty field — fall back to today so the button
            # still does something sensible instead of erroring out.
            base = date.today()
        self.ev_date.set(str(base + timedelta(days=days)))

    def _load_prev_starts(self, *_):
        d = self.ev_date.get().strip()
        if not d: return
        prev = db.get_prev_day(d)
        prev_kegs = {}
        if prev:
            prev_kegs = {k["name"]: db.keg_end_liters(k)
                         for k in prev.get("kegs", [])}
        for rw in self._kw:
            name = rw["beer"]["name"]
            val  = prev_kegs.get(name, 0.0)
            rw["_start_l"] = val
            rw["start_lbl"].configure(text=f"{val:.1f}L")
        if hasattr(self, "_pw"):
            self._recalc()

    def _collect(self):
        data = {"kegs": [], "pos": [], "corr": []}
        for rw in self._kw:
            beer = rw["beer"]
            data["kegs"].append({
                "name":     beer["name"],
                "keg":      beer["keg"],
                "start_l":  rw.get("_start_l", 0.0),
                "delivery": rw["delivery"].get() or "0",
                "full_end": rw["full_end"].get() or "0",
                "open_end": [v.get() or None for v in rw["open_end"]],
            })
        for pw in self._pw:
            data["pos"].append({
                "name":  pw["name"],
                "sizes": [{"liters": sv["liters"],
                           "qty": sv["var"].get() or "0"}
                          for sv in pw["sizes"]],
            })
        for cw in self._cw:
            data["corr"].append({
                "name":     cw["name"],
                "spill":    cw["spill"].get() or "0",
                "void_":    cw["void_"].get() or "0",
                "open_bar": cw["open_bar"].get() or "0",
            })
        return data

    def _recalc(self, *_):
        try: data = self._collect()
        except: return

        any_missing_start = any(
            not db.has_valid_start(keg) for keg in data["kegs"]
        )
        if any_missing_start:
            if not self._start_warning.winfo_ismapped():
                self._start_warning.pack(fill="x", padx=12, pady=(0,6),
                                          after=self._start_warning.master.winfo_children()[0])
        else:
            if self._start_warning.winfo_ismapped():
                self._start_warning.pack_forget()

        for i, rw in enumerate(self._kw):
            end_l = db.keg_end_liters(data["kegs"][i])
            rw["end_lbl"].configure(text=f"{end_l:.1f}L")
        pos_grand = 0
        for i, pw in enumerate(self._pw):
            t = db.pos_liters(data["pos"][i]); pos_grand += t
            pw["lbl"].configure(text=f"{t:.2f}L")
        self._pos_total_lbl.configure(text=f"Łącznie: {pos_grand:.2f} L")
        corr_grand = 0
        for i, cw in enumerate(self._cw):
            t = db.corr_liters(data["corr"][i]); corr_grand += t
            cw["lbl"].configure(text=f"−{t:.2f}")
        self._corr_total_lbl.configure(text=f"Łącznie: {corr_grand:.2f} L")
        self._render_summary(data)

    def _init_summary_rows(self, beers):
        f = self._sum_frame
        for w in f.winfo_children(): w.destroy()
        self._sum_rows = []

        for beer in beers:
            row = tk.Frame(f, bg=C("SURFACE"), bd=1, relief="solid",
                           highlightbackground=C("BORDER"), highlightthickness=0)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=beer["name"],
                     font=("Segoe UI",10,"bold"), fg=C("TEXT"),
                     bg=C("SURFACE"), width=10, anchor="w").pack(
                side="left", padx=8, pady=4)
            lbls = {}
            for key, txt in [("start","START: 0L"),("del","Del: +0L"),
                              ("end","END: 0L"),("pos","POS: 0L"),("kor","Kor: 0L")]:
                l = tk.Label(row, text=txt, font=("Segoe UI",9),
                             fg=C("MUTED"), bg=C("SURFACE"))
                l.pack(side="left", padx=8)
                lbls[key] = l
            chip_f = tk.Frame(row, bg=C("GREEN_BG"))
            chip_f.pack(side="right", padx=10, pady=4)
            chip_l = tk.Label(chip_f, text=" ✅ 0.00L ",
                              font=("Segoe UI",10,"bold"),
                              fg=C("GREEN"), bg=C("GREEN_BG"))
            chip_l.pack(padx=4, pady=2)
            lbls["chip_f"] = chip_f
            lbls["chip_l"] = chip_l
            lbls["row"] = row
            self._sum_rows.append(lbls)

        tot_f = tk.Frame(f, bg=C("GOLD_BG"), bd=1, relief="solid",
                         highlightbackground=C("GOLD_LT"), highlightthickness=0)
        tot_f.pack(fill="x", pady=(4,0))
        tk.Label(tot_f, text="ŁĄCZNIE", font=("Segoe UI",11,"bold"),
                 fg=C("GOLD"), bg=C("GOLD_BG")).pack(side="left", padx=12, pady=6)
        self._sum_pos_lbl = tk.Label(tot_f, text="POS: 0L",
                                      font=("Segoe UI",10), fg=C("MUTED"),
                                      bg=C("GOLD_BG"))
        self._sum_pos_lbl.pack(side="left", padx=10)
        self._tot_chip_f = tk.Frame(tot_f, bg=C("GREEN_BG"))
        self._tot_chip_f.pack(side="right", padx=12, pady=6)
        self._tot_chip_l = tk.Label(self._tot_chip_f, text=" ✅ 0.00L ",
                                     font=("Segoe UI",12,"bold"),
                                     fg=C("GREEN"), bg=C("GREEN_BG"))
        self._tot_chip_l.pack(padx=6, pady=3)

    def _render_summary(self, data):
        if not hasattr(self, "_sum_rows") or len(self._sum_rows) != len(data["kegs"]):
            self._init_summary_rows(db.get_beers())
        tot_diff = 0
        for i, keg in enumerate(data["kegs"]):
            if i >= len(self._sum_rows): break
            pe   = data["pos"][i]  if i < len(data["pos"])  else {"sizes":[]}
            co   = data["corr"][i] if i < len(data["corr"]) else {}
            diff = db.calc_diff(keg, pe, co)
            s    = db.diff_status(diff)
            col, bgc = diff_colors(s)
            tot_diff += diff
            lbls = self._sum_rows[i]
            start_missing = not db.has_valid_start(keg)
            start_txt = f"START: {db.keg_start_liters(keg):.1f}L"
            if start_missing:
                start_txt += " ⚠️"
            lbls["start"].configure(text=start_txt)
            lbls["del"].configure(text=f"Del: +{db.keg_delivery_liters(keg):.0f}L")
            lbls["end"].configure(text=f"END: {db.keg_end_liters(keg):.1f}L")
            lbls["pos"].configure(text=f"POS: {db.pos_liters(pe):.1f}L")
            lbls["kor"].configure(text=f"Kor: −{db.corr_liters(co):.1f}L")
            lbls["chip_f"].configure(bg=bgc)
            lbls["chip_l"].configure(
                text=f" {DIFF_ICONS[s]} {diff:+.2f}L ",
                fg=col, bg=bgc)
        ts = db.diff_status(tot_diff)
        tcol, tbg = diff_colors(ts)
        self._sum_pos_lbl.configure(
            text=f"POS: {sum(db.pos_liters(p) for p in data['pos']):.1f}L")
        self._tot_chip_f.configure(bg=tbg)
        self._tot_chip_l.configure(
            text=f" {DIFF_ICONS[ts]} {tot_diff:+.2f}L ",
            fg=tcol, bg=tbg)

    def _import_pos_xlsx(self):
        filepath = filedialog.askopenfilename(
            title="Wybierz plik XLSX z IzzyRest",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")])
        if not filepath:
            return
        try:
            all_dates = pos_import.get_available_dates(filepath)
        except ValueError as e:
            self._error("Błąd importu", str(e))
            return
        if not all_dates:
            self._warning("Brak danych", "Plik nie zawiera danych sprzedaży.")
            return
        current_date = self.ev_date.get().strip()
        if current_date in all_dates:
            chosen_date = current_date
        else:
            chosen_date = self._pick_date_dialog(all_dates, current_date)
            if not chosen_date:
                return
        try:
            sales = pos_import.get_sales_for_date(filepath, chosen_date)
        except ValueError as e:
            self._error("Błąd", str(e))
            return
        if not sales:
            self._warning("Brak danych",
                f"Brak sprzedaży w pliku dla daty {chosen_date}.")
            return
        self.ev_date.set(chosen_date)
        filled = 0
        not_found = []
        for pw in self._pw:
            beer_name = pw["name"]
            beer_sales = sales.get(beer_name, {})
            for sv in pw["sizes"]:
                size_label = sv.get("label") or ""
                qty = beer_sales.get(size_label, 0)
                if qty == 0:
                    for key, val in beer_sales.items():
                        if key.replace("L","").replace("l","").strip() == \
                           size_label.replace("L","").replace("l","").strip():
                            qty = val
                            break
                if qty > 0:
                    sv["var"].set(str(qty))
                    filled += 1
            if not beer_sales and beer_name in ["ŻYWIEC","HEINEKEN","MURPHYS","BIAŁE","IPA","BIAŁE 0%"]:
                not_found.append(beer_name)
        self._recalc()
        msg = f"✅ Zaimportowano sprzedaż z dnia {chosen_date}\n{filled} pól uzupełnionych."
        if not_found:
            msg += f"\n\nBrak danych dla: {', '.join(not_found)}"
        self._info("Import POS", msg)

    def _pick_date_dialog(self, available_dates: list, current_date: str):
        win = tk.Toplevel(self)
        win.title("Wybierz datę importu")
        win.geometry("340x420")
        win.configure(bg=C("BG"))
        win.grab_set()
        win.resizable(False, False)

        tk.Label(win, text="Dostępne daty w pliku:",
                 font=("Segoe UI",10,"bold"), fg=C("GOLD"), bg=C("BG")).pack(
            pady=(14,6))
        tk.Label(win,
                 text=f"Data w aplikacji: {current_date}",
                 font=("Segoe UI",9), fg=C("MUTED"), bg=C("BG")).pack(pady=(0,8))

        frame = tk.Frame(win, bg=C("BG"))
        frame.pack(fill="both", expand=True, padx=14, pady=(0,8))
        sb = tk.Scrollbar(frame)
        sb.pack(side="right", fill="y")
        lb = tk.Listbox(frame, yscrollcommand=sb.set,
                        font=("Segoe UI",10), selectmode="single",
                        bg=C("SURFACE"), fg=C("TEXT"), selectbackground=C("GOLD"),
                        selectforeground="white", relief="solid", bd=1)
        lb.pack(side="left", fill="both", expand=True)
        sb.config(command=lb.yview)

        for d in reversed(available_dates):
            lb.insert("end", d)

        for i, d in enumerate(reversed(available_dates)):
            if d <= current_date:
                lb.selection_set(i)
                lb.see(i)
                break

        result = {"date": None}

        def confirm():
            sel = lb.curselection()
            if sel:
                result["date"] = lb.get(sel[0])
            win.destroy()

        def cancel():
            win.destroy()

        btn_f = tk.Frame(win, bg=C("BG"))
        btn_f.pack(pady=8)
        make_btn(btn_f, "✅ Importuj", confirm,
                 font=("Segoe UI",10), padx=12, pady=5).pack(
            side="left", padx=(0,8))
        make_btn(btn_f, "Anuluj", cancel,
                 bg=C("SURFACE"), fg=C("MUTED"),
                 font=("Segoe UI",10), padx=10, pady=5).pack(side="left")

        win.wait_window()
        return result["date"]

    def _save_day(self):
        d = self.ev_date.get().strip()
        if not d: self._error("Błąd","Wpisz datę!"); return
        data = self._collect()
        db.save_day(d, data)
        self._info("Zapisano", f"Dzień {d} zapisany ✓")

    def _clear(self):
        if not self._confirm("Wyczyścić?","Wyczyścić wszystkie pola?"):
            return
        for rw in self._kw:
            rw["delivery"].set(""); rw["full_end"].set("")
            for v in rw["open_end"]: v.set("")
        for pw in self._pw:
            for sv in pw["sizes"]: sv["var"].set("")
        for cw in self._cw:
            for fld in ["spill","void_","open_bar"]: cw[fld].set("")
        self._recalc()

    # ══════════════════════════════════════════════
    #  HISTORY
    # ══════════════════════════════════════════════
    def _build_history(self):
        f = self._tab_frames["history"]
        for w in f.winfo_children(): w.destroy()
        top = tk.Frame(f, bg=C("BG"))
        top.pack(fill="x", padx=16, pady=(14,8))
        tk.Label(top, text="Miesiąc:", font=("Segoe UI",10),
                 fg=C("MUTED"), bg=C("BG")).pack(side="left", padx=(0,8))
        self._hist_month = tk.StringVar()
        self._hist_cb = tk.OptionMenu(top, self._hist_month, "(brak)")
        self._hist_cb.configure(font=("Segoe UI",10), bg=C("SURFACE"), fg=C("TEXT"),
                                 relief="solid", bd=1, width=25)
        self._hist_cb.pack(side="left")
        self._hist_month.trace_add("write",
                                    lambda *_: self._render_history())
        self._hist_list = tk.Frame(f, bg=C("BG"))
        self._hist_list.pack(fill="both", expand=True, padx=16)

    def _load_history(self):
        months = db.get_months()
        menu = self._hist_cb["menu"]
        menu.delete(0, "end")
        if months:
            labels = [self._fmt_month(m)+f"  [{m}]" for m in months]
            for lbl in labels:
                menu.add_command(label=lbl,
                                  command=lambda l=lbl:
                                  self._hist_month.set(l))
            cur = self._hist_month.get()
            if not cur or cur not in labels:
                self._hist_month.set(labels[0])
            else:
                self._render_history()
        else:
            menu.add_command(label="(brak)")
            self._hist_month.set("(brak)")
            self._render_history()

    def _render_history(self):
        for w in self._hist_list.winfo_children(): w.destroy()
        val = self._hist_month.get()
        if not val or "(brak)" in val: return
        month = val.split("[")[-1].rstrip("]").strip()
        entries = db.get_days_for_month(month)
        if not entries:
            tk.Label(self._hist_list, text="Brak wpisów w tym miesiącu.",
                     font=("Segoe UI",11), fg=C("MUTED"),
                     bg=C("BG")).pack(pady=30)
            return
        for entry_date, data in reversed(entries):
            self._hist_card(entry_date, data)

    def _hist_card(self, entry_date, data):
        beers    = data.get("kegs", [])
        tot_diff = 0
        for i, k in enumerate(beers):
            pe = data["pos"][i]  if i < len(data.get("pos",[])) else {"sizes":[]}
            co = data["corr"][i] if i < len(data.get("corr",[])) else {}
            try: tot_diff += db.calc_diff(k, pe, co)
            except: pass
        tot_pos = sum(db.pos_liters(p) for p in data.get("pos", []))
        tot_del = sum(int(k.get("delivery",0) or 0) for k in beers)
        status  = db.diff_status(tot_diff)
        col, bgc = diff_colors(status)

        card = tk.Frame(self._hist_list, bg=C("SURFACE"), bd=1,
                        relief="solid",
                        highlightbackground=C("BORDER"),
                        highlightthickness=1)
        card.pack(fill="x", pady=4)

        hdr = tk.Frame(card, bg=C("PREV_BG"))
        hdr.pack(fill="x")
        tk.Label(hdr, text=self._fmt_date(entry_date),
                 font=("Segoe UI",10,"bold"), fg=C("TEXT"),
                 bg=C("PREV_BG")).pack(side="left", padx=12, pady=6)
        if tot_del:
            tk.Label(hdr, text=f"🚚 Dostawa: {tot_del} keg",
                     font=("Segoe UI",9), fg=C("GOLD"),
                     bg=C("GOLD_BG")).pack(side="left", padx=6)
        tk.Label(hdr, text=f"POS: {tot_pos:.1f}L",
                 font=("Segoe UI",9), fg=C("MUTED"),
                 bg=C("PREV_BG")).pack(side="right", padx=12)
        cf = tk.Frame(hdr, bg=bgc)
        cf.pack(side="right", padx=6, pady=6)
        tk.Label(cf, text=f" {DIFF_ICONS[status]} {tot_diff:+.2f}L ",
                 font=("Segoe UI",10,"bold"), fg=col,
                 bg=bgc).pack(padx=4, pady=2)

        body = tk.Frame(card, bg=C("SURFACE"))
        body.pack(fill="x", padx=12, pady=8)

        for i, keg in enumerate(beers):
            pe = data["pos"][i]  if i < len(data.get("pos",[])) else {"sizes":[]}
            co = data["corr"][i] if i < len(data.get("corr",[])) else {}
            try:
                diff = db.calc_diff(keg, pe, co)
            except:
                diff = 0.0
            s = db.diff_status(diff); c, _ = diff_colors(s)
            br = tk.Frame(body, bg=C("SURFACE"))
            br.pack(fill="x", pady=1)
            tk.Label(br, text=keg["name"], font=("Segoe UI",9),
                     fg=C("TEXT"), bg=C("SURFACE"), width=10,
                     anchor="w").pack(side="left")
            tk.Label(br, text=f"{DIFF_ICONS[s]} {diff:+.2f}L",
                     font=("Calibri",9,"bold"), fg=c,
                     bg=C("SURFACE"), width=12,
                     anchor="e").pack(side="right")

        btn_f = tk.Frame(body, bg=C("SURFACE"))
        btn_f.pack(fill="x", pady=(6,0))

        det_frame = tk.Frame(body, bg=C("SURFACE"))
        state = {"open": False}

        def toggle_det(df=det_frame, s=state, e=entry_date, d=data):
            if s["open"]:
                df.pack_forget(); s["open"] = False
                det_btn.configure(text="🔍 Pokaż szczegóły")
            else:
                for w in df.winfo_children(): w.destroy()
                try:
                    self._build_det_table(df, d)
                except Exception as ex:
                    tk.Label(df, text=f"Błąd: {ex}",
                             fg=C("RED"), bg=C("SURFACE"),
                             font=("Segoe UI",9)).pack()
                df.pack(fill="x"); s["open"] = True
                det_btn.configure(text="🔍 Ukryj szczegóły")

        det_btn = make_btn(btn_f, "🔍 Pokaż szczegóły", toggle_det,
                           bg=C("GOLD_BG"), fg=C("GOLD"),
                           font=("Segoe UI",9), padx=8, pady=3)
        det_btn.pack(side="left", padx=(0,8))
        make_btn(btn_f, "✏️ Edytuj",
                 lambda e=entry_date, d=data: self._open_edit(e, d),
                 font=("Segoe UI",9), padx=8, pady=3).pack(side="left", padx=(0,8))

        def delete_day(e=entry_date, c=card):
            if self._confirm("Usuń wpis",
                f"Na pewno usunąć wpis z dnia {e}?\nTej operacji nie można cofnąć."):
                db.delete_day(e)
                c.destroy()

        make_btn(btn_f, "🗑 Usuń dzień", delete_day,
                 bg=C("RED_BG"), fg=C("RED"),
                 font=("Segoe UI",9), padx=8, pady=3).pack(side="left")

    def _build_det_table(self, parent, data):
        sizes = db.get_sizes()
        hf = tk.Frame(parent, bg=C("GOLD_BG"))
        hf.pack(fill="x", pady=(6,0))
        cols = (["Piwo","START","Del","Pełne","kg#1","kg#2","kg#3","END(L)"] +
                [sz["label"] for sz in sizes] +
                ["Spill","Void","OpenBar","RÓŻNICA"])
        ws   = ([10,6,4,5,6,6,6,6] +
                [5]*len(sizes) + [5,5,7,9])
        for h, w in zip(cols, ws):
            tk.Label(hf, text=h, font=("Segoe UI",8,"bold"),
                     fg=C("GOLD"), bg=C("GOLD_BG"), width=w,
                     anchor="center").pack(side="left", padx=1, pady=3)

        for ri, keg in enumerate(data.get("kegs",[])):
            pe   = data["pos"][ri]  if ri<len(data.get("pos",[])) else {"sizes":[]}
            co   = data["corr"][ri] if ri<len(data.get("corr",[])) else {}
            try:
                diff = db.calc_diff(keg, pe, co)
            except:
                diff = 0.0
            s = db.diff_status(diff); dcol, dbg = diff_colors(s)
            ow = keg.get("open_end") or []

            # Match saved POS quantities to CURRENT size columns by
            # liters value (not by position), so old entries saved
            # before a size was inserted/reordered still line up
            # under the correct header.
            saved_sizes = pe.get("sizes", [])
            qty_by_liters = {}
            for sz in saved_sizes:
                try:
                    lit_key = round(float(sz.get("liters", 0)), 3)
                except (ValueError, TypeError):
                    continue
                qty_by_liters[lit_key] = sz.get("qty", 0) or 0
            pos_qtys = []
            for cur_sz in sizes:
                lit_key = round(float(cur_sz.get("liters", 0)), 3)
                pos_qtys.append(str(qty_by_liters.get(lit_key, 0)))

            row_vals = ([keg["name"],
                         f"{db.keg_start_liters(keg):.1f}",
                         str(keg.get("delivery",0)),
                         str(keg.get("full_end",0)),
                         str(ow[0] if len(ow)>0 and ow[0] else "—"),
                         str(ow[1] if len(ow)>1 and ow[1] else "—"),
                         str(ow[2] if len(ow)>2 and ow[2] else "—"),
                         f"{db.keg_end_liters(keg):.2f}"] +
                        pos_qtys +
                        [str(co.get("spill",0) or 0),
                         str(co.get("void_",0) or 0),
                         str(co.get("open_bar",0) or 0),
                         f"{DIFF_ICONS[s]} {diff:+.2f}L"])
            rf = tk.Frame(parent, bg=C("SURFACE"))
            rf.pack(fill="x")
            for ci, (v, w) in enumerate(zip(row_vals, ws)):
                is_diff = ci == len(row_vals)-1
                tk.Label(rf, text=v,
                         font=("Segoe UI", 8, "bold" if is_diff else "normal"),
                         fg=(dcol if is_diff else C("TEXT")),
                         bg=(dbg if is_diff else C("SURFACE")),
                         width=w, anchor="center",
                         relief="flat").pack(side="left", padx=1, pady=1)

    def _open_edit(self, entry_date, data):
        self.show_tab("entry")
        self.ev_date.set(entry_date)
        beers = db.get_beers(); sizes = db.get_sizes()
        self._build_keg_inputs(beers)
        self._build_pos_inputs(beers, sizes)
        self._build_corr_inputs(beers)
        for i, rw in enumerate(self._kw):
            if i >= len(data.get("kegs",[])): continue
            keg = data["kegs"][i]
            rw["_start_l"] = float(keg.get("start_l",0) or 0)
            rw["start_lbl"].configure(text=f"{rw['_start_l']:.1f}L")
            del_val = keg.get("delivery","")
            rw["delivery"].set("" if not del_val or del_val == "0" else str(del_val))
            full_val = keg.get("full_end","")
            rw["full_end"].set("" if not full_val or full_val == "0" else str(full_val))
            ow = keg.get("open_end") or [None,None,None]
            for j, v in enumerate(rw["open_end"]):
                v.set(str(ow[j]) if j<len(ow) and ow[j] else "")
        for i, pw in enumerate(self._pw):
            if i >= len(data.get("pos",[])): continue
            pe = data["pos"][i]
            for j, sv in enumerate(pw["sizes"]):
                if j < len(pe.get("sizes",[])):
                    qty = pe["sizes"][j].get("qty","")
                    sv["var"].set("" if not qty or qty == "0" else str(qty))
        for i, cw in enumerate(self._cw):
            if i >= len(data.get("corr",[])): continue
            co = data["corr"][i]
            for field in ["spill","void_","open_bar"]:
                val = co.get(field,"")
                cw[field].set("" if not val or val == "0" else str(val))
        self.update_idletasks()
        self._recalc()

    # ══════════════════════════════════════════════
    #  REPORT
    # ══════════════════════════════════════════════
    def _build_report(self):
        f = self._tab_frames["report"]
        for w in f.winfo_children(): w.destroy()
        top = tk.Frame(f, bg=C("BG"))
        top.pack(fill="x", padx=16, pady=(14,8))
        tk.Label(top, text="Miesiąc:", font=("Segoe UI",10),
                 fg=C("MUTED"), bg=C("BG")).pack(side="left", padx=(0,8))
        self._rep_month = tk.StringVar()
        self._rep_cb = tk.OptionMenu(top, self._rep_month, "(brak)")
        self._rep_cb.configure(font=("Segoe UI",10), bg=C("SURFACE"), fg=C("TEXT"),
                                relief="solid", bd=1, width=25)
        self._rep_cb.pack(side="left", padx=(0,12))
        self._rep_month.trace_add("write",
                                   lambda *_: self._render_report())
        make_btn(top, "📥 Export Excel (miesiąc)",
                 self._export_month,
                 font=("Segoe UI",9), padx=8, pady=4).pack(
            side="left", padx=(0,8))
        make_btn(top, "📥 Export Excel (rok)",
                 self._export_year,
                 bg=C("GOLD_BG"), fg=C("GOLD"),
                 font=("Segoe UI",9), padx=8, pady=4).pack(side="left")
        self._rep_body = tk.Frame(f, bg=C("BG"))
        self._rep_body.pack(fill="both", expand=True, padx=16)

    def _load_report(self):
        months = db.get_months()
        menu = self._rep_cb["menu"]
        menu.delete(0,"end")
        if months:
            labels = [self._fmt_month(m)+f"  [{m}]" for m in months]
            for lbl in labels:
                menu.add_command(label=lbl,
                                  command=lambda l=lbl:
                                  self._rep_month.set(l))
            cur = self._rep_month.get()
            if not cur or cur not in labels:
                self._rep_month.set(labels[0])
            else:
                self._render_report()
        else:
            menu.add_command(label="(brak)")
            self._rep_month.set("(brak)")

    def _render_report(self):
        for w in self._rep_body.winfo_children(): w.destroy()
        val = self._rep_month.get()
        if not val or "(brak)" in val: return
        month   = val.split("[")[-1].rstrip("]").strip()
        entries = db.get_days_for_month(month)
        if not entries:
            tk.Label(self._rep_body, text="Brak wpisów.",
                     font=("Segoe UI",11), fg=C("MUTED"),
                     bg=C("BG")).pack(pady=30)
            return
        tot_days = len(entries)
        tot_del  = sum(sum(int(k.get("delivery",0) or 0)
                           for k in d.get("kegs",[])) for _,d in entries)
        tot_pos  = sum(sum(db.pos_liters(p)
                           for p in d.get("pos",[])) for _,d in entries)
        tot_corr = sum(sum(db.corr_liters(c)
                           for c in d.get("corr",[])) for _,d in entries)
        tot_diff = sum(
            db.calc_diff(k,
                         d["pos"][i]  if i<len(d.get("pos",[])) else {"sizes":[]},
                         d["corr"][i] if i<len(d.get("corr",[])) else {})
            for _,d in entries
            for i,k in enumerate(d.get("kegs",[])))

        kf = tk.Frame(self._rep_body, bg=C("BG"))
        kf.pack(fill="x", pady=(0,12))
        ts = db.diff_status(tot_diff); tcol, tbg = diff_colors(ts)
        for lbl, val2, col in [
            ("Dni",    str(tot_days),           C("GOLD")),
            ("Dostawa",f"{tot_del} keg",         C("GOLD")),
            ("POS",    f"{tot_pos:.1f}L",        C("TEXT")),
            ("Korekty",f"{tot_corr:.1f}L",       C("TEXT")),
            ("Różnica",f"{DIFF_ICONS[ts]} {tot_diff:+.1f}L", tcol),
        ]:
            kpi = tk.Frame(kf, bg=C("SURFACE"), bd=1, relief="solid",
                           highlightbackground=C("BORDER"), highlightthickness=0)
            kpi.pack(side="left", padx=(0,8))
            tk.Label(kpi, text=lbl, font=("Segoe UI",9),
                     fg=C("MUTED"), bg=C("SURFACE")).pack(padx=12, pady=(8,2))
            tk.Label(kpi, text=val2, font=("Segoe UI",18,"bold"),
                     fg=col, bg=C("SURFACE")).pack(padx=12, pady=(0,8))

        self._sec(self._rep_body, "Wynik per piwo")
        beers_cfg = db.get_beers()
        agg = {b["name"]:{"diff":0,"pos":0,"del":0,"days":0}
               for b in beers_cfg}
        for _, data in entries:
            for i, keg in enumerate(data.get("kegs",[])):
                n  = keg["name"]
                if n not in agg:
                    agg[n]={"diff":0,"pos":0,"del":0,"days":0}
                pe = data["pos"][i]  if i<len(data.get("pos",[])) else {"sizes":[]}
                co = data["corr"][i] if i<len(data.get("corr",[])) else {}
                agg[n]["diff"] += db.calc_diff(keg, pe, co)
                agg[n]["pos"]  += db.pos_liters(pe)
                agg[n]["del"]  += int(keg.get("delivery",0) or 0)
                agg[n]["days"] += 1
        for n, a in agg.items():
            diff = round(a["diff"],2); s=db.diff_status(diff)
            col, bgc = diff_colors(s)
            row = tk.Frame(self._rep_body, bg=C("SURFACE"), bd=1,
                           relief="solid",
                           highlightbackground=C("BORDER"),
                           highlightthickness=0)
            row.pack(fill="x", pady=2, padx=4)
            tk.Label(row, text=n, font=("Segoe UI",10,"bold"),
                     fg=C("TEXT"), bg=C("SURFACE"), width=12,
                     anchor="w").pack(side="left", padx=10, pady=6)
            tk.Label(row,
                     text=f"POS: {a['pos']:.1f}L | "
                          f"Del: {a['del']} keg | {a['days']} dni",
                     font=("Segoe UI",9), fg=C("MUTED"),
                     bg=C("SURFACE")).pack(side="left", padx=8)
            cf = tk.Frame(row, bg=bgc)
            cf.pack(side="right", padx=10, pady=6)
            tk.Label(cf, text=f" {DIFF_ICONS[s]} {diff:+.1f}L ",
                     font=("Segoe UI",10,"bold"), fg=col,
                     bg=bgc).pack(padx=4, pady=2)

        self._sec(self._rep_body, "Trend dzienny")
        for entry_date, data in entries:
            d_diff = sum(
                db.calc_diff(k,
                             data["pos"][i]  if i<len(data.get("pos",[])) else {"sizes":[]},
                             data["corr"][i] if i<len(data.get("corr",[])) else {})
                for i,k in enumerate(data.get("kegs",[])))
            s = db.diff_status(d_diff); col,_ = diff_colors(s)
            tr = tk.Frame(self._rep_body, bg=C("BG"))
            tr.pack(fill="x", pady=1, padx=4)
            tk.Label(tr, text=self._fmt_date(entry_date),
                     font=("Segoe UI",9), fg=C("MUTED"), bg=C("BG"),
                     width=14, anchor="w").pack(side="left")
            tk.Label(tr, text=f"{DIFF_ICONS[s]} {d_diff:+.2f}L",
                     font=("Calibri",9,"bold"), fg=col,
                     bg=C("BG"), width=12, anchor="e").pack(side="right")

    def _export_month(self):
        val = self._rep_month.get()
        if not val or "(brak)" in val:
            self._warning("Brak","Wybierz miesiąc"); return
        month = val.split("[")[-1].rstrip("]").strip()
        p = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel","*.xlsx")],
            initialfile=f"BeerCount_{month}.xlsx")
        if not p: return
        if xl.export_month(month, p):
            self._info("OK", f"Zapisano:\n{p}")
        else:
            self._error("Błąd","Brak danych")

    def _export_year(self):
        val  = self._rep_month.get()
        year = val.split("[")[-1][:4] if "[" in val else str(date.today().year)
        p = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel","*.xlsx")],
            initialfile=f"BeerCount_{year}_roczny.xlsx")
        if not p: return
        if xl.export_year(year, p):
            self._info("OK", f"Zapisano:\n{p}")
        else:
            self._error("Błąd",f"Brak danych dla roku {year}")

    # ══════════════════════════════════════════════
    #  SETTINGS
    # ══════════════════════════════════════════════
    def _build_settings(self):
        f = self._tab_frames["settings"]
        for w in f.winfo_children(): w.destroy()

        c1 = self._card(f, "🍺  Piwa na krane", fill="x", padx=16, pady=(14,6))
        self._set_beers_f = tk.Frame(c1, bg=C("SURFACE"))
        self._set_beers_f.pack(fill="x")
        make_btn(c1, "+ Dodaj piwo", self._add_beer,
                 bg=C("GOLD_BG"), fg=C("GOLD"),
                 font=("Segoe UI",9), padx=8, pady=3).pack(
            anchor="w", pady=(6,0))

        c2 = self._card(f, "🥃  Rozmiary porcji POS",
                        fill="x", padx=16, pady=(0,6))
        self._set_sizes_f = tk.Frame(c2, bg=C("SURFACE"))
        self._set_sizes_f.pack(fill="x")
        make_btn(c2, "+ Dodaj rozmiar", self._add_size,
                 bg=C("GOLD_BG"), fg=C("GOLD"),
                 font=("Segoe UI",9), padx=8, pady=3).pack(
            anchor="w", pady=(6,0))

        bf = tk.Frame(f, bg=C("BG"))
        bf.pack(fill="x", padx=16, pady=8)
        make_btn(bf, "💾  Zapisz ustawienia",
                 self._save_settings).pack(side="left", padx=(0,10))
        make_btn(bf, "🔄  Kreator pierwszego uruchomienia",
                 self._rerun_wizard,
                 bg=C("SURFACE"), fg=C("MUTED"),
                 font=("Segoe UI",9), padx=8, pady=4).pack(side="left", padx=(0,10))
        make_btn(bf, "ℹ️  O programie",
                 self._show_about,
                 bg=C("SURFACE"), fg=C("MUTED"),
                 font=("Segoe UI",9), padx=8, pady=4).pack(side="left")

        self._beer_data = []
        self._size_data = []

    def _load_settings(self):
        self._render_beer_settings(db.get_beers())
        self._render_size_settings(db.get_sizes())

    def _render_beer_settings(self, beers):
        for w in self._set_beers_f.winfo_children(): w.destroy()
        self._beer_data = []
        for b in beers:
            self._add_beer_row(b["name"], str(b["keg"]))

    def _render_size_settings(self, sizes):
        for w in self._set_sizes_f.winfo_children(): w.destroy()
        self._size_data = []
        for s in sizes:
            self._add_size_row(s["label"], str(s["liters"]))

    def _add_beer_row(self, name="NOWE", keg="20"):
        rf = tk.Frame(self._set_beers_f, bg=C("SURFACE"))
        rf.pack(fill="x", pady=2)
        nv = tk.StringVar(value=name)
        kv = tk.StringVar(value=keg)
        tk.Entry(rf, textvariable=nv, width=20, font=("Segoe UI",10),
                 relief="solid", bd=1, bg=C("SURFACE"), fg=C("TEXT"),
                 insertbackground=C("TEXT")).pack(side="left", padx=(0,6))
        om = tk.OptionMenu(rf, kv, "20", "30", "50")
        om.configure(font=("Segoe UI",10), bg=C("SURFACE"), fg=C("TEXT"),
                     relief="solid", bd=1, width=5)
        om.pack(side="left", padx=(0,4))
        tk.Label(rf, text="L keg", font=("Segoe UI",9),
                 fg=C("MUTED"), bg=C("SURFACE")).pack(side="left", padx=(0,8))
        row_data = (nv, kv, rf)
        self._beer_data.append(row_data)
        def remove(rd=row_data):
            rd[2].destroy()
            if rd in self._beer_data:
                self._beer_data.remove(rd)
        tk.Button(rf, text="✕", font=("Segoe UI",10),
                  fg=C("RED"), bg=C("SURFACE"), relief="flat",
                  bd=0, cursor="hand2", padx=4,
                  command=remove).pack(side="left")

    def _add_size_row(self, label="0.5L", liters="0.5"):
        rf = tk.Frame(self._set_sizes_f, bg=C("SURFACE"))
        rf.pack(fill="x", pady=2)
        lv  = tk.StringVar(value=label)
        lv2 = tk.StringVar(value=liters)
        tk.Entry(rf, textvariable=lv, width=8, font=("Calibri",10),
                 relief="solid", bd=1, bg=C("SURFACE"), fg=C("TEXT"),
                 insertbackground=C("TEXT")).pack(side="left", padx=(0,6))
        tk.Entry(rf, textvariable=lv2, width=8, font=("Calibri",10),
                 relief="solid", bd=1, bg=C("SURFACE"), fg=C("TEXT"),
                 insertbackground=C("TEXT")).pack(side="left", padx=(0,4))
        tk.Label(rf, text="L/szt.", font=("Segoe UI",9),
                 fg=C("MUTED"), bg=C("SURFACE")).pack(side="left", padx=(0,8))
        row_data = (lv, lv2, rf)
        self._size_data.append(row_data)
        def remove(rd=row_data):
            rd[2].destroy()
            if rd in self._size_data:
                self._size_data.remove(rd)
        tk.Button(rf, text="✕", font=("Segoe UI",10),
                  fg=C("RED"), bg=C("SURFACE"), relief="flat",
                  bd=0, cursor="hand2", padx=4,
                  command=remove).pack(side="left")

    def _add_beer(self):
        self._add_beer_row()

    def _add_size(self):
        self._add_size_row()

    def _save_settings(self):
        beers = []
        for nv, kv, rf in self._beer_data:
            if not rf.winfo_exists(): continue
            name = nv.get().strip().upper()
            try: keg = int(kv.get())
            except: keg = 20
            if name: beers.append({"name":name,"keg":keg})
        sizes = []
        for lv, lv2, rf in self._size_data:
            if not rf.winfo_exists(): continue
            lbl = lv.get().strip()
            try: lit = float(lv2.get())
            except: lit = 0.5
            if lbl: sizes.append({"label":lbl,"liters":lit})
        db.save_beers(beers); db.save_sizes(sizes)
        self._info("Zapisano","Ustawienia zapisane ✓")

    # ══════════════════════════════════════════════
    #  THEMED DIALOGS — replace raw tkinter.messagebox
    #  so popups match the app's own light/dark theme
    #  instead of using the plain OS dialog style.
    # ══════════════════════════════════════════════
    _DIALOG_KIND_STYLE = {
        "info":    ("ℹ️", "GOLD",  "GOLD_BG"),
        "success": ("✅", "GREEN", "GREEN_BG"),
        "warning": ("⚠️", "AMBER", "AMBER_BG"),
        "error":   ("❌", "RED",   "RED_BG"),
        "confirm": ("❓", "GOLD",  "GOLD_BG"),
    }

    def _themed_dialog(self, kind, title, message, buttons=("OK",)):
        """Show a small modal dialog styled like the rest of the app.
        Returns the text of the button the user clicked (or None if
        the window was closed via the X button)."""
        icon, fg_key, bg_key = self._DIALOG_KIND_STYLE.get(
            kind, self._DIALOG_KIND_STYLE["info"])

        win = tk.Toplevel(self)
        win.title(title)
        win.configure(bg=C("SURFACE"))
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        top = tk.Frame(win, bg=C(bg_key))
        top.pack(fill="x")
        row = tk.Frame(top, bg=C(bg_key))
        row.pack(padx=20, pady=16, anchor="w")
        tk.Label(row, text=icon, font=("Segoe UI", 18),
                 bg=C(bg_key)).pack(side="left", padx=(0, 12))
        tk.Label(row, text=title, font=("Segoe UI", 12, "bold"),
                 fg=C(fg_key), bg=C(bg_key)).pack(side="left")

        tk.Frame(win, bg=C("BORDER"), height=1).pack(fill="x")

        body = tk.Frame(win, bg=C("SURFACE"))
        body.pack(fill="both", expand=True, padx=22, pady=18)
        tk.Label(body, text=message, font=("Segoe UI", 10),
                 fg=C("TEXT"), bg=C("SURFACE"), justify="left",
                 wraplength=360).pack(anchor="w")

        result = {"value": None}

        def choose(val):
            result["value"] = val
            win.destroy()

        btn_row = tk.Frame(win, bg=C("SURFACE"))
        btn_row.pack(fill="x", padx=22, pady=(0, 18))
        # The last label in `buttons` is the primary/confirm action
        # (e.g. "Tak", "OK") and should render rightmost and styled
        # as the main action — that's also where users expect it.
        for label in reversed(buttons):
            is_primary = (label == buttons[-1])
            make_btn(
                btn_row, label, lambda l=label: choose(l),
                bg=(C("GOLD") if is_primary else C("SURFACE")),
                fg=("white" if is_primary else C("MUTED")),
                font=("Segoe UI", 10, "bold" if is_primary else "normal"),
                padx=18, pady=6
            ).pack(side="right", padx=(8, 0))

        win.update_idletasks()
        w, h = win.winfo_width(), win.winfo_height()
        x = self.winfo_x() + (self.winfo_width() - w) // 2
        y = self.winfo_y() + (self.winfo_height() - h) // 2
        win.geometry(f"+{x}+{y}")

        win.wait_window()
        return result["value"]

    def _info(self, title, message):
        self._themed_dialog("success", title, message, buttons=("OK",))

    def _error(self, title, message):
        self._themed_dialog("error", title, message, buttons=("OK",))

    def _warning(self, title, message):
        self._themed_dialog("warning", title, message, buttons=("OK",))

    def _confirm(self, title, message):
        """Returns True if the user confirmed, False otherwise."""
        choice = self._themed_dialog(
            "confirm", title, message, buttons=("Anuluj", "Tak"))
        return choice == "Tak"

    def _show_about(self):
        win = tk.Toplevel(self)
        win.title("O programie")
        win.geometry("420x340")
        win.configure(bg=C("SURFACE"))
        win.resizable(False, False)
        win.grab_set()

        top = tk.Frame(win, bg=C("GOLD_BG"), height=80)
        top.pack(fill="x"); top.pack_propagate(False)

        # Canvas-drawn keg icon instead of an emoji glyph — consistent
        # with the app's own icon and avoids emoji-rendering issues.
        icon_cv = tk.Canvas(top, width=48, height=48, bg=C("GOLD_BG"),
                             highlightthickness=0)
        icon_cv.pack(side="left", padx=20)
        self._draw_keg_icon(icon_cv)

        title_f = tk.Frame(top, bg=C("GOLD_BG"))
        title_f.pack(side="left", pady=14)
        tk.Label(title_f, text="Beer Count",
                 font=("Segoe UI",16,"bold"),
                 fg=C("GOLD"), bg=C("GOLD_BG")).pack(anchor="w")
        tk.Label(title_f, text="System kontroli piwa",
                 font=("Segoe UI",9), fg=C("MUTED"), bg=C("GOLD_BG")).pack(anchor="w")

        tk.Frame(win, bg=C("BORDER"), height=1).pack(fill="x")

        body = tk.Frame(win, bg=C("SURFACE"))
        body.pack(fill="both", expand=True, padx=30, pady=20)

        # Grid layout guarantees the label column and value column line
        # up cleanly regardless of text length, unlike pack() where an
        # empty label row could end up narrower than "Wersja:" etc.
        info = [
            ("Wersja:", "1.0.0  (2026)"),
            ("Autor:",  "Robert Khurshudian"),
            ("",        ""),
            ("Prawa:",  "© 2026 Robert Khurshudian"),
            ("",        "Wszelkie prawa zastrzeżone."),
        ]
        for r, (label, value) in enumerate(info):
            tk.Label(body, text=label,
                     font=("Segoe UI",10,"bold"),
                     fg=C("GOLD"), bg=C("SURFACE"),
                     anchor="w").grid(row=r, column=0, sticky="nw", pady=2)
            tk.Label(body, text=value,
                     font=("Segoe UI",10),
                     fg=C("TEXT"), bg=C("SURFACE"),
                     anchor="w").grid(row=r, column=1, sticky="nw",
                                       padx=(10,0), pady=2)
        body.grid_columnconfigure(1, weight=1)

        tk.Label(body, text="Powered by HTS",
                 font=("Segoe UI",9,"italic"),
                 fg=C("GOLD"), bg=C("SURFACE")).grid(
            row=len(info), column=0, columnspan=2, sticky="w", pady=(12,0))

        tk.Frame(win, bg=C("BORDER"), height=1).pack(fill="x")
        btn_f = tk.Frame(win, bg=C("SURFACE"))
        btn_f.pack(pady=12)
        make_btn(btn_f, "Zamknij", win.destroy,
                 bg=C("GOLD"), font=("Segoe UI",10),
                 padx=20, pady=5).pack()

    def _rerun_wizard(self):
        self._build_wizard()
        self._show("wizard")

    # ── Helpers ───────────────────────────────────
    def _fmt_date(self, d):
        try:
            dt = datetime.strptime(d, "%Y-%m-%d")
            days = ["Pon","Wt","Śr","Czw","Pt","Sob","Ndz"]
            return f"{days[dt.weekday()]} {dt.day:02d}.{dt.month:02d}.{dt.year}"
        except: return d

    def _fmt_month(self, m):
        MO = {"01":"Styczeń","02":"Luty","03":"Marzec","04":"Kwiecień",
              "05":"Maj","06":"Czerwiec","07":"Lipiec","08":"Sierpień",
              "09":"Wrzesień","10":"Październik","11":"Listopad","12":"Grudzień"}
        y, mo = m.split("-")
        return f"{MO.get(mo,mo)} {y}"


if __name__ == "__main__":
    app = App()
    app.mainloop()
