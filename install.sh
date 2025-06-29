echo "-------------------------------------"
echo "   ArkGPT Easy Install Script 0.1"
echo "-------------------------------------"
echo "installing Ollama if you have not already"
echo "LINUX ONLY!!"
echo "If you have already installed Ollama press ctrl+c to quit that script"

curl -fsSL https://ollama.com/install.sh | sh

echo "Installing ArkGPT Ollama"

git clone --branch ArcGPT-Ollama https://github.com/arc360alt/ArcGPT.git
cd ArcGPT
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

clear

echo "Thank you for using ArkGPT Ollama Easyinstall script!"
echo "You can now cd into arkgpt and run the script by doing the following"

echo "cd ArcGPT"
echo "./run.sh"
