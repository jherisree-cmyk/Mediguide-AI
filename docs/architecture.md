# MediGuide AI: architecture

All diagrams are Mermaid, so GitHub renders them automatically. To export one as an image, paste it into https://mermaid.live.

## 1. System architecture

```mermaid
flowchart TB
    subgraph Client["Browser: React 19 + Vite"]
        UI["Pages: welcome, language, assess,<br/>follow-up, result, history, profile, admin"]
        I18N["i18next UI text<br/>EN / TE / HI"]
    end

    subgraph API["FastAPI backend (backend/api)"]
        AUTH["/api/auth<br/>register, login, profile, delete"]
        ASSESS["/api/assess<br/>start + answers"]
        HIST["/api/history<br/>owner-only"]
        ADMIN["/api/admin/stats<br/>admin-only, anonymous"]
        SEC["Security: Argon2id, JWT httpOnly cookie,<br/>Fernet encryption, rate limit, headers"]
    end

    subgraph Engine["Core engine (backend/mediguide), no web code"]
        LANG["multilingual<br/>script detection + normalisation"]
        NLP["nlp<br/>Matcher, negation, attributes"]
        SAFE["safety<br/>red-flag rule engine"]
        FU["followup<br/>rule-derived questions"]
        ML["ml<br/>features + depth-6 Decision Tree"]
        REC["recommend<br/>final level + explanation"]
    end

    subgraph Knowledge["Reviewable knowledge files (knowledge/)"]
        SYM["symptoms.yaml<br/>71 concepts, EN/TE/HI"]
        RF["red_flags.yaml<br/>27 cited rules"]
        CUE["nlp_cues.yaml<br/>negation, severity, time"]
        TPL["templates.yaml<br/>all result text"]
    end

    DB[("SQLite<br/>users · assessments (encrypted)<br/>· assessment_stats (anonymous)")]
    MODEL[["models/dt_app_v1.joblib<br/>+ metadata"]]

    UI -- "JSON over /api (Vite proxy)" --> AUTH & ASSESS & HIST & ADMIN
    ASSESS --> REC
    REC --> LANG --> NLP --> SAFE
    REC --> FU & ML
    SAFE --> RF
    NLP --> SYM & CUE
    FU --> RF & TPL
    REC --> TPL
    ML --> MODEL
    AUTH & ASSESS & HIST & ADMIN --> DB
```

**Independence rule:** `safety` never imports `ml` (an AST test enforces this). The web layer (`api`) only calls the
engine's single entry point, `recommend.engine.assess()`.

## 2. Data flow of one assessment

```mermaid
sequenceDiagram
    actor P as Patient
    participant F as React app
    participant A as FastAPI
    participant E as Engine
    participant D as Database

    P->>F: Describes symptoms (any language)
    F->>A: POST /api/assess {text, age?, display_lang, save?}
    A->>E: assess(text)
    E->>E: detect language, normalise, extract symptoms
    E->>E: red-flag rules
    alt Emergency warning sign
        E-->>A: EMERGENCY result (no questions)
        A->>D: anonymous stats row (+ encrypted record if saved)
        A-->>F: result
        F-->>P: Call 112 / 108 banner, reasons, sources
    else No emergency yet
        E-->>A: needs_followup + questions
        A->>D: pending record (encrypted text, token hash, expires in 60 min)
        A-->>F: questions + one-time token
        F-->>P: "We understood: …" + questions
        P->>F: Answers
        F->>A: POST /api/assess/{id}/answers {answers, token}
        A->>E: assess(text, answers)
        E->>E: rules again, then Decision Tree (capped at URGENT)
        E-->>A: final = most urgent(rules, model)
        A->>D: stats row; keep encrypted record only if saved, else delete
        A-->>F: result
        F-->>P: level, next step, reasons, tree path, safety-net
    end
```

## 3. Use cases

```mermaid
flowchart LR
    Anon(["Anonymous patient"])
    User(["Registered user"])
    Admin(["Administrator"])

    UC1(("Choose language"))
    UC2(("Describe symptoms"))
    UC3(("Confirm extracted symptoms"))
    UC4(("Answer follow-up questions"))
    UC5(("View urgency result<br/>+ explanation"))
    UC6(("Call emergency number"))
    UC7(("Register / log in"))
    UC8(("Manage profile<br/>age, sex, language"))
    UC9(("Save, view and delete history"))
    UC10(("Delete account"))
    UC11(("View anonymous statistics<br/>+ model metrics"))

    Anon --- UC1 & UC2 & UC3 & UC4 & UC5 & UC6 & UC7
    User --- UC1 & UC2 & UC3 & UC4 & UC5 & UC6 & UC8 & UC9 & UC10
    Admin --- UC11
```

## 4. Database schema

```mermaid
erDiagram
    users ||--o{ assessments : "owns (only if saved)"
    users {
        int id PK
        string email UK
        string password_hash "Argon2id"
        string display_name
        float age_years "optional"
        string sex "optional F/M"
        string language "en/te/hi"
        bool is_admin
        datetime created_at
    }
    assessments {
        string id PK "uuid4"
        int user_id FK "null = anonymous pending"
        string status "needs_followup / complete"
        bool saved
        string input_language
        string display_language
        string level
        string followup_token_hash "SHA-256"
        bytes text_enc "Fernet"
        bytes answers_enc "Fernet"
        bytes result_enc "Fernet"
        float age_years
        datetime created_at
    }
    assessment_stats {
        int id PK
        string day "YYYY-MM-DD"
        string input_language
        string level
        string rule_level
        string ml_level
        bool asked_followup
        string symptom_ids "no user id, no text"
    }
```

## 5. Model workflow

```mermaid
flowchart TB
    A["CDC NHAMCS ED 2016–2022<br/>123,040 visits"] --> B["Keep nurse-triaged visits<br/>84,148"]
    B --> C["Label mapping<br/>Immediate/Emergent → EMERGENCY<br/>Urgent → URGENT · Semi/Non → ROUTINE"]
    C --> D["Features (shared with app)<br/>62 symptom flags, age, pain, n_symptoms<br/>no vitals, no sex"]
    D --> E{"Temporal split"}
    E -- "2016–2021: 61,388 rows" --> F["Stratified 5-fold CV<br/>grid search: DT, depth-6 DT, RF"]
    F --> G["Out-of-fold probabilities<br/>→ thresholds (dev only)"]
    E -- "2022: 8,491 rows (locked)" --> H["Evaluate ONCE"]
    G --> H
    H --> I["Results: DT 0.515 · RF 0.538 macro-F1<br/>App policy: 91.6% emergencies ≥ Urgent"]
    G --> J["Save dt_app_v1.joblib + metadata<br/>(threshold 0.45, capped at URGENT)"]
    J --> K["App: predictor.py<br/>decision path → plain-language reasons"]
```

## 6. Final-level decision logic

```mermaid
flowchart TB
    S["Extraction + answers"] --> R{"Emergency rule fired?"}
    R -- yes --> EM["EMERGENCY<br/>+ 112/108 + cited guidance"]
    R -- no --> U{"Any symptom understood?"}
    U -- no --> UC["URGENT<br/>'we could not understand'"]
    U -- yes --> AG{"Age known?"}
    AG -- no --> UA["max(rule level, URGENT)<br/>'age not provided'"]
    AG -- yes --> M["Decision Tree<br/>URGENT if P(urgent)+P(emergency) ≥ 0.45"]
    M --> FIN["FINAL = max(rule level, model level)"]
    FIN --> OUT["URGENT or ROUTINE<br/>+ safety-net list (+ self-care info if ROUTINE)"]
```
