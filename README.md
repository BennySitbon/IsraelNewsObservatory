# Israel News Observatory

מערכת MVP לניטור כותרות חדשות בעברית, סיווג AI ודשבורד אנליטי.

## מה יש בפרויקט
- איסוף RSS מתוזמן באמצעות GitHub Actions (ברירת מחדל: כל שעתיים).
- שמירת כתבות ותצפיות בכותרות במסד SQLite.
- סיווג קטגוריה, תת-קטגוריה, סנטימנט, חומרה וסיפור אנושי.
- שימוש ב-Gemini API אם מוגדר `GEMINI_API_KEY`; אחרת סיווג בסיסי מקומי (heuristics).
- דשבורד Streamlit בעברית עם KPI, גרפים, השוואת מקורות וטבלת כותרות.

## מגבלה חשובה בגרסה הראשונה
RSS מודד פריטים שפורסמו בפיד של האתר. הוא **לא בהכרח** משקף את הכותרות הראשיות בעמוד הבית או את מיקום הכותרת במסך. לכן בגרסה זו המדד נקרא "כותרות שנאספו מהפידים". כדי למדוד חשיפה ומיקום בעמוד הבית צריך להוסיף מאוחר יותר collectors ייעודיים לעמוד הבית של כל אתר, ולשמור snapshots עם מיקום וגודל/סוג slot.

## הפעלה מקומית

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # אופציונלי; הוסף GEMINI_API_KEY
python -m src.collect
streamlit run app.py
```

הדשבורד ייפתח בכתובת המקומית שמודפסת בטרמינל.

## הגדרת מקורות
ערוך את `feeds.json`. כל מקור הוא:
```json
{
  "name": "שם האתר",
  "url": "כתובת RSS",
  "enabled": true
}
```
התחלנו עם פידים ציבוריים שמצאנו ל-ynet ולוואלה. יש לבדוק מדי פעם שהפיד עדיין פעיל ובהתאם לתנאי השימוש של כל אתר. הוסף N12, הארץ, ישראל היום ומעריב רק לאחר אימות כתובת הפיד המתאימה.

## הפעלה אוטומטית בחינם באמצעות GitHub Actions

1. צור repository ב-GitHub והעלה אליו את כל הקבצים.
2. ב-GitHub: `Settings -> Secrets and variables -> Actions -> New repository secret`.
3. הוסף secret בשם `GEMINI_API_KEY` (אופציונלי; בלי זה יעבוד סיווג מקומי בסיסי).
4. ודא ש-`Actions` מופעלים.
5. ה-workflow שב-`.github/workflows/collect.yml` רץ כל שעתיים וגם ניתן להפעילו ידנית דרך `Actions -> Collect news -> Run workflow`.
6. כדי שה-SQLite יתמיד בין הרצות, ה-workflow עושה commit לקובץ `data/news.db`. מומלץ repository פרטי.

הערות:
- GitHub Actions schedule משתמש ב-UTC ועלול להתעכב בעומסים; "כל שעתיים" הוא יעד תזמון ולא SLA.
- במאגר פרטי יש מכסת דקות חודשית בהתאם לתוכנית GitHub. במאגר ציבורי runners סטנדרטיים זמינים ללא חיוב, בכפוף למדיניות GitHub.
- אל תכניס API key לקוד או לקובץ `.env` שמועלה ל-GitHub.

## פרסום הדשבורד
אפשר לפרוס את `app.py` ב-Streamlit Community Cloud:
1. התחבר ל-Streamlit Community Cloud עם GitHub.
2. בחר את ה-repository ואת `app.py`.
3. Deploy.
4. אם הדשבורד לא רואה את `data/news.db`, בדוק שהקובץ נמצא ב-branch הראשי ושה-workflow ביצע commit.

הדשבורד הציבורי עשוי להיות גלוי לכל מי שיש לו את הקישור. אל תכניס אליו מידע פרטי.

## מבנה נתונים
- `articles`: כתבה ייחודית לפי URL מנורמל.
- `observations`: כל פעם שהכתבה הופיעה בפיד, כולל כותרת ותאריך איסוף.
- `runs`: סטטוס כל ריצת איסוף.

## עקרונות מדידה
- קטגוריה וסנטימנט הם שני ממדים נפרדים.
- "שלילי" לא שווה "טרגדיה": נשמרים גם `is_human_tragedy` ו-`severity`.
- יש להציג אחוזים רק לצד הגדרת המכנה (כתבות ייחודיות או תצפיות).
- סיווג אוטומטי עלול לטעות. `confidence` נשמר כדי לאפשר בקרת איכות.
