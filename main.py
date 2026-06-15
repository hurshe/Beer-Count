"""
main.py — Beer Count HRC Warsaw v3
CustomTkinter GUI + SQLite
Fixes: smooth tab switching, responsive layout, first-run wizard
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import database as db
import export_excel as xl
from datetime import date, timedelta, datetime

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ── Colors ─────────────────────────────────────────
GOLD     = "#9a6f1e"; GOLD_LT  = "#c9a84c"; GOLD_BG  = "#fdf3df"
GREEN    = "#2a7a45"; GREEN_BG = "#eaf6ee"
RED      = "#b83232"; RED_BG   = "#fdeaea"
AMBER    = "#a06010"; AMBER_BG = "#fff4e0"
ORANGE   = "#c05000"; ORANGE_BG= "#fff0e0"
BG       = "#f5f2ec"; SURFACE  = "#ffffff"
BORDER   = "#ddd8ce"; MUTED    = "#7a7265"; TEXT = "#1a1a1a"
PREV_BG  = "#f0ede6"

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


def scaled(base, factor):
    """Scale a base size by window scale factor."""
    return max(int(base * factor), int(base * 0.7))


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        db.init_db()
        self.title("🍺 Beer Count — Hard Rock Cafe Warsaw")
        self.geometry("1120x760")
        self.minsize(800, 580)
        self.configure(fg_color=BG)

        self._scale = 1.0
        self._tab_cache = {}   # cache rendered tab content

        self._build_header()
        self._build_nav()
        self._content = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self._content.pack(fill="both", expand=True)

        self._tabs = {}
        for key in ("wizard","entry","history","report","settings"):
            f = ctk.CTkScrollableFrame(self._content, fg_color=BG, corner_radius=0)
            self._tabs[key] = f

        self._build_entry()
        self._build_history()
        self._build_report()
        self._build_settings()

        # Responsive: update scale on resize
        self.bind("<Configure>", self._on_resize)

        # First run check
        if not db.get_months() and not db.load_day(str(date.today())):
            self._build_wizard()
            self._show_tab_instant("wizard")
        else:
            self.show_tab("entry")

    # ── Resize handler ────────────────────────────
    def _on_resize(self, event=None):
        if event and event.widget != self:
            return
        w = self.winfo_width()
        new_scale = max(0.75, min(w / 1120, 1.6))
        if abs(new_scale - self._scale) > 0.05:
            self._scale = new_scale
            self._apply_scale()

    def _apply_scale(self):
        s = self._scale
        # Update nav button widths
        for btn in self._nav_btns.values():
            btn.configure(width=scaled(155, s), font=("Segoe UI", scaled(11, s)))

    # ── Header ────────────────────────────────────
    def _build_header(self):
        h = ctk.CTkFrame(self, fg_color=SURFACE, height=52, corner_radius=0)
        h.pack(fill="x", side="top")
        h.pack_propagate(False)
        ctk.CTkFrame(h, fg_color=GOLD_LT, height=2, corner_radius=0).pack(
            side="bottom", fill="x")
        ctk.CTkLabel(h, text="🍺  Beer Count",
                     font=("Segoe UI", 15, "bold"), text_color=GOLD).pack(
            side="left", padx=(16, 4))
        ctk.CTkLabel(h, text="Hard Rock Cafe Warsaw",
                     font=("Segoe UI", 10), text_color=MUTED).pack(side="left")
        ctk.CTkLabel(h, text=date.today().strftime("%A, %d.%m.%Y"),
                     font=("Segoe UI", 10), text_color=MUTED,
                     fg_color=GOLD_BG, corner_radius=10).pack(
            side="right", padx=16, pady=14)

    # ── Nav ───────────────────────────────────────
    def _build_nav(self):
        self._nav_frame = ctk.CTkFrame(self, fg_color=SURFACE, height=42,
                                        corner_radius=0)
        self._nav_frame.pack(fill="x", side="top")
        self._nav_frame.pack_propagate(False)
        ctk.CTkFrame(self, fg_color=BORDER, height=1,
                     corner_radius=0).pack(fill="x", side="top")
        self._nav_btns = {}
        for key, lbl in [("entry","📋  Wpis dnia"), ("history","📅  Historia"),
                          ("report","📊  Raport"), ("settings","⚙️  Ustawienia")]:
            b = ctk.CTkButton(
                self._nav_frame, text=lbl, width=155, height=40,
                corner_radius=0, fg_color=SURFACE, text_color=MUTED,
                hover_color=GOLD_BG, font=("Segoe UI", 11),
                command=lambda k=key: self.show_tab(k))
            b.pack(side="left")
            self._nav_btns[key] = b

    # ── Smooth tab switch ─────────────────────────
    def show_tab(self, key):
        """Switch tab without flicker using place geometry."""
        for k, b in self._nav_btns.items():
            if k == key:
                b.configure(fg_color=GOLD_BG, text_color=GOLD,
                             font=("Segoe UI", 11, "bold"))
            else:
                b.configure(fg_color=SURFACE, text_color=MUTED,
                             font=("Segoe UI", 11))
        self._show_tab_instant(key)
        getattr(self, f"_load_{key}")()

    def _show_tab_instant(self, key):
        for f in self._tabs.values():
            f.pack_forget()
        self._tabs[key].pack(fill="both", expand=True)

    # ══════════════════════════════════════════════
    #  WIZARD — First run setup
    # ══════════════════════════════════════════════
    def _build_wizard(self):
        f = self._tabs["wizard"]
        for w in f.winfo_children(): w.destroy()

        # Welcome card
        wc = ctk.CTkFrame(f, fg_color=SURFACE, corner_radius=12,
                           border_width=1, border_color=GOLD_LT)
        wc.pack(fill="x", padx=24, pady=(20, 12))
        ctk.CTkLabel(wc, text="🍺  Witaj w Beer Count!",
                     font=("Segoe UI", 18, "bold"), text_color=GOLD).pack(
            padx=20, pady=(18, 4))
        ctk.CTkLabel(wc,
                     text="Aby zacząć, podaj aktualny stan beczek.\n"
                          "To jest potrzebne tylko raz — potem każdy dzień\n"
                          "będzie się uzupełniał automatycznie z poprzedniego.",
                     font=("Segoe UI", 12), text_color=MUTED,
                     justify="center").pack(padx=20, pady=(0, 18))

        # Date card
        dc = self._card(f, "📅  Data stanu początkowego")
        dr = ctk.CTkFrame(dc, fg_color="transparent")
        dr.pack(fill="x")
        ctk.CTkLabel(dr, text="Data:", font=("Segoe UI", 11),
                     text_color=MUTED).pack(side="left", padx=(0, 8))
        self._wiz_date = ctk.StringVar(value=str(date.today()))
        ctk.CTkEntry(dr, textvariable=self._wiz_date, width=145,
                     font=("Consolas", 11)).pack(side="left")
        ctk.CTkLabel(dr,
                     text="  Wpisz datę ostatniego liczenia beczek (np. koniec poprzedniego miesiąca)",
                     font=("Segoe UI", 10), text_color=MUTED).pack(side="left", padx=8)

        # Beers input
        bc = self._card(f, "🛢  Aktualny stan beczek")
        ctk.CTkLabel(bc,
                     text="Podaj ile pełnych beczek masz teraz oraz wagę otwartych (kg brutto).\n"
                          "Tara odejmowana auto: 30L = 11kg | 20L = 7kg",
                     font=("Segoe UI", 10), text_color=MUTED).pack(
            anchor="w", pady=(0, 10))

        # Table header
        hdr = ctk.CTkFrame(bc, fg_color=GOLD_BG, corner_radius=6)
        hdr.pack(fill="x", pady=(0, 4))
        for col, w in [("Piwo", 120), ("Pełne (szt.)", 100),
                       ("Otwarty kg #1", 120), ("Otwarty kg #2", 120),
                       ("Otwarty kg #3", 120), ("Razem (L)", 100)]:
            ctk.CTkLabel(hdr, text=col, font=("Segoe UI", 9, "bold"),
                         text_color=GOLD, width=w, anchor="center").pack(
                side="left", padx=4, pady=6)

        self._wiz_rows = []
        beers = db.get_beers()
        for beer in beers:
            row = ctk.CTkFrame(bc, fg_color="transparent")
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(row, text=f"{beer['name']}\n({beer['keg']}L)",
                         font=("Segoe UI", 11, "bold"), width=120,
                         anchor="w").pack(side="left", padx=4)

            rv = {"beer": beer}
            rv["full"] = ctk.StringVar()
            ctk.CTkEntry(row, textvariable=rv["full"], width=100, height=30,
                         font=("Consolas", 11),
                         placeholder_text="0").pack(side="left", padx=4)

            rv["open"] = []
            for j in range(3):
                ov = ctk.StringVar()
                ctk.CTkEntry(row, textvariable=ov, width=120, height=30,
                             font=("Consolas", 11),
                             placeholder_text="— kg").pack(side="left", padx=4)
                rv["open"].append(ov)

            res_lbl = ctk.CTkLabel(row, text="0.00 L", font=("Consolas", 11),
                                   text_color=GOLD, width=100, anchor="center")
            res_lbl.pack(side="left", padx=4)
            rv["result_lbl"] = res_lbl

            # Live calc
            def make_updater(r=rv):
                def update(*_):
                    tara = db.TARA.get(r["beer"]["keg"], 7)
                    full_l = int(r["full"].get() or 0) * r["beer"]["keg"]
                    open_l = sum(
                        max(float(v.get()) - tara, 0)
                        for v in r["open"]
                        if v.get() and v.get() not in ("", "—")
                        and self._is_float(v.get())
                    )
                    r["result_lbl"].configure(text=f"{full_l + open_l:.2f} L")
                return update

            upd = make_updater(rv)
            rv["full"].trace_add("write", lambda *_, u=upd: u())
            for ov in rv["open"]:
                ov.trace_add("write", lambda *_, u=upd: u())

            self._wiz_rows.append(rv)

        # POS sizes reminder
        sc = self._card(f, "🥃  Rozmiary porcji POS")
        ctk.CTkLabel(sc,
                     text="Sprawdź czy poniższe rozmiary porcji są poprawne.\n"
                          "Możesz je zmienić w zakładce Ustawienia.",
                     font=("Segoe UI", 10), text_color=MUTED).pack(
            anchor="w", pady=(0, 8))
        sizes = db.get_sizes()
        sizes_f = ctk.CTkFrame(sc, fg_color="transparent")
        sizes_f.pack(anchor="w")
        for sz in sizes:
            chip = ctk.CTkFrame(sizes_f, fg_color=GOLD_BG, corner_radius=8)
            chip.pack(side="left", padx=(0, 8))
            ctk.CTkLabel(chip, text=f"  {sz['label']} = {sz['liters']}L  ",
                         font=("Segoe UI", 11, "bold"),
                         text_color=GOLD).pack(padx=6, pady=4)

        # Start button
        btn_f = ctk.CTkFrame(f, fg_color="transparent")
        btn_f.pack(fill="x", padx=24, pady=(8, 24))
        ctk.CTkButton(
            btn_f, text="✅  Zapisz stan początkowy i zacznij!",
            width=300, height=46, font=("Segoe UI", 13, "bold"),
            fg_color=GOLD, hover_color=GOLD_LT,
            command=self._save_wizard).pack(side="left")
        ctk.CTkButton(
            btn_f, text="Pomiń →", width=100, height=46,
            font=("Segoe UI", 11), fg_color=SURFACE, text_color=MUTED,
            hover_color=BORDER, border_width=1, border_color=BORDER,
            command=lambda: self.show_tab("entry")).pack(side="left", padx=12)

    def _save_wizard(self):
        d = self._wiz_date.get().strip()
        if not d:
            messagebox.showerror("Błąd", "Wpisz datę!"); return

        # Build a day entry with wizard data as END (no POS, no corr)
        beers = db.get_beers()
        sizes = db.get_sizes()
        data = {
            "kegs": [],
            "pos":  [{"name": b["name"],
                       "sizes": [{"liters": sz["liters"], "qty": "0"}
                                 for sz in sizes]}
                     for b in beers],
            "corr": [{"name": b["name"], "spill":"0","void_":"0","open_bar":"0"}
                     for b in beers],
        }

        for rv in self._wiz_rows:
            beer = rv["beer"]
            data["kegs"].append({
                "name":     beer["name"],
                "keg":      beer["keg"],
                "start_l":  0.0,
                "delivery": "0",
                "full_end": rv["full"].get() or "0",
                "open_end": [v.get() or None for v in rv["open"]],
            })

        db.save_day(d, data)
        messagebox.showinfo("Zapisano",
                            f"Stan początkowy na {d} zapisany ✓\n\n"
                            "Teraz możesz zacząć wpisywać codzienne dane!")
        self.show_tab("entry")

    def _is_float(self, s):
        try: float(s); return True
        except: return False

    # ══════════════════════════════════════════════
    #  ENTRY TAB
    # ══════════════════════════════════════════════
    def _build_entry(self):
        f = self._tabs["entry"]

        # Info banner
        banner = ctk.CTkFrame(f, fg_color=GREEN_BG, corner_radius=7,
                              border_width=1, border_color="#b3dfc0")
        banner.pack(fill="x", padx=18, pady=(14, 6))
        ctk.CTkLabel(
            banner,
            text="✅  START ładuje się automatycznie z poprzedniego dnia — "
                 "wpisujesz tylko stan END na koniec zmiany + sprzedaż POS.",
            font=("Segoe UI", 10), text_color=GREEN,
            wraplength=900).pack(padx=14, pady=8)

        # Date
        dc = self._card(f, "📅  Data wpisu")
        dr = ctk.CTkFrame(dc, fg_color="transparent")
        dr.pack(fill="x")
        ctk.CTkLabel(dr, text="Data:", font=("Segoe UI", 11),
                     text_color=MUTED).pack(side="left", padx=(0, 8))
        self.ev_date = ctk.StringVar(value=str(date.today()))
        ctk.CTkEntry(dr, textvariable=self.ev_date, width=145,
                     font=("Consolas", 11)).pack(side="left")
        for lbl, delta in [("← Wczoraj", -1), ("Dzisiaj →", 0)]:
            ctk.CTkButton(
                dr, text=lbl, width=100, height=28,
                font=("Segoe UI", 10), fg_color=GOLD_BG, text_color=GOLD,
                hover_color=BORDER, border_width=1, border_color=BORDER,
                command=lambda d=delta: self.ev_date.set(
                    str(date.today() + timedelta(days=d)))).pack(
                side="left", padx=5)
        self.ev_date.trace_add("write", lambda *_: self._load_prev_starts())

        # Kegs
        kc = self._card(f, "🛢  Stan kegów — koniec zmiany")
        ctk.CTkLabel(
            kc,
            text="szare = START auto z poprzedniego dnia  |  "
                 "żółte = dostawa  |  Tara: 30L=11kg, 20L=7kg",
            font=("Segoe UI", 10), text_color=MUTED).pack(
            anchor="w", pady=(0, 8))
        self._kegs_frame = ctk.CTkFrame(kc, fg_color="transparent")
        self._kegs_frame.pack(fill="x")

        # POS
        pc = self._card(f, "💻  Sprzedaż POS — sztuki → litry")
        self._pos_total_lbl = ctk.CTkLabel(pc, text="Łącznie: 0.00 L",
                                            font=("Segoe UI", 10),
                                            text_color=MUTED)
        self._pos_total_lbl.pack(anchor="e", pady=(0, 6))
        self._pos_frame = ctk.CTkFrame(pc, fg_color="transparent")
        self._pos_frame.pack(fill="x")

        # Corrections
        cc = self._card(f, "⚠️  Korekty — Spill / Void / Open Bar (litry)")
        self._corr_total_lbl = ctk.CTkLabel(cc, text="Łącznie: 0.00 L",
                                             font=("Segoe UI", 10),
                                             text_color=MUTED)
        self._corr_total_lbl.pack(anchor="e", pady=(0, 6))
        self._corr_frame = ctk.CTkFrame(cc, fg_color="transparent")
        self._corr_frame.pack(fill="x")

        # Summary
        sc2 = self._card(f, "📊  Wynik dnia")
        self._sum_frame = ctk.CTkFrame(sc2, fg_color="transparent")
        self._sum_frame.pack(fill="x")

        # Legend
        lc = self._card(f, "📖  Legenda")
        leg_f = ctk.CTkFrame(lc, fg_color="transparent")
        leg_f.pack(fill="x")
        for status, (col, bg) in DIFF_COLORS.items():
            chip = ctk.CTkFrame(leg_f, fg_color=bg, corner_radius=8)
            chip.pack(side="left", padx=(0, 10), pady=2)
            ctk.CTkLabel(chip,
                         text=f"  {DIFF_ICONS[status]} {DIFF_TEXTS[status]}  ",
                         font=("Segoe UI", 10), text_color=col).pack(
                padx=6, pady=3)

        # Buttons
        br = ctk.CTkFrame(f, fg_color="transparent")
        br.pack(fill="x", padx=18, pady=(4, 18))
        ctk.CTkButton(br, text="💾  Zapisz dzień", width=180, height=40,
                      font=("Segoe UI", 11, "bold"), fg_color=GOLD,
                      hover_color=GOLD_LT,
                      command=self._save_day).pack(side="left", padx=(0, 10))
        ctk.CTkButton(br, text="🔄  Przelicz", width=120, height=40,
                      font=("Segoe UI", 11), fg_color=GOLD_BG,
                      text_color=GOLD, hover_color=BORDER,
                      border_width=1, border_color=BORDER,
                      command=self._recalc).pack(side="left", padx=(0, 10))
        ctk.CTkButton(br, text="🗑  Wyczyść", width=120, height=40,
                      font=("Segoe UI", 11), fg_color=SURFACE,
                      text_color=MUTED, hover_color=BORDER,
                      border_width=1, border_color=BORDER,
                      command=self._clear).pack(side="left")

        self._kw = []
        self._pw = []
        self._cw = []

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
        hdrs = ["Piwo", "START\n(auto)", "DOSTAWA\n(kegi)",
                "PEŁNE", "Otw.kg#1", "Otw.kg#2", "Otw.kg#3", "END (L)"]
        widths = [115, 90, 75, 75, 82, 82, 82, 85]
        for ci, (h, w) in enumerate(zip(hdrs, widths)):
            ctk.CTkLabel(f, text=h, font=("Segoe UI", 9, "bold"),
                         text_color=GOLD, width=w, anchor="center",
                         justify="center").grid(row=0, column=ci,
                                                padx=2, pady=(0, 4))
        for ri, beer in enumerate(beers):
            rv = {"beer": beer}
            ctk.CTkLabel(f, text=f"{beer['name']}\n({beer['keg']}L)",
                         font=("Segoe UI", 11, "bold"), text_color=TEXT,
                         width=115, anchor="w").grid(
                row=ri+1, column=0, padx=2, pady=3)
            rv["start_lbl"] = ctk.CTkLabel(
                f, text="—", font=("Consolas", 11), text_color=GOLD,
                width=90, fg_color=PREV_BG, corner_radius=5, anchor="center")
            rv["start_lbl"].grid(row=ri+1, column=1, padx=2, pady=3)
            rv["delivery"] = ctk.StringVar()
            e = ctk.CTkEntry(f, textvariable=rv["delivery"], width=75,
                             height=30, font=("Consolas", 11),
                             fg_color=GOLD_BG, placeholder_text="0")
            e.grid(row=ri+1, column=2, padx=2, pady=3)
            e.bind("<KeyRelease>", lambda _: self._recalc())
            rv["full_end"] = ctk.StringVar()
            e2 = ctk.CTkEntry(f, textvariable=rv["full_end"], width=75,
                              height=30, font=("Consolas", 11),
                              placeholder_text="0")
            e2.grid(row=ri+1, column=3, padx=2, pady=3)
            e2.bind("<KeyRelease>", lambda _: self._recalc())
            rv["open_end"] = []
            for j in range(3):
                ov = ctk.StringVar()
                oe = ctk.CTkEntry(f, textvariable=ov, width=82, height=30,
                                  font=("Consolas", 11), placeholder_text="—")
                oe.grid(row=ri+1, column=4+j, padx=2, pady=3)
                oe.bind("<KeyRelease>", lambda _: self._recalc())
                rv["open_end"].append(ov)
            rv["end_lbl"] = ctk.CTkLabel(
                f, text="—", font=("Consolas", 11), text_color=GOLD,
                width=85, anchor="center")
            rv["end_lbl"].grid(row=ri+1, column=7, padx=2, pady=3)
            self._kw.append(rv)

    def _build_pos_inputs(self, beers, sizes):
        f = self._pos_frame
        for w in f.winfo_children(): w.destroy()
        self._pw = []
        ctk.CTkLabel(f, text="Piwo", font=("Segoe UI", 9, "bold"),
                     text_color=GOLD, width=110).grid(row=0, column=0, padx=2)
        for si, sz in enumerate(sizes):
            ctk.CTkLabel(f, text=sz["label"],
                         font=("Segoe UI", 9, "bold"), text_color=GOLD,
                         width=80).grid(row=0, column=si+1, padx=2)
        ctk.CTkLabel(f, text="Razem (L)",
                     font=("Segoe UI", 9, "bold"), text_color=GOLD,
                     width=90).grid(row=0, column=len(sizes)+1, padx=2)
        for ri, beer in enumerate(beers):
            ctk.CTkLabel(f, text=beer["name"], font=("Segoe UI", 11, "bold"),
                         width=110, anchor="w").grid(
                row=ri+1, column=0, padx=2, pady=3)
            svars = []
            for si, sz in enumerate(sizes):
                sv = ctk.StringVar()
                e = ctk.CTkEntry(f, textvariable=sv, width=80, height=28,
                                 font=("Consolas", 11), placeholder_text="0")
                e.grid(row=ri+1, column=si+1, padx=2, pady=3)
                e.bind("<KeyRelease>", lambda _: self._recalc())
                svars.append({"var": sv, "liters": sz["liters"]})
            lbl = ctk.CTkLabel(f, text="0.00 L", font=("Consolas", 11),
                               text_color=GOLD, width=90, anchor="center")
            lbl.grid(row=ri+1, column=len(sizes)+1, padx=2, pady=3)
            self._pw.append({"name": beer["name"], "sizes": svars, "lbl": lbl})

    def _build_corr_inputs(self, beers):
        f = self._corr_frame
        for w in f.winfo_children(): w.destroy()
        self._cw = []
        for ci, h in enumerate(["Piwo","Spill (L)","Void (L)",
                                  "Open Bar (L)","Razem (L)"]):
            ctk.CTkLabel(f, text=h, font=("Segoe UI", 9, "bold"),
                         text_color=GOLD, width=110).grid(
                row=0, column=ci, padx=2)
        for ri, beer in enumerate(beers):
            ctk.CTkLabel(f, text=beer["name"],
                         font=("Segoe UI", 11, "bold"), width=110,
                         anchor="w").grid(row=ri+1, column=0, padx=2, pady=3)
            cv = {}
            for ci, field in enumerate(["spill","void_","open_bar"], 1):
                v = ctk.StringVar()
                e = ctk.CTkEntry(f, textvariable=v, width=110, height=28,
                                 font=("Consolas", 11), placeholder_text="0")
                e.grid(row=ri+1, column=ci, padx=2, pady=3)
                e.bind("<KeyRelease>", lambda _: self._recalc())
                cv[field] = v
            lbl = ctk.CTkLabel(f, text="−0.00 L", font=("Consolas", 11),
                               text_color=RED, width=110, anchor="center")
            lbl.grid(row=ri+1, column=4, padx=2, pady=3)
            cv["lbl"] = lbl; cv["name"] = beer["name"]
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
            rw["start_lbl"].configure(text=f"{val:.2f} L")

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
            rw["end_lbl"].configure(text=f"{end_l:.2f} L")
        pos_grand = 0
        for i, pw in enumerate(self._pw):
            t = db.pos_liters(data["pos"][i]); pos_grand += t
            pw["lbl"].configure(text=f"{t:.2f} L")
        self._pos_total_lbl.configure(text=f"Łącznie: {pos_grand:.2f} L")
        corr_grand = 0
        for i, cw in enumerate(self._cw):
            t = db.corr_liters(data["corr"][i]); corr_grand += t
            cw["lbl"].configure(text=f"−{t:.2f} L")
        self._corr_total_lbl.configure(
            text=f"Łącznie: {corr_grand:.2f} L")
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
            row = ctk.CTkFrame(f, fg_color=SURFACE, corner_radius=6,
                               border_width=1, border_color=BORDER)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=keg["name"],
                         font=("Segoe UI", 11, "bold"),
                         width=100, anchor="w").pack(
                side="left", padx=12, pady=6)
            for lbl, val in [
                ("START", f"{db.keg_start_liters(keg):.1f}L"),
                ("Del",   f"+{db.keg_delivery_liters(keg):.0f}L"),
                ("END",   f"{db.keg_end_liters(keg):.1f}L"),
                ("POS",   f"{db.pos_liters(pe):.1f}L"),
                ("Kor",   f"−{db.corr_liters(co):.1f}L"),
            ]:
                ctk.CTkLabel(row, text=f"{lbl}: {val}",
                             font=("Segoe UI", 10),
                             text_color=MUTED).pack(side="left", padx=8)
            chip = ctk.CTkFrame(row, fg_color=bg, corner_radius=10)
            chip.pack(side="right", padx=12, pady=6)
            ctk.CTkLabel(chip,
                         text=f"  {DIFF_ICONS[s]} {diff:+.2f}L  ",
                         font=("Segoe UI", 11, "bold"),
                         text_color=col).pack(padx=4, pady=2)

        ts = db.diff_status(tot_diff)
        tcol, tbg = DIFF_COLORS[ts]
        tot = ctk.CTkFrame(f, fg_color=GOLD_BG, corner_radius=6,
                           border_width=1, border_color=GOLD_LT)
        tot.pack(fill="x", pady=(6, 0))
        ctk.CTkLabel(tot, text="ŁĄCZNIE",
                     font=("Segoe UI", 12, "bold"),
                     text_color=GOLD).pack(side="left", padx=14, pady=8)
        ctk.CTkLabel(
            tot,
            text=f"POS: {sum(db.pos_liters(p) for p in data['pos']):.1f}L",
            font=("Segoe UI", 11), text_color=MUTED).pack(
            side="left", padx=12)
        chip = ctk.CTkFrame(tot, fg_color=tbg, corner_radius=10)
        chip.pack(side="right", padx=14, pady=8)
        ctk.CTkLabel(chip,
                     text=f"  {DIFF_ICONS[ts]} {tot_diff:+.2f}L  ",
                     font=("Segoe UI", 13, "bold"),
                     text_color=tcol).pack(padx=6, pady=3)

    def _save_day(self):
        d = self.ev_date.get().strip()
        if not d: messagebox.showerror("Błąd","Wpisz datę!"); return
        data = self._collect()
        db.save_day(d, data)
        messagebox.showinfo("Zapisano", f"Dzień {d} zapisany ✓")

    def _clear(self):
        if not messagebox.askyesno("Wyczyścić?",
                                    "Wyczyścić wszystkie pola?"): return
        for rw in self._kw:
            rw["delivery"].set(""); rw["full_end"].set("")
            for v in rw["open_end"]: v.set("")
        for pw in self._pw:
            for sv in pw["sizes"]: sv["var"].set("")
        for cw in self._cw:
            for fld in ["spill","void_","open_bar"]: cw[fld].set("")
        self._recalc()

    # ══════════════════════════════════════════════
    #  HISTORY TAB
    # ══════════════════════════════════════════════
    def _build_history(self):
        f = self._tabs["history"]
        top = ctk.CTkFrame(f, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(14, 8))
        ctk.CTkLabel(top, text="Miesiąc:", font=("Segoe UI", 11),
                     text_color=MUTED).pack(side="left", padx=(0, 8))
        self._hist_month = ctk.StringVar()
        self._hist_cb = ctk.CTkOptionMenu(
            top, variable=self._hist_month, values=["(brak)"], width=240,
            command=lambda _: self._render_history())
        self._hist_cb.pack(side="left")
        self._hist_list = ctk.CTkFrame(f, fg_color="transparent")
        self._hist_list.pack(fill="both", expand=True, padx=18)

    def _load_history(self):
        months = db.get_months()
        if months:
            labels = [self._fmt_month(m)+f"  [{m}]" for m in months]
            self._hist_cb.configure(values=labels)
            if self._hist_month.get() not in labels:
                self._hist_month.set(labels[0])
        else:
            self._hist_cb.configure(values=["(brak)"])
            self._hist_month.set("(brak)")
        self._render_history()

    def _render_history(self):
        for w in self._hist_list.winfo_children(): w.destroy()
        val = self._hist_month.get()
        if "(brak)" in val: return
        month = val.split("[")[-1].rstrip("]").strip()
        entries = db.get_days_for_month(month)
        if not entries:
            ctk.CTkLabel(self._hist_list, text="Brak wpisów.",
                         font=("Segoe UI", 11),
                         text_color=MUTED).pack(pady=30)
            return
        for entry_date, data in reversed(entries):
            self._hist_card(entry_date, data)

    def _hist_card(self, entry_date, data):
        beers   = data.get("kegs", [])
        tot_diff = sum(
            db.calc_diff(k,
                         data["pos"][i]  if i<len(data.get("pos",[])) else {"sizes":[]},
                         data["corr"][i] if i<len(data.get("corr",[])) else {})
            for i, k in enumerate(beers))
        tot_pos = sum(db.pos_liters(p) for p in data.get("pos", []))
        tot_del = sum(int(k.get("delivery",0) or 0) for k in beers)
        status  = db.diff_status(tot_diff)
        col, bg = DIFF_COLORS[status]

        card = ctk.CTkFrame(self._hist_list, fg_color=SURFACE,
                            corner_radius=8, border_width=1,
                            border_color=BORDER)
        card.pack(fill="x", pady=4)

        hdr = ctk.CTkFrame(card, fg_color="#f0ede6", corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text=self._fmt_date(entry_date),
                     font=("Segoe UI", 11, "bold")).pack(
            side="left", padx=14, pady=8)
        if tot_del:
            ctk.CTkLabel(hdr, text=f"🚚 Dostawa: {tot_del} keg",
                         font=("Segoe UI", 10), text_color=GOLD,
                         fg_color=GOLD_BG, corner_radius=5).pack(
                side="left", padx=6)
        ctk.CTkLabel(hdr, text=f"POS: {tot_pos:.1f}L",
                     font=("Segoe UI", 10),
                     text_color=MUTED).pack(side="right", padx=14)
        chip = ctk.CTkFrame(hdr, fg_color=bg, corner_radius=10)
        chip.pack(side="right", padx=6, pady=8)
        ctk.CTkLabel(chip,
                     text=f"  {DIFF_ICONS[status]} {tot_diff:+.2f}L  ",
                     font=("Segoe UI", 11, "bold"),
                     text_color=col).pack(padx=4, pady=2)

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=14, pady=10)

        for i, keg in enumerate(beers):
            pe   = data["pos"][i]  if i<len(data.get("pos",[])) else {"sizes":[]}
            co   = data["corr"][i] if i<len(data.get("corr",[])) else {}
            diff = db.calc_diff(keg, pe, co)
            s    = db.diff_status(diff)
            c, _ = DIFF_COLORS[s]
            br   = ctk.CTkFrame(body, fg_color="transparent")
            br.pack(fill="x", pady=1)
            ctk.CTkLabel(br, text=keg["name"], font=("Segoe UI", 10),
                         width=90, anchor="w").pack(side="left")
            ctk.CTkLabel(br, text=f"{DIFF_ICONS[s]} {diff:+.2f}L",
                         font=("Consolas", 10), text_color=c,
                         width=90, anchor="e").pack(side="right")

        btn_f = ctk.CTkFrame(body, fg_color="transparent")
        btn_f.pack(fill="x", pady=(8, 0))
        det_frame = ctk.CTkFrame(body, fg_color="transparent")
        state = {"open": False}

        def toggle_det():
            if state["open"]:
                det_frame.pack_forget(); state["open"] = False
                det_btn.configure(text="🔍 Pokaż szczegóły")
            else:
                self._build_det_table(det_frame, data)
                det_frame.pack(fill="x"); state["open"] = True
                det_btn.configure(text="🔍 Ukryj szczegóły")

        det_btn = ctk.CTkButton(
            btn_f, text="🔍 Pokaż szczegóły", width=160, height=30,
            font=("Segoe UI", 10), fg_color=GOLD_BG, text_color=GOLD,
            hover_color=BORDER, border_width=1, border_color=BORDER,
            command=toggle_det)
        det_btn.pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            btn_f, text="✏️ Edytuj", width=110, height=30,
            font=("Segoe UI", 10), fg_color=GOLD, hover_color=GOLD_LT,
            command=lambda: self._open_edit(entry_date, data)).pack(
            side="left")

    def _build_det_table(self, parent, data):
        for w in parent.winfo_children(): w.destroy()
        sizes = db.get_sizes()
        frm = ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=6,
                           border_width=1, border_color=BORDER)
        frm.pack(fill="x", pady=(8, 0))
        hdrs = (["Piwo","START","Del","Pełne END",
                 "kg#1","kg#2","kg#3","END(L)"] +
                [sz["label"] for sz in sizes] +
                ["Spill","Void","Open Bar","RÓŻNICA"])
        for ci, h in enumerate(hdrs):
            ctk.CTkLabel(frm, text=h, font=("Segoe UI", 8, "bold"),
                         text_color=GOLD, anchor="center").grid(
                row=0, column=ci, padx=3, pady=4, sticky="ew")
        for ri, keg in enumerate(data.get("kegs", [])):
            pe   = data["pos"][ri]  if ri<len(data.get("pos",[])) else {"sizes":[]}
            co   = data["corr"][ri] if ri<len(data.get("corr",[])) else {}
            diff = db.calc_diff(keg, pe, co)
            s    = db.diff_status(diff)
            col, bg = DIFF_COLORS[s]
            ow = keg.get("open_end") or [None,None,None]
            vals = ([keg["name"],
                     f"{db.keg_start_liters(keg):.1f}",
                     str(keg.get("delivery",0)),
                     str(keg.get("full_end",0)),
                     str(ow[0] or "—"),
                     str(ow[1] if len(ow)>1 else "—"),
                     str(ow[2] if len(ow)>2 else "—"),
                     f"{db.keg_end_liters(keg):.2f}"] +
                    [str(sz.get("qty",0) or 0)
                     for sz in pe.get("sizes",[])] +
                    [str(co.get("spill",0) or 0),
                     str(co.get("void_",0) or 0),
                     str(co.get("open_bar",0) or 0),
                     f"{DIFF_ICONS[s]} {diff:+.2f}L"])
            for ci, v in enumerate(vals):
                is_diff = ci == len(vals)-1
                lbl = ctk.CTkLabel(
                    frm, text=v, font=("Segoe UI", 9),
                    anchor="center",
                    text_color=(col if is_diff else TEXT),
                    fg_color=(bg if is_diff else "transparent"),
                    corner_radius=(4 if is_diff else 0))
                lbl.grid(row=ri+1, column=ci, padx=3, pady=2, sticky="ew")

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
            rw["start_lbl"].configure(text=f"{rw['_start_l']:.2f} L")
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
    #  REPORT TAB
    # ══════════════════════════════════════════════
    def _build_report(self):
        f = self._tabs["report"]
        top = ctk.CTkFrame(f, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(14, 8))
        ctk.CTkLabel(top, text="Miesiąc:", font=("Segoe UI", 11),
                     text_color=MUTED).pack(side="left", padx=(0, 8))
        self._rep_month = ctk.StringVar()
        self._rep_cb = ctk.CTkOptionMenu(
            top, variable=self._rep_month, values=["(brak)"], width=240,
            command=lambda _: self._render_report())
        self._rep_cb.pack(side="left", padx=(0, 12))
        ctk.CTkButton(top, text="📥 Export Excel (miesiąc)", width=200,
                      height=34, font=("Segoe UI", 11), fg_color=GOLD,
                      hover_color=GOLD_LT,
                      command=self._export_month).pack(side="left", padx=(0,8))
        ctk.CTkButton(top, text="📥 Export Excel (rok)", width=180,
                      height=34, font=("Segoe UI", 11), fg_color=GOLD_BG,
                      text_color=GOLD, hover_color=BORDER,
                      border_width=1, border_color=BORDER,
                      command=self._export_year).pack(side="left")
        self._rep_body = ctk.CTkFrame(f, fg_color="transparent")
        self._rep_body.pack(fill="both", expand=True, padx=18)

    def _load_report(self):
        months = db.get_months()
        if months:
            labels = [self._fmt_month(m)+f"  [{m}]" for m in months]
            self._rep_cb.configure(values=labels)
            if self._rep_month.get() not in labels:
                self._rep_month.set(labels[0])
        else:
            self._rep_cb.configure(values=["(brak)"])
            self._rep_month.set("(brak)")
        self._render_report()

    def _render_report(self):
        for w in self._rep_body.winfo_children(): w.destroy()
        val = self._rep_month.get()
        if "(brak)" in val: return
        month   = val.split("[")[-1].rstrip("]").strip()
        entries = db.get_days_for_month(month)
        if not entries:
            ctk.CTkLabel(self._rep_body, text="Brak wpisów.",
                         font=("Segoe UI", 11),
                         text_color=MUTED).pack(pady=30)
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
            for _,d in entries for i,k in enumerate(d.get("kegs",[])))

        kpi_f = ctk.CTkFrame(self._rep_body, fg_color="transparent")
        kpi_f.pack(fill="x", pady=(0,14))
        ts = db.diff_status(tot_diff); tcol, tbg = DIFF_COLORS[ts]
        for lbl, val2, col in [
            ("Dni wpisów",   str(tot_days),           GOLD),
            ("Dostawa",      f"{tot_del} keg",         GOLD),
            ("Sprzedaż POS", f"{tot_pos:.1f} L",       TEXT),
            ("Korekty",      f"{tot_corr:.1f} L",      TEXT),
            ("Różnica",      f"{DIFF_ICONS[ts]} {tot_diff:+.1f} L", tcol),
        ]:
            kpi = ctk.CTkFrame(kpi_f, fg_color=SURFACE, corner_radius=8,
                               border_width=1, border_color=BORDER)
            kpi.pack(side="left", padx=(0,8), fill="y")
            ctk.CTkLabel(kpi, text=lbl, font=("Segoe UI", 10),
                         text_color=MUTED).pack(padx=14, pady=(10,2))
            ctk.CTkLabel(kpi, text=val2,
                         font=("Segoe UI", 20, "bold"),
                         text_color=col).pack(padx=14, pady=(0,10))

        self._sec_label(self._rep_body, "Wynik per piwo")
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
            diff = round(a["diff"],2); s=db.diff_status(diff); col,bg=DIFF_COLORS[s]
            row = ctk.CTkFrame(self._rep_body, fg_color=SURFACE,
                               corner_radius=6, border_width=1,
                               border_color=BORDER)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=n, font=("Segoe UI", 11, "bold"),
                         width=100, anchor="w").pack(side="left", padx=12, pady=7)
            ctk.CTkLabel(row,
                         text=f"POS: {a['pos']:.1f}L | "
                              f"Del: {a['del']} keg | {a['days']} dni",
                         font=("Segoe UI", 10),
                         text_color=MUTED).pack(side="left", padx=8)
            chip = ctk.CTkFrame(row, fg_color=bg, corner_radius=10)
            chip.pack(side="right", padx=12, pady=7)
            ctk.CTkLabel(chip,
                         text=f"  {DIFF_ICONS[s]} {diff:+.1f}L  ",
                         font=("Segoe UI", 11, "bold"),
                         text_color=col).pack(padx=4, pady=2)

        self._sec_label(self._rep_body, "Trend dzienny")
        for entry_date, data in entries:
            d_diff = sum(
                db.calc_diff(k,
                             data["pos"][i]  if i<len(data.get("pos",[])) else {"sizes":[]},
                             data["corr"][i] if i<len(data.get("corr",[])) else {})
                for i,k in enumerate(data.get("kegs",[])))
            s = db.diff_status(d_diff); col,_ = DIFF_COLORS[s]
            tr = ctk.CTkFrame(self._rep_body, fg_color="transparent")
            tr.pack(fill="x", pady=1)
            ctk.CTkLabel(tr, text=self._fmt_date(entry_date),
                         font=("Segoe UI", 10), text_color=MUTED,
                         width=80).pack(side="left")
            ctk.CTkLabel(tr,
                         text=f"{DIFF_ICONS[s]} {d_diff:+.2f}L",
                         font=("Consolas", 10), text_color=col,
                         width=100, anchor="e").pack(side="right")
            track = ctk.CTkFrame(tr, fg_color="#eeebe4", height=8,
                                 corner_radius=4)
            track.pack(side="left", fill="x", expand=True, padx=8)

    def _export_month(self):
        val = self._rep_month.get()
        if "(brak)" in val:
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
    #  SETTINGS TAB
    # ══════════════════════════════════════════════
    def _build_settings(self):
        f = self._tabs["settings"]
        c1 = self._card(f, "🍺  Piwa na krane")
        self._set_beers_f = ctk.CTkFrame(c1, fg_color="transparent")
        self._set_beers_f.pack(fill="x")
        ctk.CTkButton(c1, text="+ Dodaj piwo", width=130, height=30,
                      font=("Segoe UI", 10), fg_color=GOLD_BG,
                      text_color=GOLD, hover_color=BORDER,
                      border_width=1, border_color=BORDER,
                      command=self._add_beer).pack(anchor="w", pady=(8,0))

        c2 = self._card(f, "🥃  Rozmiary porcji POS")
        self._set_sizes_f = ctk.CTkFrame(c2, fg_color="transparent")
        self._set_sizes_f.pack(fill="x")
        ctk.CTkButton(c2, text="+ Dodaj rozmiar", width=140, height=30,
                      font=("Segoe UI", 10), fg_color=GOLD_BG,
                      text_color=GOLD, hover_color=BORDER,
                      border_width=1, border_color=BORDER,
                      command=self._add_size).pack(anchor="w", pady=(8,0))

        ctk.CTkButton(f, text="💾  Zapisz ustawienia", width=200, height=40,
                      font=("Segoe UI", 11, "bold"), fg_color=GOLD,
                      hover_color=GOLD_LT,
                      command=self._save_settings).pack(
            padx=18, pady=14, anchor="w")

        # Reset wizard button
        ctk.CTkButton(f, text="🔄  Uruchom ponownie kreator pierwszego uruchomienia",
                      width=360, height=36, font=("Segoe UI", 10),
                      fg_color=SURFACE, text_color=MUTED,
                      hover_color=BORDER, border_width=1,
                      border_color=BORDER,
                      command=self._rerun_wizard).pack(
            padx=18, anchor="w")

        self._beer_rows = []
        self._size_rows = []

    def _load_settings(self):
        self._render_beer_settings(db.get_beers())
        self._render_size_settings(db.get_sizes())

    def _render_beer_settings(self, beers):
        for w in self._set_beers_f.winfo_children(): w.destroy()
        self._beer_rows = []
        for b in beers:
            nv = ctk.StringVar(value=b["name"])
            kv = ctk.StringVar(value=str(b["keg"]))
            row = ctk.CTkFrame(self._set_beers_f, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkEntry(row, textvariable=nv, width=180, height=30,
                         font=("Segoe UI", 11)).pack(side="left", padx=(0,8))
            ctk.CTkOptionMenu(row, variable=kv, values=["20","30","50"],
                              width=110).pack(side="left", padx=(0,6))
            ctk.CTkLabel(row, text="L keg", font=("Segoe UI", 10),
                         text_color=MUTED).pack(side="left", padx=(0,10))
            ctk.CTkButton(row, text="✕", width=30, height=28,
                          font=("Segoe UI", 11), fg_color=RED_BG,
                          text_color=RED, hover_color="#f5c0c0",
                          command=lambda r=row: r.destroy()).pack(side="left")
            self._beer_rows.append((nv, kv))

    def _render_size_settings(self, sizes):
        for w in self._set_sizes_f.winfo_children(): w.destroy()
        self._size_rows = []
        for s in sizes:
            lv  = ctk.StringVar(value=s["label"])
            lv2 = ctk.StringVar(value=str(s["liters"]))
            row = ctk.CTkFrame(self._set_sizes_f, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkEntry(row, textvariable=lv, width=80, height=30,
                         font=("Consolas", 11)).pack(side="left", padx=(0,8))
            ctk.CTkEntry(row, textvariable=lv2, width=80, height=30,
                         font=("Consolas", 11)).pack(side="left", padx=(0,6))
            ctk.CTkLabel(row, text="L/szt.", font=("Segoe UI", 10),
                         text_color=MUTED).pack(side="left", padx=(0,10))
            ctk.CTkButton(row, text="✕", width=30, height=28,
                          font=("Segoe UI", 11), fg_color=RED_BG,
                          text_color=RED, hover_color="#f5c0c0",
                          command=lambda r=row: r.destroy()).pack(side="left")
            self._size_rows.append((lv, lv2))

    def _add_beer(self):
        current = db.get_beers()
        current.append({"name":"NOWE","keg":20})
        self._render_beer_settings(current)

    def _add_size(self):
        current = db.get_sizes()
        current.append({"label":"0.5L","liters":0.5})
        self._render_size_settings(current)

    def _save_settings(self):
        beers, sizes = [], []
        for row in self._set_beers_f.winfo_children():
            ws = row.winfo_children()
            try:
                name = ws[0].get().strip().upper()
                keg  = int(ws[1].get())
                if name: beers.append({"name":name,"keg":keg})
            except: pass
        for row in self._set_sizes_f.winfo_children():
            ws = row.winfo_children()
            try:
                lbl = ws[0].get().strip()
                lit = float(ws[1].get())
                if lbl: sizes.append({"label":lbl,"liters":lit})
            except: pass
        db.save_beers(beers); db.save_sizes(sizes)
        messagebox.showinfo("Zapisano","Ustawienia zapisane ✓")

    def _rerun_wizard(self):
        self._build_wizard()
        self._show_tab_instant("wizard")

    # ── Helpers ───────────────────────────────────
    def _card(self, parent, title):
        outer = ctk.CTkFrame(parent, fg_color="transparent")
        outer.pack(fill="x", padx=18, pady=(0, 12))
        card = ctk.CTkFrame(outer, fg_color=SURFACE, corner_radius=8,
                            border_width=1, border_color=BORDER)
        card.pack(fill="x")
        ctk.CTkLabel(card, text=title, font=("Segoe UI", 13, "bold"),
                     text_color=GOLD).pack(anchor="w", padx=16,
                                            pady=(12, 4))
        ctk.CTkFrame(card, fg_color=BORDER, height=1,
                     corner_radius=0).pack(fill="x")
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=10)
        return inner

    def _sec_label(self, parent, title):
        ctk.CTkLabel(parent, text=title, font=("Segoe UI", 13, "bold"),
                     text_color=GOLD).pack(anchor="w", pady=(12, 4))
        ctk.CTkFrame(parent, fg_color=BORDER, height=1,
                     corner_radius=0).pack(fill="x", pady=(0, 6))

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
