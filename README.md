# fregate

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Minimal CLI client for [Ollama](https://ollama.ai/) — chat with local LLMs from your terminal.

## 🚀 Quick Start

```bash
git clone https://github.com/m4rv4x/fregate.git
cd fregate

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp config.json.example config.json  # or edit config.json directly
python client.py
```

## ⚙️ Config

`config.json`:
```json
{
  "API_URL": "http://localhost:11434"
}
```

## 📄 License

[MIT](LICENSE) © [marvax](https://github.com/m4rv4x)
