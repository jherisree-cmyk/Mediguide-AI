// Phase 12 features: live detection, voice input, care actions / doctor summary, dark mode.
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import CareActions, { buildSummary } from "../components/CareActions";
import { VoiceInput } from "../components/Speech";
import { AssessmentProvider } from "../context/AssessmentContext";
import { AuthProvider } from "../context/AuthContext";
import i18n from "../i18n";

const result = {
  status: "complete", level: "URGENT", level_text: "Urgent: see a doctor today", next_step: "See a doctor today",
  display_language: "en", symptoms: [{ id: "headache", kind: "symptom", label: "Headache", severity: "severe", duration_days: 2 }],
  denied: ["Fever"], warnings: [{ rule: "UR_X", level: "URGENT", title: "Severe headache", because_of: ["Headache"],
    guidance_quote_en: "...", sources: [{ publisher: "NHS", title: "Headaches", url: "https://www.nhs.uk/h" }] }],
  model_path: ["age > 40"], safety_net: { title: "Call 112 if:", items: ["you get a stiff neck"] },
  disclaimer: "It does not diagnose diseases.",
};

function mockBackend(handlers) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (url, opts = {}) => {
    const h = handlers[`${opts.method || "GET"} ${url}`];
    if (!h) return new Response(JSON.stringify({ detail: "Please log in" }), { status: 401 });
    const body = typeof h === "function" ? h(JSON.parse(opts.body || "null")) : h;
    return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
  });
}
const renderApp = (path) => render(
  <MemoryRouter initialEntries={[path]}><AuthProvider><AssessmentProvider><App /></AssessmentProvider></AuthProvider></MemoryRouter>);

beforeEach(async () => { await act(() => i18n.changeLanguage("en")); });
afterEach(() => { vi.restoreAllMocks(); delete window.SpeechRecognition; });

describe("Live symptom detection", () => {
  it("shows recognised and negated symptoms while typing, and an emergency alert", async () => {
    const preview = vi.fn((body) => body.text.includes("breathe")
      ? { input_language: "en", detected_language: "en", symptoms: [{ id: "sob", kind: "symptom", label: "Shortness of breath" }], denied: [], emergency_sign: true }
      : { input_language: "en", detected_language: "en", symptoms: [{ id: "headache", kind: "symptom", label: "Headache" }],
          denied: [{ id: "fever", label: "Fever" }], emergency_sign: false });
    mockBackend({ "POST /api/assess/preview": preview });
    renderApp("/assess");
    const user = userEvent.setup();
    const box = screen.getByLabelText(/What are you feeling/);
    await user.type(box, "headache, no fever");
    const live = await screen.findByRole("region", { name: /Recognised so far/ });
    expect(await within(live).findByText("Headache")).toBeInTheDocument();
    expect(within(live).getByText("Fever").tagName).toBe("S");          // struck through
    expect(within(live).getByText(/not present/)).toBeInTheDocument();  // and said in words
    expect(within(live).queryByRole("alert")).toBeNull();
    expect(preview).toHaveBeenLastCalledWith(expect.objectContaining({ text: "headache, no fever", display_lang: "en" }));

    await user.clear(box);
    await user.type(box, "I can't breathe");
    expect(await screen.findByRole("alert")).toHaveTextContent(/Emergency warning sign/);
  });
});

describe("Voice input", () => {
  it("is hidden when the browser has no speech recognition", () => {
    render(<VoiceInput lang="en" onText={() => {}} />);
    expect(screen.queryByRole("button", { name: /Speak/ })).toBeNull();
  });

  it("listens in the chosen language and passes the final words on", async () => {
    let instance;
    window.SpeechRecognition = class {
      constructor() { instance = this; }
      start() {} stop() { this.onend?.(); } abort() {}
    };
    const onText = vi.fn();
    render(<VoiceInput lang="te" onText={onText} />);
    await userEvent.setup().click(screen.getByRole("button", { name: /Speak/ }));
    expect(instance.lang).toBe("te-IN");
    expect(screen.getByRole("button", { name: /Stop listening/ })).toHaveAttribute("aria-pressed", "true");
    act(() => instance.onresult({ resultIndex: 0, results: [Object.assign([{ transcript: " జ్వరం ఉంది " }], { isFinal: true })] }));
    expect(onText).toHaveBeenCalledWith("జ్వరం ఉంది");
  });
});

describe("Care actions", () => {
  it("links to hospitals near the user for urgent results and clinics for routine ones", () => {
    const { rerender } = render(<CareActions result={result} />);
    expect(screen.getByRole("link", { name: /hospital near me/ }).getAttribute("href")).toContain("hospital%20near%20me");
    rerender(<CareActions result={{ ...result, level: "ROUTINE" }} />);
    expect(screen.getByRole("link", { name: /clinic near me/ }).getAttribute("href")).toContain("clinic%20near%20me");
  });

  it("doctor summary contains the level, own words, symptom details, denials, sources and disclaimer", () => {
    const text = buildSummary(i18n.t.bind(i18n), result, "bad headache, no fever", new Date(2026, 10, 11));
    for (const part of ["Urgent", "See a doctor today", "\"bad headache, no fever\"", "Headache (severe, 2 days)",
                        "Fever", "NHS (https://www.nhs.uk/h)", "age > 40", "not a diagnosis", "does not diagnose"]) {
      expect(text).toContain(part);
    }
  });
});

describe("Dark mode", () => {
  it("toggles the theme and remembers only the theme choice", async () => {
    mockBackend({});
    renderApp("/");
    document.documentElement.dataset.theme = "light";
    const button = screen.getByRole("button", { name: "Dark mode" });
    await userEvent.setup().click(button);
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(localStorage.getItem("mg_theme")).toBe("dark");
    expect(button).toHaveAttribute("aria-pressed", "true");
    await userEvent.setup().click(button);
    expect(document.documentElement.dataset.theme).toBe("light");
  });
});
