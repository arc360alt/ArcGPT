import sys
import os
import requests
import markdown
import json
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QScrollArea, QFrame, QDialog, QComboBox, QCheckBox,
    QColorDialog, QDialogButtonBox, QSizePolicy, QListWidget, QInputDialog, QMessageBox, QSplitter
)
from PySide6.QtCore import Qt, QSize, Signal, QThread, QObject, Signal as QSignal, Slot
from PySide6.QtGui import QColor, QPalette

CHATS_DIR = "ollama_gui_chats"
SETTINGS_FILE = "ollama_gui_settings.json"

def ensure_chats_dir():
    if not os.path.exists(CHATS_DIR):
        os.makedirs(CHATS_DIR)

def chat_file_path(chat_name):
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in chat_name).strip()
    return os.path.join(CHATS_DIR, f"{safe_name}.json")

def list_chats():
    ensure_chats_dir()
    return [f[:-5] for f in os.listdir(CHATS_DIR) if f.endswith(".json")]

def save_chat(chat_name, history):
    ensure_chats_dir()
    with open(chat_file_path(chat_name), "w", encoding="utf-8") as f:
        json.dump(history, f)

def load_chat(chat_name):
    path = chat_file_path(chat_name)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_settings(settings, last_chat):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump({"settings": settings, "last_chat": last_chat}, f)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def duckduckgo_search(query):
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, safesearch="off", max_results=5))
            out = ""
            for r in results:
                out += f"**{r['title']}**\n{r['href']}\n{r['body']}\n\n"
            return out if out else "No results found."
    except Exception as e:
        return f"Search error: {e}"

class OllamaResponseWorker(QObject):
    finished = QSignal(str)
    error = QSignal(str)
    def __init__(self, model, prompt, history):
        super().__init__()
        self.model = model
        self.prompt = prompt
        self.history = history or []

    def run(self):
        url = "http://localhost:11434/api/chat"
        messages = list(self.history)
        messages.append({"role": "user", "content": self.prompt})
        try:
            response = requests.post(url, json={"model": self.model, "messages": messages}, stream=True, timeout=300)
            if response.status_code == 404:
                self.error.emit("Error: /api/chat not found. Your Ollama version may be too old **or your model is not set or loaded**.\nMake sure you have set a valid model and that it is downloaded.\nUse `ollama pull llama3` (or another model) to download a model, then select it in settings.")
                return
            response.raise_for_status()
            # Collect all content chunks, even if split across lines
            complete = ""
            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    obj = json.loads(line.decode("utf-8"))
                    chunk = obj.get("message", {}).get("content", "")
                    complete += chunk
                except Exception:
                    try:
                        obj = json.loads(line.decode("utf-8").splitlines()[0])
                        chunk = obj.get("message", {}).get("content", "")
                        complete += chunk
                    except Exception as e:
                        self.error.emit(f"Error: {e}")
                        return
            self.finished.emit(complete)
        except Exception as e:
            self.error.emit(f"Error: {e}")

def list_ollama_models():
    try:
        resp = requests.get("http://localhost:11434/api/tags")
        return [m["name"] for m in resp.json().get("models",[])]
    except Exception:
        return ["llama2"]

class Bubble(QLabel):
    def __init__(self, text_md, is_user, color, txt_color, is_dark):
        super().__init__()
        self.setTextFormat(Qt.RichText)
        # Support much longer messages by removing max height and using word wrap,
        # and fixing markdown table/paragraphs.
        html = markdown.markdown(text_md, extensions=['fenced_code', 'tables', 'nl2br'])
        code_style = (
            "background:#222;color:#eee;border-radius:7px;padding:7px"
            if is_dark else
            "background:#f5f5f5;color:#333;border-radius:7px;padding:7px"
        )
        html = html.replace("<code>", f"<code style='{code_style}'>")
        html = html.replace("<pre>", "<pre style='margin:0;padding:0;overflow-x:auto;'>")
        self.setText(html)
        self.setWordWrap(True)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.setContentsMargins(0,0,0,0)
        self.setMaximumWidth(500)  # allow wider bubbles for clarity
        self.setStyleSheet(
            f"QLabel {{"
            f"background: {color};"
            f"border-radius: 18px;"
            f"padding: 10px 16px;"
            f"margin: 3px;"
            f"font-size: 15px;"
            f"color: {txt_color};"
            f"max-width: 500px;"
            f"}}"
        )
        # Remove setSizePolicy limitation, so long text flows down
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)

class SettingsDialog(QDialog):
    settings_changed = Signal(dict)
    def __init__(self, current_settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(370, 480)
        self.settings = current_settings.copy()
        layout = QVBoxLayout(self)
        self.model_combo = QComboBox()
        self.model_combo.addItems(list_ollama_models())
        self.model_combo.setCurrentText(current_settings.get("model", "llama2"))
        layout.addWidget(QLabel("Select LLM Model:"))
        layout.addWidget(self.model_combo)
        self.dark_chk = QCheckBox("Dark Mode")
        self.dark_chk.setChecked(current_settings.get("dark_mode", True))
        layout.addWidget(self.dark_chk)
        layout.addWidget(QLabel("UI Color Scheme:"))
        self.user_color_btn = QPushButton("User Bubble Color")
        self.user_color_btn.setStyleSheet("padding:8px 12px; border-radius:8px;")
        self.bot_color_btn = QPushButton("Bot Bubble Color")
        self.bot_color_btn.setStyleSheet("padding:8px 12px; border-radius:8px;")
        layout.addWidget(self.user_color_btn)
        layout.addWidget(self.bot_color_btn)
        self.web_chk = QCheckBox("Allow LLM to search with DuckDuckGo (!usesearch or always)")
        self.web_chk.setChecked(current_settings.get("internet", False))
        layout.addWidget(self.web_chk)
        self.always_search_chk = QCheckBox("Always give LLM DuckDuckGo search context")
        self.always_search_chk.setChecked(current_settings.get("always_search", False))
        layout.addWidget(self.always_search_chk)
        btns = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        self.user_color_btn.clicked.connect(self.pick_user_color)
        self.bot_color_btn.clicked.connect(self.pick_bot_color)

    def pick_user_color(self):
        col = QColorDialog.getColor(QColor(self.settings["color_scheme"].get('user', '#007AFF')), self, "User Bubble Color")
        if col.isValid():
            self.settings["color_scheme"]["user"] = col.name()

    def pick_bot_color(self):
        col = QColorDialog.getColor(QColor(self.settings["color_scheme"].get('bot', '#444456')), self, "Bot Bubble Color")
        if col.isValid():
            self.settings["color_scheme"]["bot"] = col.name()

    def accept(self):
        self.settings["model"] = self.model_combo.currentText()
        self.settings["dark_mode"] = self.dark_chk.isChecked()
        self.settings["internet"] = self.web_chk.isChecked()
        self.settings["always_search"] = self.always_search_chk.isChecked()
        self.settings_changed.emit(self.settings)
        super().accept()

class MessageArea(QWidget):
    def __init__(self, color_scheme, dark_mode, parent=None):
        super().__init__(parent)
        self.color_scheme = color_scheme
        self.dark_mode = dark_mode
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(4)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.addStretch(1)

    def add_bubble(self, sender, content, is_user, is_thinking=False):
        if self.layout.count():
            item = self.layout.itemAt(self.layout.count()-1)
            if item and item.spacerItem():
                self.layout.takeAt(self.layout.count()-1)
        row = QHBoxLayout()
        row.setContentsMargins(0,0,0,0)
        color = self.color_scheme.get('user' if is_user else 'bot',
            "#007AFF" if is_user else ("#444456" if self.dark_mode else "#E5E5EA"))
        txt_color = "#fff" if is_user or self.dark_mode else "#222"
        bubble = Bubble(content, is_user, color, txt_color, self.dark_mode)
        if is_thinking:
            bubble.setText(f"<i>{content}</i>")
        if is_user:
            row.addStretch(1)
            row.addWidget(bubble)
        else:
            row.addWidget(bubble)
            row.addStretch(1)
        self.layout.addLayout(row)
        self.layout.addStretch(1)
        return bubble, row

    def remove_last_bubble(self):
        if self.layout.count() < 2: return
        idx = self.layout.count() - 2
        item = self.layout.itemAt(idx)
        if item and item.layout():
            while item.layout().count():
                w = item.layout().takeAt(0).widget()
                if w: w.deleteLater()
            self.layout.removeItem(item)

    def clear(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.layout():
                while item.layout().count():
                    w = item.layout().takeAt(0).widget()
                    if w: w.deleteLater()
            elif item.widget():
                item.widget().deleteLater()

class ChatSidebar(QWidget):
    chat_selected = Signal(str)
    chat_deleted = Signal(str)
    chat_added = Signal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(170)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(3,3,3,3)
        layout.setSpacing(6)
        self.list = QListWidget()
        layout.addWidget(self.list)
        btnrow = QHBoxLayout()
        self.add_btn = QPushButton("➕")
        self.add_btn.setFixedWidth(36)
        self.del_btn = QPushButton("🗑️")
        self.del_btn.setFixedWidth(36)
        btnrow.addWidget(self.add_btn)
        btnrow.addWidget(self.del_btn)
        btnrow.addStretch(1)
        layout.addLayout(btnrow)
        self.add_btn.clicked.connect(self.add_chat)
        self.del_btn.clicked.connect(self.delete_chat)
        self.list.itemClicked.connect(self.on_item_click)
    def set_chats(self, chatnames):
        self.list.clear()
        for name in chatnames:
            self.list.addItem(name)
    def select_chat(self, chatname):
        items = self.list.findItems(chatname, Qt.MatchExactly)
        if items:
            self.list.setCurrentItem(items[0])
    def add_chat(self):
        name, ok = QInputDialog.getText(self, "New Chat", "Enter chat name:")
        name = name.strip()
        if ok and name:
            if name in list_chats():
                QMessageBox.warning(self, "Chat Exists", "A chat with this name already exists.")
                return
            save_chat(name, [])
            self.set_chats(list_chats())
            self.select_chat(name)
            self.chat_added.emit(name)
    def delete_chat(self):
        item = self.list.currentItem()
        if not item:
            return
        name = item.text()
        reply = QMessageBox.question(self, "Delete Chat", f"Delete chat '{name}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                os.remove(chat_file_path(name))
            except Exception:
                pass
            self.set_chats(list_chats())
            self.chat_deleted.emit(name)
    def on_item_click(self, item):
        if item:
            self.chat_selected.emit(item.text())

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ArkGPT - Ollama Edition")
        self.resize(780, 800)
        self.setMinimumWidth(420)
        self.settings = {
            "model": "llama2",
            "dark_mode": True,
            "color_scheme": {"user": "#007AFF", "bot": "#444456"},
            "internet": False,
            "always_search": False,
        }
        loaded = load_settings()
        last_chat = None
        if loaded:
            self.settings.update(loaded.get("settings", {}))
            last_chat = loaded.get("last_chat")
        ensure_chats_dir()
        chatnames = list_chats()
        if not chatnames:
            save_chat("Chat 1", [])
            chatnames = list_chats()
        chatname = last_chat if last_chat in chatnames else chatnames[0]
        self.current_chat = chatname
        self.history = load_chat(self.current_chat)
        root_split = QSplitter()
        self.setCentralWidget(root_split)
        self.sidebar = ChatSidebar()
        self.sidebar.set_chats(list_chats())
        self.sidebar.select_chat(self.current_chat)
        self.sidebar.chat_selected.connect(self.switch_chat)
        self.sidebar.chat_added.connect(self.switch_chat)
        self.sidebar.chat_deleted.connect(self.on_chat_deleted)
        root_split.addWidget(self.sidebar)
        chat_panel = QWidget()
        vbox = QVBoxLayout(chat_panel)
        vbox.setContentsMargins(0,0,0,0)
        vbox.setSpacing(0)
        self.header = QFrame()
        self.header.setFixedHeight(56)
        self.header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2a2a2c, stop:1 #19191a);
                border-top-left-radius: 20px;
                border-top-right-radius: 20px;
                border-bottom: 1px solid #39393a;
            }
        """)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(12, 2, 12, 2)
        self.title = QLabel("ArkGPT - Ollama Edition")
        self.title.setStyleSheet("font-size:22px;font-weight:600;letter-spacing:0.5px; color: #fff;")
        header_layout.addWidget(self.title)
        header_layout.addStretch()
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedSize(QSize(36, 36))
        self.settings_btn.setStyleSheet("""
            QPushButton {
                font-size:22px;
                background: #222;
                border-radius: 18px;
                border: none;
                color: #bbb;
            }
            QPushButton:hover {
                background: #555;
            }
        """)
        header_layout.addWidget(self.settings_btn)
        vbox.addWidget(self.header)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none; background: #1a1a1b;")
        self.chat_area = MessageArea(self.settings["color_scheme"], self.settings["dark_mode"])
        self.scroll.setWidget(self.chat_area)
        vbox.addWidget(self.scroll, 1)
        self.input_area = QFrame()
        self.input_area.setStyleSheet("""
            QFrame {
                background: #222;
                border-bottom-left-radius: 20px;
                border-bottom-right-radius: 20px;
                border-top: 1px solid #39393a;
            }
        """)
        input_layout = QHBoxLayout(self.input_area)
        input_layout.setContentsMargins(12, 8, 12, 8)
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Message…")
        self.text_input.setFixedHeight(42)
        self.text_input.setStyleSheet("""
            QTextEdit {
                border-radius: 16px;
                font-size:16px;
                padding:7px 12px;
                background: #19191a;
                color: #fff;
                border:1px solid #39393a;
            }
        """)
        input_layout.addWidget(self.text_input, 1)
        self.send_btn = QPushButton("➤")
        self.send_btn.setFixedSize(QSize(40, 40))
        self.send_btn.setStyleSheet("""
            QPushButton {
                font-size:20px;
                border-radius:18px;
                background: #007AFF;
                color: #fff;
                border:none;
            }
            QPushButton:hover {
                background: #005BB5;
            }
        """)
        input_layout.addWidget(self.send_btn)
        vbox.addWidget(self.input_area)
        root_split.addWidget(chat_panel)
        root_split.setSizes([180, 540])
        self.send_btn.clicked.connect(self.on_send)
        self.settings_btn.clicked.connect(self.open_settings)
        self.text_input.keyPressEvent = self.input_keypress
        self.set_theme()
        if self.history:
            for i, msg in enumerate(self.history):
                self.chat_area.add_bubble("You" if i % 2 == 0 else self.settings["model"], msg, is_user=(i % 2 == 0))
        else:
            self.chat_area.add_bubble("Ollama",
                "👋 **Welcome to Ollama AI!**\n\nSwitch models and settings via the ⚙️ above.\nSupports Markdown. Try:\n```python\nprint('Hello, world!')\n```",
                is_user=False
            )
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())
        self.thread = None
        self.thinking_row = None

    def switch_chat(self, chatname):
        self._save_current_chat()
        self.current_chat = chatname
        self.history = load_chat(chatname)
        self.chat_area.clear()
        if self.history:
            for i, msg in enumerate(self.history):
                self.chat_area.add_bubble("You" if i % 2 == 0 else self.settings["model"], msg, is_user=(i % 2 == 0))
        else:
            self.chat_area.add_bubble("Ollama",
                "👋 **New chat started!**", is_user=False
            )
        self.sidebar.select_chat(chatname)
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())
        save_settings(self.settings, self.current_chat)

    def on_chat_deleted(self, chatname):
        chatnames = list_chats()
        if chatnames:
            self.switch_chat(chatnames[0])
        else:
            save_chat("Chat 1", [])
            self.sidebar.set_chats(list_chats())
            self.switch_chat("Chat 1")

    def input_keypress(self, event):
        if event.key() == Qt.Key_Return and not event.modifiers():
            self.on_send()
        else:
            QTextEdit.keyPressEvent(self.text_input, event)

    def on_send(self):
        text = self.text_input.toPlainText().strip()
        if not text:
            return
        self.text_input.clear()
        self.chat_area.add_bubble("You", text, is_user=True)
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())
        self.history.append(text)
        self._save_current_chat()
        should_search = False
        if "!usesearch" in text.lower():
            should_search = True
            query = text.replace("!usesearch", "").strip()
        elif self.settings.get("always_search"):
            should_search = True
            query = text
        elif self.settings.get("internet") and text.lower().startswith("!search "):
            query = text[8:].strip()
            result = duckduckgo_search(query)
            self.chat_area.add_bubble("DuckDuckGo", result, is_user=False)
            self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())
            self.history.append(result)
            self._save_current_chat()
            return
        history = [{"role": "user" if i%2==0 else "assistant", "content": m} for i,m in enumerate(self._extract_history())]
        if should_search:
            result = duckduckgo_search(query)
            context = f"\n\n[Internet search results for \"{query}\":]\n{result}\n\nUse the above web results to answer the user's question."
            prompt = text + context
        else:
            prompt = text
        self.thinking_bubble, self.thinking_row = self.chat_area.add_bubble(self.settings["model"], "Bot is thinking...", is_user=False, is_thinking=True)
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())
        self.send_btn.setEnabled(False)
        self.text_input.setEnabled(False)
        self.worker = OllamaResponseWorker(self.settings["model"], prompt, history)
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_llama_response)
        self.worker.error.connect(self.on_llama_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.error.connect(self.thread.quit)
        self.worker.error.connect(self.worker.deleteLater)
        self.thread.start()

    @Slot(str)
    def on_llama_response(self, resp):
        self.chat_area.remove_last_bubble()
        self.chat_area.add_bubble(self.settings["model"], resp, is_user=False)
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())
        self.history.append(resp)
        self._save_current_chat()
        self.send_btn.setEnabled(True)
        self.text_input.setEnabled(True)

    @Slot(str)
    def on_llama_error(self, resp):
        self.chat_area.remove_last_bubble()
        self.chat_area.add_bubble("Ollama", resp, is_user=False)
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())
        self.send_btn.setEnabled(True)
        self.text_input.setEnabled(True)

    def _extract_history(self):
        return self.history[-8:]

    def open_settings(self):
        dlg = SettingsDialog(self.settings, self)
        dlg.settings_changed.connect(self.apply_settings)
        dlg.exec()

    @Slot(dict)
    def apply_settings(self, settings):
        self.settings = settings
        self.chat_area.color_scheme = self.settings["color_scheme"]
        self.chat_area.dark_mode = self.settings["dark_mode"]
        self.set_theme()
        self.chat_area.clear()
        self.history.clear()
        self.chat_area.add_bubble("Ollama",
            "✨ **Settings updated!**\n\nSwitched to model: `{}`\n\nNew chat started.".format(self.settings["model"]),
            is_user=False
        )
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())
        self._save_current_chat()

    def set_theme(self):
        pal = QPalette()
        if self.settings["dark_mode"]:
            pal.setColor(QPalette.Window, QColor("#18181a"))
            pal.setColor(QPalette.Base, QColor("#222226"))
            pal.setColor(QPalette.Text, QColor("#e0e0e0"))
            pal.setColor(QPalette.Button, QColor("#24242c"))
            pal.setColor(QPalette.ButtonText, QColor("#f8f8fa"))
            pal.setColor(QPalette.WindowText, QColor("#f8f8fa"))
        else:
            pal.setColor(QPalette.Window, QColor("#f8f8fa"))
            pal.setColor(QPalette.Base, QColor("#fff"))
            pal.setColor(QPalette.Text, QColor("#111"))
            pal.setColor(QPalette.Button, QColor("#fff"))
            pal.setColor(QPalette.ButtonText, QColor("#111"))
            pal.setColor(QPalette.WindowText, QColor("#111"))
        self.setPalette(pal)
        self.header.setStyleSheet(
            "QFrame {background: %s; border-radius: 20px 20px 0 0; border-bottom: 1px solid #39393a;}"
            % ("#232327" if self.settings["dark_mode"] else "#f8f8fa")
        )
        self.input_area.setStyleSheet(
            "QFrame {background: %s; border-radius: 0 0 20px 20px; border-top: 1px solid #39393a;}"
            % ("#1a1a1c" if self.settings["dark_mode"] else "#f7f7fa")
        )
        self.scroll.setStyleSheet(
            "QScrollArea {border: none; background: %s;}" %
            ("#18181a" if self.settings["dark_mode"] else "#f8f8fa")
        )
        self.update()

    def closeEvent(self, event):
        self._save_current_chat()
        save_settings(self.settings, self.current_chat)
        super().closeEvent(event)

    def _save_current_chat(self):
        save_chat(self.current_chat, self.history[-40:]) # save last 40 messages for each chat

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QMainWindow {border-radius: 20px;}
        QWidget {border-radius: 13px;}
        QPushButton {border-radius: 13px;}
    """)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()