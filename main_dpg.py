"""
main_dpg.py — Beer Count v6 (DearPyGui)
GPU-rendered via DirectX 11. Replaces tkinter main.py.
Logic layers (database.py, pos_import.py, export_excel.py) unchanged.
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
#  PALETTE — same design language as tkinter version
#  but expressed as DPG (R,G,B,A) tuples 0-255
# ════════════════════════════════════════════════════════
def _h(hex6):
    h = hex6.lstrip("#")
    return tuple(int(h[i:i+2],16) for i in (0,2,4)) + (255,)

DARK = {
    "bg":          _h("15171a"),
    "surface":     _h("1f2228"),
    "surface2":    _h("2a2e38"),
    "border":      _h("383d46"),
    "gold":        _h("f0b272"),
    "gold_dim":    _h("4a3420"),
    "text":        _h("f2f3f5"),
    "muted":       _h("9aa1ab"),
    "green":       _h("7ee0a8"),
    "green_dim":   _h("1a3326"),
    "red":         _h("ff8a80"),
    "red_dim":     _h("3d1f1f"),
    "amber":       _h("ffcf7a"),
    "amber_dim":   _h("4a3a18"),
    "orange":      _h("ff9d5c"),
    "orange_dim":  _h("3d2614"),
    "delivery":    _h("3d2e1a"),
    "info":        _h("16263a"),
    "info_text":   _h("9cd0f5"),
    "prev":        _h("2a2e36"),
}

LIGHT = {
    "bg":          _h("eef1f4"),
    "surface":     _h("ffffff"),
    "surface2":    _h("e7ebef"),
    "border":      _h("dde3ea"),
    "gold":        _h("b85c38"),
    "gold_dim":    _h("f7e6dd"),
    "text":        _h("1e2530"),
    "muted":       _h("64748b"),
    "green":       _h("2a7a45"),
    "green_dim":   _h("eaf6ee"),
    "red":         _h("b83232"),
    "red_dim":     _h("fdeaea"),
    "amber":       _h("a06010"),
    "amber_dim":   _h("fff4e0"),
    "orange":      _h("c05000"),
    "orange_dim":  _h("fff0e0"),
    "delivery":    _h("fdecd9"),
    "info":        _h("e8f4fd"),
    "info_text":   _h("1a5276"),
    "prev":        _h("f0ede6"),
}

DIFF_CHIP = {
    "ok":   ("green",  "green_dim", "✅"),
    "warn": ("amber",  "amber_dim", "🟡"),
    "over": ("orange", "orange_dim","🟠"),
    "bad":  ("red",    "red_dim",   "🔴"),
}

# ── State ────────────────────────────────────────────────
_theme_mode = "dark"
PAL = dict(DARK)
_current_tab = "entry"

# UI widget tag registries
_keg_tags   = []   # list of dicts per beer row (keg section)
_pos_tags   = []   # list of dicts per beer row (pos section)
_corr_tags  = []   # list of dicts per beer row (corr section)
_sum_tags   = []   # list of dicts per beer (wynik row)
_sum_total_tag = ""

# ════════════════════════════════════════════════════════
#  THEME BUILDER
# ════════════════════════════════════════════════════════
_global_theme = None

def build_theme():
    global _global_theme, PAL
    if _global_theme and dpg.does_item_exist(_global_theme):
        dpg.delete_item(_global_theme)

    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg,      PAL["bg"])
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg,       PAL["surface"])
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg,       PAL["surface"])
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg,       PAL["surface2"])
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered,PAL["gold_dim"])
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, PAL["gold_dim"])
            dpg.add_theme_color(dpg.mvThemeCol_Border,        PAL["border"])
            dpg.add_theme_color(dpg.mvThemeCol_Text,          PAL["text"])
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled,  PAL["muted"])
            dpg.add_theme_color(dpg.mvThemeCol_Button,        PAL["gold"])
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, PAL["gold_dim"])
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,  PAL["gold"])
            dpg.add_theme_color(dpg.mvThemeCol_Header,        PAL["gold_dim"])
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, PAL["gold_dim"])
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive,  PAL["gold"])
            dpg.add_theme_color(dpg.mvThemeCol_Tab,           PAL["surface2"])
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered,    PAL["gold_dim"])
            dpg.add_theme_color(dpg.mvThemeCol_TabActive,     PAL["gold"])
            dpg.add_theme_color(dpg.mvThemeCol_TabUnfocused,       PAL["surface2"])
            dpg.add_theme_color(dpg.mvThemeCol_TabUnfocusedActive, PAL["gold_dim"])
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg,       PAL["surface2"])
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, PAL["surface2"])
            dpg.add_theme_color(dpg.mvThemeCol_MenuBarBg,     PAL["surface2"])
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg,   PAL["bg"])
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, PAL["border"])
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, PAL["gold"])
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark,     PAL["gold"])
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab,    PAL["gold"])
            dpg.add_theme_color(dpg.mvThemeCol_Separator,     PAL["border"])
            dpg.add_theme_color(dpg.mvThemeCol_SeparatorHovered, PAL["gold"])

            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding,   6)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding,    4)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,    3)
            dpg.add_theme_style(dpg.mvStyleVar_PopupRounding,    4)
            dpg.add_theme_style(dpg.mvStyleVar_TabRounding,      4)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding,     8, 5)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing,      6, 4)
            dpg.add_theme_style(dpg.mvStyleVar_CellPadding,      6, 4)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding,    12, 10)
            dpg.add_theme_style(dpg.mvStyleVar_IndentSpacing,    16)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarSize,    10)
    _global_theme = t
    dpg.bind_theme(t)

def _col(key, alpha=255):
    r,g,b,_ = PAL[key]
    return (r,g,b,alpha)

# ════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════
def _today_str():
    return str(date.today())

def _shift_entry_date(days):
    cur = dpg.get_value("entry_date") or _today_str()
    try:
        d = datetime.strptime(cur.strip(), "%Y-%m-%d").date()
    except ValueError:
        d = date.today()
    dpg.set_value("entry_date", str(d + timedelta(days=days)))
    _load_prev_starts()

def _diff_chip_parts(diff):
    s = db.diff_status(diff)
    fg_key, bg_key, icon = DIFF_CHIP[s]
    return fg_key, bg_key, icon, s

def _colored_text(parent, text, color_key, **kw):
    """Add text and bind pre-built color theme to it."""
    lbl = dpg.add_text(text, parent=parent, **kw)
    theme = _color_themes.get(color_key)
    if theme and dpg.does_item_exist(theme):
        dpg.bind_item_theme(lbl, theme)
    return lbl

def _section_header(parent, label):
    dpg.add_separator(parent=parent)
    lbl = dpg.add_text(f"  {label}", parent=parent)
    _recolor_text(lbl, "gold")
    dpg.add_separator(parent=parent)

# ════════════════════════════════════════════════════════
#  DIALOG SYSTEM  (replaces tkinter messagebox)
# ════════════════════════════════════════════════════════
def _close_modal(tag):
    if dpg.does_item_exist(tag):
        dpg.delete_item(tag)

def show_info(title, message):
    tag = f"_modal_{id(message)}"
    if dpg.does_item_exist(tag): dpg.delete_item(tag)
    with dpg.window(label=title, modal=True, tag=tag,
                    width=420, height=-1, no_resize=True,
                    pos=[dpg.get_viewport_width()//2-210,
                         dpg.get_viewport_height()//2-80]):
        dpg.add_spacer(height=8)
        _colored_text(dpg.last_container(), f"✅  {title}", "green")
        dpg.add_spacer(height=6)
        dpg.add_text(message, wrap=380)
        dpg.add_spacer(height=12)
        dpg.add_button(label="OK", width=80,
                       callback=lambda: _close_modal(tag))

def show_error(title, message):
    tag = f"_modal_{id(message)}"
    if dpg.does_item_exist(tag): dpg.delete_item(tag)
    with dpg.window(label=title, modal=True, tag=tag,
                    width=420, height=-1, no_resize=True,
                    pos=[dpg.get_viewport_width()//2-210,
                         dpg.get_viewport_height()//2-80]):
        dpg.add_spacer(height=8)
        _colored_text(dpg.last_container(), f"❌  {title}", "red")
        dpg.add_spacer(height=6)
        dpg.add_text(message, wrap=380)
        dpg.add_spacer(height=12)
        dpg.add_button(label="OK", width=80,
                       callback=lambda: _close_modal(tag))

def show_warning(title, message):
    tag = f"_modal_{id(message)}"
    if dpg.does_item_exist(tag): dpg.delete_item(tag)
    with dpg.window(label=title, modal=True, tag=tag,
                    width=420, height=-1, no_resize=True,
                    pos=[dpg.get_viewport_width()//2-210,
                         dpg.get_viewport_height()//2-80]):
        dpg.add_spacer(height=8)
        _colored_text(dpg.last_container(), f"⚠️  {title}", "amber")
        dpg.add_spacer(height=6)
        dpg.add_text(message, wrap=380)
        dpg.add_spacer(height=12)
        dpg.add_button(label="OK", width=80,
                       callback=lambda: _close_modal(tag))

def show_confirm(title, message, on_yes):
    tag = f"_modal_confirm_{id(message)}"
    if dpg.does_item_exist(tag): dpg.delete_item(tag)
    def _yes():
        _close_modal(tag)
        on_yes()
    with dpg.window(label=title, modal=True, tag=tag,
                    width=420, height=-1, no_resize=True,
                    pos=[dpg.get_viewport_width()//2-210,
                         dpg.get_viewport_height()//2-80]):
        dpg.add_spacer(height=8)
        _colored_text(dpg.last_container(), f"❓  {title}", "gold")
        dpg.add_spacer(height=6)
        dpg.add_text(message, wrap=380)
        dpg.add_spacer(height=12)
        with dpg.group(horizontal=True):
            dpg.add_button(label="Tak", width=80, callback=_yes)
            dpg.add_spacer(width=8)
            dpg.add_button(label="Anuluj", width=80,
                           callback=lambda: _close_modal(tag))

# ════════════════════════════════════════════════════════
#  DATA COLLECTION
# ════════════════════════════════════════════════════════
def _collect():
    beers = db.get_beers()
    sizes = db.get_sizes()
    data = {"kegs":[], "pos":[], "corr":[]}

    for i, rv in enumerate(_keg_tags):
        beer = beers[i] if i < len(beers) else {"name":"?","keg":20}
        data["kegs"].append({
            "name":     beer["name"],
            "keg":      beer["keg"],
            "start_l":  rv.get("_start_l", 0.0),
            "delivery": dpg.get_value(rv["delivery"]) or "0",
            "full_end": dpg.get_value(rv["full_end"]) or "0",
            "open_end": [dpg.get_value(rv["open_end"][j]) or None
                         for j in range(3)],
        })

    for i, pw in enumerate(_pos_tags):
        beer_name = beers[i]["name"] if i < len(beers) else "?"
        data["pos"].append({
            "name":  beer_name,
            "sizes": [{"liters": db.safe_float(sizes[j]["liters"]),
                       "qty":    dpg.get_value(pw["sizes"][j]) or "0"}
                      for j in range(len(sizes))
                      if j < len(pw["sizes"])],
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

    pos_grand = 0.0
    for i, pw in enumerate(_pos_tags):
        if i >= len(data["pos"]): break
        t = db.pos_liters(data["pos"][i])
        pos_grand += t
        if dpg.does_item_exist(pw.get("razem_lbl","")):
            dpg.set_value(pw["razem_lbl"], f"{t:.2f}L")

    corr_grand = 0.0
    for i, cw in enumerate(_corr_tags):
        if i >= len(data["corr"]): break
        t = db.corr_liters(data["corr"][i])
        corr_grand += t
        if dpg.does_item_exist(cw.get("razem_lbl","")):
            dpg.set_value(cw["razem_lbl"], f"−{t:.2f}")

    for i, rv in enumerate(_keg_tags):
        if i >= len(data["kegs"]): break
        end_l = db.keg_end_liters(data["kegs"][i])
        if dpg.does_item_exist(rv.get("end_lbl","")):
            dpg.set_value(rv["end_lbl"], f"{end_l:.1f}L")

    tot_diff = 0.0
    for i, lbls in enumerate(_sum_tags):
        if i >= len(data["kegs"]): break
        keg = data["kegs"][i]
        pe  = data["pos"][i]  if i < len(data["pos"])  else {"sizes":[]}
        co  = data["corr"][i] if i < len(data["corr"]) else {}
        diff = db.calc_diff(keg, pe, co)
        tot_diff += diff
        s = db.diff_status(diff)
        fg, bg, icon = DIFF_CHIP[s][:3]

        if dpg.does_item_exist(lbls.get("start_lbl","")):
            dpg.set_value(lbls["start_lbl"],
                f"START {db.keg_start_liters(keg):.1f}L  "
                f"Del +{db.keg_delivery_liters(keg):.0f}L  "
                f"END {db.keg_end_liters(keg):.1f}L  "
                f"POS {db.pos_liters(pe):.1f}L  "
                f"Kor −{db.corr_liters(co):.1f}L")
        if dpg.does_item_exist(lbls.get("diff_lbl","")):
            dpg.set_value(lbls["diff_lbl"], f"{icon} {diff:+.2f}L")
            _recolor_text(lbls["diff_lbl"], fg)

    if _sum_total_tag and dpg.does_item_exist(_sum_total_tag):
        ts = db.diff_status(tot_diff)
        fg, bg, icon = DIFF_CHIP[ts][:3]
        dpg.set_value(_sum_total_tag,
            f"{icon}  ŁĄCZNIE  {tot_diff:+.2f}L   "
            f"POS: {pos_grand:.1f}L   Kor: {corr_grand:.1f}L")
        _recolor_text(_sum_total_tag, fg)

# Pre-built text-color themes — created once at startup in build_color_themes(),
# reused for every _recolor_text call. Avoids the "Alias already exists" error
# that happens when creating/deleting themes with the same tag repeatedly.
_color_themes: dict = {}   # color_key -> dpg theme id

def build_color_themes():
    """Create one text-color theme per palette key. Call once after context init."""
    global _color_themes
    # Delete previous themes to avoid accumulation across toggle_theme calls
    for t in _color_themes.values():
        if dpg.does_item_exist(t):
            dpg.delete_item(t)
    _color_themes = {}
    for key, rgba in PAL.items():
        with dpg.theme() as t:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Text, rgba)
        _color_themes[key] = t
    # Special button themes
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button,       PAL["info"])
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, PAL["info"])
            dpg.add_theme_color(dpg.mvThemeCol_Text,          PAL["info_text"])
    _color_themes["btn_info"] = t
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button,       PAL["surface2"])
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, PAL["border"])
            dpg.add_theme_color(dpg.mvThemeCol_Text,          PAL["muted"])
    _color_themes["btn_muted"] = t

def _recolor_text(item_tag, color_key):
    """Bind a pre-built single-color theme to a text item."""
    if not dpg.does_item_exist(item_tag):
        return
    theme = _color_themes.get(color_key)
    if theme and dpg.does_item_exist(theme):
        dpg.bind_item_theme(item_tag, theme)

# ════════════════════════════════════════════════════════
#  LOAD PREVIOUS STARTS
# ════════════════════════════════════════════════════════
def _load_prev_starts():
    d = (dpg.get_value("entry_date") or "").strip()
    if not d: return
    prev = db.get_prev_day(d)
    prev_kegs = {}
    if prev:
        prev_kegs = {k["name"]: db.keg_end_liters(k)
                     for k in prev.get("kegs",[])}
    for rv in _keg_tags:
        name = rv["beer"]["name"]
        val  = prev_kegs.get(name, 0.0)
        rv["_start_l"] = val
        if dpg.does_item_exist(rv.get("start_lbl","")):
            dpg.set_value(rv["start_lbl"], f"{val:.1f}L")
    _recalc()

# ════════════════════════════════════════════════════════
#  SAVE DAY
# ════════════════════════════════════════════════════════
def _save_day():
    d = (dpg.get_value("entry_date") or "").strip()
    if not d:
        show_error("Błąd", "Wpisz datę!")
        return
    try:
        datetime.strptime(d, "%Y-%m-%d")
    except ValueError:
        show_error("Błąd", "Nieprawidłowy format daty.\nUżyj: RRRR-MM-DD")
        return
    data = _collect()
    db.save_day(d, data)
    show_info("Zapisano", f"Dzień {d} zapisany ✓")

def _clear_day():
    def do_clear():
        for rv in _keg_tags:
            dpg.set_value(rv["delivery"], "")
            dpg.set_value(rv["full_end"], "")
            for j in range(3):
                dpg.set_value(rv["open_end"][j], "")
        for pw in _pos_tags:
            for sz_tag in pw["sizes"]:
                dpg.set_value(sz_tag, "")
        for cw in _corr_tags:
            dpg.set_value(cw["spill"], "")
            dpg.set_value(cw["void_"], "")
            dpg.set_value(cw["open_bar"], "")
        _recalc()
    show_confirm("Wyczyścić?", "Wyczyścić wszystkie pola?", do_clear)

# ════════════════════════════════════════════════════════
#  POS IMPORT
# ════════════════════════════════════════════════════════
def _import_pos():
    dpg.show_item("pos_file_dialog")

def _on_pos_file_selected(sender, app_data):
    selections = app_data.get("selections", {})
    if not selections:
        return
    filepath = list(selections.values())[0]
    try:
        all_dates = pos.get_available_dates(filepath)
    except ValueError as e:
        show_error("Błąd importu", str(e))
        return

    if not all_dates:
        show_warning("Brak danych", "Plik nie zawiera danych sprzedaży.")
        return

    current = (dpg.get_value("entry_date") or "").strip()
    chosen = current if current in all_dates else all_dates[-1]

    try:
        sales = pos.get_sales_for_date(filepath, chosen)
    except ValueError as e:
        show_error("Błąd", str(e))
        return

    beers  = db.get_beers()
    sizes  = db.get_sizes()
    filled = 0

    for i, pw in enumerate(_pos_tags):
        if i >= len(beers): break
        beer_name  = beers[i]["name"]
        beer_sales = sales.get(beer_name, {})
        for j, sz_tag in enumerate(pw["sizes"]):
            if j >= len(sizes): break
            size_label = sizes[j]["label"]
            qty = beer_sales.get(size_label, 0)
            if qty == 0:
                for k, v in beer_sales.items():
                    if k.replace("L","").strip() == size_label.replace("L","").strip():
                        qty = v; break
            if qty > 0:
                dpg.set_value(sz_tag, str(qty))
                filled += 1

    dpg.set_value("entry_date", chosen)
    _load_prev_starts()
    show_info("Import POS",
              f"Zaimportowano sprzedaż z dnia {chosen}\n"
              f"{filled} pól uzupełnionych.")

# ════════════════════════════════════════════════════════
#  ENTRY TAB BUILD
# ════════════════════════════════════════════════════════
def build_entry_tab(parent):
    global _keg_tags, _pos_tags, _corr_tags, _sum_tags, _sum_total_tag
    _keg_tags  = []
    _pos_tags  = []
    _corr_tags = []
    _sum_tags  = []

    beers = db.get_beers()
    sizes = db.get_sizes()

    with dpg.group(parent=parent):

        # ── info banner ───────────────────────────
        lbl = dpg.add_text(
            "✅  START ładuje się automatycznie z poprzedniego dnia "
            "— wpisujesz tylko END + POS.",
            wrap=dpg.get_viewport_width()-40)
        _recolor_text(lbl, "green")

        dpg.add_spacer(height=4)

        # ── date row ──────────────────────────────
        with dpg.group(horizontal=True):
            dpg.add_text("Data:", color=PAL["muted"])
            dpg.add_input_text(
                tag="entry_date",
                default_value=_today_str(),
                width=130,
                callback=lambda: _load_prev_starts())
            dpg.add_button(label="◀ Poprzedni",
                           callback=lambda: _shift_entry_date(-1))
            dpg.add_button(label="Dziś",
                           callback=lambda: dpg.set_value(
                               "entry_date", _today_str()) or _load_prev_starts())
            dpg.add_button(label="Następny ▶",
                           callback=lambda: _shift_entry_date(1))
            imp_btn = dpg.add_button(label="📂 Importuj POS (xlsx)",
                                     callback=_import_pos)
            if "btn_info" in _color_themes:
                dpg.bind_item_theme(imp_btn, _color_themes["btn_info"])

        dpg.add_spacer(height=8)

        # ── 3-column layout ───────────────────────
        vp_w = dpg.get_viewport_width()
        col_w = max(280, (vp_w - 60) // 3)

        with dpg.group(horizontal=True):

            # ── Col 1: Stan kegów ─────────────────
            with dpg.child_window(width=col_w, height=-220, border=True):
                _colored_text(dpg.last_container(), "🛢  Stan kegów", "gold")
                dpg.add_text(
                    "szare=START auto | żółte=dostawa | Tara 30L=11kg 20L=7kg",
                    color=PAL["muted"])
                dpg.add_spacer(height=4)

                with dpg.table(header_row=True, resizable=False,
                               borders_innerV=True, borders_outerH=True,
                               scrollY=False, policy=dpg.mvTable_SizingStretchProp):
                    dpg.add_table_column(label="Piwo",    init_width_or_weight=2.0)
                    dpg.add_table_column(label="START",   init_width_or_weight=1.2)
                    dpg.add_table_column(label="DOSTAWA", init_width_or_weight=1.0)
                    dpg.add_table_column(label="PEŁNE",   init_width_or_weight=1.0)
                    dpg.add_table_column(label="kg#1",    init_width_or_weight=1.0)
                    dpg.add_table_column(label="kg#2",    init_width_or_weight=1.0)
                    dpg.add_table_column(label="kg#3",    init_width_or_weight=1.0)
                    dpg.add_table_column(label="END(L)",  init_width_or_weight=1.2)

                    for i, beer in enumerate(beers):
                        rv = {"beer": beer, "_start_l": 0.0}
                        with dpg.table_row():
                            dpg.add_text(f"{beer['name']} ({beer['keg']}L)",
                                         color=PAL["text"])
                            # START (read-only)
                            sl = dpg.add_text("0.0L", color=PAL["gold"])
                            rv["start_lbl"] = sl

                            # DELIVERY
                            del_tag = f"keg_del_{i}"
                            dpg.add_input_text(tag=del_tag, width=-1,
                                               hint="0",
                                               callback=lambda: _recalc())
                            rv["delivery"] = del_tag

                            # FULL END
                            full_tag = f"keg_full_{i}"
                            dpg.add_input_text(tag=full_tag, width=-1,
                                               hint="0",
                                               callback=lambda: _recalc())
                            rv["full_end"] = full_tag

                            # OPEN WEIGHTS × 3
                            rv["open_end"] = []
                            for j in range(3):
                                kg_tag = f"keg_open_{i}_{j}"
                                dpg.add_input_text(tag=kg_tag, width=-1,
                                                   hint="—",
                                                   callback=lambda: _recalc())
                                rv["open_end"].append(kg_tag)

                            # END label
                            el = dpg.add_text("0.0L", color=PAL["gold"])
                            rv["end_lbl"] = el

                        _keg_tags.append(rv)

            dpg.add_spacer(width=4)

            # ── Col 2: Sprzedaż POS ───────────────
            with dpg.child_window(width=col_w, height=-220, border=True):
                _colored_text(dpg.last_container(), "💻  Sprzedaż POS", "gold")
                dpg.add_spacer(height=20)

                with dpg.table(header_row=True, resizable=False,
                               borders_innerV=True, borders_outerH=True,
                               scrollY=False, policy=dpg.mvTable_SizingStretchProp):
                    dpg.add_table_column(label="Piwo",  init_width_or_weight=1.8)
                    for sz in sizes:
                        dpg.add_table_column(label=sz["label"],
                                             init_width_or_weight=1.0)
                    dpg.add_table_column(label="Razem", init_width_or_weight=1.2)

                    for i, beer in enumerate(beers):
                        pw = {"beer_name": beer["name"], "sizes": []}
                        with dpg.table_row():
                            dpg.add_text(beer["name"], color=PAL["text"])
                            for j, sz in enumerate(sizes):
                                sz_tag = f"pos_{i}_{j}"
                                dpg.add_input_text(tag=sz_tag, width=-1,
                                                   hint="0",
                                                   callback=lambda: _recalc())
                                pw["sizes"].append(sz_tag)
                            rl = dpg.add_text("0.00L", color=PAL["gold"])
                            pw["razem_lbl"] = rl
                        _pos_tags.append(pw)

            dpg.add_spacer(width=4)

            # ── Col 3: Korekty ────────────────────
            with dpg.child_window(width=col_w, height=-220, border=True):
                _colored_text(dpg.last_container(), "⚠️  Korekty", "gold")
                dpg.add_spacer(height=20)

                with dpg.table(header_row=True, resizable=False,
                               borders_innerV=True, borders_outerH=True,
                               scrollY=False, policy=dpg.mvTable_SizingStretchProp):
                    dpg.add_table_column(label="Piwo",     init_width_or_weight=1.8)
                    dpg.add_table_column(label="Spill",    init_width_or_weight=1.0)
                    dpg.add_table_column(label="Void",     init_width_or_weight=1.0)
                    dpg.add_table_column(label="Open Bar", init_width_or_weight=1.0)
                    dpg.add_table_column(label="Razem",    init_width_or_weight=1.2)

                    for i, beer in enumerate(beers):
                        cv = {"name": beer["name"]}
                        with dpg.table_row():
                            dpg.add_text(beer["name"], color=PAL["text"])
                            for field in ("spill","void_","open_bar"):
                                ft = f"corr_{i}_{field}"
                                dpg.add_input_text(tag=ft, width=-1,
                                                   hint="0",
                                                   callback=lambda: _recalc())
                                cv[field] = ft
                            rl = dpg.add_text("−0.00", color=PAL["red"])
                            cv["razem_lbl"] = rl
                        _corr_tags.append(cv)

        dpg.add_spacer(height=8)

        # ── Wynik dnia ────────────────────────────
        _colored_text(dpg.last_container(), "📊  Wynik dnia", "gold")
        dpg.add_separator()

        with dpg.table(header_row=False, resizable=False,
                       borders_innerV=False, borders_outerH=False,
                       scrollY=False, policy=dpg.mvTable_SizingStretchProp):
            dpg.add_table_column(init_width_or_weight=1.2)  # name
            dpg.add_table_column(init_width_or_weight=4.0)  # info
            dpg.add_table_column(init_width_or_weight=1.5)  # diff chip

            for i, beer in enumerate(beers):
                lbls = {}
                with dpg.table_row():
                    dpg.add_text(beer["name"], color=PAL["text"])
                    il = dpg.add_text("START 0L  Del +0L  END 0L  POS 0L  Kor −0L",
                                      color=PAL["muted"])
                    dl = dpg.add_text("✅ +0.00L", color=PAL["green"])
                lbls["start_lbl"] = il
                lbls["diff_lbl"]  = dl
                _sum_tags.append(lbls)

        dpg.add_separator()
        _sum_total_tag = dpg.add_text(
            "✅  ŁĄCZNIE  +0.00L   POS: 0.0L   Kor: 0.0L",
            color=PAL["green"])

        dpg.add_spacer(height=10)

        # ── legend ───────────────────────────────
        with dpg.group(horizontal=True):
            for s, (fg, bg, icon) in DIFF_CHIP.items():
                labels = {"ok":"±2L Norma","warn":">2L Sprawdź",
                          "over":">5L Poza POS?","bad":"<−5L Straty"}
                dpg.add_text(f"{icon} {labels[s]}  ", color=PAL[fg])

        dpg.add_spacer(height=8)

        # ── action buttons ───────────────────────
        with dpg.group(horizontal=True):
            dpg.add_button(label="💾  Zapisz dzień", callback=_save_day,
                           height=34)
            dpg.add_spacer(width=6)
            dpg.add_button(label="🔄  Przelicz", callback=_recalc,
                           height=34)
            dpg.add_spacer(width=6)
            clr = dpg.add_button(label="🗑  Wyczyść",
                                  callback=_clear_day, height=34)
            if "btn_muted" in _color_themes:
                dpg.bind_item_theme(clr, _color_themes["btn_muted"])

# ════════════════════════════════════════════════════════
#  HISTORY TAB
# ════════════════════════════════════════════════════════
def build_history_tab(parent):
    with dpg.group(parent=parent):
        with dpg.group(horizontal=True):
            dpg.add_text("Miesiąc:", color=PAL["muted"])
            months = db.get_months()
            choices = months if months else ["(brak)"]
            dpg.add_combo(tag="hist_month", items=choices,
                          default_value=choices[0], width=200,
                          callback=_render_history)
        dpg.add_spacer(height=8)
        with dpg.child_window(tag="hist_list", border=False,
                               autosize_x=True, autosize_y=True):
            _render_history()

def _render_history():
    if not dpg.does_item_exist("hist_list"): return
    dpg.delete_item("hist_list", children_only=True)
    month = (dpg.get_value("hist_month") or "").strip()
    entries = db.get_days_for_month(month)
    if not entries:
        dpg.add_text("Brak wpisów.", color=PAL["muted"], parent="hist_list")
        return
    sizes = db.get_sizes()
    for entry_date, data in reversed(entries):
        _build_hist_card("hist_list", entry_date, data, sizes)

def _build_hist_card(parent, entry_date, data, sizes):
    beers = data.get("kegs",[])
    tot_diff = 0.0
    for i, k in enumerate(beers):
        pe = data["pos"][i]  if i<len(data.get("pos",[])) else {"sizes":[]}
        co = data["corr"][i] if i<len(data.get("corr",[])) else {}
        try: tot_diff += db.calc_diff(k, pe, co)
        except: pass
    tot_pos = sum(db.pos_liters(p) for p in data.get("pos",[]))
    status  = db.diff_status(tot_diff)
    fg, bg, icon = DIFF_CHIP[status][:3]
    # Format date
    try:
        dt   = datetime.strptime(entry_date, "%Y-%m-%d")
        days = ["Pon","Wt","Śr","Czw","Pt","Sob","Ndz"]
        date_str = f"{days[dt.weekday()]} {dt.day:02d}.{dt.month:02d}.{dt.year}"
    except: date_str = entry_date

    with dpg.child_window(parent=parent, border=True,
                           autosize_x=True, auto_resize_y=True):
        with dpg.group(horizontal=True):
            dpg.add_text(date_str, color=PAL["text"])
            dpg.add_spacer(width=20)
            dpg.add_text(f"POS: {tot_pos:.1f}L", color=PAL["muted"])
            dpg.add_spacer(width=20)
            dpg.add_text(f"{icon} {tot_diff:+.2f}L", color=PAL[fg])

        for i, keg in enumerate(beers):
            pe = data["pos"][i]  if i<len(data.get("pos",[])) else {"sizes":[]}
            co = data["corr"][i] if i<len(data.get("corr",[])) else {}
            try: diff = db.calc_diff(keg, pe, co)
            except: diff = 0.0
            s = db.diff_status(diff)
            fg2, _, icon2 = DIFF_CHIP[s][:3]
            with dpg.group(horizontal=True):
                dpg.add_text(f"  {keg['name']}", color=PAL["muted"])
                dpg.add_spacer(width=10)
                dpg.add_text(f"{icon2} {diff:+.2f}L", color=PAL[fg2])

        dpg.add_spacer(height=4)
        with dpg.group(horizontal=True):
            dpg.add_button(label="✏️ Edytuj",
                           callback=lambda s=0,a=0,u=(entry_date,data):
                               _open_edit(u[0], u[1]))
            dpg.add_spacer(width=6)
            dpg.add_button(label="🗑 Usuń",
                           callback=lambda s=0,a=0,u=entry_date:
                               show_confirm("Usuń wpis",
                                   f"Usunąć wpis z {u}?",
                                   lambda: _delete_day(u)))
        dpg.add_spacer(height=4)

def _delete_day(entry_date):
    db.delete_day(entry_date)
    _render_history()

def _open_edit(entry_date, data):
    dpg.set_value("entry_date", entry_date)
    dpg.set_value("main_tabs", "Wpis dnia")
    beers = db.get_beers()
    sizes = db.get_sizes()
    for i, rv in enumerate(_keg_tags):
        if i >= len(data.get("kegs",[])): continue
        keg = data["kegs"][i]
        rv["_start_l"] = db.safe_float(keg.get("start_l",0))
        dpg.set_value(rv["start_lbl"], f"{rv['_start_l']:.1f}L")
        del_val = keg.get("delivery","")
        dpg.set_value(rv["delivery"], "" if not del_val or del_val=="0" else str(del_val))
        full_val = keg.get("full_end","")
        dpg.set_value(rv["full_end"], "" if not full_val or full_val=="0" else str(full_val))
        ow = keg.get("open_end") or [None,None,None]
        for j in range(3):
            dpg.set_value(rv["open_end"][j],
                          str(ow[j]) if j<len(ow) and ow[j] else "")
    for i, pw in enumerate(_pos_tags):
        if i >= len(data.get("pos",[])): continue
        pe = data["pos"][i]
        for j, sz_tag in enumerate(pw["sizes"]):
            if j >= len(pe.get("sizes",[])): continue
            qty = pe["sizes"][j].get("qty","")
            dpg.set_value(sz_tag, "" if not qty or qty=="0" else str(qty))
    for i, cw in enumerate(_corr_tags):
        if i >= len(data.get("corr",[])): continue
        co = data["corr"][i]
        for field in ["spill","void_","open_bar"]:
            val = co.get(field,"")
            dpg.set_value(cw[field], "" if not val or val=="0" else str(val))
    _recalc()

# ════════════════════════════════════════════════════════
#  REPORT TAB
# ════════════════════════════════════════════════════════
def build_report_tab(parent):
    with dpg.group(parent=parent):
        with dpg.group(horizontal=True):
            dpg.add_text("Miesiąc:", color=PAL["muted"])
            months = db.get_months()
            choices = months if months else ["(brak)"]
            dpg.add_combo(tag="rep_month", items=choices,
                          default_value=choices[0], width=200,
                          callback=_render_report)
            dpg.add_spacer(width=12)
            dpg.add_button(label="📥 Export Excel (miesiąc)",
                           callback=_export_month)
            dpg.add_spacer(width=6)
            dpg.add_button(label="📥 Export Excel (rok)",
                           callback=_export_year)
        dpg.add_spacer(height=8)
        with dpg.child_window(tag="rep_body", border=False,
                               autosize_x=True, autosize_y=True):
            _render_report()

def _render_report():
    if not dpg.does_item_exist("rep_body"): return
    dpg.delete_item("rep_body", children_only=True)
    val   = dpg.get_value("rep_month") or ""
    month = val.strip()
    entries = db.get_days_for_month(month)
    if not entries:
        dpg.add_text("Brak wpisów.", color=PAL["muted"], parent="rep_body")
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

    p = "rep_body"
    # KPIs
    with dpg.group(horizontal=True, parent=p):
        for lbl, val2, col in [
            ("Dni",     str(tot_days),          "gold"),
            ("Dostawa", f"{tot_del} keg",        "gold"),
            ("POS",     f"{tot_pos:.1f}L",       "text"),
            ("Korekty", f"{tot_corr:.1f}L",      "text"),
            ("Różnica", f"{tot_diff:+.1f}L",
             DIFF_CHIP[db.diff_status(tot_diff)][0]),
        ]:
            with dpg.child_window(width=140, height=64, border=True):
                dpg.add_text(lbl, color=PAL["muted"])
                dpg.add_text(val2, color=PAL[col])

    dpg.add_spacer(height=10, parent=p)
    dpg.add_text("Wynik per piwo", color=PAL["gold"], parent=p)
    dpg.add_separator(parent=p)

    beers_cfg = db.get_beers()
    agg = {b["name"]:{"diff":0,"pos":0,"del":0,"days":0} for b in beers_cfg}
    for _, data in entries:
        for i, keg in enumerate(data.get("kegs",[])):
            n = keg["name"]
            if n not in agg: agg[n]={"diff":0,"pos":0,"del":0,"days":0}
            pe = data["pos"][i]  if i<len(data.get("pos",[])) else {"sizes":[]}
            co = data["corr"][i] if i<len(data.get("corr",[])) else {}
            agg[n]["diff"] += db.calc_diff(keg, pe, co)
            agg[n]["pos"]  += db.pos_liters(pe)
            agg[n]["del"]  += int(keg.get("delivery",0) or 0)
            agg[n]["days"] += 1

    with dpg.table(parent=p, header_row=True, resizable=False,
                   borders_innerV=True, borders_outerH=True,
                   policy=dpg.mvTable_SizingStretchProp):
        dpg.add_table_column(label="Piwo")
        dpg.add_table_column(label="POS (L)")
        dpg.add_table_column(label="Dostawa (keg)")
        dpg.add_table_column(label="Dni")
        dpg.add_table_column(label="Różnica")
        for n, a in agg.items():
            diff = round(a["diff"],2)
            s = db.diff_status(diff)
            fg, _, icon = DIFF_CHIP[s][:3]
            with dpg.table_row():
                dpg.add_text(n)
                dpg.add_text(f"{a['pos']:.1f}L")
                dpg.add_text(str(a["del"]))
                dpg.add_text(str(a["days"]))
                dpg.add_text(f"{icon} {diff:+.2f}L", color=PAL[fg])

    dpg.add_spacer(height=10, parent=p)
    dpg.add_text("Trend dzienny", color=PAL["gold"], parent=p)
    dpg.add_separator(parent=p)

    for entry_date, data in entries:
        d_diff = sum(
            db.calc_diff(k,
                         data["pos"][i]  if i<len(data.get("pos",[])) else {"sizes":[]},
                         data["corr"][i] if i<len(data.get("corr",[])) else {})
            for i,k in enumerate(data.get("kegs",[])))
        s = db.diff_status(d_diff)
        fg, _, icon = DIFF_CHIP[s][:3]
        with dpg.group(horizontal=True, parent=p):
            dpg.add_text(entry_date, color=PAL["muted"])
            dpg.add_spacer(width=20)
            dpg.add_text(f"{icon} {d_diff:+.2f}L", color=PAL[fg])

def _export_month():
    month = (dpg.get_value("rep_month") or "").strip()
    if not month: return
    dpg.show_item("export_month_dialog")

def _export_year():
    val  = (dpg.get_value("rep_month") or "").strip()
    year = val[:4] if len(val) >= 4 else str(date.today().year)
    dpg.show_item("export_year_dialog")

def _on_export_month_selected(sender, app_data):
    month = (dpg.get_value("rep_month") or "").strip()
    p = app_data.get("file_path_name","")
    if not p: return
    if not p.endswith(".xlsx"): p += ".xlsx"
    if xl.export_month(month, p):
        show_info("OK", f"Zapisano:\n{p}")
    else:
        show_error("Błąd", "Brak danych")

def _on_export_year_selected(sender, app_data):
    val  = (dpg.get_value("rep_month") or "").strip()
    year = val[:4] if len(val) >= 4 else str(date.today().year)
    p = app_data.get("file_path_name","")
    if not p: return
    if not p.endswith(".xlsx"): p += ".xlsx"
    if xl.export_year(year, p):
        show_info("OK", f"Zapisano:\n{p}")
    else:
        show_error("Błąd", f"Brak danych dla roku {year}")

# ════════════════════════════════════════════════════════
#  SETTINGS TAB
# ════════════════════════════════════════════════════════
def build_settings_tab(parent):
    global _beer_rows, _size_rows
    _beer_rows = []
    _size_rows = []
    with dpg.group(parent=parent):
        _colored_text(dpg.last_container(), "🍺  Piwa na kranie", "gold")
        dpg.add_separator()
        with dpg.table(tag="set_beers_tbl", header_row=True,
                       resizable=False, borders_innerV=True,
                       borders_outerH=True,
                       policy=dpg.mvTable_SizingStretchProp):
            dpg.add_table_column(label="Nazwa")
            dpg.add_table_column(label="Rozmiar kegu (L)")
            dpg.add_table_column(label="")
            for b in db.get_beers():
                _add_beer_settings_row(b["name"], str(b["keg"]))

        dpg.add_button(label="+ Dodaj piwo",
                       callback=lambda: _add_beer_settings_row())
        dpg.add_spacer(height=16)

        _colored_text(dpg.last_container(), "🥃  Rozmiary porcji POS", "gold")
        dpg.add_separator()
        with dpg.table(tag="set_sizes_tbl", header_row=True,
                       resizable=False, borders_innerV=True,
                       borders_outerH=True,
                       policy=dpg.mvTable_SizingStretchProp):
            dpg.add_table_column(label="Etykieta (np. 0.5L)")
            dpg.add_table_column(label="Litry (np. 0.5)")
            dpg.add_table_column(label="")
            for s in db.get_sizes():
                _add_size_settings_row(s["label"], str(s["liters"]))

        dpg.add_button(label="+ Dodaj rozmiar",
                       callback=lambda: _add_size_settings_row())
        dpg.add_spacer(height=16)

        with dpg.group(horizontal=True):
            dpg.add_button(label="💾  Zapisz ustawienia",
                           callback=_save_settings, height=34)
            dpg.add_spacer(width=8)
            ab = dpg.add_button(label="ℹ️  O programie",
                                 callback=_show_about, height=34)
            if "btn_muted" in _color_themes:
                dpg.bind_item_theme(ab, _color_themes["btn_muted"])

_beer_rows  = []   # list of (name_tag, keg_tag, row_tag)
_size_rows  = []   # list of (label_tag, liters_tag, row_tag)

def _add_beer_settings_row(name="NOWE", keg="20"):
    row_id = f"beer_row_{len(_beer_rows)}"
    with dpg.table_row(tag=row_id, parent="set_beers_tbl"):
        nt = f"beer_name_{len(_beer_rows)}"
        kt = f"beer_keg_{len(_beer_rows)}"
        dpg.add_input_text(tag=nt, default_value=name, width=-1)
        dpg.add_combo(tag=kt, items=["20","30","50"],
                      default_value=keg, width=-1)
        def _del(rt=row_id, idx=len(_beer_rows)):
            if dpg.does_item_exist(rt):
                dpg.delete_item(rt)
        dpg.add_button(label="✕", callback=_del,
                       width=30)
    _beer_rows.append((nt, kt, row_id))

def _add_size_settings_row(label="0.5L", liters="0.5"):
    row_id = f"size_row_{len(_size_rows)}"
    with dpg.table_row(tag=row_id, parent="set_sizes_tbl"):
        lt  = f"size_label_{len(_size_rows)}"
        lit = f"size_liters_{len(_size_rows)}"
        dpg.add_input_text(tag=lt, default_value=label, width=-1)
        dpg.add_input_text(tag=lit, default_value=liters, width=-1)
        def _del(rt=row_id):
            if dpg.does_item_exist(rt):
                dpg.delete_item(rt)
        dpg.add_button(label="✕", callback=_del, width=30)
    _size_rows.append((lt, lit, row_id))

def _save_settings():
    beers = []
    for nt, kt, rt in _beer_rows:
        if not dpg.does_item_exist(rt): continue
        nm = (dpg.get_value(nt) or "").strip().upper()
        try: kg = int(dpg.get_value(kt))
        except: kg = 20
        if nm: beers.append({"name":nm,"keg":kg})
    sizes = []
    for lt, lit, rt in _size_rows:
        if not dpg.does_item_exist(rt): continue
        lbl = (dpg.get_value(lt) or "").strip()
        val = db.safe_float(dpg.get_value(lit), 0.5)
        if lbl: sizes.append({"label":lbl,"liters":val})
    db.save_beers(beers)
    db.save_sizes(sizes)
    show_info("Zapisano","Ustawienia zapisane ✓")

def _show_about():
    tag = "_about_modal"
    if dpg.does_item_exist(tag): dpg.delete_item(tag)
    with dpg.window(label="O programie", modal=True, tag=tag,
                    width=380, height=-1, no_resize=True,
                    pos=[dpg.get_viewport_width()//2-190,
                         dpg.get_viewport_height()//2-120]):
        dpg.add_text("🍺  Beer Count", color=PAL["gold"])
        dpg.add_separator()
        dpg.add_spacer(height=8)
        for k, v in [("Wersja:", "1.0.0  (2026)"),
                     ("Autor:",  "Robert Khurshudian"),
                     ("Prawa:",  "© 2026 Robert Khurshudian"),
                     ("",        "Wszelkie prawa zastrzeżone.")]:
            with dpg.group(horizontal=True):
                dpg.add_text(k, color=PAL["gold"])
                dpg.add_text(v)
        dpg.add_spacer(height=8)
        dpg.add_text("Powered by HTS", color=PAL["gold"])
        dpg.add_spacer(height=10)
        dpg.add_button(label="Zamknij", width=80,
                       callback=lambda: _close_modal(tag))

# ════════════════════════════════════════════════════════
#  THEME TOGGLE
# ════════════════════════════════════════════════════════
def toggle_theme():
    global _theme_mode, PAL
    _theme_mode = "light" if _theme_mode == "dark" else "dark"
    PAL = dict(DARK if _theme_mode == "dark" else LIGHT)
    db.save_theme(_theme_mode)
    build_theme()
    build_color_themes()
    icon = "☀️" if _theme_mode == "dark" else "🌙"
    if dpg.does_item_exist("theme_btn"):
        dpg.set_item_label("theme_btn", icon)

# ════════════════════════════════════════════════════════
#  MAIN WINDOW BUILD
# ════════════════════════════════════════════════════════
def build_ui():
    global _theme_mode, PAL

    db.init_db()
    _theme_mode = db.get_theme()
    PAL = dict(DARK if _theme_mode == "dark" else LIGHT)
    build_theme()
    build_color_themes()   # pre-build per-color text themes

    vp_w = dpg.get_viewport_width()
    vp_h = dpg.get_viewport_height()

    with dpg.window(tag="main_win", label="Beer Count",
                    width=vp_w, height=vp_h,
                    no_title_bar=True, no_move=True,
                    no_resize=True, no_scrollbar=True):

        # ── top bar ───────────────────────────────
        with dpg.group(horizontal=True):
            dpg.add_text("🍺", color=PAL["gold"])
            dpg.add_text(" Beer Count", color=PAL["gold"])
            dpg.add_text("  System kontroli piwa", color=PAL["muted"])
            dpg.add_spacer(width=-180)
            dpg.add_text(date.today().strftime("%A, %d.%m.%Y"),
                         color=PAL["muted"])
            dpg.add_spacer(width=12)
            icon = "☀️" if _theme_mode == "dark" else "🌙"
            dpg.add_button(tag="theme_btn", label=icon,
                           callback=toggle_theme, width=36, height=24)

        dpg.add_separator()
        dpg.add_spacer(height=4)

        # ── file dialogs ─────────────────────────
        with dpg.file_dialog(tag="pos_file_dialog", show=False,
                              width=700, height=440,
                              label="Wybierz plik XLSX z IzzyRest",
                              callback=_on_pos_file_selected,
                              file_count=1):
            dpg.add_file_extension(".xlsx", color=(100,200,100,255))
            dpg.add_file_extension(".xls",  color=(100,200,100,255))

        with dpg.file_dialog(tag="export_month_dialog", show=False,
                              width=700, height=440,
                              label="Zapisz raport miesięczny",
                              callback=_on_export_month_selected,
                              default_filename=f"BeerCount_{date.today().strftime('%Y-%m')}.xlsx"):
            dpg.add_file_extension(".xlsx", color=(100,200,100,255))

        with dpg.file_dialog(tag="export_year_dialog", show=False,
                              width=700, height=440,
                              label="Zapisz raport roczny",
                              callback=_on_export_year_selected,
                              default_filename=f"BeerCount_{date.today().year}_roczny.xlsx"):
            dpg.add_file_extension(".xlsx", color=(100,200,100,255))

        # ── tab bar ───────────────────────────────
        with dpg.tab_bar(tag="main_tabs"):
            with dpg.tab(label="📋  Wpis dnia"):
                with dpg.child_window(autosize_x=True, autosize_y=True,
                                       border=False):
                    build_entry_tab(dpg.last_container())

            with dpg.tab(label="📅  Historia"):
                with dpg.child_window(autosize_x=True, autosize_y=True,
                                       border=False):
                    build_history_tab(dpg.last_container())

            with dpg.tab(label="📊  Raport"):
                with dpg.child_window(autosize_x=True, autosize_y=True,
                                       border=False):
                    build_report_tab(dpg.last_container())

            with dpg.tab(label="⚙️  Ustawienia"):
                with dpg.child_window(autosize_x=True, autosize_y=True,
                                       border=False):
                    build_settings_tab(dpg.last_container())

    dpg.set_primary_window("main_win", True)
    _load_prev_starts()
    _recalc()

# ════════════════════════════════════════════════════════
#  ENTRY POINT
# ════════════════════════════════════════════════════════
if __name__ == "__main__":
    dpg.create_context()
    dpg.create_viewport(
        title="🍺 Beer Count",
        width=1280, height=800,
        min_width=900, min_height=600,
        resizable=True)

    ico = resource_path("icon.ico")
    if os.path.exists(ico):
        try: dpg.set_viewport_small_icon(ico)
        except: pass
        try: dpg.set_viewport_large_icon(ico)
        except: pass

    dpg.setup_dearpygui()
    build_ui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()
