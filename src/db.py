import sqlite3
import random

path = "database.db"

def create_db():
	connection = sqlite3.connect(path, check_same_thread=False)
	connection.row_factory = sqlite3.Row
	cursor = connection.cursor()

	cursor.execute("CREATE TABLE IF NOT EXISTS templates(name UNIQUE NOT NULL, text NOT NULL)")

	connection.commit()

class DataBase:
	def __init__(self):
		self.connection = sqlite3.connect(path, check_same_thread=False)
		self.connection.row_factory = sqlite3.Row
		self.cursor = self.connection.cursor()

	def add_template(self, name, text):
		with self.connection:
			return self.cursor.execute("INSERT INTO `templates` (`name`, `text`) VALUES (?, ?)", (name, text,))

	def set_template(self, name, text):
		with self.connection:
			return self.cursor.execute("UPDATE `templates` set `text` = ? WHERE `name` = ?", (text, name,))
	
	def delete_template(self, name):
		with self.connection:
			return self.cursor.execute("DELETE FROM `templates` WHERE `name` = ?", (name,))

	def get_template(self, name):
		with self.connection:
			return self.cursor.execute("SELECT `text` FROM `templates` WHERE `name` = ?", (name,)).fetchone()[0]
	
	def get_templates(self):
		with self.connection:
			return self.cursor.execute("SELECT `name` FROM `templates`").fetchall()[0]
	
db = DataBase() 