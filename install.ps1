echo "-------------------------------------"
echo "   ArkGPT Easy Install Script 0.1"
echo "-------------------------------------"
echo "Windows Version"

echo "Press any key when you have enshured that you have installed the following:"
echo "Git"
echo "Python"
echo "Ollama"

pause

echo "You may get an error here, ignore it, idk what its about but the git clone does sucseed"
git clone --branch ArcGPT-Ollama https://github.com/arc360alt/ArcGPT.git
cd ArcGPT
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cd ..

clear

echo "Make shure your cd'd into ArcGPT (cd ArcGPT if you arent)"
echo "Now if you see (venv) next to PS in your Powershell prompt, run python ollama_gui.py"
echo "if you dont run ./run.ps1"