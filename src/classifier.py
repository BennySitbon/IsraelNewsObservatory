import json, os, re, requests

CATEGORIES = [
    "ביטחון ומלחמה", "פוליטיקה ומשפט", "פלילים ואלימות", "תאונות ואסונות",
    "חברה וקהילה", "כלכלה", "בריאות", "תרבות ובידור", "ספורט",
    "מדע וטכנולוגיה", "חדשות טובות", "חדשות קלילות", "אחר"
]

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
        "category": category, "subcategory": "לא סווג",
        "sentiment": sentiment, "negativity_score": score if neg else (0.1 if pos else 0.0),
        "severity": "גבוהה" if any(w in text for w in ["נהרג", "נרצח", "פיגוע", "אסון"]) else ("בינונית" if neg else "נמוכה"),
        "is_human_tragedy": bool(any(w in text for w in ["נהרג", "נרצח", "פצוע", "פיגוע", "תאונה"])),
        "is_good_news": pos, "confidence": 0.35,
        "reason": "סיווג מקומי ראשוני לפי מילות מפתח; מומלץ לאמת מול מודל AI.",
        "classifier": "heuristic"
    }

def classify(title, summary=""):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return heuristic_classify(title, summary)
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
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
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    try:
        r = requests.post(url, json={"contents":[{"parts":[{"text":prompt}]}],
                                     "generationConfig":{"responseMimeType":"application/json"}},
                          timeout=30)
        r.raise_for_status()
        raw = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(raw)
        data["classifier"] = model
        return data
    except Exception:
        # Keep the pipeline running if the free API is unavailable or quota is exhausted.
        return heuristic_classify(title, summary)
