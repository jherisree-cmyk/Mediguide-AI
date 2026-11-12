import { useCallback, useEffect, useState } from "react";

// Light / dark theme. Only the theme choice is stored in the browser (never health data).
const KEY = "mg_theme";

function initialTheme() {
  if (typeof window === "undefined") return "light";
  const saved = window.localStorage?.getItem(KEY);
  if (saved === "light" || saved === "dark") return saved;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function useTheme() {
  const [theme, setTheme] = useState(initialTheme);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.querySelector('meta[name="color-scheme"]')?.setAttribute("content", theme);
  }, [theme]);
  const toggle = useCallback(() => {
    setTheme((t) => {
      const next = t === "dark" ? "light" : "dark";
      window.localStorage?.setItem(KEY, next);
      return next;
    });
  }, []);
  return { theme, toggle };
}
