import pickle
import numpy as np
import os
from sentence_transformers import SentenceTransformer
from groq import Groq

print("Loading classifier models...")

# ✅ FIX 1: All models loaded once at startup — never reloaded per call
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

with open("classifier.pkl", "rb") as f:
    clf = pickle.load(f)

with open("label_encoder.pkl", "rb") as f:
    le = pickle.load(f)

try:
    with open("rf_classifier.pkl", "rb") as f:
        rf_clf = pickle.load(f)
    print("RF model loaded.")
except FileNotFoundError:
    print("WARNING: rf_classifier.pkl not found. Using SVM only.")
    rf_clf = None

# ✅ FIX 2: Groq client created ONCE as a singleton — not on every analyze call
_groq_client = None

def get_groq_client():
    global _groq_client
    if _groq_client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if api_key:
            _groq_client = Groq(api_key=api_key)
    return _groq_client

print("Models loaded.")

ATTACK_THRESHOLD = 0.6
_attack_history = []
MAX_HISTORY = 50


def normalize_text(text):
    text = text.lower().strip()
    leet_map = {
        '0': 'o', '1': 'i', '3': 'e', '4': 'a',
        '5': 's', '6': 'g', '7': 't', '@': 'a',
        '$': 's', '!': 'i', '+': 't'
    }
    for k, v in leet_map.items():
        text = text.replace(k, v)
    return text


def check_repeat_attack(text):
    global _attack_history
    text_lower = text.lower().strip()
    recent_texts = [h["text"] for h in _attack_history[-10:]]
    text_words = set(text_lower.split())

    # ✅ FIX 3: Count actual similar matches, not total history size
    similar_count = 0
    for recent in recent_texts:
        recent_words = set(recent.split())
        overlap = len(text_words & recent_words) / max(1, len(text_words))
        if overlap > 0.7:
            similar_count += 1

    if similar_count >= 3:
        return True, f"Similar attack seen {similar_count} times this session"
    return False, None


def log_attack(text):
    global _attack_history
    _attack_history.append({
        "text": text.lower().strip(),
        "count": len(_attack_history) + 1
    })
    if len(_attack_history) > MAX_HISTORY:
        _attack_history.pop(0)


def get_attack_pattern_name(text):
    text_lower = text.lower()
    patterns = {
        "DAN Variant": [
            "do anything now", "dan ", "jailbreak"
        ],
        "Developer Mode Exploit": [
            "developer mode", "dev mode", "debug mode"
        ],
        "Grandma Exploit": [
            "grandma", "bedtime story", "used to tell me"
        ],
        "Hypothetical Framing": [
            "hypothetically", "in a fictional", "in a story",
            "for a creative writing", "imagine a world"
        ],
        "Instruction Override": [
            "ignore previous", "ignore all", "disregard",
            "forget everything", "new instruction"
        ],
        "Privilege Escalation": [
            "you are now", "from now on", "your new role",
            "override", "bypass"
        ],
        "System Prompt Extraction": [
            "system prompt", "starting instructions",
            "what were you told", "repeat your instructions",
            "reveal your prompt"
        ],
        "Persona Hijack": [
            "pretend you are", "act as", "roleplay as",
            "simulate", "your true self"
        ],
        "Reverse Psychology": [
            "don't tell me", "you cannot", "i bet you won't",
            "prove you can"
        ],
    }
    for pattern_name, keywords in patterns.items():
        for keyword in keywords:
            if keyword in text_lower:
                return pattern_name
    return None


def get_attack_category(text):
    text_lower = text.lower()
    jailbreak_words = [
        "ignore previous", "ignore all", "disregard", "bypass",
        "jailbreak", "dan ", "do anything now", "developer mode",
        "no restrictions", "lifted", "pwned", "override"
    ]
    prompt_leak_words = [
        "repeat your instructions", "reveal your prompt",
        "what are your instructions", "system prompt",
        "starting instructions", "what were you told",
        "summarize your context"
    ]
    role_hijack_words = [
        "pretend you are", "act as", "you are now",
        "roleplay as", "simulate", "your true self",
        "respond as", "from now on you"
    ]
    for w in jailbreak_words:
        if w in text_lower:
            return "jailbreak", [w]
    for w in prompt_leak_words:
        if w in text_lower:
            return "prompt_leak", [w]
    for w in role_hijack_words:
        if w in text_lower:
            return "role_hijack", [w]
    return None, []


def get_severity(confidence):
    if confidence < 0.4:
        return "Low"
    elif confidence < 0.6:
        return "Medium"
    elif confidence < 0.8:
        return "High"
    else:
        return "Critical"


def get_safe_rephrasing(text):
    # ✅ FIX 2 applied: reuse singleton client
    client = get_groq_client()
    if not client:
        return None
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "Rephrase the following prompt to make it safe and appropriate. Reply with only the rephrased prompt."
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            max_tokens=200
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("Groq rephrasing failed: " + str(e))
        return None


def analyze_prompt(text, rephrase=True):
    normalized = normalize_text(text)
    embedding = model.encode([text])

    proba = clf.predict_proba(embedding)[0]
    classes = le.classes_
    confidence_dict = dict(zip(classes, proba))
    attack_confidence = confidence_dict.get("attack", 0)

    if attack_confidence > ATTACK_THRESHOLD:
        label = "attack"
        confidence = attack_confidence
    else:
        label = "safe"
        confidence = confidence_dict.get("safe", 1 - attack_confidence)

    category, matched = get_attack_category(normalized)
    pattern_name = get_attack_pattern_name(normalized)

    # Override SVM if keyword detection catches obfuscated attack
    if category and label == "safe":
        label = "attack"
        confidence = ATTACK_THRESHOLD + 0.01

    if label == "attack":
        explanation = (
            f"Triggered by: '{matched[0]}'" if matched
            else "Detected by ML model as attack pattern"
        )
        severity = get_severity(attack_confidence)
        is_repeat, repeat_warning = check_repeat_attack(text)
        log_attack(text)
    else:
        category = None
        matched = []
        pattern_name = None
        explanation = "No attack patterns detected"
        severity = None
        is_repeat = False
        repeat_warning = None

    safe_rephrasing = None
    if label == "attack" and rephrase:
        safe_rephrasing = get_safe_rephrasing(text)

    return {
        "label": label,
        "confidence": round(float(confidence), 4),
        "category": category,
        "severity": severity,
        "safe_rephrasing": safe_rephrasing,
        "explanation": explanation,
        "pattern_name": pattern_name,
        "is_repeat_attack": is_repeat,
        "repeat_warning": repeat_warning
    }