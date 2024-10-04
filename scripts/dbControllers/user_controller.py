import sqlite3
from telegram import Update

class UserController:
    def __init__(self, db_name='users.db'):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        """
        Initializes the database and creates the 'users' table if it doesn't exist.
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Create table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                username TEXT,
                first_name TEXT,
                last_name TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def add_user(self, update: Update):
        """
        Adds a user to the database if they don't already exist.
        """
        user = update.message.from_user
        user_id = user.id
        username = user.username
        first_name = user.first_name
        last_name = user.last_name

        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Insert user into the database (ignoring if already exists)
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name))

        conn.commit()
        conn.close()

    def list_users(self):
        """
        Retrieves all users from the database.
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('SELECT username, first_name, last_name FROM users')
        users = cursor.fetchall()

        conn.close()
        return users

    def get_user_count(self):
        """
        Returns the count of registered users.
        """
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]

        conn.close()
        return user_count
