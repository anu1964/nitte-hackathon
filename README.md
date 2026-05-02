# 🛡️ Safe Prompt Guardian

A real-time semantic firewall that detects prompt injection attacks before they reach an LLM.

## Problem Statement
LLM-integrated applications are vulnerable to prompt injection attacks where malicious users manipulate AI behavior by hijacking system instructions. Existing solutions rely on keyword filtering which is easily bypassed.

## Solution
Safe Prompt Guardian uses semantic embeddings + SVM classification to detect adversarial intent at the input level — before the prompt reaches the LLM.

## Architecture
User Prompt → Embedding Extraction → Semantic Classifier → Safety Decision → LLM or Block

## Tech Stack
- **Embeddings:** all-MiniLM-L6-v2 (sentence-transformers)
- **Classifier:** SVM (scikit-learn)
- **Safe Rephrasing:** LLaMA 3.1 via Groq API
- **UI:** Gradio
- **Datasets:** HackAPrompt, AdvBench, Alpaca

## Setup
```bash
python -m venv .venv
.venv\Scripts\activate
pip install gradio sentence-transformers scikit-learn datasets groq
python pretrain.py
python app.py
```

## Usage
1. Run `python pretrain.py` once to train the classifier
2. Run `python app.py` to start the app
3. Enter any prompt — app detects ATTACK or SAFE instantly

## Features
- Semantic analysis using embeddings
- Real-time classification
- Safe prompt rephrasing for detected attacks
- Logging of all predictions to `log.csv`

