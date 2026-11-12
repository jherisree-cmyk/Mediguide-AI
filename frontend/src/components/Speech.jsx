import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

// Browser speech features. Both are progressive enhancements: if the browser does not support
// them, the buttons are simply not shown and typing still works.
export const SPEECH_LANG = { en: "en-IN", te: "te-IN", hi: "hi-IN" };

const getRecognition = () => (typeof window !== "undefined" ? (window.SpeechRecognition || window.webkitSpeechRecognition) : null);

function MicIcon() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
    </svg>
  );
}

function SpeakerIcon() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 9h4l5-4v14l-5-4H4z" /><path d="M16.5 8.5a5 5 0 0 1 0 7M19 6a8.5 8.5 0 0 1 0 12" />
    </svg>
  );
}

/** Microphone button: speech is turned into text and appended to the description. */
export function VoiceInput({ lang, onText }) {
  const { t } = useTranslation();
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const [error, setError] = useState("");
  const recRef = useRef(null);

  useEffect(() => () => recRef.current?.abort?.(), []);
  const Recognition = getRecognition();
  if (!Recognition) return null;

  const start = () => {
    setError("");
    const rec = new Recognition();
    rec.lang = SPEECH_LANG[lang] || "en-IN";
    rec.interimResults = true;
    rec.continuous = true;
    rec.onresult = (e) => {
      let finalText = "", partial = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i];
        if (r.isFinal) finalText += r[0].transcript; else partial += r[0].transcript;
      }
      if (finalText.trim()) onText(finalText.trim());
      setInterim(partial);
    };
    rec.onerror = (e) => { if (e.error !== "aborted" && e.error !== "no-speech") setError(t("assess.voiceError")); };
    rec.onend = () => { setListening(false); setInterim(""); };
    recRef.current = rec;
    try { rec.start(); setListening(true); } catch { setError(t("assess.voiceError")); }
  };
  const stop = () => recRef.current?.stop();

  return (
    <div className="voice">
      <button type="button" className={`btn btn-voice ${listening ? "listening" : ""}`} aria-pressed={listening}
              onClick={listening ? stop : start}>
        <MicIcon /> {listening ? t("assess.voiceStop") : t("assess.voice")}
        {listening && <span className="voice-wave" aria-hidden="true"><i /><i /><i /><i /><i /></span>}
      </button>
      <span className="hint" aria-live="polite">{listening ? (interim || t("assess.listening")) : t("assess.voiceHint")}</span>
      {error && <span className="error small" role="alert">{error}</span>}
    </div>
  );
}

/** Reads the most important part of a result aloud in the result's language. */
export function ReadAloud({ lang, text }) {
  const { t } = useTranslation();
  const synth = typeof window !== "undefined" ? window.speechSynthesis : null;
  const [speaking, setSpeaking] = useState(false);
  const [hasVoice, setHasVoice] = useState(true);

  useEffect(() => {
    if (!synth) return undefined;
    const check = () => {
      const voices = synth.getVoices();
      setHasVoice(voices.length === 0 || voices.some((v) => v.lang?.toLowerCase().startsWith(lang)));
    };
    check();
    synth.addEventListener?.("voiceschanged", check);
    return () => { synth.removeEventListener?.("voiceschanged", check); synth.cancel(); };
  }, [synth, lang]);

  if (!synth || typeof window.SpeechSynthesisUtterance === "undefined") return null;

  const speak = () => {
    synth.cancel();
    const u = new window.SpeechSynthesisUtterance(text);
    u.lang = SPEECH_LANG[lang] || "en-IN";
    const voice = synth.getVoices().find((v) => v.lang?.toLowerCase().startsWith(lang));
    if (voice) u.voice = voice;
    u.rate = 0.95;
    u.onend = u.onerror = () => setSpeaking(false);
    setSpeaking(true);
    synth.speak(u);
  };
  const stop = () => { synth.cancel(); setSpeaking(false); };

  return (
    <span className="read-aloud">
      <button type="button" className="btn" onClick={speaking ? stop : speak} aria-pressed={speaking}>
        <SpeakerIcon /> {speaking ? t("result.stopReading") : t("result.readAloud")}
      </button>
      {!hasVoice && <span className="hint">{t("result.noVoice")}</span>}
    </span>
  );
}
