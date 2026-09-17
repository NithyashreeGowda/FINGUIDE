import { useState } from "react";
import Login from "./pages/Login";
import MainApp from "./pages/MainApp";

export default function App() {
  const [loggedIn, setLoggedIn] = useState(false);

  if (!loggedIn) {
    return <Login onLogin={() => setLoggedIn(true)} />;
  }

  return <MainApp />;
}