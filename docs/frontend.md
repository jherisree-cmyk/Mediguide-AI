# Frontend (React + Vite)

## Run the whole app (two terminals)

**Terminal 1, backend:**
```powershell
cd C:\Users\donep\mediguide-ai\backend
..\.venv\Scripts\Activate.ps1
uvicorn api.main:app --reload
```

**Terminal 2, frontend:**
```powershell
cd C:\Users\donep\mediguide-ai\frontend
npm install        # first time only
npm run dev
```

Open **http://localhost:5173**. The Vite dev server forwards `/api/*` to the backend on port 8000,
so the browser sees a single origin and the httpOnly login cookie just works.

## Pages
| Path | Page |
|---|---|
| `/` | Welcome: what the app does and does not do, language buttons, emergency notice |
| `/language` | Language selection (English / తెలుగు / हिंदी) |
| `/login`, `/register` | Optional account |
| `/assess` | Describe symptoms (free text), optional age, input language, "save to history" |
| `/assess/questions` | Symptom confirmation ("We understood: …") + follow-up questions |
| `/assess/result` | Urgency (icon + text + colour), emergency call buttons, reasons, sources, tree path, safety-net |
| `/history`, `/history/:id` | Saved assessments: view, delete one, delete all |
| `/profile` | Age, sex, language; delete account |
| `/admin` | Admin dashboard (Phase 10) |

## Design and accessibility
- Urgency is never shown by colour alone: there is always an icon and a text label.
- The emergency banner sits at the top, with tap-to-call `tel:112` / `tel:108` links.
- Base font is 18px with taller line spacing for Telugu and Devanagari. Touch targets are at least 44–48px.
- There is a skip link, focus moves to the new page on navigation (not on first load), focus outlines are visible, and form fields have labels.
- Mobile-first: on phones the navigation gets its own row. The print stylesheet hides navigation.
- **Privacy:** the current assessment lives only in React memory. Only the chosen UI language is stored in `localStorage`.

## Advanced features (Phase 12)
| Feature | Where | Privacy / safety notes |
|---|---|---|
| **Live symptom detection** while typing | `LiveDetection.jsx` → `POST /api/assess/preview` | Stateless: no database row, no statistics. Shows recognised (✓) and negated (✕, struck through and said in words) symptoms, and an alert if an EMERGENCY sign is already present. Never shows Routine/Urgent before the full check. |
| **Voice input** (en-IN / te-IN / hi-IN) | `Speech.jsx` `VoiceInput` | Browser Web Speech API; hidden if unsupported. The UI says the audio may go to the browser vendor's speech service. Text is appended, never auto-submitted. |
| **Read aloud** | `Speech.jsx` `ReadAloud` | Reads level, next step and "call 112 if" items; notes when no voice for the language is installed. |
| **Find a hospital / clinic near me** | `CareActions.jsx` | A Google Maps search link; the app never reads the user's location. |
| **Summary for a doctor** (.txt) | `CareActions.jsx` `buildSummary` | Built in the browser from the result (nothing uploaded); UTF-8 with BOM so Telugu/Hindi open correctly in Notepad. |
| **Dark mode** | `theme.js`, header toggle | Only the theme choice is stored. Applied before first paint. Admin charts stay on light cards because their palette was validated against a light surface. |
| **Animated background** | `MedicalBackground.jsx` (canvas) | Aurora, a neural network of nodes and crosses with travelling signals, DNA helices beside the content, an ECG sweep. No flashing; paused in hidden tabs; a single still frame with *reduce motion*; hidden when printing. |

## Tests
- `features.test.jsx`: **6 tests** for live detection (chips, negation in words, emergency alert), voice input (hidden when unsupported; language; final text), care links, the doctor summary and the theme toggle.
- `npm test`: **11 component tests** (Vitest + Testing Library) covering:
  - the badge (icon + text);
  - emergency and routine results;
  - the follow-up answer format and the exclusive "none" option;
  - language switching;
  - the full text → questions → result flow with a mocked backend;
  - redirecting protected pages to login;
  - no health data in browser storage.
- `python scripts/e2e_browser.py` (from the project root; needs `pip install -r backend/requirements-dev.txt`):
  drives the real app in Microsoft Edge. **8 steps**, in EN/TE/HI, on desktop and mobile. Screenshots go to `reports/figures/p9_*.png`.

## Bugs found by these tests (and fixed)
| Bug | Found by | Effect |
|---|---|---|
| After answering the questions, users were sent back to the start page | component test | The follow-up page redirected a *completed* assessment to `/assess` instead of `/assess/result` |
| 5 English labels truncated ("Pain spreading to arm" lost ", jaw, neck or back"; cyanosis shown as "Blue") | browser screenshot | Unquoted commas in YAML `{...}`. Labels quoted, and the validator now rejects extra label keys |
| First Tab skipped the skip link | browser test | Focus moved to main content on first load (and React StrictMode ran the effect twice) |
| Navigation words squeezed onto two lines on phones | screenshot review | Navigation now gets its own row on small screens |
| "Select all that apply" shown twice | screenshot review | Duplicate hint removed |

## Admin dashboard (Phase 10)
1. Register an account in the app.
2. Run `python scripts\create_admin.py you@example.com`.
3. Log in again and open `/admin`.

The dashboard shows:
- **Tiles:** completed assessments, share that needed follow-up questions, model version, thresholds.
- **Charts:** urgency recommendations, input language, top 15 symptoms, assessments per day, rule level → model level. Every chart has a "Show as table" view.
- **Model evaluation:** NHAMCS 2022 test results for the app policy and for the Random Forest comparison, under a "not clinically validated" warning.

Data source: the anonymous `assessment_stats` table only. Groups smaller than 5 are shown as "<5"; with very little data the charts are therefore mostly "<5", which is intended.
Chart colours were checked with the dataviz palette validator (colour-blind separation passes). The amber bar is 2.99:1 against the background, so every bar also has a value label and a table view.

**Demo data for presentations:** `python scripts\seed_demo_stats.py` runs the ~260 synthetic test sentences
through the real engine and stores anonymous stats rows. These are **not real usage**; say so whenever you show them.
