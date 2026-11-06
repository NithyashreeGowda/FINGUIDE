import { useState } from "react";
import Login from "./pages/Login";
import { OnboardingWizard } from "./components/MyProfile";
import MainApp from "./pages/MainApp";
import { clearToken, fetchProfile, fetchSettings, setToken } from "./api";

export default function App() {
  const [user, setUser] = useState(null);
  const [profileData, setProfileData] = useState(null);

  const syncLocal = (u) => {
    localStorage.setItem("userName", u.name);
    localStorage.setItem("username", u.username);
    localStorage.setItem("email", u.email);
  };

  const applyTheme = (s) => {
    const dark = !!s?.dark_mode;
    document.body.classList.toggle("dark-mode", dark);
    localStorage.setItem("darkMode", dark);
  };

  const handleAuth = async ({ token, user: u }) => {
  setToken(token);
  syncLocal(u);

  const [settings, profile] = await Promise.all([
    fetchSettings().catch(() => null),
    fetchProfile().catch(() => null),
  ]);

  applyTheme(settings);
  setProfileData(profile);
  setUser(u);
};

  const handleSignOut = () => {
    clearToken();
    document.body.classList.remove("dark-mode");
    setUser(null);
    setProfileData(null);
  };

  const handleUserUpdated = (u) => {
    syncLocal(u);
    setUser(u);
  };

  if (!user) return <Login onAuth={handleAuth} />;

  // New user: no profile yet, so show the step-by-step onboarding
  if (!profileData) {
    return <OnboardingWizard user={user} onSaved={setProfileData} />;
  }

  return (
    <MainApp
      user={user}
      profileData={profileData}
      onProfileUpdated={setProfileData}
      onUserUpdated={handleUserUpdated}
      onSignOut={handleSignOut}
    />
  );
}