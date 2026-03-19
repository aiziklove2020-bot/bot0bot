import sqlite3

DB_PATH = "bot_data.db"

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                is_banned INTEGER DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER UNIQUE,
                name TEXT,
                username TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE TABLE IF NOT EXISTS custom_buttons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT,
                url TEXT
            );
            CREATE TABLE IF NOT EXISTS auto_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT,
                send_time TEXT
            );
        """)
        self.conn.commit()

    # ===== משתמשים =====
    def add_user(self, user_id, username, first_name):
        self.conn.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)", (user_id, username, first_name))
        self.conn.commit()

    def get_all_users(self):
        return [dict(r) for r in self.conn.execute("SELECT * FROM users WHERE is_banned = 0").fetchall()]

    def get_users_count(self):
        return self.conn.execute("SELECT COUNT(*) FROM users WHERE is_banned = 0").fetchone()[0]

    def ban_user(self, user_id):
        self.conn.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def unban_user(self, user_id):
        self.conn.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def get_banned_users(self):
        return [dict(r) for r in self.conn.execute("SELECT * FROM users WHERE is_banned = 1").fetchall()]

    def get_banned_count(self):
        return self.conn.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1").fetchone()[0]

    # ===== ערוצים =====
    def add_channel(self, chat_id, name, username=""):
        self.conn.execute("INSERT OR REPLACE INTO channels (chat_id, name, username) VALUES (?, ?, ?)", (chat_id, name, username))
        self.conn.commit()

    def remove_channel(self, chat_id):
        self.conn.execute("DELETE FROM channels WHERE chat_id = ?", (chat_id,))
        self.conn.commit()

    def get_channels(self):
        return [dict(r) for r in self.conn.execute("SELECT * FROM channels").fetchall()]

    # ===== הגדרות (חוקים) =====
    def get_rules(self):
        r = self.conn.execute("SELECT value FROM settings WHERE key = 'rules'").fetchone()
        return r[0] if r else None

    def set_rules(self, text):
        self.conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('rules', ?)", (text,))
        self.conn.commit()

    # ===== כפתורים מותאמים =====
    def add_custom_button(self, text, url):
        self.conn.execute("INSERT INTO custom_buttons (text, url) VALUES (?, ?)", (text, url))
        self.conn.commit()

    def get_custom_buttons(self):
        return [dict(r) for r in self.conn.execute("SELECT * FROM custom_buttons").fetchall()]

    def delete_custom_button(self, btn_id):
        self.conn.execute("DELETE FROM custom_buttons WHERE id = ?", (btn_id,))
        self.conn.commit()

    # ===== הודעות אוטומטיות =====
    def add_auto_message(self, text, send_time):
        self.conn.execute("INSERT INTO auto_messages (text, send_time) VALUES (?, ?)", (text, send_time))
        self.conn.commit()

    def get_auto_messages(self):
        return [dict(r) for r in self.conn.execute("SELECT * FROM auto_messages").fetchall()]

    def delete_auto_message(self, msg_id):
        self.conn.execute("DELETE FROM auto_messages WHERE id = ?", (msg_id,))
        self.conn.commit()
