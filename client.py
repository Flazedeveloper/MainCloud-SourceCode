import sys, asyncio, json, threading, requests, websockets
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTextEdit, QListWidget, QLabel, QStackedWidget
)
from PyQt6.QtCore import Qt

STYLE = """
QWidget {
    background-color: #121212;
    color: #E0E0E0;
    font-size: 16px;
}
QLineEdit, QTextEdit {
    background-color: #1E1E1E;
    border: 1px solid #6A1B9A;
    color: #FFFFFF;
}
QPushButton {
    background-color: #6A1B9A;
    color: white;
    border-radius: 5px;
    padding: 6px;
}
QPushButton:hover {
    background-color: #8E24AA;
}
QListWidget {
    background-color: #1E1E1E;
    border: none;
    color: #FFFFFF;
}
"""

class ChatTab(QWidget):
    def __init__(self, username):
        super().__init__()
        self.username = username
        layout = QHBoxLayout()

        self.list = QListWidget()
        self.list.setFixedWidth(200)
        self.list.itemClicked.connect(self.select_chat)

        self.chat = QTextEdit(); self.chat.setReadOnly(True)
        self.input = QLineEdit(); self.input.setPlaceholderText("Введите сообщение...")
        self.input.returnPressed.connect(self.send_message)

        right = QVBoxLayout()
        right.addWidget(self.chat)
        right.addWidget(self.input)

        layout.addWidget(self.list)
        layout.addLayout(right)
        self.setLayout(layout)

        threading.Thread(target=self.ws_loop, daemon=True).start()

    def add_chat(self, peer):
        if not any(peer == self.list.item(i).text() for i in range(self.list.count())):
            self.list.addItem(peer)

    def select_chat(self, item):
        self.peer = item.text()
        self.chat.clear()

    def send_message(self):
        text = self.input.text()
        if hasattr(self, "peer"):
            asyncio.run(self.ws.send(json.dumps({"from": self.username, "to": self.peer, "text": text})))
            self.chat.append(f"Вы: {text}")
            self.input.clear()

    def ws_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.ws_run())

    async def ws_run(self):
        async with websockets.connect("ws://localhost:9898/ws") as ws:
            self.ws = ws
            await ws.send(json.dumps({"type": "init", "from": self.username}))
            try:
                async for msg in ws:
                    data = json.loads(msg)
                    sender = data["from"]
                    if sender != self.username:
                        self.add_chat(sender)
                        if hasattr(self, "peer") and sender == self.peer:
                            self.chat.append(f"{sender}: {data['text']}")
            except:
                self.chat.append("⚠️ Сервер отключился.")

class MainCloud(QWidget):
    def __init__(self, username, is_admin):
        super().__init__()
        self.username = username
        self.setWindowTitle("MainCloud — Альфа 0.0.1")
        self.setStyleSheet(STYLE)
        self.resize(1000, 600)

        self.stack = QStackedWidget()
        self.profile_tab = self.build_profile(is_admin)
        self.search_tab = self.build_search()
        self.chat_tab = ChatTab(username)
        self.stack.addWidget(self.profile_tab)
        self.stack.addWidget(self.search_tab)
        self.stack.addWidget(self.chat_tab)

        nav = QVBoxLayout()
        for i, name in enumerate(["Профиль", "Поиск", "Чаты"]):
            btn = QPushButton(name)
            btn.clicked.connect(lambda _, i=i: self.stack.setCurrentIndex(i))
            nav.addWidget(btn)

        if is_admin and username == "root":
            self.root_tab = self.build_root_panel()
            self.stack.addWidget(self.root_tab)
            btn = QPushButton("Root-панель")
            btn.clicked.connect(lambda: self.stack.setCurrentWidget(self.root_tab))
            nav.addWidget(btn)

        nav.addStretch()

        layout = QHBoxLayout()
        layout.addLayout(nav, 1)
        layout.addWidget(self.stack, 4)
        self.setLayout(layout)

    def build_profile(self, is_admin):
        w = QWidget(); layout = QVBoxLayout()
        layout.addWidget(QLabel(f"👤 Имя пользователя: {self.username}"))
        layout.addWidget(QLabel("🛡️ Уровень доступа: Админ" if is_admin else "🛡️ Пользователь"))
        layout.addStretch()
        w.setLayout(layout); return w

    def build_search(self):
        w = QWidget(); layout = QVBoxLayout()
        self.search_input = QLineEdit(); self.search_input.setPlaceholderText("🔍 Введите имя пользователя")
        self.search_result = QLabel("")
        btn = QPushButton("Найти и открыть чат")
        btn.clicked.connect(self.search_user)
        layout.addWidget(self.search_input)
        layout.addWidget(btn)
        layout.addWidget(self.search_result)
        layout.addStretch()
        w.setLayout(layout); return w

    def search_user(self):
        target = self.search_input.text()
        r = requests.get(f"http://localhost:9898/find_user?username={target}")
        if r.json()["found"]:
            self.search_result.setText(f"✅ Найден: {target}")
            self.chat_tab.add_chat(target)
        else:
            self.search_result.setText("❌ Пользователь не найден")

    def build_root_panel(self):
        w = QWidget(); layout = QVBoxLayout()
        layout.addWidget(QLabel("🔧 Root-панель"))
        self.admin_input = QLineEdit(); self.admin_input.setPlaceholderText("Имя для выдачи админки")
        btn = QPushButton("Выдать админку")
        btn.clicked.connect(self.grant_admin)
        self.root_result = QLabel("")
        layout.addWidget(self.admin_input)
        layout.addWidget(btn)
        layout.addWidget(self.root_result)
        layout.addStretch()
        w.setLayout(layout); return w

    def grant_admin(self):
        target = self.admin_input.text()
        r = requests.post(f"http://localhost:9898/grant_admin?by={self.username}", json={"username": target})
        if r.json()["status"] == "ok":
            self.root_result.setText(f"✅ {target} теперь админ")
        else:
            self.root_result.setText("❌ Ошибка выдачи")

def auth():
    username = input("Имя: ")
    password = input("Пароль: ")
    requests.post("http://localhost:9898/register", json={"username": username, "password": password})
    requests.post("http://localhost:9898/login", json={"username": username, "password": password})
    r = requests.get(f"http://localhost:9898/is_admin?username={username}")
    return username, r.json()["admin"]

if __name__ == "__main__":
    user, is_admin = auth()
    app = QApplication(sys.argv)
    window = MainCloud(user, is_admin)
    window.show()
    sys.exit(app.exec())