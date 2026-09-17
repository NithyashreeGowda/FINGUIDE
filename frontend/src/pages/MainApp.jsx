import { useState } from "react";

import {
  LayoutDashboard,
  User,
  MessageSquare,
  History as HistoryIcon,
  Settings as SettingsIcon,
  LogOut,
} from "lucide-react";

import Overview from "../components/Overview";
import MyProfile from "../components/MyProfile";
import Assistant from "../components/Assistant";
import History from "../components/History";
import Settings from "../components/Settings";

const NAV_ITEMS = [
  {
    id: "assistant",
    label: "Assistant",
    icon: MessageSquare,
  },
  {
    id: "profile",
    label: "Financial Profile",
    icon: User,
  },
  {
    id: "overview",
    label: "Overview",
    icon: LayoutDashboard,
  },
  {
    id: "history",
    label: "History",
    icon: HistoryIcon,
  },
];

export default function MainApp({ onSignOut }) {
  const [activeTab, setActiveTab] = useState("assistant");

  /* =========================================================
     CHANGE PAGE
  ========================================================= */

  const changeTab = (tab) => {
    setActiveTab(tab);
  };

  /* =========================================================
     SIGN OUT
  ========================================================= */

  const handleSignOut = () => {
    /*
      If App.jsx controls authentication,
      use the function passed from App.jsx.
    */
    if (onSignOut) {
      onSignOut();
      return;
    }

    /*
      Fallback cleanup if MainApp is being used
      without an authentication callback.
    */
    localStorage.removeItem("isLoggedIn");
    localStorage.removeItem("loggedIn");
    localStorage.removeItem("user");
    localStorage.removeItem("profile");
    localStorage.removeItem("userName");
    localStorage.removeItem("username");
    localStorage.removeItem("email");

    document.body.classList.remove("dark-mode");

    window.location.href = "/login";
  };

  return (
    <div className="app-shell">

      {/* =====================================================
          SIDEBAR
      ===================================================== */}

      <aside className="sidebar">

        {/* BRAND */}
        <div className="sidebar-brand">
          <div className="brand-name">
            FinGuide
          </div>

          <div className="brand-sub">
            Personal Financial Assistant
          </div>
        </div>

        {/* NAVIGATION */}
        <nav className="sidebar-nav">

          {NAV_ITEMS.map(
            ({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                className={`nav-item ${
                  activeTab === id ? "active" : ""
                }`}
                onClick={() => changeTab(id)}
              >
                <Icon size={17} />
                <span>{label}</span>
              </button>
            )
          )}

        </nav>

        {/* SIDEBAR FOOTER */}
        <div className="sidebar-footer">

          {/* SETTINGS */}
          <button
            type="button"
            className={`nav-item ${
              activeTab === "settings"
                ? "active"
                : ""
            }`}
            onClick={() => changeTab("settings")}
          >
            <SettingsIcon size={17} />
            <span>Settings</span>
          </button>

          {/* LOG OUT */}
          <button
            type="button"
            className="nav-item logout-button"
            onClick={handleSignOut}
          >
            <LogOut size={17} />
            <span>Log Out</span>
          </button>

        </div>

      </aside>

      {/* =====================================================
          MAIN COLUMN
      ===================================================== */}

      <div className="main-column">

        {/* ===================================================
            PAGE CONTENT
        =================================================== */}

        <main
          className="content-area fade-in"
          key={activeTab}
        >

          {/* OVERVIEW */}
          {activeTab === "overview" && (
            <Overview />
          )}

          {/* FINANCIAL PROFILE */}
          {activeTab === "profile" && (
            <MyProfile
              onProfileSaved={() =>
                setActiveTab("assistant")
              }
            />
          )}

          {/* ASSISTANT */}
          {activeTab === "assistant" && (
            <Assistant />
          )}

          {/* HISTORY */}
          {activeTab === "history" && (
            <History />
          )}

          {/* SETTINGS */}
          {activeTab === "settings" && (
            <Settings
              onSignOut={handleSignOut}
            />
          )}

        </main>

      </div>

    </div>
  );
}