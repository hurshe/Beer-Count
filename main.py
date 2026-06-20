"""
main.py — Beer Count HRC Warsaw v4
- 3-column layout: Stan kegów | Sprzedaż POS | Korekty
- Wynik dnia below
- No stretch fields
- Fixed history crash
- Fixed settings add/remove
"""
import tkinter as tk
from tkinter import messagebox, filedialog
import database as db
import export_excel as xl
from datetime import date, timedelta, datetime

GOLD    = "#9a6f1e"; GOLD_LT  = "#c9a84c"; GOLD_BG  = "#fdf3df"
GREEN   = "#2a7a45"; GREEN_BG = "#eaf6ee"
RED     = "#b83232"; RED_BG   = "#fdeaea"
AMBER   = "#a06010"; AMBER_BG = "#fff4e0"
ORANGE  = "#c05000"; ORANGE_BG= "#fff0e0"
BG      = "#f5f2ec"; SURFACE  = "#ffffff"
BORDER  = "#ddd8ce"; MUTED    = "#7a7265"; TEXT = "#1a1a1a"
PREV_BG = "#f0ede6"

DIFF_COLORS = {
    "ok":   (GREEN,  GREEN_BG),
    "warn": (AMBER,  AMBER_BG),
    "over": (ORANGE, ORANGE_BG),
    "bad":  (RED,    RED_BG),
}
DIFF_ICONS = {"ok":"✅","warn":"🟡","over":"🟠","bad":"🔴"}
DIFF_TEXTS = {
    "ok":   "Norma (±2L)",
    "warn": "+2/+5L — Sprawdź",
    "over": ">+5L — Sprzedaż poza POS?",
    "bad":  "<−5L — Straty/spille",
}


class ScrollFrame(tk.Frame):
    """A plain tk Frame with vertical scrollbar — instant, no animation."""
    def __init__(self, parent, bg=BG, **kw):
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

    @property
    def inner(self):
        return self._inner


def make_label(parent, text, font=None, color=TEXT, bg=BG, anchor="w", **kw):
    return tk.Label(parent, text=text,
                    font=font or ("Segoe UI", 10),
                    fg=color, bg=bg, anchor=anchor, **kw)


def make_entry(parent, var, width=8, bg=SURFACE, font=("Consolas", 10)):
    e = tk.Entry(parent, textvariable=var, width=width,
                 font=font, bg=bg, fg=TEXT,
                 relief="solid", bd=1,
                 highlightthickness=1,
                 highlightcolor=GOLD,
                 highlightbackground=BORDER)
    return e


def make_btn(parent, text, cmd, bg=GOLD, fg="white",
             font=("Segoe UI", 10, "bold"), padx=12, pady=6):
    return tk.Button(parent, text=text, command=cmd,
                     bg=bg, fg=fg, font=font,
                     relief="flat", cursor="hand2",
                     padx=padx, pady=pady,
                     activebackground=GOLD_LT,
                     activeforeground="white",
                     bd=0)


def chip_label(parent, text, col, bg):
    f = tk.Frame(parent, bg=bg, bd=0)
    tk.Label(f, text=text, fg=col, bg=bg,
             font=("Segoe UI", 10, "bold"),
             padx=8, pady=2).pack()
    return f


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        db.init_db()
        self.title("🍺 Beer Count — Hard Rock Cafe Warsaw")
        self.geometry("1200x780")
        self.minsize(900, 600)
        self.configure(bg=BG)
        self._build_header()
        self._build_nav()
        self._tabs = {}
        self._tab_frames = {}
        for key in ("wizard","entry","history","report","settings"):
            sf = ScrollFrame(self, bg=BG)
            self._tabs[key] = sf
            self._tab_frames[key] = sf.inner
        self._build_entry()
        self._build_history()
        self._build_report()
        self._build_settings()
        # First run
        if not db.get_months() and not db.load_day(str(date.today())):
            self._build_wizard()
            self._show("wizard")
        else:
            self.show_tab("entry")

    # ── Header ────────────────────────────────────
    def _build_header(self):
        h = tk.Frame(self, bg=SURFACE, height=50)
        h.pack(fill="x"); h.pack_propagate(False)
        tk.Frame(h, bg=GOLD_LT, height=2).pack(side="bottom", fill="x")
        tk.Label(h, text="🍺  Beer Count", font=("Segoe UI",14,"bold"),
                 fg=GOLD, bg=SURFACE).pack(side="left", padx=(16,4))
        tk.Label(h, text="Hard Rock Cafe Warsaw",
                 font=("Segoe UI",10), fg=MUTED, bg=SURFACE).pack(side="left")
        tk.Label(h, text=date.today().strftime("%A, %d.%m.%Y"),
                 font=("Segoe UI",10), fg=MUTED, bg=GOLD_BG,
                 padx=10, pady=3, relief="flat").pack(side="right", padx=16, pady=12)

    # ── Nav ───────────────────────────────────────
    def _build_nav(self):
        nav = tk.Frame(self, bg=SURFACE, height=40)
        nav.pack(fill="x"); nav.pack_propagate(False)
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")
        self._nav_btns = {}
        for key, lbl in [("entry","📋  Wpis dnia"),("history","📅  Historia"),
                          ("report","📊  Raport"),("settings","⚙️  Ustawienia")]:
            b = tk.Button(nav, text=lbl, font=("Segoe UI",10),
                          fg=MUTED, bg=SURFACE, relief="flat",
                          bd=0, padx=16, pady=10, cursor="hand2",
                          activebackground=GOLD_BG, activeforeground=GOLD,
                          command=lambda k=key: self.show_tab(k))
            b.pack(side="left")
            self._nav_btns[key] = b

    def show_tab(self, key):
        for k, b in self._nav_btns.items():
            if k == key:
                b.configure(bg=GOLD_BG, fg=GOLD,
                            font=("Segoe UI",10,"bold"))
            else:
                b.configure(bg=SURFACE, fg=MUTED,
                            font=("Segoe UI",10))
        self._show(key)
        loader = getattr(self, f"_load_{key}", None)
        if loader: loader()

    def _show(self, key):
        for sf in self._tabs.values():
            sf.pack_forget()
        self._tabs[key].pack(fill="both", expand=True)

    # ── Card helper ───────────────────────────────
    def _card(self, parent, title, side=None, fill="both",
              expand=False, padx=6, pady=6):
        outer = tk.Frame(parent, bg=SURFACE, bd=1, relief="solid",
                         highlightbackground=BORDER,
                         highlightthickness=1)
        if side:
            outer.pack(side=side, fill=fill, expand=expand,
                       padx=padx, pady=pady)
        else:
            outer.pack(fill=fill, expand=expand, padx=padx, pady=pady)
        # title bar
        th = tk.Frame(outer, bg=GOLD_BG)
        th.pack(fill="x")
        tk.Label(th, text=title, font=("Segoe UI",10,"bold"),
                 fg=GOLD, bg=GOLD_BG, anchor="w",
                 padx=10, pady=5).pack(fill="x")
        tk.Frame(outer, bg=BORDER, height=1).pack(fill="x")
        body = tk.Frame(outer, bg=SURFACE)
        body.pack(fill="both", expand=True, padx=8, pady=8)
        return body

    def _sec(self, parent, title):
        tk.Label(parent, text=title, font=("Segoe UI",10,"bold"),
                 fg=GOLD, bg=BG, anchor="w").pack(
            fill="x", padx=12, pady=(10,2))
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=12)

    # ══════════════════════════════════════════════
    #  WIZARD
    # ══════════════════════════════════════════════
    def _build_wizard(self):
        f = self._tab_frames["wizard"]
        for w in f.winfo_children(): w.destroy()

        # Welcome
        wf = tk.Frame(f, bg=GREEN_BG, bd=1, relief="solid",
                      highlightbackground="#b3dfc0", highlightthickness=1)
        wf.pack(fill="x", padx=20, pady=(20,10))
        tk.Label(wf, text="🍺  Witaj w Beer Count!",
                 font=("Segoe UI",16,"bold"), fg=GOLD, bg=GREEN_BG).pack(pady=(14,4))
        tk.Label(wf,
                 text="Aby zacząć, podaj aktualny stan beczek.\n"
                      "To jest potrzebne tylko raz — potem każdy dzień\n"
                      "będzie się uzupełniał automatycznie z poprzedniego.",
                 font=("Segoe UI",11), fg=MUTED, bg=GREEN_BG,
                 justify="center").pack(pady=(0,14))

        # Date
        dc = self._card(f, "📅  Data stanu początkowego",
                        fill="x", padx=20, pady=(0,8))
        df = tk.Frame(dc, bg=SURFACE)
        df.pack(anchor="w")
        tk.Label(df, text="Data:", font=("Segoe UI",10),
                 fg=MUTED, bg=SURFACE).pack(side="left", padx=(0,6))
        self._wiz_date = tk.StringVar(value=str(date.today()))
        tk.Entry(df, textvariable=self._wiz_date, width=14,
                 font=("Consolas",11), relief="solid", bd=1).pack(side="left")
        tk.Label(df,
                 text="  Wpisz datę ostatniego liczenia beczek",
                 font=("Segoe UI",9), fg=MUTED, bg=SURFACE).pack(side="left")

        # Beers table
        bc = self._card(f, "🛢  Aktualny stan beczek",
                        fill="x", padx=20, pady=(0,8))
        tk.Label(bc, text="Tara: 30L=11kg | 20L=7kg",
                 font=("Segoe UI",9), fg=MUTED, bg=SURFACE).pack(anchor="w", pady=(0,6))

        hf = tk.Frame(bc, bg=GOLD_BG)
        hf.pack(fill="x")
        for col, w in [("Piwo",14),("Pełne (szt.)",10),
                       ("Otw.kg#1",10),("Otw.kg#2",10),
                       ("Otw.kg#3",10),("Razem (L)",10)]:
            tk.Label(hf, text=col, font=("Segoe UI",9,"bold"),
                     fg=GOLD, bg=GOLD_BG, width=w,
                     anchor="center").pack(side="left", padx=4, pady=4)

        self._wiz_rows = []
        for beer in db.get_beers():
            rf = tk.Frame(bc, bg=SURFACE)
            rf.pack(fill="x", pady=2)
            tk.Label(rf, text=f"{beer['name']} ({beer['keg']}L)",
                     font=("Segoe UI",10,"bold"), fg=TEXT,
                     bg=SURFACE, width=14, anchor="w").pack(side="left", padx=4)
            rv = {"beer": beer}
            rv["full"] = tk.StringVar()
            make_entry(rf, rv["full"], width=10).pack(side="left", padx=4)
            rv["open"] = []
            for _ in range(3):
                ov = tk.StringVar()
                make_entry(rf, ov, width=10).pack(side="left", padx=4)
                rv["open"].append(ov)
            res = tk.Label(rf, text="0.00 L", font=("Consolas",10),
                           fg=GOLD, bg=SURFACE, width=10, anchor="center")
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

        # Buttons
        bf = tk.Frame(f, bg=BG)
        bf.pack(fill="x", padx=20, pady=12)
        make_btn(bf, "✅  Zapisz stan początkowy i zacznij!",
                 self._save_wizard).pack(side="left")
        make_btn(bf, "Pomiń →",
                 lambda: self.show_tab("entry"),
                 bg=SURFACE, fg=MUTED, font=("Segoe UI",10)).pack(
            side="left", padx=10)

    def _save_wizard(self):
        d = self._wiz_date.get().strip()
        if not d: messagebox.showerror("Błąd","Wpisz datę!"); return
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
        messagebox.showinfo("Zapisano",
            f"Stan początkowy na {d} zapisany ✓\n\n"
            "Możesz teraz zacząć wpisywać codzienne dane!")
        self.show_tab("entry")

    def _is_float(self, s):
        try: float(s); return True
        except: return False

    # ══════════════════════════════════════════════
    #  ENTRY TAB — 3-column layout
    # ══════════════════════════════════════════════
    def _build_entry(self):
        f = self._tab_frames["entry"]

        # Banner
        banner = tk.Frame(f, bg=GREEN_BG, bd=1, relief="solid",
                          highlightbackground="#b3dfc0",
                          highlightthickness=1)
        banner.pack(fill="x", padx=12, pady=(10,6))
        tk.Label(banner,
                 text="✅  START ładuje się automatycznie z poprzedniego dnia"
                      " — wpisujesz tylko END na koniec zmiany + POS.",
                 font=("Segoe UI",9), fg=GREEN, bg=GREEN_BG,
                 anchor="w", padx=10, pady=6).pack(fill="x")

        # Date row
        df = tk.Frame(f, bg=BG)
        df.pack(fill="x", padx=12, pady=(0,6))
        tk.Label(df, text="Data:", font=("Segoe UI",10),
                 fg=MUTED, bg=BG).pack(side="left", padx=(0,6))
        self.ev_date = tk.StringVar(value=str(date.today()))
        tk.Entry(df, textvariable=self.ev_date, width=14,
                 font=("Consolas",11), relief="solid", bd=1).pack(side="left")
        for lbl, d in [("← Wczoraj",-1),("Dzisiaj →",0)]:
            make_btn(df, lbl,
                     lambda d=d: self.ev_date.set(
                         str(date.today()+timedelta(days=d))),
                     bg=GOLD_BG, fg=GOLD,
                     font=("Segoe UI",9), padx=8, pady=4).pack(
                side="left", padx=5)
        self.ev_date.trace_add("write", lambda *_: self._load_prev_starts())

        # ── 3-column row ──────────────────────────
        cols = tk.Frame(f, bg=BG)
        cols.pack(fill="both", expand=True, padx=6)

        # Col 1: Stan kegów
        self._kegs_card = self._card(cols, "🛢  Stan kegów",
                                      side="left", fill="both",
                                      expand=True, padx=4, pady=4)
        tk.Label(self._kegs_card,
                 text="szare=START auto | żółte=dostawa | Tara: 30L=11kg, 20L=7kg",
                 font=("Segoe UI",8), fg=MUTED,
                 bg=SURFACE).pack(anchor="w", pady=(0,4))
        self._kegs_frame = tk.Frame(self._kegs_card, bg=SURFACE)
        self._kegs_frame.pack(anchor="w")

        # Col 2: POS
        self._pos_card = self._card(cols, "💻  Sprzedaż POS",
                                     side="left", fill="both",
                                     expand=True, padx=4, pady=4)
        self._pos_total_lbl = tk.Label(self._pos_card,
                                        text="Łącznie: 0.00 L",
                                        font=("Segoe UI",9), fg=MUTED,
                                        bg=SURFACE, anchor="e")
        self._pos_total_lbl.pack(fill="x", pady=(0,4))
        self._pos_frame = tk.Frame(self._pos_card, bg=SURFACE)
        self._pos_frame.pack(anchor="w")

        # Col 3: Korekty
        self._corr_card = self._card(cols, "⚠️  Korekty",
                                      side="left", fill="both",
                                      expand=True, padx=4, pady=4)
        self._corr_total_lbl = tk.Label(self._corr_card,
                                         text="Łącznie: 0.00 L",
                                         font=("Segoe UI",9), fg=MUTED,
                                         bg=SURFACE, anchor="e")
        self._corr_total_lbl.pack(fill="x", pady=(0,4))
        self._corr_frame = tk.Frame(self._corr_card, bg=SURFACE)
        self._corr_frame.pack(anchor="w")

        # Wynik dnia — full width below
        self._sum_card = self._card(f, "📊  Wynik dnia",
                                     fill="x", padx=10, pady=(0,6))
        self._sum_frame = tk.Frame(self._sum_card, bg=SURFACE)
        self._sum_frame.pack(fill="x")

        # Legend
        leg = tk.Frame(f, bg=BG)
        leg.pack(fill="x", padx=12, pady=(0,6))
        for status, (col, bg) in DIFF_COLORS.items():
            lf = tk.Frame(leg, bg=bg, bd=1, relief="solid",
                          highlightbackground=col, highlightthickness=0)
            lf.pack(side="left", padx=(0,8))
            tk.Label(lf, text=f" {DIFF_ICONS[status]} {DIFF_TEXTS[status]} ",
                     font=("Segoe UI",9), fg=col, bg=bg).pack(padx=4, pady=2)

        # Buttons
        bf = tk.Frame(f, bg=BG)
        bf.pack(fill="x", padx=12, pady=(0,14))
        make_btn(bf, "💾  Zapisz dzień",
                 self._save_day).pack(side="left", padx=(0,8))
        make_btn(bf, "🔄  Przelicz", self._recalc,
                 bg=GOLD_BG, fg=GOLD,
                 font=("Segoe UI",10)).pack(side="left", padx=(0,8))
        make_btn(bf, "🗑  Wyczyść", self._clear,
                 bg=SURFACE, fg=MUTED,
                 font=("Segoe UI",10)).pack(side="left")

        self._kw = []; self._pw = []; self._cw = []

    def _load_entry(self):
        beers = db.get_beers()
        sizes = db.get_sizes()
        self._build_keg_inputs(beers)
        self._build_pos_inputs(beers, sizes)
        self._build_corr_inputs(beers)
        self._load_prev_starts()
        self._recalc()

    def _build_keg_inputs(self, beers):
        f = self._kegs_frame
        for w in f.winfo_children(): w.destroy()
        self._kw = []
        hdrs = ["Piwo","START","DOSTAWA","PEŁNE",
                "kg#1","kg#2","kg#3","END(L)"]
        ws   = [12,    9,      7,        6,
                7,     7,      7,        7]
        hf = tk.Frame(f, bg=GOLD_BG)
        hf.pack(fill="x", pady=(0,2))
        for h, w in zip(hdrs, ws):
            tk.Label(hf, text=h, font=("Segoe UI",8,"bold"),
                     fg=GOLD, bg=GOLD_BG, width=w,
                     anchor="center").pack(side="left", padx=2, pady=3)
        for beer in beers:
            rv = {"beer": beer, "_start_l": 0.0}
            rf = tk.Frame(f, bg=SURFACE)
            rf.pack(fill="x", pady=1)
            tk.Label(rf, text=f"{beer['name']}\n({beer['keg']}L)",
                     font=("Segoe UI",9,"bold"), fg=TEXT, bg=SURFACE,
                     width=12, anchor="w").pack(side="left", padx=2)
            rv["start_lbl"] = tk.Label(rf, text="—",
                                        font=("Consolas",9), fg=GOLD,
                                        bg=PREV_BG, width=9, anchor="center",
                                        relief="flat")
            rv["start_lbl"].pack(side="left", padx=2)
            rv["delivery"] = tk.StringVar()
            e = make_entry(rf, rv["delivery"], width=7, bg=GOLD_BG)
            e.pack(side="left", padx=2)
            e.bind("<KeyRelease>", lambda _: self._recalc())
            rv["full_end"] = tk.StringVar()
            e2 = make_entry(rf, rv["full_end"], width=6)
            e2.pack(side="left", padx=2)
            e2.bind("<KeyRelease>", lambda _: self._recalc())
            rv["open_end"] = []
            for _ in range(3):
                ov = tk.StringVar()
                oe = make_entry(rf, ov, width=7)
                oe.pack(side="left", padx=2)
                oe.bind("<KeyRelease>", lambda _: self._recalc())
                rv["open_end"].append(ov)
            rv["end_lbl"] = tk.Label(rf, text="—",
                                      font=("Consolas",9,"bold"),
                                      fg=GOLD, bg=SURFACE,
                                      width=7, anchor="center")
            rv["end_lbl"].pack(side="left", padx=2)
            self._kw.append(rv)

    def _build_pos_inputs(self, beers, sizes):
        f = self._pos_frame
        for w in f.winfo_children(): w.destroy()
        self._pw = []
        hf = tk.Frame(f, bg=GOLD_BG)
        hf.pack(fill="x", pady=(0,2))
        tk.Label(hf, text="Piwo", font=("Segoe UI",8,"bold"),
                 fg=GOLD, bg=GOLD_BG, width=10,
                 anchor="w").pack(side="left", padx=2, pady=3)
        for sz in sizes:
            tk.Label(hf, text=sz["label"], font=("Segoe UI",8,"bold"),
                     fg=GOLD, bg=GOLD_BG, width=7,
                     anchor="center").pack(side="left", padx=2, pady=3)
        tk.Label(hf, text="Razem", font=("Segoe UI",8,"bold"),
                 fg=GOLD, bg=GOLD_BG, width=8,
                 anchor="center").pack(side="left", padx=2, pady=3)
        for beer in beers:
            rf = tk.Frame(f, bg=SURFACE)
            rf.pack(fill="x", pady=1)
            tk.Label(rf, text=beer["name"], font=("Segoe UI",9,"bold"),
                     fg=TEXT, bg=SURFACE, width=10,
                     anchor="w").pack(side="left", padx=2)
            svars = []
            for sz in sizes:
                sv = tk.StringVar()
                e = make_entry(rf, sv, width=7)
                e.pack(side="left", padx=2)
                e.bind("<KeyRelease>", lambda _: self._recalc())
                svars.append({"var": sv, "liters": sz["liters"]})
            lbl = tk.Label(rf, text="0.00L", font=("Consolas",9,"bold"),
                           fg=GOLD, bg=SURFACE, width=8, anchor="center")
            lbl.pack(side="left", padx=2)
            self._pw.append({"name": beer["name"], "sizes": svars, "lbl": lbl})

    def _build_corr_inputs(self, beers):
        f = self._corr_frame
        for w in f.winfo_children(): w.destroy()
        self._cw = []
        hf = tk.Frame(f, bg=GOLD_BG)
        hf.pack(fill="x", pady=(0,2))
        for h, w in [("Piwo",10),("Spill",7),("Void",7),("Open Bar",8),("Razem",8)]:
            tk.Label(hf, text=h, font=("Segoe UI",8,"bold"),
                     fg=GOLD, bg=GOLD_BG, width=w,
                     anchor="center").pack(side="left", padx=2, pady=3)
        for beer in beers:
            rf = tk.Frame(f, bg=SURFACE)
            rf.pack(fill="x", pady=1)
            tk.Label(rf, text=beer["name"], font=("Segoe UI",9,"bold"),
                     fg=TEXT, bg=SURFACE, width=10,
                     anchor="w").pack(side="left", padx=2)
            cv = {"name": beer["name"]}
            for field, w in [("spill",7),("void_",7),("open_bar",8)]:
                v = tk.StringVar()
                e = make_entry(rf, v, width=w)
                e.pack(side="left", padx=2)
                e.bind("<KeyRelease>", lambda _: self._recalc())
                cv[field] = v
            lbl = tk.Label(rf, text="−0.00", font=("Consolas",9,"bold"),
                           fg=RED, bg=SURFACE, width=8, anchor="center")
            lbl.pack(side="left", padx=2)
            cv["lbl"] = lbl
            self._cw.append(cv)

    def _load_prev_starts(self, *_):
        d = self.ev_date.get().strip()
        if not d: return
        prev = db.get_prev_day(d)
        if not prev: return
        prev_kegs = {k["name"]: db.keg_end_liters(k)
                     for k in prev.get("kegs", [])}
        for rw in self._kw:
            name = rw["beer"]["name"]
            val  = prev_kegs.get(name, 0.0)
            rw["_start_l"] = val
            rw["start_lbl"].configure(text=f"{val:.1f}L")

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

    def _render_summary(self, data):
        f = self._sum_frame
        for w in f.winfo_children(): w.destroy()
        tot_diff = 0
        for i, keg in enumerate(data["kegs"]):
            pe   = data["pos"][i]  if i < len(data["pos"])  else {"sizes":[]}
            co   = data["corr"][i] if i < len(data["corr"]) else {}
            diff = db.calc_diff(keg, pe, co)
            s    = db.diff_status(diff)
            col, bg = DIFF_COLORS[s]
            tot_diff += diff
            row = tk.Frame(f, bg=SURFACE, bd=1, relief="solid",
                           highlightbackground=BORDER, highlightthickness=0)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=keg["name"], font=("Segoe UI",10,"bold"),
                     fg=TEXT, bg=SURFACE, width=10, anchor="w").pack(
                side="left", padx=8, pady=4)
            for lbl, val in [
                ("START", f"{db.keg_start_liters(keg):.1f}L"),
                ("Del",   f"+{db.keg_delivery_liters(keg):.0f}L"),
                ("END",   f"{db.keg_end_liters(keg):.1f}L"),
                ("POS",   f"{db.pos_liters(pe):.1f}L"),
                ("Kor",   f"−{db.corr_liters(co):.1f}L"),
            ]:
                tk.Label(row, text=f"{lbl}: {val}",
                         font=("Segoe UI",9), fg=MUTED,
                         bg=SURFACE).pack(side="left", padx=8)
            cf = tk.Frame(row, bg=bg)
            cf.pack(side="right", padx=10, pady=4)
            tk.Label(cf, text=f" {DIFF_ICONS[s]} {diff:+.2f}L ",
                     font=("Segoe UI",10,"bold"), fg=col,
                     bg=bg).pack(padx=4, pady=2)

        # Total
        ts = db.diff_status(tot_diff)
        tcol, tbg = DIFF_COLORS[ts]
        tot = tk.Frame(f, bg=GOLD_BG, bd=1, relief="solid",
                       highlightbackground=GOLD_LT, highlightthickness=0)
        tot.pack(fill="x", pady=(4,0))
        tk.Label(tot, text="ŁĄCZNIE", font=("Segoe UI",11,"bold"),
                 fg=GOLD, bg=GOLD_BG).pack(side="left", padx=12, pady=6)
        tk.Label(tot,
                 text=f"POS: {sum(db.pos_liters(p) for p in data['pos']):.1f}L",
                 font=("Segoe UI",10), fg=MUTED,
                 bg=GOLD_BG).pack(side="left", padx=10)
        cf = tk.Frame(tot, bg=tbg)
        cf.pack(side="right", padx=12, pady=6)
        tk.Label(cf, text=f" {DIFF_ICONS[ts]} {tot_diff:+.2f}L ",
                 font=("Segoe UI",12,"bold"), fg=tcol,
                 bg=tbg).pack(padx=6, pady=3)

    def _save_day(self):
        d = self.ev_date.get().strip()
        if not d: messagebox.showerror("Błąd","Wpisz datę!"); return
        data = self._collect()
        db.save_day(d, data)
        messagebox.showinfo("Zapisano", f"Dzień {d} zapisany ✓")

    def _clear(self):
        if not messagebox.askyesno("Wyczyścić?","Wyczyścić wszystkie pola?"):
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
        top = tk.Frame(f, bg=BG)
        top.pack(fill="x", padx=16, pady=(14,8))
        tk.Label(top, text="Miesiąc:", font=("Segoe UI",10),
                 fg=MUTED, bg=BG).pack(side="left", padx=(0,8))
        self._hist_month = tk.StringVar()
        self._hist_cb = tk.OptionMenu(top, self._hist_month, "(brak)")
        self._hist_cb.configure(font=("Segoe UI",10), bg=SURFACE,
                                 relief="solid", bd=1, width=25)
        self._hist_cb.pack(side="left")
        self._hist_month.trace_add("write",
                                    lambda *_: self._render_history())
        self._hist_list = tk.Frame(f, bg=BG)
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
                     font=("Segoe UI",11), fg=MUTED,
                     bg=BG).pack(pady=30)
            return
        for entry_date, data in reversed(entries):
            self._hist_card(entry_date, data)

    def _hist_card(self, entry_date, data):
        beers    = data.get("kegs", [])
        # Safe diff calculation
        tot_diff = 0
        for i, k in enumerate(beers):
            pe = data["pos"][i]  if i < len(data.get("pos",[])) else {"sizes":[]}
            co = data["corr"][i] if i < len(data.get("corr",[])) else {}
            try: tot_diff += db.calc_diff(k, pe, co)
            except: pass
        tot_pos = sum(db.pos_liters(p) for p in data.get("pos", []))
        tot_del = sum(int(k.get("delivery",0) or 0) for k in beers)
        status  = db.diff_status(tot_diff)
        col, bg = DIFF_COLORS[status]

        card = tk.Frame(self._hist_list, bg=SURFACE, bd=1,
                        relief="solid",
                        highlightbackground=BORDER,
                        highlightthickness=1)
        card.pack(fill="x", pady=4)

        # Header
        hdr = tk.Frame(card, bg="#f0ede6")
        hdr.pack(fill="x")
        tk.Label(hdr, text=self._fmt_date(entry_date),
                 font=("Segoe UI",10,"bold"), fg=TEXT,
                 bg="#f0ede6").pack(side="left", padx=12, pady=6)
        if tot_del:
            tk.Label(hdr, text=f"🚚 Dostawa: {tot_del} keg",
                     font=("Segoe UI",9), fg=GOLD,
                     bg=GOLD_BG).pack(side="left", padx=6)
        tk.Label(hdr, text=f"POS: {tot_pos:.1f}L",
                 font=("Segoe UI",9), fg=MUTED,
                 bg="#f0ede6").pack(side="right", padx=12)
        cf = tk.Frame(hdr, bg=bg)
        cf.pack(side="right", padx=6, pady=6)
        tk.Label(cf, text=f" {DIFF_ICONS[status]} {tot_diff:+.2f}L ",
                 font=("Segoe UI",10,"bold"), fg=col,
                 bg=bg).pack(padx=4, pady=2)

        # Body
        body = tk.Frame(card, bg=SURFACE)
        body.pack(fill="x", padx=12, pady=8)

        # Bars per beer
        for i, keg in enumerate(beers):
            pe = data["pos"][i]  if i < len(data.get("pos",[])) else {"sizes":[]}
            co = data["corr"][i] if i < len(data.get("corr",[])) else {}
            try:
                diff = db.calc_diff(keg, pe, co)
            except:
                diff = 0.0
            s = db.diff_status(diff); c, _ = DIFF_COLORS[s]
            br = tk.Frame(body, bg=SURFACE)
            br.pack(fill="x", pady=1)
            tk.Label(br, text=keg["name"], font=("Segoe UI",9),
                     fg=TEXT, bg=SURFACE, width=10,
                     anchor="w").pack(side="left")
            tk.Label(br, text=f"{DIFF_ICONS[s]} {diff:+.2f}L",
                     font=("Consolas",9,"bold"), fg=c,
                     bg=SURFACE, width=12,
                     anchor="e").pack(side="right")

        # Buttons row
        btn_f = tk.Frame(body, bg=SURFACE)
        btn_f.pack(fill="x", pady=(6,0))

        # Detail frame — created once, toggled
        det_frame = tk.Frame(body, bg=SURFACE)
        state = {"open": False}

        def toggle_det(df=det_frame, s=state, e=entry_date, d=data):
            if s["open"]:
                df.pack_forget(); s["open"] = False
                det_btn.configure(text="🔍 Pokaż szczegóły")
            else:
                # Clear and rebuild detail table safely
                for w in df.winfo_children(): w.destroy()
                try:
                    self._build_det_table(df, d)
                except Exception as ex:
                    tk.Label(df, text=f"Błąd: {ex}",
                             fg=RED, bg=SURFACE,
                             font=("Segoe UI",9)).pack()
                df.pack(fill="x"); s["open"] = True
                det_btn.configure(text="🔍 Ukryj szczegóły")

        det_btn = make_btn(btn_f, "🔍 Pokaż szczegóły", toggle_det,
                           bg=GOLD_BG, fg=GOLD,
                           font=("Segoe UI",9), padx=8, pady=3)
        det_btn.pack(side="left", padx=(0,8))
        make_btn(btn_f, "✏️ Edytuj",
                 lambda e=entry_date, d=data: self._open_edit(e, d),
                 font=("Segoe UI",9), padx=8, pady=3).pack(side="left")

    def _build_det_table(self, parent, data):
        """Build detail table safely — no crash."""
        sizes = db.get_sizes()
        # Header
        hf = tk.Frame(parent, bg=GOLD_BG)
        hf.pack(fill="x", pady=(6,0))
        cols = (["Piwo","START","Del","Pełne","kg#1","kg#2","kg#3","END(L)"] +
                [sz["label"] for sz in sizes] +
                ["Spill","Void","OpenBar","RÓŻNICA"])
        ws   = ([10,6,4,5,6,6,6,6] +
                [5]*len(sizes) + [5,5,7,9])
        for h, w in zip(cols, ws):
            tk.Label(hf, text=h, font=("Segoe UI",8,"bold"),
                     fg=GOLD, bg=GOLD_BG, width=w,
                     anchor="center").pack(side="left", padx=1, pady=3)

        for ri, keg in enumerate(data.get("kegs",[])):
            pe   = data["pos"][ri]  if ri<len(data.get("pos",[])) else {"sizes":[]}
            co   = data["corr"][ri] if ri<len(data.get("corr",[])) else {}
            try:
                diff = db.calc_diff(keg, pe, co)
            except:
                diff = 0.0
            s = db.diff_status(diff); dcol, dbg = DIFF_COLORS[s]
            ow = keg.get("open_end") or []
            row_vals = ([keg["name"],
                         f"{db.keg_start_liters(keg):.1f}",
                         str(keg.get("delivery",0)),
                         str(keg.get("full_end",0)),
                         str(ow[0] if len(ow)>0 and ow[0] else "—"),
                         str(ow[1] if len(ow)>1 and ow[1] else "—"),
                         str(ow[2] if len(ow)>2 and ow[2] else "—"),
                         f"{db.keg_end_liters(keg):.2f}"] +
                        [str(sz.get("qty",0) or 0)
                         for sz in pe.get("sizes",[])] +
                        [str(co.get("spill",0) or 0),
                         str(co.get("void_",0) or 0),
                         str(co.get("open_bar",0) or 0),
                         f"{DIFF_ICONS[s]} {diff:+.2f}L"])
            rf = tk.Frame(parent, bg=SURFACE)
            rf.pack(fill="x")
            for ci, (v, w) in enumerate(zip(row_vals, ws)):
                is_diff = ci == len(row_vals)-1
                tk.Label(rf, text=v,
                         font=("Segoe UI", 8, "bold" if is_diff else "normal"),
                         fg=(dcol if is_diff else TEXT),
                         bg=(dbg if is_diff else SURFACE),
                         width=w, anchor="center",
                         relief="flat").pack(side="left", padx=1, pady=1)

    def _open_edit(self, entry_date, data):
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
            rw["delivery"].set(str(keg.get("delivery","") or ""))
            rw["full_end"].set(str(keg.get("full_end","") or ""))
            ow = keg.get("open_end") or [None,None,None]
            for j, v in enumerate(rw["open_end"]):
                v.set(str(ow[j]) if j<len(ow) and ow[j] else "")
        for i, pw in enumerate(self._pw):
            if i >= len(data.get("pos",[])): continue
            pe = data["pos"][i]
            for j, sv in enumerate(pw["sizes"]):
                if j < len(pe.get("sizes",[])):
                    sv["var"].set(str(pe["sizes"][j].get("qty","") or ""))
        for i, cw in enumerate(self._cw):
            if i >= len(data.get("corr",[])): continue
            co = data["corr"][i]
            cw["spill"].set(str(co.get("spill","") or ""))
            cw["void_"].set(str(co.get("void_","") or ""))
            cw["open_bar"].set(str(co.get("open_bar","") or ""))
        self._recalc()
        self.show_tab("entry")

    # ══════════════════════════════════════════════
    #  REPORT
    # ══════════════════════════════════════════════
    def _build_report(self):
        f = self._tab_frames["report"]
        top = tk.Frame(f, bg=BG)
        top.pack(fill="x", padx=16, pady=(14,8))
        tk.Label(top, text="Miesiąc:", font=("Segoe UI",10),
                 fg=MUTED, bg=BG).pack(side="left", padx=(0,8))
        self._rep_month = tk.StringVar()
        self._rep_cb = tk.OptionMenu(top, self._rep_month, "(brak)")
        self._rep_cb.configure(font=("Segoe UI",10), bg=SURFACE,
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
                 bg=GOLD_BG, fg=GOLD,
                 font=("Segoe UI",9), padx=8, pady=4).pack(side="left")
        self._rep_body = tk.Frame(f, bg=BG)
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
                     font=("Segoe UI",11), fg=MUTED,
                     bg=BG).pack(pady=30)
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

        # KPIs
        kf = tk.Frame(self._rep_body, bg=BG)
        kf.pack(fill="x", pady=(0,12))
        ts = db.diff_status(tot_diff); tcol, tbg = DIFF_COLORS[ts]
        for lbl, val2, col in [
            ("Dni",    str(tot_days),           GOLD),
            ("Dostawa",f"{tot_del} keg",         GOLD),
            ("POS",    f"{tot_pos:.1f}L",        TEXT),
            ("Korekty",f"{tot_corr:.1f}L",       TEXT),
            ("Różnica",f"{DIFF_ICONS[ts]} {tot_diff:+.1f}L", tcol),
        ]:
            kpi = tk.Frame(kf, bg=SURFACE, bd=1, relief="solid",
                           highlightbackground=BORDER, highlightthickness=0)
            kpi.pack(side="left", padx=(0,8))
            tk.Label(kpi, text=lbl, font=("Segoe UI",9),
                     fg=MUTED, bg=SURFACE).pack(padx=12, pady=(8,2))
            tk.Label(kpi, text=val2, font=("Segoe UI",18,"bold"),
                     fg=col, bg=SURFACE).pack(padx=12, pady=(0,8))

        # Per-beer
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
            col, bg = DIFF_COLORS[s]
            row = tk.Frame(self._rep_body, bg=SURFACE, bd=1,
                           relief="solid",
                           highlightbackground=BORDER,
                           highlightthickness=0)
            row.pack(fill="x", pady=2, padx=4)
            tk.Label(row, text=n, font=("Segoe UI",10,"bold"),
                     fg=TEXT, bg=SURFACE, width=12,
                     anchor="w").pack(side="left", padx=10, pady=6)
            tk.Label(row,
                     text=f"POS: {a['pos']:.1f}L | "
                          f"Del: {a['del']} keg | {a['days']} dni",
                     font=("Segoe UI",9), fg=MUTED,
                     bg=SURFACE).pack(side="left", padx=8)
            cf = tk.Frame(row, bg=bg)
            cf.pack(side="right", padx=10, pady=6)
            tk.Label(cf, text=f" {DIFF_ICONS[s]} {diff:+.1f}L ",
                     font=("Segoe UI",10,"bold"), fg=col,
                     bg=bg).pack(padx=4, pady=2)

        # Trend
        self._sec(self._rep_body, "Trend dzienny")
        for entry_date, data in entries:
            d_diff = sum(
                db.calc_diff(k,
                             data["pos"][i]  if i<len(data.get("pos",[])) else {"sizes":[]},
                             data["corr"][i] if i<len(data.get("corr",[])) else {})
                for i,k in enumerate(data.get("kegs",[])))
            s = db.diff_status(d_diff); col,_ = DIFF_COLORS[s]
            tr = tk.Frame(self._rep_body, bg=BG)
            tr.pack(fill="x", pady=1, padx=4)
            tk.Label(tr, text=self._fmt_date(entry_date),
                     font=("Segoe UI",9), fg=MUTED, bg=BG,
                     width=14, anchor="w").pack(side="left")
            tk.Label(tr, text=f"{DIFF_ICONS[s]} {d_diff:+.2f}L",
                     font=("Consolas",9,"bold"), fg=col,
                     bg=BG, width=12, anchor="e").pack(side="right")

    def _export_month(self):
        val = self._rep_month.get()
        if not val or "(brak)" in val:
            messagebox.showwarning("Brak","Wybierz miesiąc"); return
        month = val.split("[")[-1].rstrip("]").strip()
        p = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel","*.xlsx")],
            initialfile=f"BeerCount_{month}.xlsx")
        if not p: return
        if xl.export_month(month, p):
            messagebox.showinfo("OK", f"Zapisano:\n{p}")
        else:
            messagebox.showerror("Błąd","Brak danych")

    def _export_year(self):
        val  = self._rep_month.get()
        year = val.split("[")[-1][:4] if "[" in val else str(date.today().year)
        p = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel","*.xlsx")],
            initialfile=f"BeerCount_{year}_roczny.xlsx")
        if not p: return
        if xl.export_year(year, p):
            messagebox.showinfo("OK", f"Zapisano:\n{p}")
        else:
            messagebox.showerror("Błąd",f"Brak danych dla roku {year}")

    # ══════════════════════════════════════════════
    #  SETTINGS — fixed add/remove
    # ══════════════════════════════════════════════
    def _build_settings(self):
        f = self._tab_frames["settings"]

        c1 = self._card(f, "🍺  Piwa na krane", fill="x", padx=16, pady=(14,6))
        self._set_beers_f = tk.Frame(c1, bg=SURFACE)
        self._set_beers_f.pack(fill="x")
        make_btn(c1, "+ Dodaj piwo", self._add_beer,
                 bg=GOLD_BG, fg=GOLD,
                 font=("Segoe UI",9), padx=8, pady=3).pack(
            anchor="w", pady=(6,0))

        c2 = self._card(f, "🥃  Rozmiary porcji POS",
                        fill="x", padx=16, pady=(0,6))
        self._set_sizes_f = tk.Frame(c2, bg=SURFACE)
        self._set_sizes_f.pack(fill="x")
        make_btn(c2, "+ Dodaj rozmiar", self._add_size,
                 bg=GOLD_BG, fg=GOLD,
                 font=("Segoe UI",9), padx=8, pady=3).pack(
            anchor="w", pady=(6,0))

        bf = tk.Frame(f, bg=BG)
        bf.pack(fill="x", padx=16, pady=8)
        make_btn(bf, "💾  Zapisz ustawienia",
                 self._save_settings).pack(side="left", padx=(0,10))
        make_btn(bf, "🔄  Kreator pierwszego uruchomienia",
                 self._rerun_wizard,
                 bg=SURFACE, fg=MUTED,
                 font=("Segoe UI",9), padx=8, pady=4).pack(side="left")

        # Internal lists — source of truth for settings
        self._beer_data = []  # list of (name_var, keg_var, frame)
        self._size_data = []  # list of (label_var, liters_var, frame)

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
        rf = tk.Frame(self._set_beers_f, bg=SURFACE)
        rf.pack(fill="x", pady=2)
        nv = tk.StringVar(value=name)
        kv = tk.StringVar(value=keg)
        tk.Entry(rf, textvariable=nv, width=20, font=("Segoe UI",10),
                 relief="solid", bd=1).pack(side="left", padx=(0,6))
        om = tk.OptionMenu(rf, kv, "20", "30", "50")
        om.configure(font=("Segoe UI",10), bg=SURFACE,
                     relief="solid", bd=1, width=5)
        om.pack(side="left", padx=(0,4))
        tk.Label(rf, text="L keg", font=("Segoe UI",9),
                 fg=MUTED, bg=SURFACE).pack(side="left", padx=(0,8))
        row_data = (nv, kv, rf)
        self._beer_data.append(row_data)
        def remove(rd=row_data):
            rd[2].destroy()
            if rd in self._beer_data:
                self._beer_data.remove(rd)
        tk.Button(rf, text="✕", font=("Segoe UI",10),
                  fg=RED, bg=SURFACE, relief="flat",
                  bd=0, cursor="hand2", padx=4,
                  command=remove).pack(side="left")

    def _add_size_row(self, label="0.5L", liters="0.5"):
        rf = tk.Frame(self._set_sizes_f, bg=SURFACE)
        rf.pack(fill="x", pady=2)
        lv  = tk.StringVar(value=label)
        lv2 = tk.StringVar(value=liters)
        tk.Entry(rf, textvariable=lv, width=8, font=("Consolas",10),
                 relief="solid", bd=1).pack(side="left", padx=(0,6))
        tk.Entry(rf, textvariable=lv2, width=8, font=("Consolas",10),
                 relief="solid", bd=1).pack(side="left", padx=(0,4))
        tk.Label(rf, text="L/szt.", font=("Segoe UI",9),
                 fg=MUTED, bg=SURFACE).pack(side="left", padx=(0,8))
        row_data = (lv, lv2, rf)
        self._size_data.append(row_data)
        def remove(rd=row_data):
            rd[2].destroy()
            if rd in self._size_data:
                self._size_data.remove(rd)
        tk.Button(rf, text="✕", font=("Segoe UI",10),
                  fg=RED, bg=SURFACE, relief="flat",
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
        messagebox.showinfo("Zapisano","Ustawienia zapisane ✓")

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
