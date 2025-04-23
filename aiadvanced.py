import sys
import os
import json
import pathlib
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QScrollArea, QLabel, QDialog,
    QFormLayout, QDialogButtonBox, QColorDialog, QRadioButton, QGroupBox,
    QSizePolicy, QFrame
)
from PySide6.QtGui import QColor, QPalette, QFont, QIcon, QTextCursor, QPixmap, QTextDocument
from PySide6.QtCore import Qt, Signal, QThread, QSettings, QSize, QTimer

# --- Gemini API Interaction ---
try:
    import google.generativeai as genai
    GOOGLE_AI_AVAILABLE = True
except ImportError:
    GOOGLE_AI_AVAILABLE = False
    print("WARNING: google-generativeai library not found. AI functionality will be disabled.")
    print("Install it using: pip install google-generativeai")

# --- Configuration Handling ---
CONFIG_FILE = "chat_config.json"
DEFAULT_CONFIG = {
    "api_key": "",
    "theme": "light",
    "accent_color": "#3498db" # Default blue accent
}

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent

def load_config():
    """Loads configuration from a JSON file using absolute path."""
    config_path = SCRIPT_DIR / CONFIG_FILE
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
                merged_config = DEFAULT_CONFIG.copy()
                merged_config.update(config_data)
                # Validate loaded accent color
                try:
                    QColor(merged_config["accent_color"])
                except:
                    print(f"Warning: Invalid accent color '{merged_config['accent_color']}' in config, reverting to default.")
                    merged_config["accent_color"] = DEFAULT_CONFIG["accent_color"]
                return merged_config
        except json.JSONDecodeError:
            print(f"Error reading config file {config_path}. Using defaults.")
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()

def save_config(config_to_save):
    """Saves configuration to a JSON file using absolute path."""
    config_path = SCRIPT_DIR / CONFIG_FILE
    try:
        with open(config_path, 'w') as f:
            json.dump(config_to_save, f, indent=4)
    except IOError:
        print(f"Error writing config file {config_path}.")

config = load_config()

# --- API Worker Thread ---
# (Worker code remains the same - omitted for brevity)
class GeminiWorker(QThread):
    """Handles API calls in a separate thread."""
    response_received = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, api_key, message, chat_history=None):
        super().__init__()
        self.api_key = api_key
        self.message = message
        self.history = chat_history if isinstance(chat_history, list) else []

    def run(self):
        """ Executes the API call. """
        if not GOOGLE_AI_AVAILABLE:
            self.error_occurred.emit("Google AI library not installed.")
            return
        if not self.api_key:
            self.error_occurred.emit("API Key not set. Please configure it in Settings.")
            return

        try:
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            formatted_history = [item for item in self.history if 'role' in item and 'parts' in item]

            if not formatted_history:
                 response = model.generate_content(self.message)
            else:
                 chat = model.start_chat(history=formatted_history)
                 response = chat.send_message(self.message)

            response_text = ""
            if response:
                 try:
                      response_text = response.text
                      self.response_received.emit(response_text)
                      return
                 except ValueError:
                      if hasattr(response, 'candidates') and response.candidates:
                           candidate_parts = response.candidates[0].content.parts
                           if candidate_parts:
                                response_text = "".join(part.text for part in candidate_parts if hasattr(part, 'text'))
                                if response_text:
                                     self.response_received.emit(response_text)
                                     return
                                else:
                                     self.error_occurred.emit("API response candidate parts contained no text.")
                                     return
                 if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                      reason = response.prompt_feedback.block_reason
                      self.error_occurred.emit(f"Request blocked: {reason}. Please modify your prompt.")
                      return

            if not response_text:
                 print(f"Unexpected API response structure (no text found): {response}")
                 self.error_occurred.emit("Received an empty or unexpected response format from the API.")

        except Exception as e:
            error_message = f"API Error: {str(e)}"
            print(f"API Exception: {type(e).__name__} - {e}")
            # Add specific error checks as before...
            if "API key not valid" in str(e) or "API_KEY_INVALID" in str(e):
                 error_message = "API Error: Invalid API Key. Please check it in Settings."
            elif "quota" in str(e).lower() or "RESOURCE_EXHAUSTED" in str(e):
                 error_message = "API Error: Quota exceeded. Please check your Google AI usage limits."
            elif "Deadline Exceeded" in str(e):
                 error_message = "API Error: Request timed out. Please try again."
            elif "PermissionDenied" in str(e) or "permission denied" in str(e).lower():
                 error_message = "API Error: Permission denied. Check API key permissions."
            elif "NotFound" in str(e) and "models/" in str(e):
                 error_message = "API Error: Model not found. Check the model name."
            self.error_occurred.emit(error_message)


# --- Settings Dialog ---
# (SettingsDialog code remains the same - omitted for brevity)
class SettingsDialog(QDialog):
    """Dialog for configuring API Key, Theme, and Accent Color."""
    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)
        self.setModal(True)
        self.current_config = load_config()
        self.selected_color = self.current_config.get("accent_color", DEFAULT_CONFIG["accent_color"])

        layout = QVBoxLayout(self)
        api_group = QGroupBox("API Configuration")
        api_layout = QFormLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("Enter your Google AI API Key")
        self.api_key_input.setText(self.current_config.get("api_key", ""))
        api_layout.addRow("API Key:", self.api_key_input)
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)

        theme_group = QGroupBox("Appearance")
        theme_layout = QVBoxLayout()
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Theme:")
        self.light_radio = QRadioButton("Light")
        self.dark_radio = QRadioButton("Dark")
        self.light_radio.toggled.connect(self.apply_styles)
        self.dark_radio.toggled.connect(self.apply_styles)
        if self.current_config.get("theme", "light") == "dark":
            self.dark_radio.setChecked(True)
        else:
            self.light_radio.setChecked(True)
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.light_radio)
        mode_layout.addWidget(self.dark_radio)
        mode_layout.addStretch()
        theme_layout.addLayout(mode_layout)

        color_layout = QHBoxLayout()
        color_label = QLabel("Accent Color:")
        self.color_button = QPushButton("Choose Color")
        self.color_preview = QLabel()
        self.color_preview.setObjectName("colorPreviewLabel")
        self.color_preview.setFixedSize(24, 24)
        self.set_color_preview(self.selected_color)
        self.color_button.clicked.connect(self.choose_color)
        color_layout.addWidget(color_label)
        color_layout.addWidget(self.color_preview)
        color_layout.addWidget(self.color_button)
        color_layout.addStretch()
        theme_layout.addLayout(color_layout)
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.save_settings)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        self.apply_styles()

    def set_color_preview(self, color_hex):
        """Updates the color preview label."""
        try:
            color = QColor(color_hex)
            pixmap = QPixmap(24, 24)
            if color.isValid(): pixmap.fill(color)
            else: pixmap.fill(Qt.gray)
            self.color_preview.setPixmap(pixmap)
            self.color_preview.setStyleSheet("border: 1px solid grey; border-radius: 4px;")
        except Exception as e: print(f"Error setting color preview: {e}")

    def choose_color(self):
        """Opens a color dialog to select the accent color."""
        try: initial_color = QColor(self.selected_color)
        except: initial_color = QColor(DEFAULT_CONFIG["accent_color"])
        color = QColorDialog.getColor(initial_color if initial_color.isValid() else Qt.white, self, "Choose Accent Color")
        if color.isValid():
            self.selected_color = color.name()
            self.set_color_preview(self.selected_color)
            self.apply_styles()

    def save_settings(self):
        """Saves the selected settings to the config file."""
        global config
        config["api_key"] = self.api_key_input.text()
        config["theme"] = "dark" if self.dark_radio.isChecked() else "light"
        config["accent_color"] = self.selected_color
        save_config(config)
        self.settings_changed.emit()
        self.accept()

    def apply_styles(self):
         """ Applies basic styling consistent with the main app theme. """
         theme = "dark" if self.dark_radio.isChecked() else "light"
         accent = self.selected_color
         try:
             q_accent_color = QColor(accent)
             if not q_accent_color.isValid(): accent = DEFAULT_CONFIG["accent_color"]; q_accent_color = QColor(accent)
         except Exception: accent = DEFAULT_CONFIG["accent_color"]; q_accent_color = QColor(accent)

         # --- Define default text colors BEFORE the if/else ---
         default_dark_text = "#2c3e50" # Dark text for light themes
         default_light_text = "#ffffff" # Use white for dark theme text for max contrast
         # ----------------------------------------------------

         if theme == "dark":
             # Dark Theme: Make backgrounds very dark versions of accent
             bg_color_base = q_accent_color.darker(300)
             if bg_color_base.lightnessF() < 0.1: bg_color_base.setHslF(bg_color_base.hslHueF(), bg_color_base.hslSaturationF(), 0.1)
             bg_color = bg_color_base.name()
             secondary_bg = bg_color_base.lighter(115).name()
             header_bg = secondary_bg
             ai_msg_bg = bg_color_base.lighter(130).name()
             input_bg = secondary_bg
             # Determine text color based on the darkest background
             text_color = default_light_text # Use white for general dark theme text
             ai_msg_text = default_light_text # Use white for AI message text
             header_text = default_light_text
         else: # Light Theme
             # Light Theme: Make backgrounds very light versions of accent
             bg_color_base = q_accent_color.lighter(180)
             if bg_color_base.hslSaturationF() < 0.05: bg_color_base.setHslF(bg_color_base.hslHueF(), 0.05, bg_color_base.lightnessF())
             if bg_color_base.lightnessF() > 0.98: bg_color_base.setHslF(bg_color_base.hslHueF(), bg_color_base.hslSaturationF(), 0.98)
             bg_color = bg_color_base.name()
             secondary_bg = bg_color_base.darker(105).name()
             header_bg = secondary_bg
             ai_msg_bg = bg_color_base.darker(108).name()
             input_bg = secondary_bg
             # Determine text color based on the lightest background
             text_color = default_dark_text # Use dark for general light theme text
             ai_msg_text = default_dark_text # Use dark for AI message text
             header_text = default_dark_text

         button_text = "#ffffff" if q_accent_color.lightnessF() < 0.5 else "#000000"
         user_msg_text = button_text
         border_color = "#a0a0a0" if theme == 'light' else "#505050"
         try: hover_bg, pressed_bg = q_accent_color.lighter(115).name(), q_accent_color.darker(115).name()
         except Exception: hover_bg, pressed_bg = accent, accent

         # Simplified QSS for brevity (same content as before)
         self.setStyleSheet(f"""
             QDialog {{ background-color: {bg_color}; color: {text_color}; font-family: Segoe UI, Arial, sans-serif; font-size: 10pt; }}
             QGroupBox {{ background-color: {"transparent" if theme == 'dark' else secondary_bg}; border: 1px solid {border_color}; border-radius: 8px; margin-top: 10px; padding: 15px 10px 10px 10px; }}
             QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; background-color: {bg_color}; color: {text_color}; left: 10px; top: -8px; }}
             QLabel {{ color: {text_color}; padding: 2px; background-color: transparent; }}
             QLabel#colorPreviewLabel {{ border: 1px solid grey; border-radius: 4px; }}
             QLineEdit {{ background-color: {input_bg}; color: {text_color}; border: 1px solid {border_color}; border-radius: 5px; padding: 8px; font-size: 10pt; }}
             QLineEdit:focus {{ border: 1px solid {accent}; }}
             QPushButton {{ background-color: {accent}; color: {button_text}; border: none; border-radius: 5px; padding: 8px 16px; font-size: 10pt; min-width: 80px; }}
             QPushButton:hover {{ background-color: {hover_bg}; }}
             QPushButton:pressed {{ background-color: {pressed_bg}; }}
             QDialogButtonBox QPushButton {{ min-width: 80px; }}
             QRadioButton {{ color: {text_color}; spacing: 5px; background-color: transparent; }}
             QRadioButton::indicator {{ width: 14px; height: 14px; border-radius: 7px; border: 1px solid {border_color}; background-color: {input_bg}; }}
             QRadioButton::indicator:hover {{ border: 1px solid {accent}; }}
             QRadioButton::indicator:checked {{ background-color: qradialgradient(spread:pad, cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0.6 {accent}, stop:0.7 rgba(0, 0, 0, 0)); border: 1px solid {accent}; }}
             QRadioButton::indicator:checked:hover {{ border: 1px solid {q_accent_color.lighter(120).name()}; }}
         """)


# --- Main Application Window ---
class ChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gemini AI Chat")
        self.setGeometry(100, 100, 600, 700)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # --- Header ---
        self.header = QWidget()
        self.header.setObjectName("header")
        self.header_layout = QHBoxLayout(self.header)
        self.header_layout.setContentsMargins(10, 5, 10, 5)
        self.title_label = QLabel("Gemini AI Chat")
        self.title_label.setObjectName("headerTitle")
        self.settings_button = QPushButton() # Create button
        self.settings_button.setObjectName("settingsButton")
        self.settings_button.setFixedSize(35, 35) # Slightly larger for emoji
        self.settings_button.setToolTip("Settings")
        self.settings_button.setCursor(Qt.PointingHandCursor)
        self.settings_button.clicked.connect(self.open_settings)
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch()
        self.header_layout.addWidget(self.settings_button)
        self.layout.addWidget(self.header)

        # --- Chat Display Area ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setObjectName("scrollArea")

        self.chat_container = QWidget()
        self.chat_container.setObjectName("chatContainer")
        self.chat_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_layout.setSpacing(10)
        self.scroll_area.setWidget(self.chat_container)
        self.layout.addWidget(self.scroll_area)

        # --- Input Area ---
        self.input_widget = QWidget()
        self.input_widget.setObjectName("inputArea")
        self.input_layout = QHBoxLayout(self.input_widget)
        self.input_layout.setSpacing(10)
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type your message...")
        self.message_input.returnPressed.connect(self.send_message)
        self.input_layout.addWidget(self.message_input)
        self.send_button = QPushButton("Send")
        self.send_button.setCursor(Qt.PointingHandCursor)
        self.send_button.clicked.connect(self.send_message)
        self.input_layout.addWidget(self.send_button)
        self.layout.addWidget(self.input_widget)

        # --- Status Label ---
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFixedHeight(25)
        self.status_label.hide()
        self.layout.addWidget(self.status_label)

        self.apply_styles()
        self.chat_history = []
        self.update_status_based_on_config()

    def add_message_to_chat(self, text, sender="user"):
        """Adds a message bubble (QTextEdit) to the chat display."""
        message_widget = QTextEdit()
        message_widget.setReadOnly(True)
        message_widget.setMarkdown(text)
        message_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        message_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        message_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        # Connect signal for dynamic height adjustment
        message_widget.document().contentsChanged.connect(
            lambda mw=message_widget: self.adjust_text_edit_height(mw)
        )
        # Trigger initial height adjustment
        QTimer.singleShot(10, lambda mw=message_widget: self.adjust_text_edit_height(mw))
        object_name = "aiMessage" if sender == "model" else "userMessage"
        message_widget.setObjectName(object_name)
        container_widget = QWidget()
        # Container is transparent, background comes from main window or chatContainer style
        container_widget.setStyleSheet("background: transparent;")
        container_layout = QHBoxLayout(container_widget)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        if sender == "model":
            container_layout.addWidget(message_widget)
            container_layout.addStretch(1)
        else:
            container_layout.addStretch(1)
            container_layout.addWidget(message_widget)
        container_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.chat_layout.addWidget(container_widget)
        QTimer.singleShot(50, self.scroll_to_bottom)

    def adjust_text_edit_height(self, text_edit):
        """Adjusts the QTextEdit height to fit its content."""
        if not text_edit or not text_edit.document(): return
        doc_size = text_edit.document().size()
        if not doc_size.isValid(): return
        doc_height = doc_size.height()
        margins = text_edit.contentsMargins()
        v_margin = margins.top() + margins.bottom()
        buffer = 4 # Small buffer for padding/border
        new_height = int(doc_height + v_margin + buffer)
        min_height = 30 # Ensure a minimum height
        final_height = max(new_height, min_height)
        if text_edit.height() != final_height:
            text_edit.setFixedHeight(final_height)

    def scroll_to_bottom(self):
        """Scrolls the chat area to the bottom."""
        v_scroll_bar = self.scroll_area.verticalScrollBar()
        QTimer.singleShot(0, lambda: v_scroll_bar.setValue(v_scroll_bar.maximum()))

    # send_message, handle_response, handle_error, on_worker_finished remain the same
    # show_status_message, hide_specific_status_message, hide_status_message remain the same
    # open_settings, on_settings_changed, update_status_based_on_config, clear_chat_display remain the same
    # (Code omitted for brevity)
    def send_message(self):
        """Handles sending the user's message and initiating the API call."""
        user_message = self.message_input.text().strip()
        if not user_message: return
        api_key = config.get("api_key")
        if not api_key: self.show_status_message("Error: API Key not set...", error=True); return
        if not GOOGLE_AI_AVAILABLE: self.show_status_message("Error: Google AI library not installed.", error=True); return
        self.add_message_to_chat(user_message, sender="user")
        self.message_input.clear()
        self.show_status_message("AI is thinking...", error=False)
        self.send_button.setEnabled(False); self.message_input.setEnabled(False)
        self.chat_history.append({'role': 'user', 'parts': [user_message]})
        self.worker = GeminiWorker(api_key, user_message, list(self.chat_history))
        self.worker.response_received.connect(self.handle_response)
        self.worker.error_occurred.connect(self.handle_error)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    def handle_response(self, ai_message):
        """Handles the successful response from the AI."""
        self.add_message_to_chat(ai_message, sender="model")
        self.chat_history.append({'role': 'model', 'parts': [ai_message]})
        self.hide_status_message()

    def handle_error(self, error_message):
        """Handles errors during the API call."""
        print(f"Error: {error_message}")
        self.show_status_message(f"{error_message}", error=True)
        if self.chat_history and self.chat_history[-1]['role'] == 'user':
            last_user_message = self.chat_history.pop(); print(f"Removed user msg: {last_user_message}")

    def on_worker_finished(self):
        """Called when the worker thread finishes."""
        self.send_button.setEnabled(True); self.message_input.setEnabled(True)
        self.message_input.setFocus()
        is_error = self.status_label.property("isError")
        if is_error is None or not is_error: self.hide_status_message()

    def show_status_message(self, message, error=False, duration=5000):
        """Displays a message in the status bar."""
        self.status_label.setText(message)
        self.status_label.setProperty("isError", error)
        self.status_label.show()
        self.status_label.style().unpolish(self.status_label); self.status_label.style().polish(self.status_label)
        is_persistent = duration == 0 or "API Key not set" in message or "google-generativeai not found" in message
        if not is_persistent: QTimer.singleShot(duration, lambda: self.hide_specific_status_message(message))

    def hide_specific_status_message(self, message_to_hide):
         """Hides the status message only if it matches."""
         if self.status_label.isVisible() and self.status_label.text() == message_to_hide:
              is_error = self.status_label.property("isError")
              is_persistent_error = is_error and ("API Key not set" in message_to_hide or "google-generativeai not found" in message_to_hide)
              if not is_persistent_error: self.status_label.hide()

    def hide_status_message(self):
        """Hides the status bar message if not persistent."""
        text = self.status_label.text()
        is_error = self.status_label.property("isError")
        is_persistent = is_error and ("API Key not set" in text or "google-generativeai not found" in text)
        if not is_persistent: self.status_label.hide()

    def open_settings(self):
        """Opens the settings dialog."""
        dialog = SettingsDialog(self)
        dialog.settings_changed.connect(self.on_settings_changed)
        dialog.exec()

    def on_settings_changed(self):
        """Called when settings are saved."""
        global config
        config = load_config()
        self.apply_styles()
        self.update_status_based_on_config()
        self.clear_chat_display()
        self.chat_history = []

    def update_status_based_on_config(self):
        """Checks config and updates status bar."""
        if not GOOGLE_AI_AVAILABLE: self.show_status_message("Warning: google-generativeai not found...", error=True, duration=0)
        elif not config.get("api_key"): self.show_status_message("API Key not set...", error=True, duration=0)
        else: self.hide_status_message()

    def clear_chat_display(self):
         """Removes all message container widgets."""
         while self.chat_layout.count():
              item = self.chat_layout.takeAt(0)
              widget = item.widget()
              if widget is not None: widget.deleteLater()

    # ***********************************************************************
    # * AI TEXT COLOR FIX START                           *
    # ***********************************************************************
    def apply_styles(self):
        """Applies the stylesheet based on current config."""
        global config
        theme = config.get("theme", "light")
        accent_hex = config.get("accent_color", DEFAULT_CONFIG["accent_color"])

        # Validate and get QColor for accent
        try:
            q_accent_color = QColor(accent_hex)
            if not q_accent_color.isValid():
                print(f"Invalid accent color '{accent_hex}', using default.")
                accent_hex = DEFAULT_CONFIG["accent_color"]
                q_accent_color = QColor(accent_hex)
        except Exception:
            print(f"Error parsing accent color '{accent_hex}', using default.")
            accent_hex = DEFAULT_CONFIG["accent_color"]
            q_accent_color = QColor(accent_hex)

        # --- Define default text colors BEFORE the if/else ---
        default_dark_text_color = "#2c3e50" # Dark text for light themes
        default_light_text_color = "#ffffff" # Use white for dark theme text for max contrast
        # ----------------------------------------------------

        # --- Determine Text/Link Colors (Based on Theme Mode primarily) ---
        if theme == "dark":
            link_color = "#5dade2"         # Light blue links
        else: # Light theme
            link_color = "#2980b9"         # Standard blue links

        # --- Derive Background Colors from Accent ---
        dark_bg_lightness = 0.15; dark_secondary_lightness = 0.20; dark_ai_msg_lightness = 0.23
        light_bg_lightness = 0.97; light_secondary_lightness = 0.92; light_ai_msg_lightness = 0.90

        accent_h = q_accent_color.hslHueF(); accent_s = q_accent_color.hslSaturationF(); accent_l = q_accent_color.lightnessF()
        base_saturation = max(0.1, accent_s)

        if theme == "dark":
            bg_color_q = QColor.fromHslF(accent_h, base_saturation, dark_bg_lightness)
            secondary_bg_q = QColor.fromHslF(accent_h, base_saturation, dark_secondary_lightness)
            ai_msg_bg_q = QColor.fromHslF(accent_h, base_saturation, dark_ai_msg_lightness)
            header_bg_q = secondary_bg_q; input_bg_q = secondary_bg_q; scrollbar_bg_q = bg_color_q
            scrollbar_handle_q = secondary_bg_q.lighter(130)
            # Text colors
            text_color = default_light_text_color # Use white for general dark theme text
            ai_msg_text = default_light_text_color # <<<< FORCE WHITE FOR AI MESSAGES
            header_text = default_light_text_color
        else: # Light theme
            bg_color_q = QColor.fromHslF(accent_h, base_saturation, light_bg_lightness)
            secondary_bg_q = QColor.fromHslF(accent_h, base_saturation, light_secondary_lightness)
            ai_msg_bg_q = QColor.fromHslF(accent_h, base_saturation, light_ai_msg_lightness)
            header_bg_q = secondary_bg_q; input_bg_q = secondary_bg_q; scrollbar_bg_q = bg_color_q
            scrollbar_handle_q = secondary_bg_q.darker(115)
            # Text colors
            text_color = default_dark_text_color # Use dark for general light theme text
            ai_msg_text = default_dark_text_color # Use dark for AI messages
            header_text = default_dark_text_color

        bg_color = bg_color_q.name(); secondary_bg = secondary_bg_q.name(); header_bg = header_bg_q.name()
        ai_msg_bg = ai_msg_bg_q.name(); input_bg = input_bg_q.name()
        scrollbar_bg = scrollbar_bg_q.name(); scrollbar_handle = scrollbar_handle_q.name()
        scrollbar_handle_hover = scrollbar_handle_q.lighter(110).name() if theme == 'dark' else scrollbar_handle_q.darker(110).name()

        user_msg_bg = accent_hex
        user_msg_text = "#ffffff" if accent_l < 0.5 else "#000000"
        button_text = user_msg_text
        border_color = "#4a627a" if theme == 'dark' else "#bdc3c7" # Use slightly less harsh border

        try:
            button_hover_bg = q_accent_color.lighter(115).name()
            button_pressed_bg = q_accent_color.darker(115).name()
            disabled_bg = q_accent_color.darker(110).name() if theme=='dark' else '#bdc3c7'
        except Exception: button_hover_bg, button_pressed_bg, disabled_bg = accent_hex, accent_hex, '#bdc3c7'

        self.settings_button.setText("⚙️")
        settings_button_text_color = header_text # Match header text

        # --- QSS Stylesheet ---
        # Uses the newly calculated color variables
        stylesheet = f"""
            QMainWindow {{ background-color: {bg_color}; }}
            QWidget {{ color: {text_color}; font-family: Segoe UI, Arial, sans-serif; font-size: 10pt; }}
            #header {{ background-color: {header_bg}; border-bottom: 1px solid {border_color if theme == 'light' else 'transparent'}; padding: 5px 10px; }}
            #headerTitle {{ color: {header_text}; font-size: 12pt; font-weight: bold; background-color: transparent; }}

            #settingsButton {{
                background-color: transparent; border: none; padding: 0px; border-radius: 17px;
                font-size: 16pt; color: {settings_button_text_color};
                min-width: 35px; max-width: 35px; min-height: 35px; max-height: 35px;
                line-height: 35px; text-align: center;
            }}
            #settingsButton:hover {{ background-color: {QColor(header_bg).lighter(110).name() if theme == 'dark' else QColor(header_bg).darker(110).name()}; }}
            #settingsButton:pressed {{ background-color: {QColor(header_bg).lighter(120).name() if theme == 'dark' else QColor(header_bg).darker(120).name()}; }}

            #scrollArea {{ border: none; background-color: transparent; }}
            #chatContainer {{ background-color: {bg_color}; padding: 10px 15px; }}

            QTextEdit#userMessage, QTextEdit#aiMessage {{
                border-radius: 12px; padding: 8px 12px; font-size: 10pt;
                background-clip: padding-box; background-color: transparent; border: 1px solid transparent;
            }}
            QTextEdit:focus {{ outline: none; border: 1px solid transparent; }}

            QTextEdit#userMessage {{ background-color: {user_msg_bg}; color: {user_msg_text}; border-color: {user_msg_bg}; }}
            QTextEdit#userMessage a {{ color: {user_msg_text}; text-decoration: underline; }}

            QTextEdit#aiMessage {{ background-color: {ai_msg_bg}; color: {ai_msg_text}; border-color: {ai_msg_bg}; }} /* Uses calculated ai_msg_text */
            QTextEdit#aiMessage a {{ color: {link_color}; text-decoration: underline; }}

            #inputArea {{ background-color: {secondary_bg}; border-top: 1px solid {border_color}; padding: 10px 15px; }}
            QLineEdit {{ background-color: {input_bg}; color: {text_color}; border: 1px solid {border_color}; border-radius: 18px; padding: 10px 15px; font-size: 10pt; }}
            QLineEdit:focus {{ border: 1px solid {accent_hex}; }}

            QPushButton {{ background-color: {accent_hex}; color: {button_text}; border: none; border-radius: 18px; padding: 10px 20px; font-size: 10pt; font-weight: bold; min-width: 70px; }}
            QPushButton:hover {{ background-color: {button_hover_bg}; }}
            QPushButton:pressed {{ background-color: {button_pressed_bg}; }}
            QPushButton:disabled {{ background-color: {disabled_bg}; color: #7f8c8d; }}

            #statusLabel {{ padding: 4px; font-size: 9pt; font-weight: normal; border-radius: 0px; min-height: 25px; color: {default_light_text_color}; background-color: transparent; }} /* Default light text */
            #statusLabel[isError="true"] {{ background-color: {QColor(accent_hex).darker(150).name() if theme=='dark' else "#e74c3c"}; color: #ffffff; }}
            #statusLabel[isError="false"] {{ background-color: {QColor(accent_hex).darker(120).name() if theme=='dark' else QColor(accent_hex).lighter(120).name()}; color: {button_text}; }}

            QScrollBar:vertical {{ border: none; background: {scrollbar_bg}; width: 12px; margin: 0px; }}
            QScrollBar::handle:vertical {{ background: {scrollbar_handle}; min-height: 30px; border-radius: 6px; border: 1px solid {scrollbar_bg}; }}
            QScrollBar::handle:vertical:hover {{ background: {scrollbar_handle_hover}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ border: none; background: none; height: 0px; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
            #scrollArea QScrollBar:vertical {{ margin: 1px; }}
        """
        self.setStyleSheet(stylesheet)
    # ***********************************************************************
    # * AI TEXT COLOR FIX END                             *
    # ***********************************************************************


# --- Application Entry Point ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    # app.setStyle("Fusion")
    window = ChatWindow()
    window.show()
    sys.exit(app.exec())
