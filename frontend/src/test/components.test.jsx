import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import QuestionForm, { buildAnswers } from "../components/QuestionForm";
import ResultView from "../components/ResultView";
import UrgencyBadge from "../components/UrgencyBadge";
import { AssessmentProvider } from "../context/AssessmentContext";
import { AuthProvider } from "../context/AuthContext";
import i18n from "../i18n";

const baseResult = {
  status: "complete", level: "ROUTINE", level_text: "Routine: book an appointment", next_step: "Book a doctor visit",
  display_language: "en", notes: [], support: "", symptoms: [{ id: "cough", kind: "symptom", label: "Cough", severity: "mild", duration_days: 2 }],
  denied: ["Fever"], warnings: [], model_path: ["age <= 40", "Cough: yes"], corrections: [],
  safety_net: { title: "Call 112 if:", items: ["breathing becomes difficult"] }, self_care_info: "Rest and drink fluids.",
  emergency_contacts: [], disclaimer: "It does not diagnose diseases.", prototype_notice: "Educational prototype",
};

beforeEach(async () => { await act(() => i18n.changeLanguage("en")); });
afterEach(() => vi.restoreAllMocks());

describe("UrgencyBadge", () => {
  it.each(["EMERGENCY", "URGENT", "ROUTINE"])("shows text and an icon for %s (never colour alone)", (level) => {
    const { container } = render(<UrgencyBadge level={level} />);
    expect(screen.getByRole("status")).toHaveTextContent(i18n.t(`level.${level}`));
    expect(container.querySelector("svg[aria-hidden='true']")).not.toBeNull();
  });
});

describe("ResultView", () => {
  it("emergency result shows a call banner with tap-to-call links and no self-care", () => {
    render(<ResultView result={{ ...baseResult, level: "EMERGENCY", level_text: "Emergency", safety_net: {}, self_care_info: "",
      warnings: [{ rule: "EM_BREATHING", level: "EMERGENCY", title: "Severe difficulty breathing", because_of: ["Shortness of breath"],
        guidance_quote_en: "Call 999...", sources: [{ title: "Shortness of breath", publisher: "NHS", url: "https://www.nhs.uk/x" }] }] }} />);
    const banner = screen.getByRole("region", { name: /emergency help/i });
    expect(within(banner).getByRole("link", { name: /112/ })).toHaveAttribute("href", "tel:112");
    expect(within(banner).getByRole("link", { name: /108/ })).toHaveAttribute("href", "tel:108");
    expect(screen.queryByText("Rest and drink fluids.")).toBeNull();
    expect(screen.getByRole("link", { name: /NHS/ })).toHaveAttribute("href", "https://www.nhs.uk/x");
  });

  it("routine result shows safety-netting, symptoms, denied symptoms, tree path and disclaimer", () => {
    const { container } = render(<ResultView result={baseResult} />);
    expect(screen.queryByRole("region", { name: /emergency help/i })).toBeNull();
    expect(screen.getByText("breathing becomes difficult")).toBeInTheDocument();
    expect(container.querySelector(".symptom-list")).toHaveTextContent(/Cough.*mild.*2 days/);
    expect(screen.getByText("Fever")).toBeInTheDocument();
    expect(screen.getByText("Cough: yes")).toBeInTheDocument();
    expect(screen.getByText(/does not diagnose/)).toBeInTheDocument();
  });
});

describe("QuestionForm", () => {
  const questions = [
    { id: "checklist", kind: "multi", text: { en: "Any of these?" }, options: [
      { value: "sweating", text: { en: "Sweating" } }, { value: "nausea", text: { en: "Nausea" } }, { value: "none", text: { en: "None of these" } }] },
    { id: "pain", kind: "number", text: { en: "Pain 0-10?" }, options: [], min: 0, max: 10 },
    { id: "onset:chest_pain", kind: "choice", text: { en: "Sudden?" }, options: [
      { value: "sudden", text: { en: "Suddenly" } }, { value: "gradual", text: { en: "Gradually" } }] },
  ];

  it("builds the answers object the backend expects", () => {
    expect(buildAnswers(questions, { checklist: ["sweating"], pain: "7.4", "onset:chest_pain": "sudden" }))
      .toEqual({ checklist: ["sweating"], pain: 7, "onset:chest_pain": "sudden" });
    expect(buildAnswers(questions, {})).toEqual({ checklist: [] });   // blanks are allowed
  });

  it("'None of these' is exclusive", async () => {
    const onSubmit = vi.fn();
    render(<QuestionForm questions={questions} lang="en" onSubmit={onSubmit} />);
    const user = userEvent.setup();
    await user.click(screen.getByLabelText("Sweating"));
    await user.click(screen.getByLabelText("None of these"));
    expect(screen.getByLabelText("Sweating")).not.toBeChecked();
    await user.click(screen.getByLabelText("Nausea"));
    expect(screen.getByLabelText("None of these")).not.toBeChecked();
    await user.click(screen.getByLabelText("Suddenly"));
    await user.click(screen.getByRole("button", { name: /result/i }));
    expect(onSubmit).toHaveBeenCalledWith({ checklist: ["nausea"], "onset:chest_pain": "sudden" });
  });
});

// ---- full app with a mocked backend ---------------------------------------------------------
function mockBackend(handlers) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (url, opts = {}) => {
    const key = `${opts.method || "GET"} ${url}`;
    const h = handlers[key] || handlers[url];
    if (!h) return new Response(JSON.stringify({ detail: "Please log in" }), { status: 401 });
    const body = typeof h === "function" ? h(JSON.parse(opts.body || "null")) : h;
    return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
  });
}

function renderApp(path = "/") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider><AssessmentProvider><App /></AssessmentProvider></AuthProvider>
    </MemoryRouter>,
  );
}

describe("App", () => {
  it("switches the interface language to Telugu", async () => {
    mockBackend({});
    renderApp("/");
    await userEvent.setup().click(screen.getByRole("button", { name: "తెలుగు" }));
    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent("మీ లక్షణాలను");
    expect(document.documentElement.lang).toBe("te");
  });

  it("text -> follow-up questions -> result, sending the follow-up token", async () => {
    const answerSpy = vi.fn(() => ({ ...baseResult, level: "URGENT", level_text: "Urgent: today", saved: false }));
    mockBackend({
      "POST /api/assess": (body) => ({
        id: "abc", followup_token: "tok", status: "needs_followup", saved: false, display_language: body.display_lang,
        preliminary_level: "URGENT", symptoms: [{ id: "chest_pain", kind: "symptom", label: "Chest pain" }], denied: [],
        questions: [{ id: "pain", kind: "number", text: { en: "Pain 0-10?" }, options: [], min: 0, max: 10 }],
      }),
      "POST /api/assess/abc/answers": answerSpy,
    });
    renderApp("/assess");
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/What are you feeling/), "I have chest pain");
    await user.click(screen.getByRole("button", { name: "Check urgency" }));
    expect(await screen.findByText("Chest pain")).toBeInTheDocument();     // symptom confirmation
    await user.type(screen.getByLabelText("Pain 0-10?"), "4");
    await user.click(screen.getByRole("button", { name: /See my result/ }));
    expect(await screen.findByText("Urgent: today")).toBeInTheDocument();
    expect(answerSpy).toHaveBeenCalledWith({ answers: { pain: 4 }, followup_token: "tok" });
  });

  it("protected pages redirect to login when not logged in", async () => {
    mockBackend({});
    renderApp("/history");
    expect(await screen.findByRole("heading", { name: "Log in" })).toBeInTheDocument();
  });

  it("does not store health data in browser storage", async () => {
    mockBackend({ "POST /api/assess": { ...baseResult, id: null, saved: false } });
    renderApp("/assess");
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/What are you feeling/), "runny nose secret-xyz");
    await user.click(screen.getByRole("button", { name: "Check urgency" }));
    await screen.findByText("Book a doctor visit");
    const stored = JSON.stringify({ ...localStorage }) + JSON.stringify({ ...sessionStorage });
    expect(stored).not.toContain("secret-xyz");
  });
});

describe("Admin dashboard", () => {
  const per = { precision: 0.5, recall: 0.6, "f1-score": 0.55, support: 100 };
  const metrics = { accuracy: 0.55, macro_f1: 0.47, emergency_to_at_least_urgent: 0.916, under_triage_rate: 0.19,
                    per_class: { ROUTINE: per, URGENT: per, EMERGENCY: per } };
  const stats = {
    total_assessments: 12, followup_rate: 0.5, levels: { EMERGENCY: 6, URGENT: "<5", ROUTINE: 5 },
    languages: { en: 8, te: "<5" }, top_symptoms: [{ id: "fever", label: "Fever", count: 7 }],
    daily_last_30_days: { "2026-11-10": 5, "2026-11-11": 7 }, rule_vs_model: { "rule=none / model=ROUTINE": 5 },
    model: { version: "v1", trained: "2026-11-10", status: "EDUCATIONAL PROTOTYPE - not clinically validated",
             thresholds: { t_emergency: 0.2, t_urgent_or_higher: 0.45 }, test_2022_app_policy: metrics, test_2022_random_forest: metrics },
    privacy_note: "Aggregated anonymous data only; groups smaller than 5 are suppressed.",
  };

  it("shows tiles, labelled charts, suppressed small groups, table views and the validation warning", async () => {
    mockBackend({ "/api/auth/me": { id: 1, email: "a@b.co", is_admin: true, language: "en" }, "/api/admin/stats": stats });
    renderApp("/admin");
    expect(await screen.findByText("Completed assessments")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    const urgency = screen.getByRole("img", { name: "Urgency recommendations" });
    expect(within(urgency).getAllByText("<5").length).toBeGreaterThan(0);          // small group suppressed
    expect(within(urgency).getByText("Emergency")).toBeInTheDocument();           // text label, not colour only
    expect(screen.getAllByText("Show as table").length).toBe(5);
    expect(screen.getAllByText(/not clinically validated/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/91.6%/).length).toBe(2);
  });

  it("non-admin users are redirected away", async () => {
    mockBackend({ "/api/auth/me": { id: 2, email: "u@b.co", is_admin: false, language: "en" } });
    renderApp("/admin");
    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent("Describe your symptoms");
  });
});
