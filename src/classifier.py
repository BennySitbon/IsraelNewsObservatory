
import json
import os
import time
import requests

CATEGORIES = [
    "ביטחון ומלחמה", "פוליטיקה ומשפט", "פלילים ואלימות", "תאונות ואסונות",
    "חברה וקהילה", "כלכלה", "בריאות", "תרבות ובידור", "ספורט",
    "מדע וטכנולוגיה", "חדשות טובות", "חדשות קלילות", "אחר"
]

# Gemini rate limit: 12 requests per minute
GEMINI_MIN_INTERVAL = 5.0
_last_gemini_request = 0.0


def wait_for_gemini_slot():
    global _last_gemini_request

    now = time.monotonic()
    elapsed = now - _last_gemini_request
    wait_time = GEMINI_MIN_INTERVAL - elapsed

    if wait_time > 0:
        print(
            f"CLASSIFIER: Rate limit - waiting {wait_time:.1f}s",
            flush=True
        )
        time.sleep(wait_time)

    _last_gemini_request = time.monotonic()

def heuristic_classify(title, summary=""):
    text = (title + " " + summary).lower()

    rules = [
        ("תאונות ואסונות", ["תאונה", "נהרג", "הרוג", "נפצע", "שריפה", "הצפה", "אסון"]),
        ("פלילים ואלימות", ["רצח", "דקירה", "חשד", "נעצר", "תקיפה", "אלימות", "כתב אישום"]),
        ("ביטחון ומלחמה", ["צה\"ל", "צבא", "חמאס", "חיזבאללה", "איראן", "טיל", "כטב\"ם", "מלחמה", "חטוף"]),
        ("פוליטיקה ומשפט", ["ממשלה", "כנסת", "נתניהו", "בחירות", "אופוזיציה", "בג\"ץ", "בית המשפט"]),
        ("כלכלה", ["כלכלה", "מחיר", "יוקר המחיה", "שקל", "ריבית", "נדל\"ן", "מניות"]),
        ("בריאות", ["רופא", "בית חולים", "מחלה", "בריאות", "תרופה", "קורונה"]),
        ("ספורט", ["כדורגל", "כדורסל", "מכבי", "הפועל", "נבחרת", "ליגה"]),
        ("תרבות ובידור", ["זמר", "סרט", "טלוויזיה", "שחקן", "אירוויזיון", "מוזיקה"]),
        ("מדע וטכנולוגיה", ["בינה מלאכותית", "טכנולוגיה", "מחקר", "מדע", "סטארט-אפ", "סייבר"]),
        ("חדשות טובות", ["הציל", "זכה", "זכייה", "הישג", "תרומה", "התנדבות"])
    ]

    category = "אחר"
    for cat, words in rules:
        if any(w in text for w in words):
            category = cat
            break

    negative_words = ["נהרג", "נרצח", "פיגוע", "פצוע", "אסון", "תקיפה", "שריפה", "משבר", "קריסה"]
    positive_words = ["הציל", "זכה", "הישג", "ניצחון", "הצלחה", "נחנך"]

    neg = any(w in text for w in negative_words)
    pos = any(w in text for w in positive_words)

    sentiment = "שלילי" if neg else ("חיובי" if pos else "ניטרלי")
    score = 0.85 if neg else (0.8 if pos else 0.15)

    return {
        "category": category,
        "subcategory": "לא סווג",
        "sentiment": sentiment,
        "negativity_score": score if neg else (0.1 if pos else 0.0),
        "severity": "גבוהה" if any(w in text for w in ["נהרג", "נרצח", "פיגוע", "אסון"]) else ("בינונית" if neg else "נמוכה"),
        "is_human_tragedy": bool(any(w in text for w in ["נהרג", "נרצח", "פצוע", "פיגוע", "תאונה"])),
        "is_good_news": pos,
        "confidence": 0.35,
        "reason": "סיווג מקומי ראשוני לפי מילות מפתח; מומלץ לאמת מול מודל AI.",
        "classifier": "heuristic"
    }



def classify(title, summary=""):
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("CLASSIFIER: No API key. Using heuristic.", flush=True)
        return heuristic_classify(title, summary)

    model = "gemini-3.5-flash-lite"

    prompt = f"""
סווג את הכותרת החדשותית הבאה בעברית. החזר JSON בלבד עם השדות:
category (אחת מהקטגוריות: {", ".join(CATEGORIES)}),
subcategory (מחרוזת קצרה), sentiment (שלילי/ניטרלי/חיובי),
negativity_score (מספר 0 עד 1 שמודד שליליות בטון/תוכן),
severity (נמוכה/בינונית/גבוהה),
is_human_tragedy (boolean), is_good_news (boolean),
confidence (0 עד 1), reason (משפט קצר בעברית).
הבחן בין סיקור שלילי לבין טרגדיה אנושית. אל תסיק עובדות שאינן בכותרת.

כותרת: {title}
תקציר: {summary[:1200]}
"""

    schema = {
        "type": "OBJECT",
        "properties": {
            "category": {"type": "STRING", "enum": CATEGORIES},
            "subcategory": {"type": "STRING"},
            "sentiment": {
                "type": "STRING",
                "enum": ["שלילי", "ניטרלי", "חיובי"]
            },
            "negativity_score": {"type": "NUMBER"},
            "severity": {
                "type": "STRING",
                "enum": ["נמוכה", "בינונית", "גבוהה"]
            },
            "is_human_tragedy": {"type": "BOOLEAN"},
            "is_good_news": {"type": "BOOLEAN"},
            "confidence": {"type": "NUMBER"},
            "reason": {"type": "STRING"}
        },
        "required": [
            "category", "subcategory", "sentiment",
            "negativity_score", "severity",
            "is_human_tragedy", "is_good_news",
            "confidence", "reason"
        ]
    }

    try:
        wait_for_gemini_slot()
        r = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/interactions",
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "input": prompt,      
                "generation_config": {
                    "thinking_level": "low"
                },
                "response_format": {
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": schema
                }
            },
            timeout=60
        )

        r.raise_for_status()
        response = r.json()

        # Extract text from the Interactions API response.
        raw = response.get("output_text")

        if not raw:
            blocks = []
            for key in ("steps", "outputs"):
                for step in response.get(key, []):
                    for item in step.get("content", []):
                        if item.get("type") == "text":
                            blocks.append(item.get("text", ""))
            raw = "".join(blocks)

        if not raw:
            raise ValueError("No text returned by Gemini")

        data = json.loads(raw)
        data["classifier"] = model

        print(f"CLASSIFIER: Gemini SUCCESS ({model})", flush=True)
        return data

    except requests.HTTPError:
        print(
            f"CLASSIFIER: Gemini HTTP ERROR "
            f"{r.status_code}: {r.text[:1500]}",
            flush=True
        )
        return heuristic_classify(title, summary)

    except Exception as e:
        print(
            f"CLASSIFIER: Gemini FAILED "
            f"({type(e).__name__}): {e}",
            flush=True
        )
        return heuristic_classify(title, summary)
