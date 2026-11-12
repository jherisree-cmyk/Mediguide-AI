import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";
import hi from "./locales/hi.json";
import te from "./locales/te.json";

export const LANGUAGES = [
  { code: "en", name: "English" },
  { code: "te", name: "తెలుగు" },
  { code: "hi", name: "हिंदी" },
];

// Only the chosen UI language is remembered (no health data in browser storage).
const saved = typeof localStorage !== "undefined" ? localStorage.getItem("mg_lang") : null;

i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, te: { translation: te }, hi: { translation: hi } },
  lng: saved || "en",
  fallbackLng: "en",
  interpolation: { escapeValue: false }, // React already escapes output
  returnObjects: true,
});

i18n.on("languageChanged", (lng) => {
  if (typeof document !== "undefined") document.documentElement.lang = lng;
  if (typeof localStorage !== "undefined") localStorage.setItem("mg_lang", lng);
});

export default i18n;
