![gaming](https://github.com/user-attachments/assets/100c3780-7da1-4cca-93ce-fe471a99aed7)

## Please check [How to use](https://github.com/arc360alt/ArcGPT/edit/ArcGPT-Ollama/README.md#how-to-use) and [Troubleshooting](https://github.com/arc360alt/ArcGPT/edit/ArcGPT-Ollama/README.md#troubleshooting) before using!

# ArkGPT Ollama

This app is a Python Qt-based GUI for chatting with Ollama using multiple persistent chat sessions.  
These instructions will guide you through setup on **Windows** and **Linux**.

---

## Prerequisites

- Python **3.9+** (recommend 3.10 or 3.11)
- [Git](https://git-scm.com/downloads)
- [Ollama](https://ollama.com/download) running locally
- Internet connection (for installing dependencies)

---

# Easy Install on Linux
- ``curl https://raw.githubusercontent.com/arc360alt/ArcGPT/refs/heads/ArcGPT-Ollama/install.sh | sh ``
- Then after install
- ``cd ArcGPT``
- ``./run.sh``

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
- If you get an error about a localhost adress not being acsessable, go to the settings and make shure you have a Ollama LLM set, not having one set or not pressing OK after setting one opon first launch causes this issue

---

## Screenshots:
![image](https://github.com/user-attachments/assets/b6eb7ea2-643d-429f-b44d-377db9a20c03)

## How to use
- Chat whith it
- to use internet, check the 2 bottom options in the settings app, and type !usesearch to force the bot to use DuckDuckGo to search (unchangable)
- You can use multiple chats that save, and the bot will remember what you said in each one, the memory will not reset after a relaunch. but memory acrost multiple chats does not work
- Create an issue if you got an error and i can clarify it!
