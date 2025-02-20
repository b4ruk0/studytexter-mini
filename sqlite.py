import sqlite3


class DataBase:

    def __init__(self, database_name, current_sheet="sheet1"):
        self.database_name = database_name
        self.current_sheet = current_sheet

    def move_to_sheet(self, sheet):

        self.current_sheet = sheet

    def create_sheet(self, new_sheet_name, variables):

        connection = sqlite3.connect(f"{self.database_name}")
        curs = connection.cursor()

        curs.execute(f"CREATE TABLE IF NOT EXISTS {new_sheet_name} (id INTEGER PRIMARY KEY, {variables})")

        connection.commit()
        connection.close()

        return None

    def add_column(self, column_name, column_type):

        connection = sqlite3.connect(f"{self.database_name}")
        curs = connection.cursor()

        curs.execute(f"ALTER TABLE {self.current_sheet} ADD COLUMN {column_name} {column_type};")

        connection.commit()
        connection.close()

        return None

    def delete_sheet(self):

        connection = sqlite3.connect(f"{self.database_name}")
        curs = connection.cursor()

        curs.execute(f"DROP TABLE IF EXISTS {self.current_sheet};")

        connection.commit()
        connection.close()

        return None

    def insert(self, variable_names, variable_values):

        if len(variable_names) != len(variable_values):
            raise ValueError("The number of columns must match the number of values.")

        connection = sqlite3.connect(self.database_name)
        curs = connection.cursor()

        columns = ", ".join(variable_names)
        placeholders = ", ".join(["?" for _ in variable_names])

        query = f"INSERT INTO {self.current_sheet} ({columns}) VALUES ({placeholders});"

        curs.execute(query, tuple(variable_values))

        connection.commit()
        connection.close()

        return None

    def get_all(self):

        connection = sqlite3.connect(f"{self.database_name}")
        curs = connection.cursor()

        curs.execute(f"SELECT * FROM {self.current_sheet};")
        output = curs.fetchall()

        connection.close()

        return output

    def get_line(self, id):

        connection = sqlite3.connect(f"{self.database_name}")
        curs = connection.cursor()

        curs.execute(f"SELECT * FROM {self.current_sheet} WHERE id = '{id}';")
        output = curs.fetchall()

        connection.close()

        return output

    def get_element(self, where_variable_name, where_variable_value, column):

        connection = sqlite3.connect(f"{self.database_name}")
        curs = connection.cursor()

        curs.execute(f"SELECT {column} FROM {self.current_sheet} WHERE {where_variable_name} = '{where_variable_value}';")
        output = curs.fetchone()

        connection.close()

        return str(output).replace("(", "").replace(",)", "")

    def update(self, setting_variable_name, variable_new_value, variable_name, variable_value):

        connection = sqlite3.connect(f"{self.database_name}")
        curs = connection.cursor()

        if isinstance(variable_value, list):
            try:
                variable_value = variable_value[0]
            except Exception as e:
                raise (e)

        curs.execute(rf"""UPDATE {self.current_sheet} SET {setting_variable_name} = '{variable_new_value}' WHERE {variable_name} = '{variable_value}';""")

        connection.commit()
        connection.close()

        return None

    def delete(self, variable_name, variable_value):

        connection = sqlite3.connect(f"{self.database_name}")
        curs = connection.cursor()

        curs.execute(f"DELETE FROM {self.current_sheet} WHERE {variable_name} = '{variable_value}';")

        connection.commit()
        connection.close()

        return None

    def get_last_line_id(self):

        connection = sqlite3.connect(f"{self.database_name}")
        curs = connection.cursor()

        curs.execute(f"SELECT MAX(id) FROM {self.current_sheet};")
        output = curs.fetchone()

        connection.close()

        return int(str(output)[1:-2])

    def check_if_exists(self, variable_name, variable_value):

        connection = sqlite3.connect(f"{self.database_name}")
        curs = connection.cursor()

        query = f"SELECT COUNT(*) FROM {self.current_sheet} WHERE {variable_name} = ?"
        curs.execute(query, (variable_value,))
        result = curs.fetchone()[0]

        connection.close()
        return result > 0
