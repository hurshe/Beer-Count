"""
database.py — SQLite backend for Beer Count HRC Warsaw
"""
import sqlite3, json, os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "beer_count.db")


def safe_float(value, default=0.0):
    """Parse a number that may use either '.' or ',' as the decimal
    separator. Polish keyboards and habits commonly produce values
    like '33,5' for what should be 33.5 — Python's float() rejects
    that outright and crashes the whole calculation. This accepts
    both, and falls back to `default` for anything else unparseable
    (empty string, None, garbage text) instead of raising."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return default
    # Normalize a comma decimal separator to a dot. This assumes the
    # comma is a decimal point, not a thousands separator — correct
    # for how these fields are actually used (small liter/kg values).
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return default


def safe_int(value, default=0):
    """Same idea as safe_float, but for whole-count fields (number of
    full kegs, number of delivered kegs) where a stray comma/decimal
    shouldn't crash things either — it's rounded to the nearest int."""
    return int(round(safe_float(value, default)))

DEFAULT_BEERS = [
    {"name": "ŻYWIEC",   "keg": 30},
    {"name": "HEINEKEN", "keg": 30},
    {"name": "MURPHYS",  "keg": 30},
    {"name": "BIAŁE",    "keg": 20},
    {"name": "IPA",      "keg": 20},
    {"name": "BIAŁE 0%", "keg": 20},
]
DEFAULT_SIZES = [
    {"label": "0.3L", "liters": 0.3},
    {"label": "0.4L", "liters": 0.4},
    {"label": "0.5L", "liters": 0.5},
    {"label": "1.5L", "liters": 1.5},
]
TARA = {20: 7, 30: 11, 50: 15}

_conn = None


def get_conn():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH)
        _conn.row_factory = sqlite3.Row
    return _conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS day_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_date TEXT UNIQUE NOT NULL,
        data_json  TEXT NOT NULL,
        updated_at TEXT DEFAULT (datetime('now')))""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_day_date ON day_entries(entry_date)")
    if not conn.execute("SELECT 1 FROM settings WHERE key='beers'").fetchone():
        conn.execute("INSERT INTO settings VALUES ('beers',?)", (json.dumps(DEFAULT_BEERS),))
    if not conn.execute("SELECT 1 FROM settings WHERE key='sizes'").fetchone():
        conn.execute("INSERT INTO settings VALUES ('sizes',?)", (json.dumps(DEFAULT_SIZES),))
    # Theme setting
    if not conn.execute("SELECT 1 FROM settings WHERE key='theme'").fetchone():
        conn.execute("INSERT INTO settings VALUES ('theme',?)", (json.dumps("light"),))
    conn.commit()


# ── Settings ──────────────────────────────────────
def get_beers():
    row = get_conn().execute("SELECT value FROM settings WHERE key='beers'").fetchone()
    return json.loads(row["value"]) if row else DEFAULT_BEERS

def save_beers(beers):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO settings VALUES ('beers',?)", (json.dumps(beers),))
    conn.commit()

def get_sizes():
    row = get_conn().execute("SELECT value FROM settings WHERE key='sizes'").fetchone()
    return json.loads(row["value"]) if row else DEFAULT_SIZES

def save_sizes(sizes):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO settings VALUES ('sizes',?)", (json.dumps(sizes),))
    conn.commit()

def get_theme():
    row = get_conn().execute("SELECT value FROM settings WHERE key='theme'").fetchone()
    return json.loads(row["value"]) if row else "light"

def save_theme(theme):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO settings VALUES ('theme',?)", (json.dumps(theme),))
    conn.commit()


# ── Day entries ───────────────────────────────────
def save_day(entry_date: str, data: dict):
    conn = get_conn()
    conn.execute("""INSERT INTO day_entries (entry_date, data_json, updated_at)
        VALUES (?,?,datetime('now'))
        ON CONFLICT(entry_date) DO UPDATE SET
            data_json=excluded.data_json,
            updated_at=datetime('now')""",
        (entry_date, json.dumps(data)))
    conn.commit()

def load_day(entry_date: str):
    row = get_conn().execute(
        "SELECT data_json FROM day_entries WHERE entry_date=?", (entry_date,)
    ).fetchone()
    return json.loads(row["data_json"]) if row else None

def get_prev_day(entry_date: str):
    """Return the last saved entry before entry_date."""
    row = get_conn().execute(
        "SELECT data_json FROM day_entries WHERE entry_date<? ORDER BY entry_date DESC LIMIT 1",
        (entry_date,)
    ).fetchone()
    return json.loads(row["data_json"]) if row else None

def get_months():
    rows = get_conn().execute(
        "SELECT DISTINCT substr(entry_date,1,7) AS m FROM day_entries ORDER BY m DESC"
    ).fetchall()
    return [r["m"] for r in rows]

def get_days_for_month(month: str):
    rows = get_conn().execute(
        "SELECT entry_date, data_json FROM day_entries WHERE entry_date LIKE ? ORDER BY entry_date ASC",
        (month + "%",)
    ).fetchall()
    return [(r["entry_date"], json.loads(r["data_json"])) for r in rows]

def get_all_days():
    rows = get_conn().execute(
        "SELECT entry_date, data_json FROM day_entries ORDER BY entry_date ASC"
    ).fetchall()
    return [(r["entry_date"], json.loads(r["data_json"])) for r in rows]

def delete_day(entry_date: str):
    conn = get_conn()
    conn.execute("DELETE FROM day_entries WHERE entry_date=?", (entry_date,))
    conn.commit()


# ── Calc helpers ──────────────────────────────────
def keg_end_liters(keg_data: dict) -> float:
    keg_size = safe_int(keg_data.get("keg", 20), 20)
    tara = TARA.get(keg_size, 7)
    full = safe_int(keg_data.get("full_end", 0)) * keg_size
    open_l = sum(
        max(safe_float(w) - tara, 0)
        for w in (keg_data.get("open_end") or [])
        if w not in (None, "", 0, "0")
    )
    return round(full + open_l, 3)

def keg_start_liters(keg_data: dict) -> float:
    """Start comes from prev day end — stored in 'start_l' field."""
    return safe_float(keg_data.get("start_l", 0))

def keg_delivery_liters(keg_data: dict) -> float:
    keg_size = safe_int(keg_data.get("keg", 20), 20)
    return safe_int(keg_data.get("delivery", 0)) * keg_size

def pos_liters(pos_entry: dict) -> float:
    return sum(
        safe_float(sz.get("qty", 0)) * safe_float(sz.get("liters", 0))
        for sz in (pos_entry.get("sizes") or [])
    )

def corr_liters(corr: dict) -> float:
    return (safe_float(corr.get("spill", 0)) +
            safe_float(corr.get("void_", 0)) +
            safe_float(corr.get("open_bar", 0)))

def calc_diff(keg_data, pos_entry, corr_data) -> float:
    """
    Różnica = END_faktyczny − (START + dostawa − POS − korekty)

    Logika:
      Teoretyczny_END = ile piwa POWINNO zostać po sprzedaży
                       = START + Dostawa − Sprzedaż_POS − Korekty

      Faktyczny_END   = ile piwa REALNIE zostało (ważenie/liczenie)

      Różnica = Faktyczny_END − Teoretyczny_END

    + (dodatnia) = zostało WIĘCEJ niż powinno
                 = niedolewanie porcji / sprzedaż poza systemem POS
    − (ujemna)   = zostało MNIEJ niż powinno
                 = spille, przelewy, straty, kradzież

    WAŻNE: jeśli START = 0 (brak danych z poprzedniego dnia, np.
    pierwszy dzień użytkowania aplikacji bez Kreatora), wynik
    Różnicy NIE jest miarodajny — będzie sztucznie bardzo ujemny,
    bo aplikacja nie wie ile piwa było w beczce na początku dnia.
    W takim wypadku najpierw uzupełnij stan początkowy w Kreatorze
    pierwszego uruchomienia (zakładka Ustawienia).
    """
    end_fact        = keg_end_liters(keg_data)
    start           = keg_start_liters(keg_data)
    delivery        = keg_delivery_liters(keg_data)
    pos             = pos_liters(pos_entry)
    corr            = corr_liters(corr_data)
    theoretical_end = start + delivery - pos - corr
    return round(end_fact - theoretical_end, 3)

def diff_status(diff: float) -> str:
    """Returns: ok / warn / over / bad"""
    if -2 <= diff <= 2: return "ok"
    if 2  < diff <= 5:  return "warn"
    if diff > 5:        return "over"
    return "bad"

def has_valid_start(keg_data: dict) -> bool:
    """True if this keg has a real START value (not zero/missing)."""
    return keg_start_liters(keg_data) > 0
