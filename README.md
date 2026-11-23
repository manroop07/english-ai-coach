# English Coach – Phase 5

## Run it on Windows (VS Code)

1. Unzip the folder and open it in VS Code (File → Open Folder → `english_coach`).
2. Open the terminal in VS Code (Ctrl + `) and run these one at a time:

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

3. Open the new `.env` file and replace `your_key_here` with your Gemini key
   (free key: https://aistudio.google.com/apikey).
4. Start the app:

```
streamlit run app.py
```

If PowerShell blocks `activate`, run `Set-ExecutionPolicy -Scope Process Bypass` first.

## Folder structure

```
english_coach/
├── app.py                  # entry point, sidebar navigation
├── config.py               # settings, XP rules, topics
├── requirements.txt
├── .env / .env.example     # your Gemini key (never share .env)
├── .streamlit/config.toml  # theme colours
├── data/                   # SQLite database is created here
├── core/
│   ├── database.py         # all tables + query helpers
│   ├── auth.py             # register, login, password hashing, profile
│   ├── gamification.py     # XP, levels, streaks
│   ├── ai.py               # Gemini wrapper with friendly errors
│   ├── conversation.py     # AI teacher + grammar feedback
│   ├── vocab.py / vocab_bank.py
│   └── ui.py               # CSS and UI components
└── views/                  # one file per page
```

## Phase 2 – what's new
- **My Schedule**: Today / Week / Plan / Targets tabs, edit, delete, reschedule missed tasks.
- Tasks for conversation (3+ messages), vocabulary quiz, word of the day and flashcards complete **automatically** when you do them. Marking done by hand gives no XP.
- In-app reminders (top of every page, refresh every minute) and optional browser notifications.
- AI-suggested weekly plan from your level, time and real weak areas.
- Upgrading from Phase 1: just copy the new files over. Your database upgrades itself; no data is lost.

## Phase 3 – what's new
- **My Progress** page with 6 tabs: Overview, Weekly & monthly, Skills, Grammar & quizzes, Weekly report, AI coach.
- Interactive Plotly charts: activity calendar, 7-day and 30-day XP + time, 8-week history, skill bars,
  grammar categories, grammar improvement, quiz accuracy.
- Weekly report with this-week vs last-week comparison and a downloadable `.md` file.
- AI coach: rule-based recommendations, targeted practice sets built from your real mistakes
  (earn XP, complete planned "Grammar" tasks) and a weekly improvement plan you can add to My Schedule.
- **Learning time**: quizzes are timed for real; other activities are *estimated* from the gap between your actions.
  Time only starts counting from the day you install Phase 3 (older activities have no time recorded).
- Nothing is faked: scores need a minimum amount of data, otherwise the page says "not enough data".
- Upgrading from Phase 2: copy the files over (same folders). The database adds its new table automatically.

## Phase 4 – what's new
- **Grammar & Writing**: AI grammar lessons for 7 topics with a 5-question quiz; writing tab for journal, paragraph,
  email and essay with a score, corrected version, explained mistakes, sentence and vocabulary upgrades; saved history.
  Mistakes found in your writing feed My Progress, just like conversation mistakes.
- **Speaking Practice**: AI practice sentences by real-life scenario, 🔊 Listen (browser voice), record with the
  microphone, word-by-word match, history. Roleplay as interviewer, friend, teacher or shopkeeper by voice or text.
- Pronunciation scores are **speech-to-text matching**, not phonetic assessment. XP is given only the first time you
  reach 70% on a sentence.
- Voice recording needs Streamlit 1.39+ (`pip install -U streamlit`) and microphone permission in the browser.
- Upgrading from Phase 3: copy the files over. The database adds its new table automatically.

## Phase 5 – what's new
- **Streaks & Achievements** page: streak calendar (browse months), milestones at 7, 15, 30 and 100 days,
  20 badges, daily and weekly challenges, and a leaderboard (this week / all time).
- Badges unlock automatically after real activities and pop up as a toast. Challenge progress is counted from your
  own records; the bonus XP is paid when you press **Claim**, after the app re-checks the progress. Each reward can be
  claimed once. Bonus XP adds to total XP but does not count as study time or extend your streak.
- Leaderboard shows only name, avatar and XP. You can switch yourself off with the toggle on that tab.
- Upgrading from Phase 4: copy the files over. The database adds its new table and column automatically.
