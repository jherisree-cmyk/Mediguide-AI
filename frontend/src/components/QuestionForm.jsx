import { useState } from "react";
import { useTranslation } from "react-i18next";

/**
 * Renders the backend's follow-up questions and builds the answers object:
 *   number -> number | null          choice / yesno -> option value
 *   multi  -> [values]  ("none" is exclusive: choosing it clears the others and vice versa)
 * Every question may be left blank; the backend then stays conservative.
 */
export function buildAnswers(questions, values) {
  const answers = {};
  for (const q of questions) {
    const v = values[q.id];
    if (q.kind === "multi") {
      answers[q.id] = v && v.length ? v : [];
    } else if (q.kind === "number") {
      if (v !== undefined && v !== "") {
        const n = Number(v);
        if (!Number.isNaN(n)) answers[q.id] = q.id === "pain" ? Math.round(n) : n;
      }
    } else if (v) {
      answers[q.id] = v;
    }
  }
  return answers;
}

export default function QuestionForm({ questions, lang, onSubmit, busy }) {
  const { t } = useTranslation();
  const [values, setValues] = useState({});
  const set = (id, v) => setValues((old) => ({ ...old, [id]: v }));

  const toggle = (id, value) => {
    const cur = values[id] || [];
    if (value === "none") return set(id, cur.includes("none") ? [] : ["none"]);
    const without = cur.filter((x) => x !== "none");
    set(id, without.includes(value) ? without.filter((x) => x !== value) : [...without, value]);
  };

  const submit = (e) => {
    e.preventDefault();
    onSubmit(buildAnswers(questions, values));
  };

  return (
    <form onSubmit={submit} className="question-form" noValidate>
      {questions.map((q) => (
        <fieldset key={q.id} className="question">
          <legend>{q.text[lang] || q.text.en}</legend>
          {q.kind === "multi" && (
            <>
              {/* the question text from the backend already says "select all that apply" */}
              <div className="options">
                {q.options.map((o) => (
                  <label key={o.value} className="option">
                    <input type="checkbox" checked={(values[q.id] || []).includes(o.value)}
                           onChange={() => toggle(q.id, o.value)} />
                    <span>{o.text[lang] || o.text.en}</span>
                  </label>
                ))}
              </div>
            </>
          )}
          {(q.kind === "choice" || q.kind === "yesno") && (
            <div className="options options-inline">
              {q.options.map((o) => (
                <label key={o.value} className="option">
                  <input type="radio" name={q.id} value={o.value} checked={values[q.id] === o.value}
                         onChange={() => set(q.id, o.value)} />
                  <span>{o.text[lang] || o.text.en}</span>
                </label>
              ))}
            </div>
          )}
          {q.kind === "number" && (
            <label className="number-input">
              <input type="number" inputMode="decimal" min={q.min ?? undefined} max={q.max ?? undefined}
                     step={q.id === "pain" ? 1 : "any"} value={values[q.id] ?? ""} aria-label={q.text[lang] || q.text.en}
                     onChange={(e) => set(q.id, e.target.value)} />
              <span>{q.id === "pain" ? t("followup.painUnit") : t("followup.yearsUnit")}</span>
            </label>
          )}
        </fieldset>
      ))}
      <p className="hint">{t("followup.optional")}</p>
      <button type="submit" className="btn btn-primary" disabled={busy}>
        {busy ? t("assess.checking") : t("followup.submit")}
      </button>
    </form>
  );
}
