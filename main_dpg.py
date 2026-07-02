"""
main_dpg.py — Beer Count v6 (DearPyGui)
GPU-rendered via DirectX 11.
Architecture mirrors tkinter v5 exactly:
  - _card() equivalent via child_window
  - grid-style rows via group(horizontal=True)
  - same data flow: _collect() → db.calc_diff()
  - database.py / pos_import.py / export_excel.py unchanged
"""
import dearpygui.dearpygui as dpg
import database as db
import export_excel as xl
import pos_import as pos
from datetime import date, timedelta, datetime
import os, sys

# ── Resource path (PyInstaller-compatible) ──────────────
def resource_path(name):
    base = getattr(sys, "_MEIPASS",
                   os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)

# ════════════════════════════════════════════════════════
#  PALETTE  (mirrors tkinter LIGHT/DARK dicts exactly)
# ════════════════════════════════════════════════════════
def _h(hex6):
    h = hex6.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (255,)

LIGHT = {
    "GOLD":        _h("b85c38"), "GOLD_LT":    _h("d68a64"),
    "GOLD_BG":     _h("f7e6dd"),
    "GREEN":       _h("2a7a45"), "GREEN_BG":   _h("eaf6ee"),
    "RED":         _h("b83232"), "RED_BG":     _h("fdeaea"),
    "AMBER":       _h("a06010"), "AMBER_BG":   _h("fff4e0"),
    "ORANGE":      _h("c05000"), "ORANGE_BG":  _h("fff0e0"),
    "BG":          _h("eef1f4"), "SURFACE":    _h("ffffff"),
    "BORDER":      _h("dde3ea"), "MUTED":      _h("64748b"),
    "TEXT":        _h("1e2530"), "PREV_BG":    _h("e7ebef"),
    "INFO_BG":     _h("e8f4fd"), "INFO_FG":    _h("1a5276"),
    "DELIVERY_BG": _h("fdecd9"),
}

DARK = {
    "GOLD":        _h("f0b272"), "GOLD_LT":    _h("ffc98c"),
    "GOLD_BG":     _h("4a3420"),
    "GREEN":       _h("7ee0a8"), "GREEN_BG":   _h("1a3326"),
    "RED":         _h("ff8a80"), "RED_BG":     _h("3d1f1f"),
    "AMBER":       _h("ffcf7a"), "AMBER_BG":   _h("4a3a18"),
    "ORANGE":      _h("ff9d5c"), "ORANGE_BG":  _h("3d2614"),
    "BG":          _h("15171a"), "SURFACE":    _h("1f2228"),
    "BORDER":      _h("383d46"), "MUTED":      _h("9aa1ab"),
    "TEXT":        _h("f2f3f5"), "PREV_BG":    _h("2a2e36"),
    "INFO_BG":     _h("16263a"), "INFO_FG":    _h("9cd0f5"),
    "DELIVERY_BG": _h("3d2e1a"),
}

DIFF_KEYS = {
    "ok":   ("GREEN",  "GREEN_BG"),
    "warn": ("AMBER",  "AMBER_BG"),
    "over": ("ORANGE", "ORANGE_BG"),
    "bad":  ("RED",    "RED_BG"),
}
DIFF_LABELS = {
    "ok":   "+OK",
    "warn": " ! ",
    "over": "!!",
    "bad":  " X ",
}
DIFF_TEXTS = {
    "ok":   "Norma (+-2L)",
    "warn": "+2/+5L - Sprawdz",
    "over": ">+5L - Poza POS?",
    "bad":  "<-5L - Straty",
}

# ── Active palette ───────────────────────────────────────
PAL = dict(DARK)
_theme_mode = "dark"

def C(key):
    return PAL[key]

# ── Pre-built theme cache (avoid alias conflicts) ────────
_color_themes = {}
_global_theme  = None

# ── Entry field registries ───────────────────────────────
_keg_tags      = []
_pos_tags      = []
_corr_tags     = []
_sum_tags      = []
_sum_total_tag = 0

# ════════════════════════════════════════════════════════
#  THEME
# ════════════════════════════════════════════════════════
def build_theme():
    global _global_theme
    if _global_theme and dpg.does_item_exist(_global_theme):
        dpg.delete_item(_global_theme)
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg,       C("BG"))
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg,        C("SURFACE"))
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg,        C("SURFACE"))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg,        C("SURFACE"))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, C("GOLD_BG"))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive,  C("GOLD_BG"))
            dpg.add_theme_color(dpg.mvThemeCol_Border,         C("BORDER"))
            dpg.add_theme_color(dpg.mvThemeCol_Text,           C("TEXT"))
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled,   C("MUTED"))
            dpg.add_theme_color(dpg.mvThemeCol_Button,         C("GOLD"))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered,  C("GOLD_LT"))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,   C("GOLD"))
            dpg.add_theme_color(dpg.mvThemeCol_Tab,            C("BG"))
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered,     C("GOLD_BG"))
            dpg.add_theme_color(dpg.mvThemeCol_TabActive,      C("GOLD"))
            dpg.add_theme_color(dpg.mvThemeCol_TabUnfocused,        C("BG"))
            dpg.add_theme_color(dpg.mvThemeCol_TabUnfocusedActive,  C("GOLD_BG"))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg,        C("BG"))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive,  C("BG"))
            dpg.add_theme_color(dpg.mvThemeCol_MenuBarBg,      C("BG"))
            dpg.add_theme_color(dpg.mvThemeCol_Header,         C("GOLD_BG"))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered,  C("GOLD_BG"))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive,   C("GOLD"))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg,    C("BG"))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab,  C("BORDER"))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, C("GOLD"))
            dpg.add_theme_color(dpg.mvThemeCol_Separator,      C("BORDER"))
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark,      C("GOLD"))

            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding,  8)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding,   6)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,   4)
            dpg.add_theme_style(dpg.mvStyleVar_TabRounding,     6)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding,    8, 5)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing,     6, 4)
            dpg.add_theme_style(dpg.mvStyleVar_CellPadding,     6, 4)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding,  10, 8)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarSize,  10)
    _global_theme = t
    dpg.bind_theme(t)


def build_color_themes():
    """One anonymous theme per palette key — no tags, no alias conflicts."""
    global _color_themes
    for th in _color_themes.values():
        try:
            if dpg.does_item_exist(th):
                dpg.delete_item(th)
        except Exception:
            pass
    _color_themes = {}
    for key in PAL:
        with dpg.theme() as t:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Text, C(key))
        _color_themes[key] = t
    # Special button themes
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button,        C("INFO_BG"))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, C("INFO_BG"))
            dpg.add_theme_color(dpg.mvThemeCol_Text,          C("INFO_FG"))
    _color_themes["_btn_info"] = t
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button,        C("SURFACE"))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, C("BORDER"))
            dpg.add_theme_color(dpg.mvThemeCol_Text,          C("MUTED"))
    _color_themes["_btn_muted"] = t
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button,        C("GOLD_BG"))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, C("GOLD_LT"))
            dpg.add_theme_color(dpg.mvThemeCol_Text,          C("GOLD"))
    _color_themes["_btn_secondary"] = t
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button,        C("RED_BG"))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, C("RED"))
            dpg.add_theme_color(dpg.mvThemeCol_Text,          C("RED"))
    _color_themes["_btn_danger"] = t
    # Input fields — delivery yellow bg
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvInputText):
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg,       C("DELIVERY_BG"))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered,C("DELIVERY_BG"))
            dpg.add_theme_color(dpg.mvThemeCol_Text,          C("TEXT"))
    _color_themes["_input_delivery"] = t
    # Prev START read-only
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvText):
            dpg.add_theme_color(dpg.mvThemeCol_Text,          C("GOLD"))
    _color_themes["_start_lbl"] = t
    # Card header background via child_window
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg,       C("GOLD_BG"))
            dpg.add_theme_color(dpg.mvThemeCol_Border,        C("GOLD"))
    _color_themes["_card_header"] = t
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg,       C("SURFACE"))
            dpg.add_theme_color(dpg.mvThemeCol_Border,        C("BORDER"))
    _color_themes["_card_body"] = t


def _ct(key):
    return _color_themes.get(key)


def _recolor(item, key):
    t = _color_themes.get(key)
    if t and dpg.does_item_exist(item) and dpg.does_item_exist(t):
        dpg.bind_item_theme(item, t)


def _colored_text(text, color_key, parent=None, **kw):
    kw_f = {}
    if parent is not None:
        kw_f["parent"] = parent
    kw_f.update(kw)
    item = dpg.add_text(text, **kw_f)
    _recolor(item, color_key)
    return item


# ════════════════════════════════════════════════════════
#  CARD HELPER  (mirrors tkinter _card())
# ════════════════════════════════════════════════════════
def _card_begin(parent, title, width=-1, height=-1):
    """
    Renders:
      ┌─────────────────────────────┐
      │  TITLE                      │  ← gold bg header strip
      ├─────────────────────────────┤
      │  body (returned)            │
      └─────────────────────────────┘
    Returns (outer_tag, body_tag) so caller can use body_tag as parent.
    """
    kw = {"border": True, "parent": parent}
    if width  != -1: kw["width"]  = width
    if height != -1: kw["height"] = height
    outer = dpg.add_child_window(**kw)
    # Header strip
    hdr = dpg.add_child_window(parent=outer, height=28, border=False)
    dpg.bind_item_theme(hdr, _ct("_card_header"))
    dpg.add_spacer(width=6, parent=hdr)
    _colored_text(title, "GOLD", parent=hdr)
    # Separator
    dpg.add_separator(parent=outer)
    # Body
    body = dpg.add_child_window(parent=outer, border=False,
                                 autosize_x=True, autosize_y=True)
    dpg.bind_item_theme(body, _ct("_card_body"))
    return outer, body


# ════════════════════════════════════════════════════════
#  MODAL DIALOGS
# ════════════════════════════════════════════════════════
def _close_modal(tag):
    if dpg.does_item_exist(tag):
        dpg.delete_item(tag)


def show_info(title, message):
    tag = f"__modal_{abs(hash(message))}"
    if dpg.does_item_exist(tag): dpg.delete_item(tag)
    vw = dpg.get_viewport_width()
    vh = dpg.get_viewport_height()
    with dpg.window(label=title, modal=True, tag=tag,
                    width=400, no_resize=True,
                    pos=[vw//2-200, vh//2-80]):
        _colored_text(f"OK  {title}", "GREEN")
        dpg.add_spacer(height=6)
        dpg.add_text(message, wrap=370)
        dpg.add_spacer(height=10)
        dpg.add_button(label="OK", width=80,
                       callback=lambda: _close_modal(tag))


def show_error(title, message):
    tag = f"__modal_{abs(hash(message + 'e'))}"
    if dpg.does_item_exist(tag): dpg.delete_item(tag)
    vw = dpg.get_viewport_width()
    vh = dpg.get_viewport_height()
    with dpg.window(label=title, modal=True, tag=tag,
                    width=400, no_resize=True,
                    pos=[vw//2-200, vh//2-80]):
        _colored_text(f"!  {title}", "RED")
        dpg.add_spacer(height=6)
        dpg.add_text(message, wrap=370)
        dpg.add_spacer(height=10)
        dpg.add_button(label="OK", width=80,
                       callback=lambda: _close_modal(tag))


def show_warning(title, message):
    tag = f"__modal_{abs(hash(message + 'w'))}"
    if dpg.does_item_exist(tag): dpg.delete_item(tag)
    vw = dpg.get_viewport_width()
    vh = dpg.get_viewport_height()
    with dpg.window(label=title, modal=True, tag=tag,
                    width=400, no_resize=True,
                    pos=[vw//2-200, vh//2-80]):
        _colored_text(f"!  {title}", "AMBER")
        dpg.add_spacer(height=6)
        dpg.add_text(message, wrap=370)
        dpg.add_spacer(height=10)
        dpg.add_button(label="OK", width=80,
                       callback=lambda: _close_modal(tag))


def show_confirm(title, message, on_yes):
    tag = f"__modal_c{abs(hash(message))}"
    if dpg.does_item_exist(tag): dpg.delete_item(tag)
    vw = dpg.get_viewport_width()
    vh = dpg.get_viewport_height()
    def _yes():
        _close_modal(tag)
        on_yes()
    with dpg.window(label=title, modal=True, tag=tag,
                    width=400, no_resize=True,
                    pos=[vw//2-200, vh//2-80]):
        _colored_text(f"?  {title}", "GOLD")
        dpg.add_spacer(height=6)
        dpg.add_text(message, wrap=370)
        dpg.add_spacer(height=10)
        with dpg.group(horizontal=True):
            b = dpg.add_button(label="Tak", width=80, callback=_yes)
            _recolor(b, "_btn_danger")
            dpg.add_spacer(width=8)
            dpg.add_button(label="Anuluj", width=80,
                           callback=lambda: _close_modal(tag))


# ════════════════════════════════════════════════════════
#  DATA COLLECTION  (mirrors tkinter _collect())
# ════════════════════════════════════════════════════════
def _collect():
    beers = db.get_beers()
    sizes = db.get_sizes()
    data  = {"kegs": [], "pos": [], "corr": []}

    for i, rv in enumerate(_keg_tags):
        beer = beers[i] if i < len(beers) else {"name": "?", "keg": 20}
        data["kegs"].append({
            "name":     beer["name"],
            "keg":      beer["keg"],
            "start_l":  rv.get("_start_l", 0.0),
            "delivery": dpg.get_value(rv["delivery"]) or "0",
            "full_end": dpg.get_value(rv["full_end"]) or "0",
            "open_end": [dpg.get_value(rv["open"][j]) or None
                         for j in range(3)],
        })

    for i, pw in enumerate(_pos_tags):
        beer_name = beers[i]["name"] if i < len(beers) else "?"
        data["pos"].append({
            "name":  beer_name,
            "sizes": [
                {"liters": db.safe_float(sizes[j]["liters"]),
                 "qty":    dpg.get_value(pw["sizes"][j]) or "0"}
                for j in range(len(sizes))
                if j < len(pw["sizes"])
            ],
        })

    for i, cw in enumerate(_corr_tags):
        data["corr"].append({
            "name":     cw["name"],
            "spill":    dpg.get_value(cw["spill"])    or "0",
            "void_":    dpg.get_value(cw["void_"])    or "0",
            "open_bar": dpg.get_value(cw["open_bar"]) or "0",
        })
    return data


def _recalc():
    try:
        data = _collect()
    except Exception:
        return

    # Update END(L) labels in keg section
    for i, rv in enumerate(_keg_tags):
        if i >= len(data["kegs"]): break
        end_l = db.keg_end_liters(data["kegs"][i])
        if dpg.does_item_exist(rv.get("end_lbl", 0)):
            dpg.set_value(rv["end_lbl"], f"{end_l:.1f}L")

    # Update POS totals
    pos_grand = 0.0
    for i, pw in enumerate(_pos_tags):
        if i >= len(data["pos"]): break
        t = db.pos_liters(data["pos"][i])
        pos_grand += t
        if dpg.does_item_exist(pw.get("razem", 0)):
            dpg.set_value(pw["razem"], f"{t:.2f}L")
            _recolor(pw["razem"], "GOLD")

    if dpg.does_item_exist("pos_total_lbl"):
        dpg.set_value("pos_total_lbl", f"Lacznie: {pos_grand:.2f} L")

    # Update Korekty totals
    corr_grand = 0.0
    for i, cw in enumerate(_corr_tags):
        if i >= len(data["corr"]): break
        t = db.corr_liters(data["corr"][i])
        corr_grand += t
        if dpg.does_item_exist(cw.get("razem", 0)):
            dpg.set_value(cw["razem"], f"-{t:.2f}")
            _recolor(cw["razem"], "RED")

    if dpg.does_item_exist("corr_total_lbl"):
        dpg.set_value("corr_total_lbl", f"Lacznie: {corr_grand:.2f} L")

    # Update Wynik dnia summary
    tot_diff = 0.0
    for i, lbls in enumerate(_sum_tags):
        if i >= len(data["kegs"]): break
        keg = data["kegs"][i]
        pe  = data["pos"][i]  if i < len(data["pos"])  else {"sizes": []}
        co  = data["corr"][i] if i < len(data["corr"]) else {}
        diff = db.calc_diff(keg, pe, co)
        tot_diff += diff
        s = db.diff_status(diff)
        fg_key, _ = DIFF_KEYS[s]

        if dpg.does_item_exist(lbls.get("info", 0)):
            start_flag = "" if db.has_valid_start(keg) else "  [!]"
            dpg.set_value(lbls["info"],
                f"START {db.keg_start_liters(keg):.1f}L{start_flag}  "
                f"Del +{db.keg_delivery_liters(keg):.0f}L  "
                f"END {db.keg_end_liters(keg):.1f}L  "
                f"POS {db.pos_liters(pe):.1f}L  "
                f"Kor -{db.corr_liters(co):.1f}L")
            _recolor(lbls["info"], "MUTED")

        if dpg.does_item_exist(lbls.get("diff", 0)):
            dpg.set_value(lbls["diff"],
                f"{DIFF_LABELS[s]}  {diff:+.2f}L")
            _recolor(lbls["diff"], fg_key)

    if dpg.does_item_exist(_sum_total_tag):
        ts = db.diff_status(tot_diff)
        fg_key, _ = DIFF_KEYS[ts]
        dpg.set_value(_sum_total_tag,
            f"LACZNIE:  {DIFF_LABELS[ts]}  {tot_diff:+.2f}L"
            f"    POS: {pos_grand:.1f}L    Kor: {corr_grand:.1f}L")
        _recolor(_sum_total_tag, fg_key)


# ════════════════════════════════════════════════════════
#  LOAD PREV STARTS
# ════════════════════════════════════════════════════════
def _load_prev_starts():
    d = (dpg.get_value("entry_date") or "").strip()
    if not d: return
    prev = db.get_prev_day(d)
    prev_kegs = {}
    if prev:
        prev_kegs = {k["name"]: db.keg_end_liters(k)
                     for k in prev.get("kegs", [])}
    for rv in _keg_tags:
        val = prev_kegs.get(rv.get("name", ""), 0.0)
        rv["_start_l"] = val
        if dpg.does_item_exist(rv.get("start_lbl", 0)):
            dpg.set_value(rv["start_lbl"], f"{val:.1f}L")
    _recalc()


def _shift_date(days):
    cur = (dpg.get_value("entry_date") or "").strip()
    try:
        d = datetime.strptime(cur, "%Y-%m-%d").date()
    except ValueError:
        d = date.today()
    dpg.set_value("entry_date", str(d + timedelta(days=days)))
    _load_prev_starts()


# ════════════════════════════════════════════════════════
#  SAVE / CLEAR
# ════════════════════════════════════════════════════════
def _save_day():
    d = (dpg.get_value("entry_date") or "").strip()
    if not d:
        show_error("Blad", "Wpisz date!")
        return
    try:
        datetime.strptime(d, "%Y-%m-%d")
    except ValueError:
        show_error("Blad", "Nieprawidlowy format daty.\nUzyj: RRRR-MM-DD")
        return
    db.save_day(d, _collect())
    show_info("Zapisano", f"Dzien {d} zapisany.")


def _clear_day():
    def _do():
        for rv in _keg_tags:
            dpg.set_value(rv["delivery"], "")
            dpg.set_value(rv["full_end"], "")
            for j in range(3):
                dpg.set_value(rv["open"][j], "")
        for pw in _pos_tags:
            for tag in pw["sizes"]:
                dpg.set_value(tag, "")
        for cw in _corr_tags:
            dpg.set_value(cw["spill"], "")
            dpg.set_value(cw["void_"], "")
            dpg.set_value(cw["open_bar"], "")
        _recalc()
    show_confirm("Wyczysc?", "Wyczysc wszystkie pola?", _do)


# ════════════════════════════════════════════════════════
#  POS IMPORT
# ════════════════════════════════════════════════════════
def _import_pos():
    dpg.show_item("pos_file_dialog")


def _on_pos_file(sender, app_data):
    sels = app_data.get("selections", {})
    if not sels: return
    filepath = list(sels.values())[0]
    try:
        all_dates = pos.get_available_dates(filepath)
    except ValueError as e:
        show_error("Blad importu", str(e)); return
    if not all_dates:
        show_warning("Brak danych", "Plik nie zawiera danych sprzedazy."); return

    current = (dpg.get_value("entry_date") or "").strip()
    chosen  = current if current in all_dates else all_dates[-1]

    try:
        sales = pos.get_sales_for_date(filepath, chosen)
    except ValueError as e:
        show_error("Blad", str(e)); return

    beers  = db.get_beers()
    sizes  = db.get_sizes()
    filled = 0

    for i, pw in enumerate(_pos_tags):
        if i >= len(beers): break
        beer_sales = sales.get(beers[i]["name"], {})
        for j, sz_tag in enumerate(pw["sizes"]):
            if j >= len(sizes): break
            lbl = sizes[j]["label"]
            qty = beer_sales.get(lbl, 0)
            if qty == 0:
                for k, v in beer_sales.items():
                    if k.replace("L","").strip() == lbl.replace("L","").strip():
                        qty = v; break
            if qty > 0:
                dpg.set_value(sz_tag, str(qty))
                filled += 1

    dpg.set_value("entry_date", chosen)
    _load_prev_starts()
    show_info("Import POS",
              f"Zaimportowano sprzedaz z dnia {chosen}\n"
              f"{filled} pol uzupelnionych.")


# ════════════════════════════════════════════════════════
#  ENTRY TAB — 3-column layout  (mirrors tkinter exactly)
# ════════════════════════════════════════════════════════
def build_entry_tab(parent):
    global _keg_tags, _pos_tags, _corr_tags, _sum_tags, _sum_total_tag
    _keg_tags = []; _pos_tags = []; _corr_tags = []; _sum_tags = []

    beers = db.get_beers()
    sizes = db.get_sizes()

    with dpg.group(parent=parent):

        # ── Info banner (green) ────────────────────────────
        with dpg.child_window(height=32, border=True, autosize_x=True):
            with dpg.theme() as _banner_t:
                with dpg.theme_component(dpg.mvChildWindow):
                    dpg.add_theme_color(dpg.mvThemeCol_ChildBg,  C("GREEN_BG"))
                    dpg.add_theme_color(dpg.mvThemeCol_Border,   C("GREEN"))
            dpg.bind_item_theme(dpg.last_container(), _banner_t)
            dpg.add_spacer(height=4)
            _colored_text(
                "START laduje sie automatycznie z poprzedniego dnia"
                " - wpisujesz tylko END na koniec zmiany + POS.",
                "GREEN")

        dpg.add_spacer(height=6)

        # ── Date row ───────────────────────────────────────
        with dpg.group(horizontal=True):
            _colored_text("Data:", "MUTED")
            dpg.add_spacer(width=6)
            dpg.add_input_text(tag="entry_date", width=120,
                               default_value=str(date.today()),
                               on_enter=False,
                               callback=lambda: _load_prev_starts())
            dpg.add_spacer(width=4)
            b1 = dpg.add_button(label="< Poprzedni",
                                 callback=lambda: _shift_date(-1),
                                 height=26, width=110)
            _recolor(b1, "_btn_secondary")
            b2 = dpg.add_button(label="Dzis",
                                 callback=lambda: (
                                     dpg.set_value("entry_date",
                                                   str(date.today())),
                                     _load_prev_starts()),
                                 height=26, width=60)
            _recolor(b2, "_btn_secondary")
            b3 = dpg.add_button(label="Nastepny >",
                                 callback=lambda: _shift_date(1),
                                 height=26, width=110)
            _recolor(b3, "_btn_secondary")
            dpg.add_spacer(width=14)
            b4 = dpg.add_button(label="Importuj POS (.xlsx)",
                                 callback=_import_pos,
                                 height=26)
            _recolor(b4, "_btn_info")

        dpg.add_spacer(height=8)

        # ── 3-column area ─────────────────────────────────
        vp_w   = dpg.get_viewport_width()
        col_w  = max(260, (vp_w - 40) // 3)
        row_h  = max(220, len(beers) * 28 + 60)

        with dpg.group(horizontal=True):

            # ── Col 1: Stan kegow ─────────────────────────
            _, keg_body = _card_begin(parent=dpg.last_container(),
                                      title="STAN KEGOW",
                                      width=col_w, height=row_h)
            _colored_text(
                "Szary=START auto | Zolty=dostawa | Tara 30L=11kg 20L=7kg",
                "MUTED", parent=keg_body)
            dpg.add_spacer(height=4, parent=keg_body)

            # Header row
            with dpg.group(horizontal=True, parent=keg_body):
                for lbl, w in [("Piwo",110),("START",58),("DOST.",54),
                                ("PELNE",50),("kg#1",50),("kg#2",50),
                                ("kg#3",50),("END",52)]:
                    t = dpg.add_text(lbl)
                    _recolor(t, "GOLD")
                    dpg.add_spacer(width=w - len(lbl)*8)
            dpg.add_separator(parent=keg_body)

            for beer in beers:
                rv = {"beer": beer, "_start_l": 0.0, "name": beer["name"]}
                with dpg.group(horizontal=True, parent=keg_body):
                    # Beer name
                    dpg.add_text(f"{beer['name']} ({beer['keg']}L)",
                                 color=C("TEXT"))
                    dpg.add_spacer(width=4)
                    # START (read-only)
                    sl = dpg.add_text("0.0L")
                    _recolor(sl, "GOLD")
                    rv["start_lbl"] = sl
                    dpg.add_spacer(width=4)
                    # DOSTAWA (yellow bg)
                    dt = f"kd_{beer['name']}"
                    dpg.add_input_text(tag=dt, width=50,
                                       callback=lambda: _recalc())
                    _recolor(dt, "_input_delivery")
                    rv["delivery"] = dt
                    # PEŁNE
                    ft = f"kf_{beer['name']}"
                    dpg.add_input_text(tag=ft, width=50,
                                       callback=lambda: _recalc())
                    rv["full_end"] = ft
                    # kg#1 kg#2 kg#3
                    rv["open"] = []
                    for j in range(3):
                        kt = f"ko_{beer['name']}_{j}"
                        dpg.add_input_text(tag=kt, width=50,
                                           callback=lambda: _recalc())
                        rv["open"].append(kt)
                    # END label
                    el = dpg.add_text("0.0L")
                    _recolor(el, "GOLD")
                    rv["end_lbl"] = el
                _keg_tags.append(rv)

            dpg.add_spacer(width=6)

            # ── Col 2: Sprzedaz POS ───────────────────────
            _, pos_body = _card_begin(parent=dpg.last_container(),
                                      title="SPRZEDAZ POS",
                                      width=col_w, height=row_h)
            dpg.add_text("", tag="pos_total_lbl",
                          color=C("MUTED"), parent=pos_body)
            dpg.add_spacer(height=4, parent=pos_body)

            # Header
            with dpg.group(horizontal=True, parent=pos_body):
                dpg.add_text("Piwo", color=C("GOLD"))
                for sz in sizes:
                    dpg.add_spacer(width=8)
                    dpg.add_text(sz["label"], color=C("GOLD"))
                dpg.add_spacer(width=8)
                dpg.add_text("Razem", color=C("GOLD"))
            dpg.add_separator(parent=pos_body)

            for beer in beers:
                pw = {"beer_name": beer["name"], "sizes": []}
                with dpg.group(horizontal=True, parent=pos_body):
                    dpg.add_text(beer["name"], color=C("TEXT"))
                    for j, sz in enumerate(sizes):
                        dpg.add_spacer(width=4)
                        pt = f"pp_{beer['name']}_{j}"
                        dpg.add_input_text(tag=pt, width=52,
                                           callback=lambda: _recalc())
                        pw["sizes"].append(pt)
                    dpg.add_spacer(width=6)
                    rl = dpg.add_text("0.00L")
                    _recolor(rl, "GOLD")
                    pw["razem"] = rl
                _pos_tags.append(pw)

            dpg.add_spacer(width=6)

            # ── Col 3: Korekty ─────────────────────────────
            _, corr_body = _card_begin(parent=dpg.last_container(),
                                       title="KOREKTY",
                                       width=col_w, height=row_h)
            dpg.add_text("", tag="corr_total_lbl",
                          color=C("MUTED"), parent=corr_body)
            dpg.add_spacer(height=4, parent=corr_body)

            # Header
            with dpg.group(horizontal=True, parent=corr_body):
                for lbl in ["Piwo", "Spill", "Void", "Open Bar", "Razem"]:
                    dpg.add_text(lbl, color=C("GOLD"))
                    dpg.add_spacer(width=8)
            dpg.add_separator(parent=corr_body)

            for beer in beers:
                cw = {"name": beer["name"]}
                with dpg.group(horizontal=True, parent=corr_body):
                    dpg.add_text(beer["name"], color=C("TEXT"))
                    dpg.add_spacer(width=6)
                    for field in ("spill", "void_", "open_bar"):
                        ct = f"cc_{beer['name']}_{field}"
                        dpg.add_input_text(tag=ct, width=60,
                                           callback=lambda: _recalc())
                        cw[field] = ct
                        dpg.add_spacer(width=4)
                    rl = dpg.add_text("-0.00")
                    _recolor(rl, "RED")
                    cw["razem"] = rl
                _corr_tags.append(cw)

        dpg.add_spacer(height=8)

        # ── Wynik dnia (mirrors tkinter _sum_frame) ───────
        _, sum_body = _card_begin(parent=dpg.last_container(),
                                   title="WYNIK DNIA", height=36 + len(beers)*26 + 36)
        for beer in beers:
            lbls = {}
            with dpg.group(horizontal=True, parent=sum_body):
                dpg.add_text(f"{beer['name']:10s}", color=C("TEXT"))
                dpg.add_spacer(width=12)
                il = dpg.add_text(
                    "START 0.0L   Del +0L   END 0.0L   POS 0.0L   Kor -0.0L",
                    color=C("MUTED"))
                lbls["info"] = il
                # Push diff to right
                dpg.add_spacer(width=40)
                dl = dpg.add_text("+OK  +0.00L")
                _recolor(dl, "GREEN")
                lbls["diff"] = dl
            _sum_tags.append(lbls)
        dpg.add_separator(parent=sum_body)
        _sum_total_tag = dpg.add_text(
            "LACZNIE:  +OK  +0.00L    POS: 0.0L    Kor: 0.0L",
            parent=sum_body, color=C("GREEN"))

        dpg.add_spacer(height=8)

        # ── Legend ─────────────────────────────────────────
        with dpg.group(horizontal=True):
            for s, (fg, _) in DIFF_KEYS.items():
                dpg.add_text(
                    f"  {DIFF_LABELS[s]} = {DIFF_TEXTS[s]}  ",
                    color=C(fg))

        dpg.add_spacer(height=8)

        # ── Action buttons ─────────────────────────────────
        with dpg.group(horizontal=True):
            dpg.add_button(label="Zapisz dzien",
                           callback=_save_day, height=32, width=140)
            dpg.add_spacer(width=6)
            b = dpg.add_button(label="Przelicz",
                               callback=_recalc, height=32, width=100)
            _recolor(b, "_btn_secondary")
            dpg.add_spacer(width=6)
            b = dpg.add_button(label="Wyczysc",
                               callback=_clear_day, height=32, width=100)
            _recolor(b, "_btn_muted")


# ════════════════════════════════════════════════════════
#  HISTORY TAB
# ════════════════════════════════════════════════════════
def build_history_tab(parent):
    with dpg.group(parent=parent):
        with dpg.group(horizontal=True):
            _colored_text("Miesiac:", "MUTED")
            dpg.add_spacer(width=6)
            months  = db.get_months()
            choices = months if months else ["(brak)"]
            dpg.add_combo(tag="hist_month", items=choices,
                          default_value=choices[0], width=180,
                          callback=_render_history)
        dpg.add_spacer(height=8)
        with dpg.child_window(tag="hist_list", border=False,
                               autosize_x=True, autosize_y=True):
            _render_history()


def _render_history():
    if not dpg.does_item_exist("hist_list"): return
    dpg.delete_item("hist_list", children_only=True)
    month   = (dpg.get_value("hist_month") or "").strip()
    entries = db.get_days_for_month(month)
    if not entries:
        dpg.add_text("Brak wpisow.", color=C("MUTED"), parent="hist_list")
        return
    for entry_date, data in reversed(entries):
        _hist_card("hist_list", entry_date, data)


def _hist_card(parent, entry_date, data):
    beers    = data.get("kegs", [])
    tot_diff = 0.0
    for i, k in enumerate(beers):
        pe = data["pos"][i]  if i < len(data.get("pos",  [])) else {"sizes": []}
        co = data["corr"][i] if i < len(data.get("corr", [])) else {}
        try: tot_diff += db.calc_diff(k, pe, co)
        except: pass
    tot_pos = sum(db.pos_liters(p) for p in data.get("pos", []))
    tot_del = sum(int(k.get("delivery", 0) or 0) for k in beers)
    s = db.diff_status(tot_diff)
    fg, _ = DIFF_KEYS[s]

    try:
        dt   = datetime.strptime(entry_date, "%Y-%m-%d")
        days = ["Pon","Wt","Sr","Czw","Pt","Sob","Ndz"]
        date_str = f"{days[dt.weekday()]} {dt.day:02d}.{dt.month:02d}.{dt.year}"
    except:
        date_str = entry_date

    with dpg.child_window(parent=parent, border=True,
                           autosize_x=True, auto_resize_y=True):
        with dpg.group(horizontal=True):
            dpg.add_text(date_str, color=C("TEXT"))
            if tot_del:
                dpg.add_spacer(width=16)
                dpg.add_text(f"Dostawa: {tot_del} keg", color=C("GOLD"))
            dpg.add_spacer(width=16)
            dpg.add_text(f"POS: {tot_pos:.1f}L", color=C("MUTED"))
            dpg.add_spacer(width=16)
            t = dpg.add_text(f"{DIFF_LABELS[s]}  {tot_diff:+.2f}L")
            _recolor(t, fg)

        for i, keg in enumerate(beers):
            pe = data["pos"][i]  if i < len(data.get("pos",  [])) else {"sizes": []}
            co = data["corr"][i] if i < len(data.get("corr", [])) else {}
            try: diff = db.calc_diff(keg, pe, co)
            except: diff = 0.0
            ks = db.diff_status(diff)
            kfg, _ = DIFF_KEYS[ks]
            with dpg.group(horizontal=True):
                dpg.add_text(f"  {keg['name']}", color=C("MUTED"))
                dpg.add_spacer(width=8)
                t = dpg.add_text(f"{DIFF_LABELS[ks]}  {diff:+.2f}L")
                _recolor(t, kfg)

        dpg.add_spacer(height=4)
        with dpg.group(horizontal=True):
            dpg.add_button(label="Edytuj",
                           callback=lambda s=0,a=0,u=(entry_date,data):
                               _open_edit(u[0], u[1]))
            dpg.add_spacer(width=6)
            b = dpg.add_button(
                label="Usun",
                callback=lambda s=0,a=0,u=entry_date:
                    show_confirm("Usun wpis",
                                 f"Usunac wpis z {u}?",
                                 lambda: (_hist_delete(u))))
            _recolor(b, "_btn_danger")
        dpg.add_spacer(height=4)


def _hist_delete(entry_date):
    db.delete_day(entry_date)
    _render_history()


def _open_edit(entry_date, data):
    dpg.set_value("entry_date", entry_date)
    dpg.set_value("main_tabs", "Wpis dnia")
    beers = db.get_beers()
    sizes = db.get_sizes()
    for i, rv in enumerate(_keg_tags):
        if i >= len(data.get("kegs", [])): continue
        keg = data["kegs"][i]
        rv["_start_l"] = db.safe_float(keg.get("start_l", 0))
        if dpg.does_item_exist(rv.get("start_lbl", 0)):
            dpg.set_value(rv["start_lbl"], f"{rv['_start_l']:.1f}L")
        v = keg.get("delivery", "")
        dpg.set_value(rv["delivery"],
                      "" if not v or v == "0" else str(v))
        v = keg.get("full_end", "")
        dpg.set_value(rv["full_end"],
                      "" if not v or v == "0" else str(v))
        ow = keg.get("open_end") or [None, None, None]
        for j in range(3):
            dpg.set_value(rv["open"][j],
                          str(ow[j]) if j < len(ow) and ow[j] else "")
    for i, pw in enumerate(_pos_tags):
        if i >= len(data.get("pos", [])): continue
        pe = data["pos"][i]
        for j, sz_tag in enumerate(pw["sizes"]):
            if j >= len(pe.get("sizes", [])): continue
            qty = pe["sizes"][j].get("qty", "")
            dpg.set_value(sz_tag, "" if not qty or qty == "0" else str(qty))
    for i, cw in enumerate(_corr_tags):
        if i >= len(data.get("corr", [])): continue
        co = data["corr"][i]
        for field in ["spill", "void_", "open_bar"]:
            v = co.get(field, "")
            dpg.set_value(cw[field], "" if not v or v == "0" else str(v))
    _recalc()


# ════════════════════════════════════════════════════════
#  REPORT TAB
# ════════════════════════════════════════════════════════
def build_report_tab(parent):
    with dpg.group(parent=parent):
        with dpg.group(horizontal=True):
            _colored_text("Miesiac:", "MUTED")
            dpg.add_spacer(width=6)
            months  = db.get_months()
            choices = months if months else ["(brak)"]
            dpg.add_combo(tag="rep_month", items=choices,
                          default_value=choices[0], width=180,
                          callback=_render_report)
            dpg.add_spacer(width=12)
            dpg.add_button(label="Export Excel (miesiac)",
                           callback=_export_month)
            dpg.add_spacer(width=6)
            b = dpg.add_button(label="Export Excel (rok)",
                               callback=_export_year)
            _recolor(b, "_btn_secondary")
        dpg.add_spacer(height=8)
        with dpg.child_window(tag="rep_body", border=False,
                               autosize_x=True, autosize_y=True):
            _render_report()


def _render_report():
    if not dpg.does_item_exist("rep_body"): return
    dpg.delete_item("rep_body", children_only=True)
    month   = (dpg.get_value("rep_month") or "").strip()
    entries = db.get_days_for_month(month)
    if not entries:
        dpg.add_text("Brak wpisow.", color=C("MUTED"), parent="rep_body")
        return

    tot_days = len(entries)
    tot_del  = sum(sum(int(k.get("delivery", 0) or 0)
                       for k in d.get("kegs", [])) for _, d in entries)
    tot_pos  = sum(sum(db.pos_liters(p)
                       for p in d.get("pos", [])) for _, d in entries)
    tot_corr = sum(sum(db.corr_liters(c)
                       for c in d.get("corr", [])) for _, d in entries)
    tot_diff = sum(
        db.calc_diff(k,
                     d["pos"][i]  if i < len(d.get("pos",  [])) else {"sizes": []},
                     d["corr"][i] if i < len(d.get("corr", [])) else {})
        for _, d in entries for i, k in enumerate(d.get("kegs", [])))

    p = "rep_body"
    ts = db.diff_status(tot_diff)
    fg, _ = DIFF_KEYS[ts]

    # KPI strip
    with dpg.group(horizontal=True, parent=p):
        for lbl, val, col in [
            ("Dni",     str(tot_days),         "GOLD"),
            ("Dostawa", f"{tot_del} keg",       "GOLD"),
            ("POS",     f"{tot_pos:.1f}L",      "TEXT"),
            ("Korekty", f"{tot_corr:.1f}L",     "TEXT"),
            ("Roznica",
             f"{DIFF_LABELS[ts]} {tot_diff:+.1f}L", fg),
        ]:
            with dpg.child_window(width=130, height=60, border=True):
                dpg.add_text(lbl, color=C("MUTED"))
                dpg.add_text(val, color=C(col))

    dpg.add_spacer(height=10, parent=p)
    _colored_text("WYNIK PER PIWO", "GOLD", parent=p)
    dpg.add_separator(parent=p)
    dpg.add_spacer(height=4, parent=p)

    beers_cfg = db.get_beers()
    agg = {b["name"]: {"diff": 0, "pos": 0, "del": 0, "days": 0}
           for b in beers_cfg}
    for _, data in entries:
        for i, keg in enumerate(data.get("kegs", [])):
            n  = keg["name"]
            if n not in agg:
                agg[n] = {"diff": 0, "pos": 0, "del": 0, "days": 0}
            pe = data["pos"][i]  if i < len(data.get("pos",  [])) else {"sizes": []}
            co = data["corr"][i] if i < len(data.get("corr", [])) else {}
            agg[n]["diff"] += db.calc_diff(keg, pe, co)
            agg[n]["pos"]  += db.pos_liters(pe)
            agg[n]["del"]  += int(keg.get("delivery", 0) or 0)
            agg[n]["days"] += 1

    for n, a in agg.items():
        diff = round(a["diff"], 2)
        s = db.diff_status(diff)
        rfg, _ = DIFF_KEYS[s]
        with dpg.group(horizontal=True, parent=p):
            dpg.add_text(f"{n:12s}", color=C("TEXT"))
            dpg.add_spacer(width=8)
            dpg.add_text(f"POS {a['pos']:.1f}L", color=C("MUTED"))
            dpg.add_spacer(width=8)
            dpg.add_text(f"Del {a['del']} keg", color=C("MUTED"))
            dpg.add_spacer(width=8)
            dpg.add_text(f"{a['days']} dni", color=C("MUTED"))
            dpg.add_spacer(width=20)
            t = dpg.add_text(f"{DIFF_LABELS[s]}  {diff:+.2f}L")
            _recolor(t, rfg)

    dpg.add_spacer(height=12, parent=p)
    _colored_text("TREND DZIENNY", "GOLD", parent=p)
    dpg.add_separator(parent=p)
    dpg.add_spacer(height=4, parent=p)

    for entry_date, data in entries:
        d_diff = sum(
            db.calc_diff(k,
                         data["pos"][i]  if i < len(data.get("pos",  [])) else {"sizes": []},
                         data["corr"][i] if i < len(data.get("corr", [])) else {})
            for i, k in enumerate(data.get("kegs", [])))
        ds = db.diff_status(d_diff)
        dfg, _ = DIFF_KEYS[ds]
        with dpg.group(horizontal=True, parent=p):
            dpg.add_text(entry_date, color=C("MUTED"))
            dpg.add_spacer(width=20)
            t = dpg.add_text(f"{DIFF_LABELS[ds]}  {d_diff:+.2f}L")
            _recolor(t, dfg)


def _export_month():
    dpg.show_item("export_month_dlg")


def _export_year():
    dpg.show_item("export_year_dlg")


def _on_export_month(sender, app_data):
    month = (dpg.get_value("rep_month") or "").strip()
    p = app_data.get("file_path_name", "")
    if not p: return
    if not p.endswith(".xlsx"): p += ".xlsx"
    if xl.export_month(month, p):
        show_info("OK", f"Zapisano:\n{p}")
    else:
        show_error("Blad", "Brak danych")


def _on_export_year(sender, app_data):
    val  = (dpg.get_value("rep_month") or "").strip()
    year = val[:4] if len(val) >= 4 else str(date.today().year)
    p = app_data.get("file_path_name", "")
    if not p: return
    if not p.endswith(".xlsx"): p += ".xlsx"
    if xl.export_year(year, p):
        show_info("OK", f"Zapisano:\n{p}")
    else:
        show_error("Blad", f"Brak danych dla roku {year}")


# ════════════════════════════════════════════════════════
#  SETTINGS TAB
# ════════════════════════════════════════════════════════
_beer_rows = []
_size_rows = []


def build_settings_tab(parent):
    global _beer_rows, _size_rows
    _beer_rows = []
    _size_rows = []

    with dpg.group(parent=parent):
        _colored_text("PIWA NA KRANIE", "GOLD")
        dpg.add_separator()
        dpg.add_spacer(height=4)
        dpg.add_group(tag="set_beers_grp")
        for b in db.get_beers():
            _add_beer_row(b["name"], str(b["keg"]))
        dpg.add_spacer(height=6)
        b = dpg.add_button(label="+ Dodaj piwo",
                           callback=lambda: _add_beer_row())
        _recolor(b, "_btn_secondary")

        dpg.add_spacer(height=16)
        _colored_text("ROZMIARY PORCJI POS", "GOLD")
        dpg.add_separator()
        dpg.add_spacer(height=4)
        dpg.add_group(tag="set_sizes_grp")
        for s in db.get_sizes():
            _add_size_row(s["label"], str(s["liters"]))
        dpg.add_spacer(height=6)
        b = dpg.add_button(label="+ Dodaj rozmiar",
                           callback=lambda: _add_size_row())
        _recolor(b, "_btn_secondary")

        dpg.add_spacer(height=20)
        with dpg.group(horizontal=True):
            dpg.add_button(label="Zapisz ustawienia",
                           callback=_save_settings, height=32, width=160)
            dpg.add_spacer(width=8)
            b = dpg.add_button(label="O programie",
                               callback=_show_about, height=32, width=120)
            _recolor(b, "_btn_muted")


def _add_beer_row(name="NOWE", keg="20"):
    row_id = f"br_{len(_beer_rows)}"
    nt     = f"bn_{len(_beer_rows)}"
    kt     = f"bk_{len(_beer_rows)}"
    with dpg.group(horizontal=True, tag=row_id,
                   parent="set_beers_grp"):
        dpg.add_input_text(tag=nt, default_value=name, width=160)
        dpg.add_spacer(width=6)
        dpg.add_combo(tag=kt, items=["20", "30", "50"],
                      default_value=keg, width=60)
        dpg.add_spacer(width=6)
        dpg.add_text("L keg", color=C("MUTED"))
        dpg.add_spacer(width=8)
        idx = len(_beer_rows)
        dpg.add_button(label="X",
                       callback=lambda: _del_row(row_id, _beer_rows, idx),
                       width=28)
    _beer_rows.append((nt, kt, row_id))


def _add_size_row(label="0.5L", liters="0.5"):
    row_id = f"sr_{len(_size_rows)}"
    lt     = f"sl_{len(_size_rows)}"
    lv     = f"sv_{len(_size_rows)}"
    with dpg.group(horizontal=True, tag=row_id,
                   parent="set_sizes_grp"):
        dpg.add_input_text(tag=lt, default_value=label,  width=80)
        dpg.add_spacer(width=6)
        dpg.add_input_text(tag=lv, default_value=liters, width=80)
        dpg.add_spacer(width=6)
        dpg.add_text("L/szt.", color=C("MUTED"))
        dpg.add_spacer(width=8)
        idx = len(_size_rows)
        dpg.add_button(label="X",
                       callback=lambda: _del_row(row_id, _size_rows, idx),
                       width=28)
    _size_rows.append((lt, lv, row_id))


def _del_row(row_id, lst, idx):
    if dpg.does_item_exist(row_id):
        dpg.delete_item(row_id)


def _save_settings():
    beers = []
    for nt, kt, rid in _beer_rows:
        if not dpg.does_item_exist(rid): continue
        nm = (dpg.get_value(nt) or "").strip().upper()
        try: kg = int(dpg.get_value(kt))
        except: kg = 20
        if nm: beers.append({"name": nm, "keg": kg})

    sizes = []
    for lt, lv, rid in _size_rows:
        if not dpg.does_item_exist(rid): continue
        lbl = (dpg.get_value(lt) or "").strip()
        val = db.safe_float(dpg.get_value(lv), 0.5)
        if lbl: sizes.append({"label": lbl, "liters": val})

    db.save_beers(beers)
    db.save_sizes(sizes)
    show_info("Zapisano", "Ustawienia zapisane.")


def _show_about():
    tag = "__about_modal"
    if dpg.does_item_exist(tag): dpg.delete_item(tag)
    vw = dpg.get_viewport_width()
    vh = dpg.get_viewport_height()
    with dpg.window(label="O programie", modal=True, tag=tag,
                    width=360, no_resize=True,
                    pos=[vw//2-180, vh//2-110]):
        _colored_text("Beer Count", "GOLD")
        _colored_text("System kontroli piwa", "MUTED")
        dpg.add_separator()
        dpg.add_spacer(height=8)
        for lbl, val in [("Wersja:", "1.0.0  (2026)"),
                          ("Autor:",  "Robert Khurshudian"),
                          ("Prawa:",  "(c) 2026 Robert Khurshudian"),
                          ("",        "Wszelkie prawa zastrzezone.")]:
            with dpg.group(horizontal=True):
                if lbl:
                    _colored_text(f"{lbl:9s}", "GOLD")
                else:
                    dpg.add_spacer(width=74)
                dpg.add_text(val)
        dpg.add_spacer(height=8)
        _colored_text("Powered by HTS", "GOLD")
        dpg.add_spacer(height=10)
        dpg.add_button(label="Zamknij", width=80,
                       callback=lambda: _close_modal(tag))


# ════════════════════════════════════════════════════════
#  THEME TOGGLE
# ════════════════════════════════════════════════════════
def toggle_theme():
    global _theme_mode, PAL
    _theme_mode = "light" if _theme_mode == "dark" else "dark"
    PAL = dict(LIGHT if _theme_mode == "light" else DARK)
    db.save_theme(_theme_mode)
    build_theme()
    build_color_themes()
    _lbl = "[ Ciemny ]" if _theme_mode == "light" else "[ Jasny ]"
    if dpg.does_item_exist("theme_btn"):
        dpg.set_item_label("theme_btn", _lbl)
        _recolor("theme_btn", "_btn_muted")


# ════════════════════════════════════════════════════════
#  MAIN WINDOW
# ════════════════════════════════════════════════════════
def build_ui():
    global _theme_mode, PAL
    db.init_db()
    _theme_mode = db.get_theme()
    PAL = dict(DARK if _theme_mode == "dark" else LIGHT)
    build_theme()
    build_color_themes()

    vp_w = dpg.get_viewport_width()
    vp_h = dpg.get_viewport_height()

    with dpg.window(tag="main_win", no_title_bar=True, no_move=True,
                    no_resize=True, no_scrollbar=True,
                    width=vp_w, height=vp_h):

        # ── Header bar ────────────────────────────────────
        dpg.add_spacer(height=4)
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=8)
            _colored_text("Beer Count", "GOLD")
            dpg.add_spacer(width=12)
            _colored_text("System kontroli piwa", "MUTED")
            dpg.add_spacer(width=20)
            _colored_text("|", "BORDER")
            dpg.add_spacer(width=20)
            _colored_text(date.today().strftime("%A, %d.%m.%Y"), "MUTED")
            dpg.add_spacer(width=30)
            _lbl = "[ Ciemny ]" if _theme_mode == "light" else "[ Jasny ]"
            tb = dpg.add_button(tag="theme_btn", label=_lbl,
                                 callback=toggle_theme,
                                 width=100, height=26)
            _recolor(tb, "_btn_muted")
            dpg.add_spacer(width=8)
        dpg.add_spacer(height=4)
        dpg.add_separator()
        dpg.add_spacer(height=4)

        # ── File dialogs ──────────────────────────────────
        with dpg.file_dialog(tag="pos_file_dialog", show=False,
                              width=700, height=440,
                              label="Wybierz plik XLSX z IzzyRest",
                              callback=_on_pos_file, file_count=1):
            dpg.add_file_extension(".xlsx", color=(100,200,100,255))
            dpg.add_file_extension(".xls",  color=(100,200,100,255))

        with dpg.file_dialog(tag="export_month_dlg", show=False,
                              width=700, height=440,
                              label="Zapisz raport miesięczny",
                              callback=_on_export_month,
                              default_filename=f"BeerCount_{date.today().strftime('%Y-%m')}.xlsx"):
            dpg.add_file_extension(".xlsx", color=(100,200,100,255))

        with dpg.file_dialog(tag="export_year_dlg", show=False,
                              width=700, height=440,
                              label="Zapisz raport roczny",
                              callback=_on_export_year,
                              default_filename=f"BeerCount_{date.today().year}_roczny.xlsx"):
            dpg.add_file_extension(".xlsx", color=(100,200,100,255))

        # ── Tab bar ───────────────────────────────────────
        with dpg.tab_bar(tag="main_tabs"):
            with dpg.tab(label="Wpis dnia"):
                with dpg.child_window(autosize_x=True, autosize_y=True,
                                       border=False):
                    build_entry_tab(dpg.last_container())

            with dpg.tab(label="Historia"):
                with dpg.child_window(autosize_x=True, autosize_y=True,
                                       border=False):
                    build_history_tab(dpg.last_container())

            with dpg.tab(label="Raport"):
                with dpg.child_window(autosize_x=True, autosize_y=True,
                                       border=False):
                    build_report_tab(dpg.last_container())

            with dpg.tab(label="Ustawienia"):
                with dpg.child_window(autosize_x=True, autosize_y=True,
                                       border=False):
                    build_settings_tab(dpg.last_container())

    dpg.set_primary_window("main_win", True)
    _load_prev_starts()
    _recalc()


# ════════════════════════════════════════════════════════
#  FONT LOADING
# ════════════════════════════════════════════════════════
def _load_fonts():
    with dpg.font_registry():
        for font_path in [
            r"C:/Windows/Fonts/segoeui.ttf",
            resource_path("NotoSans-Regular.ttf"),
        ]:
            if os.path.exists(font_path):
                try:
                    with dpg.font(font_path, 16.0, tag="default_font"):
                        dpg.add_font_range_hint(dpg.mvFontRangeHint_Default)
                        dpg.add_font_chars([
                            ord(c) for c in
                            "aacellonoszzAACELLNOSZZ"  # Polish base
                            "\u0105\u0107\u0119\u0142\u0144\u00f3"
                            "\u015b\u017a\u017c"
                            "\u0104\u0106\u0118\u0141\u0143\u00d3"
                            "\u015a\u0179\u017b"
                        ])
                    dpg.bind_font("default_font")
                    return
                except Exception:
                    pass


# ════════════════════════════════════════════════════════
#  ENTRY POINT
# ════════════════════════════════════════════════════════
if __name__ == "__main__":
    dpg.create_context()
    dpg.create_viewport(
        title="Beer Count",
        width=1400, height=860,
        min_width=1000, min_height=660,
        resizable=True)

    ico = resource_path("icon.ico")
    if os.path.exists(ico):
        try: dpg.set_viewport_small_icon(ico)
        except: pass
        try: dpg.set_viewport_large_icon(ico)
        except: pass

    dpg.setup_dearpygui()
    _load_fonts()
    build_ui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()
