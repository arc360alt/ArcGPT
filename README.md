# Ollama Multi-Chat GUI

This app is a Python Qt-based GUI for chatting with Ollama using multiple persistent chat sessions.  
These instructions will guide you through setup on **Windows** and **Linux**.

---

## Prerequisites

- Python **3.9+** (recommend 3.10 or 3.11)
- [Git](https://git-scm.com/downloads)
- [Ollama](https://ollama.com/download) running locally
- Internet connection (for installing dependencies)

---

## 1. Clone the Repository (ArcGPT-Ollama Branch)

```sh
git clone --branch ArcGPT-Ollama https://github.com/arc360alt/ArcGPT.git
cd ArcGPT
```

---

## 2. Create and Activate a Virtual Environment

### Linux

```sh
python3 -m venv venv
source venv/bin/activate
```

### Windows

```sh
python -m venv venv
venv\Scripts\activate
```

---

## 3. Install Required Python Packages

```sh
pip install -r requirements.txt
```

---

## 4. Run the Application

```sh
python ollama_gui.py
```

---

## Notes

- Make sure Ollama is running (`ollama serve` or via the tray app on Windows) before launching the GUI.
- The app will automatically create chat history folders/files as needed.
- You may use `pip install --upgrade pip` if you have issues with older pip versions.

---

## Troubleshooting

- If you get errors about missing PySide6 or markdown, re-run `pip install -r requirements.txt`
- If you run into problems with DuckDuckGo search, you can comment out/remove the `duckduckgo_search` lines.
- For Linux users, ensure you have Qt dependencies (e.g., `sudo apt install libxcb-xinerama0` for Ubuntu if you get Qt errors).

---

Enjoy your multi-chat Ollama GUI!