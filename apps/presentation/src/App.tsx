import React from "react";
import { DeckShell } from "./components/DeckShell";
import { SLIDES } from "./slides";

export const App: React.FC = () => {
  return <DeckShell slides={SLIDES} />;
};

export default App;
