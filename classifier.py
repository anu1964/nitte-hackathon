import pickle
import numpy as np
from sentence_transformers import SentenceTransformer

# Load models
model = SentenceTransformer('all-MiniLM-L6-v2')
with open('classifier.pkl', 'rb') as f:
    clf = pickle.load(f)
with open('label_encoder.pkl', 'rb') as f:
    le = pickle.load(f)

ATTACK_THRESHOLD = 0.6

def get_attack_category(text: str) -> str | None:
    text_lower = text.lower()
    if any(w in text_lower for w in ["ignore previous", "ignore all", "disregard", "bypass", "jailbreak", "dan ", "do anything now"]):
        return "jailbreak"
    if any(w in text_lower for w in ["repeat your instructions", "reveal your prompt", "what are your instructions", "system prompt"]):
        return "prompt_leak"
    if any(w in text_lower for w in ["pretend you are", "act as", "you are now", "roleplay as", "simulate"]):
        return "role_hijack"
    return None

def get_severity(confidence: float) -> str:
    if confidence < 0.4:
        return "Low"
    elif confidence < 0.6:
        return "Medium"
    elif confidence < 0.8:
        return "High"
    else:
        return "Critical"

def analyze_prompt(text: str, groq_rephrase_fn=None) -> dict:
    embedding = model.encode([text])
    proba = clf.predict_proba(embedding)[0]
    classes = le.classes_
    confidence_dict = dict(zip(classes, proba))

    attack_confidence = confidence_dict.get('attack', 0)

    if attack_confidence > ATTACK_THRESHOLD:
        label = "attack"
        confidence = attack_confidence
    else:
        label = "safe"
        confidence = confidence_dict.get('safe', 1 - attack_confidence)

    category = get_attack_category(text) if label == "attack" else None
    severity = get_severity(attack_confidence) if label == "attack" else None

    safe_rephrasing = None
    if label == "attack" and groq_rephrase_fn:
        safe_rephrasing = groq_rephrase_fn(text)

    return {
        "label": label,
        "confidence": round(confidence, 4),
        "category": category,
        "severity": severity,
        "safe_rephrasing": safe_rephrasing
    }