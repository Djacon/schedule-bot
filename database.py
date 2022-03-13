import sqlite3

DEFAULT = ('фабричная', 'выхино', 20, 60, 4, 'Не указана')
COLUMNS = ('homestation', 'workstation', 'hometotrain', 'worktotrain',
           'countofitems', 'unigroup')


class USERS:
    def __init__(self, filename: str):
        self.db = sqlite3.connect(filename)
        self.sql = self.db.cursor()

        self.sql.execute("""CREATE TABLE IF NOT EXISTS users (
            userid INT PRIMARY KEY  NOT NULL,
            homestation        TEXT NOT NULL,
            workstation        TEXT NOT NULL,
            hometotrain        INT  NOT NULL,
            worktotrain        INT  NOT NULL,
            countofitems       INT  NOT NULL,
            unigroup           TEXT NOT NULL
        )""")

    def addUser(self, userid: int) -> None:
        self.sql.execute('INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)',
                         (userid, *DEFAULT))
        self.db.commit()

    def getUser(self, userid: int) -> tuple:
        res = self.sql.execute('SELECT * FROM users WHERE userid = ?',
                               (userid,))
        user = res.fetchall()

        if not len(user):
            self.addUser(userid)
            return DEFAULT
        return user[0][1:]

    def editUser(self, userid: int, i: int, value) -> None:
        self.sql.execute(f"UPDATE users SET {COLUMNS[i]} = ? WHERE userid = ?",
                         (value, userid))
        self.db.commit()

    def userCount(self) -> int:
        return self.sql.execute('SELECT COUNT(*) FROM users').fetchone()[0]


DB = USERS('users.db')
