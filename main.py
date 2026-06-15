"""
main.py — Beer Count HRC Warsaw v4 (PyQt6)
PyQt6 GUI + SQLite. No canvas glitches, native Windows rendering.
database.py and export_excel.py unchanged.
"""
from __future__ import annotations
import sys
from datetime import date, timedelta, datetime

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton,
    QLineEdit, QComboBox, QScrollArea, QStackedWidget, QMessageBox,
    QFileDialog, QGridLayout, QVBoxLayout, QHBoxLayout,
)

import database as db
import export_excel as xl

# ── Colors ───────────────────────────────────────────────────────────
GOLD    = "#9a6f1e"; GOLD_LT = "#c9a84c"; GOLD_BG = "#fdf3df"
GREEN   = "#2a7a45"; GREEN_BG= "#eaf6ee"
RED     = "#b83232"; RED_BG  = "#fdeaea"
AMBER   = "#a06010"; AMBER_BG= "#fff4e0"
ORANGE  = "#c05000"; ORANGE_BG="#fff0e0"
BG      = "#f5f2ec"; SURFACE = "#ffffff"
BORDER  = "#ddd8ce"; MUTED   = "#7a7265"; TEXT = "#1a1a1a"
PREV_BG = "#f0ede6"

DIFF_COLORS = {
    "ok":   (GREEN,  GREEN_BG),
    "warn": (AMBER,  AMBER_BG),
    "over": (ORANGE, ORANGE_BG),
    "bad":  (RED,    RED_BG),
}
DIFF_ICONS = {"ok": "✅", "warn": "🟡", "over": "🟠", "bad": "🔴"}
DIFF_TEXTS = {
    "ok":   "Norma (±2L)",
    "warn": "+2/+5L — Sprawdź",
    "over": ">+5L — Sprzedaż poza POS?",
    "bad":  "<−5L — Straty/spille",
}


# ── Widget factories ─────────────────────────────────────────────────
def _lbl(text: str, size: int = 10, bold: bool = False,
         color: str = TEXT) -> QLabel:
    w = QLabel(text)
    f = QFont("Segoe UI", size)
    f.setBold(bold)
    w.setFont(f)
    w.setStyleSheet(f"color:{color};background:transparent;")
    return w


def _btn(text: str, bg: str = GOLD, fg: str = "white",
         w: int = 0, h: int = 36, bold: bool = True,
         border: str = "") -> QPushButton:
    b = QPushButton(text)
    if w: b.setFixedWidth(w)
    b.setFixedHeight(h)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    border_css = f"border:1px solid {border};" if border else "border:none;"
    weight = "bold" if bold else "normal"
    b.setStyleSheet(f"""
        QPushButton{{background:{bg};color:{fg};{border_css}
            border-radius:6px;padding:0 12px;
            font-family:'Segoe UI';font-size:11px;font-weight:{weight};}}
        QPushButton:hover{{background:{_dk(bg)};}}
    """)
    return b


def _entry(w: int = 100, h: int = 30, ph: str = "",
           bg: str = SURFACE, mono: bool = True) -> QLineEdit:
    e = QLineEdit()
    e.setFixedWidth(w); e.setFixedHeight(h)
    e.setFont(QFont("Consolas" if mono else "Segoe UI", 11))
    if ph: e.setPlaceholderText(ph)
    e.setStyleSheet(
        f"background:{bg};color:{TEXT};border:1px solid {BORDER};"
        f"border-radius:4px;padding:0 6px;"
    )
    return e


def _dk(hex_c: str, a: int = 12) -> str:
    hex_c = hex_c.lstrip("#")
    r, g, b = int(hex_c[:2],16), int(hex_c[2:4],16), int(hex_c[4:],16)
    return f"#{max(0,r-a):02x}{max(0,g-a):02x}{max(0,b-a):02x}"


def _sep(vertical: bool = False) -> QFrame:
    f = QFrame()
    f.setFrameShape(
        QFrame.Shape.VLine if vertical else QFrame.Shape.HLine)
    f.setFixedHeight(1) if not vertical else f.setFixedWidth(1)
    f.setStyleSheet(f"background:{BORDER};border:none;")
    return f


def _chip_frame(text: str, fg: str, bg: str):
    """Return (QFrame, QLabel) colour chip."""
    frame = QFrame()
    frame.setStyleSheet(f"background:{bg};border-radius:10px;")
    lay = QHBoxLayout(frame)
    lay.setContentsMargins(8, 3, 8, 3)
    lbl = _lbl(text, 11, bold=True, color=fg)
    lay.addWidget(lbl)
    return frame, lbl


def _make_card(parent_lay: QVBoxLayout, title: str):
    """White card with gold title. Returns inner QVBoxLayout."""
    wrapper = QWidget(); wrapper.setStyleSheet("background:transparent;")
    wl = QVBoxLayout(wrapper); wl.setContentsMargins(18, 0, 18, 12); wl.setSpacing(0)

    card = QFrame()
    card.setStyleSheet(
        f"QFrame{{background:{SURFACE};border:1px solid {BORDER};border-radius:8px;}}")
    cl = QVBoxLayout(card); cl.setContentsMargins(0, 0, 0, 12); cl.setSpacing(0)

    tl = _lbl(title, 13, bold=True, color=GOLD)
    tl.setStyleSheet(
        f"color:{GOLD};background:transparent;padding:12px 16px 4px 16px;")
    cl.addWidget(tl)
    cl.addWidget(_sep())

    inner = QWidget(); inner.setStyleSheet("background:transparent;")
    il = QVBoxLayout(inner)
    il.setContentsMargins(16, 10, 16, 0); il.setSpacing(4)
    cl.addWidget(inner); wl.addWidget(card); parent_lay.addWidget(wrapper)
    return il


# ═════════════════════════════════════════════════════════════════════
class App(QMainWindow):
    def __init__(self):
        super().__init__()
        db.init_db()
        self.setWindowTitle("🍺 Beer Count — Hard Rock Cafe Warsaw")
        self.resize(1120, 760)
        self.setMinimumSize(800, 580)

        # State
        self._tab_cache: set[str] = set()
        self._kw: list[dict] = []
        self._pw: list[dict] = []
        self._cw: list[dict] = []
        self._sum_row_labels: list[dict] = []
        self._beer_rows: list[tuple] = []
        self._size_rows: list[tuple] = []
        self._kegs_grid_w = None
        self._pos_grid_w = None
        self._corr_grid_w = None

        root_w = QWidget(); root_w.setStyleSheet(f"background:{BG};")
        self.setCentralWidget(root_w)
        root = QVBoxLayout(root_w)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        self._build_header(root)
        self._build_nav(root)
        root.addWidget(_sep())

        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background:{BG};")
        root.addWidget(self._stack)

        self._scrolls: dict[str, QScrollArea] = {}
        self._tab_lay: dict[str, QVBoxLayout] = {}

        for key in ("wizard", "entry", "history", "report", "settings"):
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setStyleSheet(f"background:{BG};border:none;")
            inner = QWidget(); inner.setStyleSheet(f"background:{BG};")
            lay = QVBoxLayout(inner)
            lay.setContentsMargins(0, 0, 0, 20); lay.setSpacing(0)
            scroll.setWidget(inner)
            self._stack.addWidget(scroll)
            self._scrolls[key] = scroll
            self._tab_lay[key] = lay

        self._build_entry_tab()
        self._build_history_tab()
        self._build_report_tab()
        self._build_settings_tab()

        if not db.get_months() and not db.load_day(str(date.today())):
            self._build_wizard()
            self._show_raw("wizard")
        else:
            self.show_tab("entry")

    # ── Header ───────────────────────────────────────────────────────
    def _build_header(self, root: QVBoxLayout):
        h = QFrame(); h.setFixedHeight(52)
        h.setStyleSheet(
            f"background:{SURFACE};border-bottom:2px solid {GOLD_LT};")
        hl = QHBoxLayout(h); hl.setContentsMargins(16, 0, 16, 0)
        t1 = _lbl("🍺  Beer Count", 15, bold=True, color=GOLD)
        hl.addWidget(t1)
        hl.addWidget(_lbl("Hard Rock Cafe Warsaw", 10, color=MUTED))
        hl.addStretch()
        today = _lbl(date.today().strftime("%A, %d.%m.%Y"), 10, color=MUTED)
        today.setStyleSheet(
            f"color:{MUTED};background:{GOLD_BG};border-radius:10px;"
            f"padding:4px 12px;")
        hl.addWidget(today)
        root.addWidget(h)

    # ── Nav ──────────────────────────────────────────────────────────
    def _build_nav(self, root: QVBoxLayout):
        nav = QFrame(); nav.setFixedHeight(42)
        nav.setStyleSheet(f"background:{SURFACE};")
        nl = QHBoxLayout(nav); nl.setContentsMargins(0,0,0,0); nl.setSpacing(0)
        self._nav_btns: dict[str, QPushButton] = {}
        for key, label in [
            ("entry",    "📋  Wpis dnia"),
            ("history",  "📅  Historia"),
            ("report",   "📊  Raport"),
            ("settings", "⚙️  Ustawienia"),
        ]:
            b = QPushButton(label)
            b.setFixedHeight(42); b.setFixedWidth(155)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFont(QFont("Segoe UI", 11))
            b.clicked.connect(lambda _checked, k=key: self.show_tab(k))
            nl.addWidget(b); self._nav_btns[key] = b
        nl.addStretch(); root.addWidget(nav)
        self._set_nav("entry")

    def _set_nav(self, active: str):
        for k, b in self._nav_btns.items():
            if k == active:
                b.setStyleSheet(f"""QPushButton{{
                    background:{GOLD_BG};color:{GOLD};border:none;
                    border-bottom:2px solid {GOLD};
                    font-family:'Segoe UI';font-size:11px;font-weight:bold;}}""")
            else:
                b.setStyleSheet(f"""QPushButton{{
                    background:{SURFACE};color:{MUTED};border:none;
                    font-family:'Segoe UI';font-size:11px;}}
                    QPushButton:hover{{background:{GOLD_BG};}}""")

    # ── Tab switch ───────────────────────────────────────────────────
    def show_tab(self, key: str):
        self._set_nav(key)
        self._show_raw(key)
        if key not in self._tab_cache:
            loader = getattr(self, f"_load_{key}", None)
            if loader: loader()
            self._tab_cache.add(key)

    def _show_raw(self, key: str):
        self._stack.setCurrentWidget(self._scrolls[key])

    # ── Convenience ──────────────────────────────────────────────────
    def _card(self, key: str, title: str):
        return _make_card(self._tab_lay[key], title)

    # ══════════════════════════════════════════════════════════════════
    #  WIZARD
    # ══════════════════════════════════════════════════════════════════
    def _build_wizard(self):
        lay = self._tab_lay["wizard"]
        while lay.count():
            item = lay.takeAt(0)
            if item.widget(): item.widget().setParent(None)

        # Welcome banner
        bw = QWidget(); bw.setStyleSheet("background:transparent;")
        bwl = QVBoxLayout(bw); bwl.setContentsMargins(18, 20, 18, 12)
        card = QFrame()
        card.setStyleSheet(
            f"background:{SURFACE};border:1px solid {GOLD_LT};border-radius:12px;")
        cv = QVBoxLayout(card); cv.setContentsMargins(20, 18, 20, 18)
        t1 = _lbl("🍺  Witaj w Beer Count!", 18, bold=True, color=GOLD)
        t1.setAlignment(Qt.AlignmentFlag.AlignCenter); cv.addWidget(t1)
        t2 = _lbl(
            "Aby zacząć, podaj aktualny stan beczek.\n"
            "To jest potrzebne tylko raz — potem każdy dzień\n"
            "będzie się uzupełniał automatycznie z poprzedniego.",
            12, color=MUTED)
        t2.setAlignment(Qt.AlignmentFlag.AlignCenter); cv.addWidget(t2)
        bwl.addWidget(card); lay.addWidget(bw)

        # Date card
        dc = self._card("wizard", "📅  Data stanu początkowego")
        dr = QWidget(); dr.setStyleSheet("background:transparent;")
        drl = QHBoxLayout(dr); drl.setContentsMargins(0,0,0,0); drl.setSpacing(8)
        drl.addWidget(_lbl("Data:", 11, color=MUTED))
        self._wiz_date = _entry(145, ph="2025-01-01")
        self._wiz_date.setText(str(date.today()))
        drl.addWidget(self._wiz_date)
        drl.addWidget(_lbl(
            "  Wpisz datę ostatniego liczenia beczek", 10, color=MUTED))
        drl.addStretch(); dc.addWidget(dr)

        # Beers card
        bc = self._card("wizard", "🛢  Aktualny stan beczek")
        bc.addWidget(_lbl(
            "Podaj ile pełnych beczek masz teraz oraz wagę otwartych (kg brutto).\n"
            "Tara odejmowana auto: 30L = 11kg | 20L = 7kg", 10, color=MUTED))
        hdr = QFrame(); hdr.setStyleSheet(f"background:{GOLD_BG};border-radius:6px;")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(4, 6, 4, 6)
        for col, cw in [("Piwo",120),("Pełne (szt.)",100),
                         ("Otwarty kg #1",120),("Otwarty kg #2",120),
                         ("Otwarty kg #3",120),("Razem (L)",100)]:
            l = _lbl(col, 9, bold=True, color=GOLD)
            l.setFixedWidth(cw); l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hl.addWidget(l)
        hl.addStretch(); bc.addWidget(hdr)

        self._wiz_rows = []
        for beer in db.get_beers():
            rw = QWidget(); rw.setStyleSheet("background:transparent;")
            rl = QHBoxLayout(rw); rl.setContentsMargins(0,2,0,2); rl.setSpacing(4)
            nl = _lbl(f"{beer['name']}\n({beer['keg']}L)", 11, bold=True)
            nl.setFixedWidth(120); rl.addWidget(nl)
            full_e = _entry(100, ph="0"); rl.addWidget(full_e)
            open_es = []
            for _ in range(3):
                oe = _entry(120, ph="— kg"); rl.addWidget(oe); open_es.append(oe)
            res_l = _lbl("0.00 L", 11, color=GOLD)
            res_l.setFixedWidth(100)
            res_l.setAlignment(Qt.AlignmentFlag.AlignCenter); rl.addWidget(res_l)
            rl.addStretch(); bc.addWidget(rw)
            rv = {"beer": beer, "full": full_e, "open": open_es, "res": res_l}
            def make_upd(r=rv):
                def upd(_=""):
                    tara = db.TARA.get(r["beer"]["keg"], 7)
                    try: full_l = int(r["full"].text() or "0") * r["beer"]["keg"]
                    except: full_l = 0
                    open_l = 0
                    for v in r["open"]:
                        try: open_l += max(float(v.text()) - tara, 0)
                        except: pass
                    r["res"].setText(f"{full_l+open_l:.2f} L")
                return upd
            u = make_upd(rv)
            full_e.textChanged.connect(u)
            for oe in open_es: oe.textChanged.connect(u)
            self._wiz_rows.append(rv)

        # POS sizes reminder
        sc = self._card("wizard", "🥃  Rozmiary porcji POS")
        sc.addWidget(_lbl(
            "Sprawdź czy poniższe rozmiary porcji są poprawne.\n"
            "Możesz je zmienić w zakładce Ustawienia.", 10, color=MUTED))
        sf = QWidget(); sf.setStyleSheet("background:transparent;")
        sfl = QHBoxLayout(sf); sfl.setContentsMargins(0,0,0,0); sfl.setSpacing(8)
        for sz in db.get_sizes():
            ch = QFrame()
            ch.setStyleSheet(f"background:{GOLD_BG};border-radius:8px;")
            chl = QHBoxLayout(ch); chl.setContentsMargins(6,4,6,4)
            chl.addWidget(_lbl(
                f"  {sz['label']} = {sz['liters']}L  ", 11,
                bold=True, color=GOLD))
            sfl.addWidget(ch)
        sfl.addStretch(); sc.addWidget(sf)

        # Buttons
        brow = QWidget(); brow.setStyleSheet("background:transparent;")
        brl = QHBoxLayout(brow); brl.setContentsMargins(18, 8, 18, 24); brl.setSpacing(12)
        save_b = _btn("✅  Zapisz stan początkowy i zacznij!", h=46)
        save_b.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        save_b.clicked.connect(self._save_wizard); brl.addWidget(save_b)
        skip_b = _btn("Pomiń →", bg=SURFACE, fg=MUTED, w=100, h=46,
                       bold=False, border=BORDER)
        skip_b.clicked.connect(lambda: self.show_tab("entry"))
        brl.addWidget(skip_b); brl.addStretch(); lay.addWidget(brow)
        lay.addStretch()

    def _save_wizard(self):
        d = self._wiz_date.text().strip()
        if not d: QMessageBox.critical(self, "Błąd", "Wpisz datę!"); return
        beers = db.get_beers(); sizes = db.get_sizes()
        data = {
            "kegs": [],
            "pos":  [{"name": b["name"],
                       "sizes": [{"liters": sz["liters"], "qty": "0"} for sz in sizes]}
                     for b in beers],
            "corr": [{"name": b["name"], "spill":"0","void_":"0","open_bar":"0"}
                     for b in beers],
        }
        for rv in self._wiz_rows:
            beer = rv["beer"]
            data["kegs"].append({
                "name": beer["name"], "keg": beer["keg"], "start_l": 0.0,
                "delivery": "0",
                "full_end": rv["full"].text() or "0",
                "open_end": [v.text() or None for v in rv["open"]],
            })
        db.save_day(d, data)
        QMessageBox.information(
            self, "Zapisano",
            f"Stan początkowy na {d} zapisany ✓\n\n"
            "Teraz możesz zacząć wpisywać codzienne dane!")
        self.show_tab("entry")

    # ══════════════════════════════════════════════════════════════════
    #  ENTRY TAB
    # ══════════════════════════════════════════════════════════════════
    def _build_entry_tab(self):
        lay = self._tab_lay["entry"]

        # Info banner
        bw = QWidget(); bw.setStyleSheet("background:transparent;")
        bwl = QHBoxLayout(bw); bwl.setContentsMargins(18, 14, 18, 6)
        banner = QFrame()
        banner.setStyleSheet(
            f"background:{GREEN_BG};border:1px solid #b3dfc0;border-radius:7px;")
        bl = QHBoxLayout(banner); bl.setContentsMargins(14, 8, 14, 8)
        bi = _lbl(
            "✅  START ładuje się automatycznie z poprzedniego dnia — "
            "wpisujesz tylko stan END na koniec zmiany + sprzedaż POS.",
            10, color=GREEN)
        bi.setWordWrap(True); bl.addWidget(bi); bwl.addWidget(banner)
        lay.addWidget(bw)

        # Date card
        dc = self._card("entry", "📅  Data wpisu")
        dr = QWidget(); dr.setStyleSheet("background:transparent;")
        drl = QHBoxLayout(dr); drl.setContentsMargins(0,0,0,0); drl.setSpacing(8)
        drl.addWidget(_lbl("Data:", 11, color=MUTED))
        self.ev_date = _entry(145)
        self.ev_date.setText(str(date.today()))
        self.ev_date.textChanged.connect(self._load_prev_starts)
        drl.addWidget(self.ev_date)
        for txt, delta in [("← Wczoraj", -1), ("Dzisiaj →", 0)]:
            b = _btn(txt, bg=GOLD_BG, fg=GOLD, w=100, h=28, bold=False, border=BORDER)
            b.clicked.connect(
                lambda _c, d=delta:
                self.ev_date.setText(str(date.today() + timedelta(days=d))))
            drl.addWidget(b)
        drl.addStretch(); dc.addWidget(dr)

        # Kegs card
        kc = self._card("entry", "🛢  Stan kegów — koniec zmiany")
        kc.addWidget(_lbl(
            "szare = START auto z poprzedniego dnia  |  "
            "żółte = dostawa  |  Tara: 30L=11kg, 20L=7kg",
            10, color=MUTED))
        self._kegs_lay = kc

        # POS card
        pc = self._card("entry", "💻  Sprzedaż POS — sztuki → litry")
        self._pos_total_lbl = _lbl("Łącznie: 0.00 L", 10, color=MUTED)
        self._pos_total_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        pc.addWidget(self._pos_total_lbl)
        self._pos_lay = pc

        # Corr card
        cc = self._card("entry", "⚠️  Korekty — Spill / Void / Open Bar (litry)")
        self._corr_total_lbl = _lbl("Łącznie: 0.00 L", 10, color=MUTED)
        self._corr_total_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        cc.addWidget(self._corr_total_lbl)
        self._corr_lay = cc

        # Summary card
        self._sum_lay = self._card("entry", "📊  Wynik dnia")

        # Legend card
        lc = self._card("entry", "📖  Legenda")
        leg = QWidget(); leg.setStyleSheet("background:transparent;")
        legl = QHBoxLayout(leg); legl.setContentsMargins(0,0,0,0); legl.setSpacing(10)
        for status, (col, bg) in DIFF_COLORS.items():
            ch = QFrame()
            ch.setStyleSheet(f"background:{bg};border-radius:8px;")
            chl = QHBoxLayout(ch); chl.setContentsMargins(6,3,6,3)
            chl.addWidget(
                _lbl(f"  {DIFF_ICONS[status]} {DIFF_TEXTS[status]}  ", 10, color=col))
            legl.addWidget(ch)
        legl.addStretch(); lc.addWidget(leg)

        # Buttons
        brow = QWidget(); brow.setStyleSheet("background:transparent;")
        brl = QHBoxLayout(brow); brl.setContentsMargins(18,4,18,18); brl.setSpacing(10)
        sb = _btn("💾  Zapisz dzień", w=180, h=40)
        sb.clicked.connect(self._save_day); brl.addWidget(sb)
        rb = _btn("🔄  Przelicz", bg=GOLD_BG, fg=GOLD, w=120, h=40,
                   bold=False, border=BORDER)
        rb.clicked.connect(self._recalc); brl.addWidget(rb)
        cb = _btn("🗑  Wyczyść", bg=SURFACE, fg=MUTED, w=120, h=40,
                   bold=False, border=BORDER)
        cb.clicked.connect(self._clear_entry); brl.addWidget(cb)
        brl.addStretch(); lay.addWidget(brow); lay.addStretch()

    def _load_entry(self):
        beers = db.get_beers(); sizes = db.get_sizes()
        self._build_keg_inputs(beers)
        self._build_pos_inputs(beers, sizes)
        self._build_corr_inputs(beers)
        self._build_summary_rows(beers)
        self._load_prev_starts()
        self._recalc()

    def _build_keg_inputs(self, beers):
        if self._kegs_grid_w:
            self._kegs_lay.removeWidget(self._kegs_grid_w)
            self._kegs_grid_w.deleteLater()
        gw = QWidget(); gw.setStyleSheet("background:transparent;")
        g = QGridLayout(gw); g.setContentsMargins(0,0,0,0); g.setSpacing(3)
        self._kegs_grid_w = gw; self._kegs_lay.addWidget(gw)

        hdrs = ["Piwo","START\n(auto)","DOSTAWA\n(kegi)","PEŁNE",
                 "Otw.kg#1","Otw.kg#2","Otw.kg#3","END (L)"]
        widths = [115, 90, 75, 75, 82, 82, 82, 85]
        for ci, (h, cw) in enumerate(zip(hdrs, widths)):
            l = _lbl(h, 9, bold=True, color=GOLD)
            l.setFixedWidth(cw); l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            g.addWidget(l, 0, ci)

        self._kw = []
        for ri, beer in enumerate(beers):
            rv = {"beer": beer, "_start_l": 0.0}
            nl = _lbl(f"{beer['name']}\n({beer['keg']}L)", 11, bold=True)
            nl.setFixedWidth(115); g.addWidget(nl, ri+1, 0)

            sl = _lbl("—", 11, color=GOLD)
            sl.setFixedWidth(90); sl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sl.setStyleSheet(
                f"color:{GOLD};background:{PREV_BG};border-radius:5px;")
            g.addWidget(sl, ri+1, 1); rv["start_lbl"] = sl

            de = _entry(75, bg=GOLD_BG, ph="0")
            de.textChanged.connect(self._recalc)
            g.addWidget(de, ri+1, 2); rv["delivery"] = de

            fe = _entry(75, ph="0")
            fe.textChanged.connect(self._recalc)
            g.addWidget(fe, ri+1, 3); rv["full_end"] = fe

            rv["open_end"] = []
            for j in range(3):
                oe = _entry(82, ph="—")
                oe.textChanged.connect(self._recalc)
                g.addWidget(oe, ri+1, 4+j); rv["open_end"].append(oe)

            el = _lbl("—", 11, color=GOLD)
            el.setFixedWidth(85); el.setAlignment(Qt.AlignmentFlag.AlignCenter)
            g.addWidget(el, ri+1, 7); rv["end_lbl"] = el
            self._kw.append(rv)

    def _build_pos_inputs(self, beers, sizes):
        if self._pos_grid_w:
            self._pos_lay.removeWidget(self._pos_grid_w)
            self._pos_grid_w.deleteLater()
        gw = QWidget(); gw.setStyleSheet("background:transparent;")
        g = QGridLayout(gw); g.setContentsMargins(0,0,0,0); g.setSpacing(3)
        self._pos_grid_w = gw; self._pos_lay.addWidget(gw)

        h0 = _lbl("Piwo", 9, bold=True, color=GOLD)
        h0.setFixedWidth(110); g.addWidget(h0, 0, 0)
        for si, sz in enumerate(sizes):
            hl = _lbl(sz["label"], 9, bold=True, color=GOLD)
            hl.setFixedWidth(80); hl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            g.addWidget(hl, 0, si+1)
        hr = _lbl("Razem (L)", 9, bold=True, color=GOLD)
        hr.setFixedWidth(90); hr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        g.addWidget(hr, 0, len(sizes)+1)

        self._pw = []
        for ri, beer in enumerate(beers):
            nl = _lbl(beer["name"], 11, bold=True)
            nl.setFixedWidth(110); g.addWidget(nl, ri+1, 0)
            svars = []
            for si, sz in enumerate(sizes):
                e = _entry(80, h=28, ph="0")
                e.textChanged.connect(self._recalc)
                g.addWidget(e, ri+1, si+1)
                svars.append({"entry": e, "liters": sz["liters"]})
            tl = _lbl("0.00 L", 11, color=GOLD)
            tl.setFixedWidth(90); tl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            g.addWidget(tl, ri+1, len(sizes)+1)
            self._pw.append({"name": beer["name"], "sizes": svars, "lbl": tl})

    def _build_corr_inputs(self, beers):
        if self._corr_grid_w:
            self._corr_lay.removeWidget(self._corr_grid_w)
            self._corr_grid_w.deleteLater()
        gw = QWidget(); gw.setStyleSheet("background:transparent;")
        g = QGridLayout(gw); g.setContentsMargins(0,0,0,0); g.setSpacing(3)
        self._corr_grid_w = gw; self._corr_lay.addWidget(gw)

        for ci, h in enumerate(["Piwo","Spill (L)","Void (L)","Open Bar (L)","Razem (L)"]):
            hl = _lbl(h, 9, bold=True, color=GOLD)
            hl.setFixedWidth(110); hl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            g.addWidget(hl, 0, ci)

        self._cw = []
        for ri, beer in enumerate(beers):
            nl = _lbl(beer["name"], 11, bold=True)
            nl.setFixedWidth(110); g.addWidget(nl, ri+1, 0)
            cv = {"name": beer["name"]}
            for ci, field in enumerate(["spill","void_","open_bar"], 1):
                e = _entry(110, h=28, ph="0")
                e.textChanged.connect(self._recalc)
                g.addWidget(e, ri+1, ci); cv[field] = e
            tl = _lbl("−0.00 L", 11, color=RED)
            tl.setFixedWidth(110); tl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            g.addWidget(tl, ri+1, 4); cv["lbl"] = tl
            self._cw.append(cv)

    def _build_summary_rows(self, beers):
        lay = self._sum_lay
        for i in reversed(range(lay.count())):
            item = lay.itemAt(i)
            if item.widget(): item.widget().setParent(None)
        self._sum_row_labels = []

        for beer in beers:
            row = QFrame()
            row.setStyleSheet(
                f"QFrame{{background:{SURFACE};border:1px solid {BORDER};"
                f"border-radius:6px;}}")
            rl = QHBoxLayout(row); rl.setContentsMargins(12,6,12,6)
            rl.addWidget(_lbl(beer["name"], 11, bold=True))
            detail = {}
            for key in ("START","Del","END","POS","Kor"):
                l = _lbl(f"{key}: —", 10, color=MUTED); rl.addWidget(l)
                detail[key] = l
            rl.addStretch()
            chip, chip_lbl = _chip_frame("—", GREEN, GREEN_BG)
            rl.addWidget(chip); lay.addWidget(row)
            self._sum_row_labels.append(
                {"detail": detail, "chip": chip, "chip_lbl": chip_lbl})

        # Total row
        tot = QFrame()
        tot.setStyleSheet(
            f"QFrame{{background:{GOLD_BG};border:1px solid {GOLD_LT};"
            f"border-radius:6px;}}")
        tl = QHBoxLayout(tot); tl.setContentsMargins(14,8,14,8)
        tl.addWidget(_lbl("ŁĄCZNIE", 12, bold=True, color=GOLD))
        self._sum_pos_lbl = _lbl("POS: —", 11, color=MUTED)
        tl.addWidget(self._sum_pos_lbl); tl.addStretch()
        self._sum_tot_chip, self._sum_tot_lbl = _chip_frame("—", GREEN, GREEN_BG)
        tl.addWidget(self._sum_tot_chip); lay.addWidget(tot)

    def _load_prev_starts(self, _=""):
        d = self.ev_date.text().strip()
        if len(d) != 10: return
        try: datetime.strptime(d, "%Y-%m-%d")
        except ValueError: return
        prev = db.get_prev_day(d)
        if not prev: return
        pk = {k["name"]: db.keg_end_liters(k) for k in prev.get("kegs", [])}
        for rw in self._kw:
            val = pk.get(rw["beer"]["name"], 0.0)
            rw["_start_l"] = val
            rw["start_lbl"].setText(f"{val:.2f} L")

    def _collect(self):
        data = {"kegs": [], "pos": [], "corr": []}
        for rw in self._kw:
            b = rw["beer"]
            data["kegs"].append({
                "name": b["name"], "keg": b["keg"],
                "start_l": rw.get("_start_l", 0.0),
                "delivery": rw["delivery"].text() or "0",
                "full_end": rw["full_end"].text() or "0",
                "open_end": [v.text() or None for v in rw["open_end"]],
            })
        for pw in self._pw:
            data["pos"].append({"name": pw["name"], "sizes": [
                {"liters": sv["liters"], "qty": sv["entry"].text() or "0"}
                for sv in pw["sizes"]]})
        for cw in self._cw:
            data["corr"].append({
                "name": cw["name"],
                "spill": cw["spill"].text() or "0",
                "void_": cw["void_"].text() or "0",
                "open_bar": cw["open_bar"].text() or "0",
            })
        return data

    def _recalc(self, _=""):
        try: data = self._collect()
        except Exception: return
        for i, rw in enumerate(self._kw):
            rw["end_lbl"].setText(f"{db.keg_end_liters(data['kegs'][i]):.2f} L")
        pos_g = 0
        for i, pw in enumerate(self._pw):
            t = db.pos_liters(data["pos"][i]); pos_g += t
            pw["lbl"].setText(f"{t:.2f} L")
        self._pos_total_lbl.setText(f"Łącznie: {pos_g:.2f} L")
        corr_g = 0
        for i, cw in enumerate(self._cw):
            t = db.corr_liters(data["corr"][i]); corr_g += t
            cw["lbl"].setText(f"−{t:.2f} L")
        self._corr_total_lbl.setText(f"Łącznie: {corr_g:.2f} L")
        self._render_summary(data)

    def _render_summary(self, data):
        if (not self._sum_row_labels or
                len(self._sum_row_labels) != len(data["kegs"])):
            self._build_summary_rows([{"name": k["name"]} for k in data["kegs"]])
        tot = 0
        for i, keg in enumerate(data["kegs"]):
            pe = data["pos"][i]  if i < len(data["pos"])  else {"sizes": []}
            co = data["corr"][i] if i < len(data["corr"]) else {}
            diff = db.calc_diff(keg, pe, co); s = db.diff_status(diff)
            col, bg = DIFF_COLORS[s]; tot += diff
            refs = self._sum_row_labels[i]
            refs["detail"]["START"].setText(f"START: {db.keg_start_liters(keg):.1f}L")
            refs["detail"]["Del"].setText(f"Del: +{db.keg_delivery_liters(keg):.0f}L")
            refs["detail"]["END"].setText(f"END: {db.keg_end_liters(keg):.1f}L")
            refs["detail"]["POS"].setText(f"POS: {db.pos_liters(pe):.1f}L")
            refs["detail"]["Kor"].setText(f"Kor: −{db.corr_liters(co):.1f}L")
            refs["chip"].setStyleSheet(f"background:{bg};border-radius:10px;")
            refs["chip_lbl"].setText(f"  {DIFF_ICONS[s]} {diff:+.2f}L  ")
            refs["chip_lbl"].setStyleSheet(f"color:{col};background:transparent;")
        ts = db.diff_status(tot); tcol, tbg = DIFF_COLORS[ts]
        pt = sum(db.pos_liters(p) for p in data["pos"])
        self._sum_pos_lbl.setText(f"POS: {pt:.1f}L")
        self._sum_tot_chip.setStyleSheet(f"background:{tbg};border-radius:10px;")
        self._sum_tot_lbl.setText(f"  {DIFF_ICONS[ts]} {tot:+.2f}L  ")
        self._sum_tot_lbl.setStyleSheet(f"color:{tcol};background:transparent;")

    def _save_day(self):
        d = self.ev_date.text().strip()
        if not d: QMessageBox.critical(self, "Błąd", "Wpisz datę!"); return
        data = self._collect(); db.save_day(d, data)
        self._tab_cache.discard("history"); self._tab_cache.discard("report")
        QMessageBox.information(self, "Zapisano", f"Dzień {d} zapisany ✓")

    def _clear_entry(self):
        if (QMessageBox.question(self, "Wyczyścić?", "Wyczyścić wszystkie pola?") !=
                QMessageBox.StandardButton.Yes):
            return
        for rw in self._kw:
            rw["delivery"].clear(); rw["full_end"].clear()
            for v in rw["open_end"]: v.clear()
        for pw in self._pw:
            for sv in pw["sizes"]: sv["entry"].clear()
        for cw in self._cw:
            for f in ["spill","void_","open_bar"]: cw[f].clear()
        self._recalc()

    # ══════════════════════════════════════════════════════════════════
    #  HISTORY TAB
    # ══════════════════════════════════════════════════════════════════
    def _build_history_tab(self):
        lay = self._tab_lay["history"]
        top = QWidget(); top.setStyleSheet("background:transparent;")
        tl = QHBoxLayout(top); tl.setContentsMargins(18,14,18,8); tl.setSpacing(8)
        tl.addWidget(_lbl("Miesiąc:", 11, color=MUTED))
        self._hist_cb = QComboBox()
        self._hist_cb.setFixedWidth(240); self._hist_cb.setFixedHeight(34)
        self._hist_cb.addItem("(brak)")
        self._hist_cb.currentIndexChanged.connect(self._render_history)
        tl.addWidget(self._hist_cb); tl.addStretch(); lay.addWidget(top)

        self._hist_list_w = QWidget(); self._hist_list_w.setStyleSheet("background:transparent;")
        self._hist_list_lay = QVBoxLayout(self._hist_list_w)
        self._hist_list_lay.setContentsMargins(18,0,18,0); self._hist_list_lay.setSpacing(4)
        lay.addWidget(self._hist_list_w); lay.addStretch()

    def _load_history(self):
        months = db.get_months()
        self._hist_cb.blockSignals(True); self._hist_cb.clear()
        if months:
            for m in months:
                self._hist_cb.addItem(self._fmt_month(m) + f"  [{m}]")
        else:
            self._hist_cb.addItem("(brak)")
        self._hist_cb.blockSignals(False); self._render_history()

    def _render_history(self):
        while self._hist_list_lay.count():
            item = self._hist_list_lay.takeAt(0)
            if item.widget(): item.widget().setParent(None)
        val = self._hist_cb.currentText()
        if "(brak)" in val: return
        month = val.split("[")[-1].rstrip("]").strip()
        entries = db.get_days_for_month(month)
        if not entries:
            self._hist_list_lay.addWidget(_lbl("Brak wpisów.", 11, color=MUTED))
            return
        for entry_date, data in reversed(entries):
            self._hist_card(entry_date, data)
        self._hist_list_lay.addStretch()

    def _hist_card(self, entry_date: str, data: dict):
        beers = data.get("kegs", [])
        tot = sum(
            db.calc_diff(
                k,
                data["pos"][i]  if i < len(data.get("pos",[])) else {"sizes":[]},
                data["corr"][i] if i < len(data.get("corr",[])) else {})
            for i, k in enumerate(beers))
        tot_pos = sum(db.pos_liters(p) for p in data.get("pos", []))
        tot_del = sum(int(k.get("delivery",0) or 0) for k in beers)
        s = db.diff_status(tot); col, bg = DIFF_COLORS[s]

        card = QFrame()
        card.setStyleSheet(
            f"QFrame{{background:{SURFACE};border:1px solid {BORDER};"
            f"border-radius:8px;}}")
        cv = QVBoxLayout(card); cv.setContentsMargins(0,0,0,0); cv.setSpacing(0)

        # Header
        hdr = QFrame()
        hdr.setStyleSheet(f"background:{PREV_BG};border-radius:8px 8px 0 0;")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(14,8,14,8)
        hl.addWidget(_lbl(self._fmt_date(entry_date), 11, bold=True))
        if tot_del:
            dc = QFrame(); dc.setStyleSheet(f"background:{GOLD_BG};border-radius:5px;")
            dcl = QHBoxLayout(dc); dcl.setContentsMargins(6,2,6,2)
            dcl.addWidget(_lbl(f"🚚 Dostawa: {tot_del} keg", 10, color=GOLD))
            hl.addWidget(dc)
        hl.addStretch()
        hl.addWidget(_lbl(f"POS: {tot_pos:.1f}L", 10, color=MUTED))
        diff_chip, diff_lbl = _chip_frame(
            f"  {DIFF_ICONS[s]} {tot:+.2f}L  ", col, bg)
        hl.addWidget(diff_chip); cv.addWidget(hdr)

        # Body
        body = QWidget(); body.setStyleSheet("background:transparent;")
        bl = QVBoxLayout(body); bl.setContentsMargins(14,10,14,10); bl.setSpacing(2)
        for i, keg in enumerate(beers):
            pe = data["pos"][i]  if i < len(data.get("pos",[])) else {"sizes":[]}
            co = data["corr"][i] if i < len(data.get("corr",[])) else {}
            d2 = db.calc_diff(keg, pe, co)
            s2 = db.diff_status(d2); c2, _ = DIFF_COLORS[s2]
            brow = QWidget(); brow.setStyleSheet("background:transparent;")
            brl = QHBoxLayout(brow); brl.setContentsMargins(0,0,0,0)
            nl = _lbl(keg["name"], 10); nl.setFixedWidth(90); brl.addWidget(nl)
            brl.addStretch()
            brl.addWidget(_lbl(f"{DIFF_ICONS[s2]} {d2:+.2f}L", 10, color=c2))
            bl.addWidget(brow)

        # Buttons
        det_frame = QWidget(); det_frame.setStyleSheet("background:transparent;")
        det_lay = QVBoxLayout(det_frame)
        det_lay.setContentsMargins(0,8,0,0); det_frame.setVisible(False)

        btn_row = QWidget(); btn_row.setStyleSheet("background:transparent;")
        brl2 = QHBoxLayout(btn_row); brl2.setContentsMargins(0,8,0,0); brl2.setSpacing(8)
        det_btn = _btn("🔍 Pokaż szczegóły", bg=GOLD_BG, fg=GOLD,
                        w=160, h=30, bold=False, border=BORDER)
        edit_btn = _btn("✏️ Edytuj", w=110, h=30)
        edit_btn.clicked.connect(
            lambda _, ed=entry_date, d=data: self._open_edit(ed, d))

        state = {"open": False}
        def toggle(s=state, df=det_frame, dl=det_lay, db2=det_btn, d=data):
            s["open"] = not s["open"]
            if s["open"]:
                self._fill_det_table(dl, d); df.setVisible(True)
                db2.setText("🔍 Ukryj szczegóły")
            else:
                df.setVisible(False); db2.setText("🔍 Pokaż szczegóły")

        det_btn.clicked.connect(toggle)
        brl2.addWidget(det_btn); brl2.addWidget(edit_btn); brl2.addStretch()
        bl.addWidget(btn_row); bl.addWidget(det_frame)
        cv.addWidget(body); self._hist_list_lay.addWidget(card)

    def _fill_det_table(self, lay: QVBoxLayout, data: dict):
        while lay.count():
            item = lay.takeAt(0)
            if item.widget(): item.widget().setParent(None)
        sizes = db.get_sizes()
        frm = QFrame()
        frm.setStyleSheet(
            f"QFrame{{background:{SURFACE};border:1px solid {BORDER};"
            f"border-radius:6px;}}")
        gl = QGridLayout(frm); gl.setContentsMargins(4,4,4,4); gl.setSpacing(3)
        hdrs = (["Piwo","START","Del","Pełne END","kg#1","kg#2","kg#3","END(L)"]
                + [sz["label"] for sz in sizes]
                + ["Spill","Void","Open Bar","RÓŻNICA"])
        for ci, h in enumerate(hdrs):
            l = _lbl(h, 8, bold=True, color=GOLD)
            l.setAlignment(Qt.AlignmentFlag.AlignCenter); gl.addWidget(l, 0, ci)
        for ri, keg in enumerate(data.get("kegs", [])):
            pe   = data["pos"][ri]  if ri < len(data.get("pos",[])) else {"sizes":[]}
            co   = data["corr"][ri] if ri < len(data.get("corr",[])) else {}
            diff = db.calc_diff(keg, pe, co)
            s    = db.diff_status(diff); col, bg = DIFF_COLORS[s]
            ow   = keg.get("open_end") or [None,None,None]
            vals = (
                [keg["name"],
                 f"{db.keg_start_liters(keg):.1f}",
                 str(keg.get("delivery",0)), str(keg.get("full_end",0)),
                 str(ow[0] or "—"), str(ow[1] if len(ow)>1 else "—"),
                 str(ow[2] if len(ow)>2 else "—"),
                 f"{db.keg_end_liters(keg):.2f}"]
                + [str(sz.get("qty",0) or 0) for sz in pe.get("sizes",[])]
                + [str(co.get("spill",0) or 0),
                   str(co.get("void_",0) or 0),
                   str(co.get("open_bar",0) or 0),
                   f"{DIFF_ICONS[s]} {diff:+.2f}L"])
            for ci, v in enumerate(vals):
                is_d = ci == len(vals)-1
                l = _lbl(v, 9, color=(col if is_d else TEXT))
                l.setAlignment(Qt.AlignmentFlag.AlignCenter)
                if is_d:
                    l.setStyleSheet(
                        f"color:{col};background:{bg};border-radius:4px;")
                gl.addWidget(l, ri+1, ci)
        lay.addWidget(frm)

    def _open_edit(self, entry_date: str, data: dict):
        self.ev_date.setText(entry_date)
        beers = db.get_beers(); sizes = db.get_sizes()
        self._build_keg_inputs(beers); self._build_pos_inputs(beers, sizes)
        self._build_corr_inputs(beers)
        for i, rw in enumerate(self._kw):
            if i >= len(data.get("kegs",[])): continue
            keg = data["kegs"][i]
            rw["_start_l"] = float(keg.get("start_l",0) or 0)
            rw["start_lbl"].setText(f"{rw['_start_l']:.2f} L")
            rw["delivery"].setText(str(keg.get("delivery","") or ""))
            rw["full_end"].setText(str(keg.get("full_end","") or ""))
            ow = keg.get("open_end") or [None,None,None]
            for j, v in enumerate(rw["open_end"]):
                v.setText(str(ow[j]) if j < len(ow) and ow[j] else "")
        for i, pw in enumerate(self._pw):
            if i >= len(data.get("pos",[])): continue
            pe = data["pos"][i]
            for j, sv in enumerate(pw["sizes"]):
                if j < len(pe.get("sizes",[])):
                    sv["entry"].setText(str(pe["sizes"][j].get("qty","") or ""))
        for i, cw in enumerate(self._cw):
            if i >= len(data.get("corr",[])): continue
            co = data["corr"][i]
            cw["spill"].setText(str(co.get("spill","") or ""))
            cw["void_"].setText(str(co.get("void_","") or ""))
            cw["open_bar"].setText(str(co.get("open_bar","") or ""))
        self._recalc(); self.show_tab("entry")

    # ══════════════════════════════════════════════════════════════════
    #  REPORT TAB
    # ══════════════════════════════════════════════════════════════════
    def _build_report_tab(self):
        lay = self._tab_lay["report"]
        top = QWidget(); top.setStyleSheet("background:transparent;")
        tl = QHBoxLayout(top); tl.setContentsMargins(18,14,18,8); tl.setSpacing(8)
        tl.addWidget(_lbl("Miesiąc:", 11, color=MUTED))
        self._rep_cb = QComboBox()
        self._rep_cb.setFixedWidth(240); self._rep_cb.setFixedHeight(34)
        self._rep_cb.addItem("(brak)")
        self._rep_cb.currentIndexChanged.connect(self._render_report)
        tl.addWidget(self._rep_cb)
        em = _btn("📥 Export Excel (miesiąc)", h=34)
        em.clicked.connect(self._export_month); tl.addWidget(em)
        ey = _btn("📥 Export Excel (rok)", bg=GOLD_BG, fg=GOLD,
                   h=34, bold=False, border=BORDER)
        ey.clicked.connect(self._export_year); tl.addWidget(ey)
        tl.addStretch(); lay.addWidget(top)

        self._rep_body_w = QWidget(); self._rep_body_w.setStyleSheet("background:transparent;")
        self._rep_body = QVBoxLayout(self._rep_body_w)
        self._rep_body.setContentsMargins(18,0,18,0); self._rep_body.setSpacing(4)
        lay.addWidget(self._rep_body_w); lay.addStretch()

    def _load_report(self):
        months = db.get_months()
        self._rep_cb.blockSignals(True); self._rep_cb.clear()
        if months:
            for m in months:
                self._rep_cb.addItem(self._fmt_month(m) + f"  [{m}]")
        else:
            self._rep_cb.addItem("(brak)")
        self._rep_cb.blockSignals(False); self._render_report()

    def _render_report(self):
        while self._rep_body.count():
            item = self._rep_body.takeAt(0)
            if item.widget(): item.widget().setParent(None)
        val = self._rep_cb.currentText()
        if "(brak)" in val: return
        month = val.split("[")[-1].rstrip("]").strip()
        entries = db.get_days_for_month(month)
        if not entries:
            self._rep_body.addWidget(_lbl("Brak wpisów.", 11, color=MUTED))
            return

        tot_days = len(entries)
        tot_del  = sum(sum(int(k.get("delivery",0) or 0)
                           for k in d.get("kegs",[])) for _,d in entries)
        tot_pos  = sum(sum(db.pos_liters(p)
                           for p in d.get("pos",[])) for _,d in entries)
        tot_corr = sum(sum(db.corr_liters(c)
                           for c in d.get("corr",[])) for _,d in entries)
        tot_diff = sum(
            db.calc_diff(
                k,
                d["pos"][i]  if i<len(d.get("pos",[])) else {"sizes":[]},
                d["corr"][i] if i<len(d.get("corr",[])) else {})
            for _,d in entries for i,k in enumerate(d.get("kegs",[])))

        # KPIs
        kw = QWidget(); kw.setStyleSheet("background:transparent;")
        kl = QHBoxLayout(kw); kl.setContentsMargins(0,0,0,14); kl.setSpacing(8)
        ts = db.diff_status(tot_diff); tcol, _ = DIFF_COLORS[ts]
        for lbl_t, val2, colr in [
            ("Dni wpisów",   str(tot_days),            GOLD),
            ("Dostawa",      f"{tot_del} keg",          GOLD),
            ("Sprzedaż POS", f"{tot_pos:.1f} L",        TEXT),
            ("Korekty",      f"{tot_corr:.1f} L",       TEXT),
            ("Różnica",      f"{DIFF_ICONS[ts]} {tot_diff:+.1f} L", tcol),
        ]:
            kc = QFrame()
            kc.setStyleSheet(
                f"QFrame{{background:{SURFACE};border:1px solid {BORDER};"
                f"border-radius:8px;}}")
            kv = QVBoxLayout(kc); kv.setContentsMargins(14,10,14,10)
            l1 = _lbl(lbl_t, 10, color=MUTED)
            l1.setAlignment(Qt.AlignmentFlag.AlignCenter); kv.addWidget(l1)
            l2 = _lbl(val2, 20, bold=True, color=colr)
            l2.setAlignment(Qt.AlignmentFlag.AlignCenter); kv.addWidget(l2)
            kl.addWidget(kc)
        kl.addStretch(); self._rep_body.addWidget(kw)

        # Per-beer
        self._rep_body.addWidget(_lbl("Wynik per piwo", 13, bold=True, color=GOLD))
        self._rep_body.addWidget(_sep())
        agg = {b["name"]: {"diff":0,"pos":0,"del":0,"days":0}
               for b in db.get_beers()}
        for _, data in entries:
            for i, keg in enumerate(data.get("kegs",[])):
                n = keg["name"]
                if n not in agg: agg[n] = {"diff":0,"pos":0,"del":0,"days":0}
                pe = data["pos"][i]  if i<len(data.get("pos",[])) else {"sizes":[]}
                co = data["corr"][i] if i<len(data.get("corr",[])) else {}
                agg[n]["diff"] += db.calc_diff(keg, pe, co)
                agg[n]["pos"]  += db.pos_liters(pe)
                agg[n]["del"]  += int(keg.get("delivery",0) or 0)
                agg[n]["days"] += 1
        for n, a in agg.items():
            diff = round(a["diff"], 2); s = db.diff_status(diff); col, bg = DIFF_COLORS[s]
            row = QFrame()
            row.setStyleSheet(
                f"QFrame{{background:{SURFACE};border:1px solid {BORDER};"
                f"border-radius:6px;}}")
            rl = QHBoxLayout(row); rl.setContentsMargins(12,7,12,7)
            nl = _lbl(n, 11, bold=True); nl.setFixedWidth(100); rl.addWidget(nl)
            rl.addWidget(_lbl(
                f"POS: {a['pos']:.1f}L | Del: {a['del']} keg | {a['days']} dni",
                10, color=MUTED))
            rl.addStretch()
            chip, lbl2 = _chip_frame(
                f"  {DIFF_ICONS[s]} {diff:+.1f}L  ", col, bg)
            rl.addWidget(chip); self._rep_body.addWidget(row)

        # Daily trend
        self._rep_body.addWidget(_lbl("Trend dzienny", 13, bold=True, color=GOLD))
        self._rep_body.addWidget(_sep())
        for entry_date, data in entries:
            d_diff = sum(
                db.calc_diff(
                    k,
                    data["pos"][i]  if i<len(data.get("pos",[])) else {"sizes":[]},
                    data["corr"][i] if i<len(data.get("corr",[])) else {})
                for i,k in enumerate(data.get("kegs",[])))
            s = db.diff_status(d_diff); col, _ = DIFF_COLORS[s]
            tr = QWidget(); tr.setStyleSheet("background:transparent;")
            trl = QHBoxLayout(tr); trl.setContentsMargins(0,1,0,1)
            dl = _lbl(self._fmt_date(entry_date), 10, color=MUTED)
            dl.setFixedWidth(80); trl.addWidget(dl); trl.addStretch()
            vl = _lbl(f"{DIFF_ICONS[s]} {d_diff:+.2f}L", 10, color=col)
            vl.setFixedWidth(100)
            vl.setAlignment(Qt.AlignmentFlag.AlignRight); trl.addWidget(vl)
            self._rep_body.addWidget(tr)

    def _export_month(self):
        val = self._rep_cb.currentText()
        if "(brak)" in val:
            QMessageBox.warning(self, "Brak", "Wybierz miesiąc"); return
        month = val.split("[")[-1].rstrip("]").strip()
        p, _ = QFileDialog.getSaveFileName(
            self, "Zapisz Excel", f"BeerCount_{month}.xlsx", "Excel (*.xlsx)")
        if not p: return
        if xl.export_month(month, p):
            QMessageBox.information(self, "OK", f"Zapisano:\n{p}")
        else:
            QMessageBox.critical(self, "Błąd", "Brak danych")

    def _export_year(self):
        val = self._rep_cb.currentText()
        year = val.split("[")[-1][:4] if "[" in val else str(date.today().year)
        p, _ = QFileDialog.getSaveFileName(
            self, "Zapisz Excel", f"BeerCount_{year}_roczny.xlsx", "Excel (*.xlsx)")
        if not p: return
        if xl.export_year(year, p):
            QMessageBox.information(self, "OK", f"Zapisano:\n{p}")
        else:
            QMessageBox.critical(self, "Błąd", f"Brak danych dla roku {year}")

    # ══════════════════════════════════════════════════════════════════
    #  SETTINGS TAB
    # ══════════════════════════════════════════════════════════════════
    def _build_settings_tab(self):
        lay = self._tab_lay["settings"]

        bc = self._card("settings", "🍺  Piwa na krane")
        self._set_beers_lay = bc
        add_b = _btn("+ Dodaj piwo", bg=GOLD_BG, fg=GOLD, w=130, h=30,
                      bold=False, border=BORDER)
        add_b.clicked.connect(self._add_beer); bc.addWidget(add_b)

        sc = self._card("settings", "🥃  Rozmiary porcji POS")
        self._set_sizes_lay = sc
        add_s = _btn("+ Dodaj rozmiar", bg=GOLD_BG, fg=GOLD, w=140, h=30,
                      bold=False, border=BORDER)
        add_s.clicked.connect(self._add_size); sc.addWidget(add_s)

        brow = QWidget(); brow.setStyleSheet("background:transparent;")
        brl = QHBoxLayout(brow); brl.setContentsMargins(18,14,18,6)
        sb = _btn("💾  Zapisz ustawienia", w=200, h=40)
        sb.clicked.connect(self._save_settings); brl.addWidget(sb)
        brl.addStretch(); lay.addWidget(brow)

        ww = QWidget(); ww.setStyleSheet("background:transparent;")
        wwl = QHBoxLayout(ww); wwl.setContentsMargins(18,0,18,6)
        wb = _btn(
            "🔄  Uruchom ponownie kreator pierwszego uruchomienia",
            bg=SURFACE, fg=MUTED, w=380, h=36, bold=False, border=BORDER)
        wb.clicked.connect(self._rerun_wizard)
        wwl.addWidget(wb); wwl.addStretch(); lay.addWidget(ww)
        lay.addStretch()
        self._beer_rows = []; self._size_rows = []

    def _load_settings(self):
        self._render_beer_settings(db.get_beers())
        self._render_size_settings(db.get_sizes())

    def _render_beer_settings(self, beers):
        # Remove all but last item (the "Dodaj" button)
        while self._set_beers_lay.count() > 1:
            item = self._set_beers_lay.takeAt(0)
            if item.widget(): item.widget().setParent(None)
        self._beer_rows = []
        for i, b in enumerate(beers):
            row = QWidget(); row.setStyleSheet("background:transparent;")
            rl = QHBoxLayout(row); rl.setContentsMargins(0,3,0,3); rl.setSpacing(8)
            ne = _entry(180, ph="PIWO", mono=False); ne.setText(b["name"])
            rl.addWidget(ne)
            kc = QComboBox(); kc.addItems(["20","30","50"])
            kc.setCurrentText(str(b["keg"]))
            kc.setFixedWidth(80); kc.setFixedHeight(30); rl.addWidget(kc)
            rl.addWidget(_lbl("L keg", 10, color=MUTED))
            del_b = QPushButton("✕"); del_b.setFixedSize(30, 28)
            del_b.setCursor(Qt.CursorShape.PointingHandCursor)
            del_b.setStyleSheet(
                f"background:{RED_BG};color:{RED};border-radius:4px;border:none;")
            def make_del(r, rows=self._beer_rows):
                def do():
                    r.setParent(None)
                    for j, (_, _, rr) in enumerate(rows):
                        if rr is r: rows.pop(j); break
                return do
            del_b.clicked.connect(make_del(row, self._beer_rows))
            rl.addWidget(del_b); rl.addStretch()
            self._set_beers_lay.insertWidget(i, row)
            self._beer_rows.append((ne, kc, row))

    def _render_size_settings(self, sizes):
        while self._set_sizes_lay.count() > 1:
            item = self._set_sizes_lay.takeAt(0)
            if item.widget(): item.widget().setParent(None)
        self._size_rows = []
        for i, s in enumerate(sizes):
            row = QWidget(); row.setStyleSheet("background:transparent;")
            rl = QHBoxLayout(row); rl.setContentsMargins(0,3,0,3); rl.setSpacing(8)
            le = _entry(80, ph="0.5L"); le.setText(s["label"]); rl.addWidget(le)
            ve = _entry(80, ph="0.5"); ve.setText(str(s["liters"])); rl.addWidget(ve)
            rl.addWidget(_lbl("L/szt.", 10, color=MUTED))
            del_b = QPushButton("✕"); del_b.setFixedSize(30, 28)
            del_b.setCursor(Qt.CursorShape.PointingHandCursor)
            del_b.setStyleSheet(
                f"background:{RED_BG};color:{RED};border-radius:4px;border:none;")
            def make_del(r, rows=self._size_rows):
                def do():
                    r.setParent(None)
                    for j, (_, _, rr) in enumerate(rows):
                        if rr is r: rows.pop(j); break
                return do
            del_b.clicked.connect(make_del(row, self._size_rows))
            rl.addWidget(del_b); rl.addStretch()
            self._set_sizes_lay.insertWidget(i, row)
            self._size_rows.append((le, ve, row))

    def _add_beer(self):
        curr = db.get_beers(); curr.append({"name":"NOWE","keg":20})
        self._render_beer_settings(curr)

    def _add_size(self):
        curr = db.get_sizes(); curr.append({"label":"0.5L","liters":0.5})
        self._render_size_settings(curr)

    def _save_settings(self):
        beers = []
        for ne, kc, row in self._beer_rows:
            name = ne.text().strip().upper()
            if name: beers.append({"name": name, "keg": int(kc.currentText())})
        sizes = []
        for le, ve, row in self._size_rows:
            lbl = le.text().strip()
            try: lit = float(ve.text())
            except: continue
            if lbl: sizes.append({"label": lbl, "liters": lit})
        db.save_beers(beers); db.save_sizes(sizes)
        self._tab_cache.discard("entry")
        QMessageBox.information(self, "Zapisano", "Ustawienia zapisane ✓")

    def _rerun_wizard(self):
        self._build_wizard(); self._show_raw("wizard")

    # ── Helpers ──────────────────────────────────────────────────────
    def _fmt_date(self, d: str) -> str:
        try:
            dt = datetime.strptime(d, "%Y-%m-%d")
            days = ["Pon","Wt","Śr","Czw","Pt","Sob","Ndz"]
            return f"{days[dt.weekday()]} {dt.day:02d}.{dt.month:02d}.{dt.year}"
        except: return d

    def _fmt_month(self, m: str) -> str:
        MO = {"01":"Styczeń","02":"Luty","03":"Marzec","04":"Kwiecień",
              "05":"Maj","06":"Czerwiec","07":"Lipiec","08":"Sierpień",
              "09":"Wrzesień","10":"Październik","11":"Listopad","12":"Grudzień"}
        y, mo = m.split("-"); return f"{MO.get(mo,mo)} {y}"


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = App()
    window.show()
    sys.exit(app.exec())
