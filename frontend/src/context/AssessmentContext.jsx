import { createContext, useContext, useState } from "react";

// Holds the CURRENT assessment in memory only (never localStorage): closing the tab clears it.
const AssessmentContext = createContext(null);

export function AssessmentProvider({ children }) {
  const [current, setCurrent] = useState(null); // backend response (questions or final result)
  const [draft, setDraft] = useState({ text: "", age: "", lang: "", save: false });
  return (
    <AssessmentContext.Provider value={{ current, setCurrent, draft, setDraft }}>
      {children}
    </AssessmentContext.Provider>
  );
}

export const useAssessment = () => useContext(AssessmentContext);
