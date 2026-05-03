# 🛡️ Safe Prompt Guardian

Middleware API that detects and blocks prompt injection attacks 
before they reach your LLM.

## Problem
Prompt injection is the #1 LLM security risk (OWASP 2025).
In June 2025, McDonald's AI hiring bot exposed 64M records —
prompt injection was the first attack vector tried.

## Solution
Safe Prompt Guardian sits between the user and your LLM.
Attacks are blocked instantly. Safe prompts pass through normally.

## How It Works
1. User sends prompt
2. all-MiniLM-L6-v2 converts it to 384-dim vector
3. SVM classifier detects if it's an attack
4. Attack → blocked, logged, never reaches LLM
5. Safe → forwarded to LLM, response returned

## Model Stats
| Metric | Value |
|---|---|
| Algorithm | SVM + RBF kernel + GridSearchCV |
| Embeddings | all-MiniLM-L6-v2 (384 dimensions) |
| Dataset | 500+ real prompts (HackAPrompt, AdvBench, Alpaca) |
| K-Fold Accuracy | 96.88% ± 0.99% |
| Best F1 Score | 96.6% |

## Features
- Real-time prompt injection detection
- Obfuscation detection (leetspeak, spaced letters, special chars)
- Attack categorization (Jailbreak, Role Hijack, Prompt Leak)
- Severity rating (Low / Medium / High / Critical)
- REST API for any developer to integrate
- CSV logging of all attempts
- Live demo: vulnerable vs protected bot side by side

## Tech Stack
- Python, scikit-learn, sentence-transformers
- FastAPI, Gradio, Groq (LLaMA 3.1 8B)
- HuggingFace datasets

## Setup
```bash
git clone <your-repo>
cd nitte-hack
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python pretrain.py
python app.py
```

## API Endpoints
| Endpoint | Method | Description |
|---|---|---|
| /analyze | POST | Classify any prompt |
| /chat | POST | Proxy — blocks attacks, forwards safe |
| /stats | GET | Total analyzed, attack rate |
| /logs | GET | Recent prompt history |
| /health | GET | Server uptime |

## AI Usage
Built with assistance from Claude (Anthropic) for code 
structure and debugging. All ML decisions, dataset selection,
and architecture designed by the team.

## Team
- Anu — ML pipeline, API, classifier
- [Partner name] — Gradio UI, demo bots, PPT

## Demo
[Add your Hugging Face or demo link here]