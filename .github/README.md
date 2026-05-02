# Safe Prompt Guardian — GitHub Action

Automatically scans your repository for prompt injection 
attacks on every push.

## What it does
- Scans all .py, .txt, .json, .md files
- Detects prompt injection patterns
- Reports file, line number, category, severity
- Warns before deploying to production

## Setup
Add GUARDIAN_API_URL to your GitHub Secrets:
Settings → Secrets → New secret
Name: GUARDIAN_API_URL
Value: your deployed API URL