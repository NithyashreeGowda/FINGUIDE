import { useState } from "react";

import {
  MessageSquare,
  History as HistoryIcon,
  Settings as SettingsIcon,
  LogOut,
  Newspaper,
  TrendingUp,
  Menu,
} from "lucide-react";

import Assistant from "../components/Assistant";
import History from "../components/History";
import Settings from "../components/Settings";
import MarketNews from "../pages/MarketNews";
import MarketInsights from "../pages/MarketInsights";
import Finn from "../components/Finn";
const NAV_ITEMS = [
  { id: "assistant", label: "Assistant", icon: MessageSquare },
  { id: "history", label: "History", icon: HistoryIcon },
  { id: "market-insights", label: "Market Insights", icon: TrendingUp },
  { id: "market-news", label: "Market News", icon: Newspaper },
];


export default function MainApp({
  user,
  profileData,
  onProfileUpdated,
  onUserUpdated,
  onSignOut,
}) {
  const [activeTab, setActiveTab] = useState("assistant");
  const [settingsModal, setSettingsModal] = useState(null);
  const [openConvId, setOpenConvId] = useState(null);

  const [sidebarOpen, setSidebarOpen] = useState(() => {
    try { return localStorage.getItem("fg_sidebar") !== "closed"; } catch { return true; }
  });

  const toggleSidebar = () => {
    setSidebarOpen((open) => {
      try { localStorage.setItem("fg_sidebar", open ? "closed" : "open"); } catch {}
      return !open;
    });
  };

  const openSettings = (modal = null) => {
    setSettingsModal(modal);
    setActiveTab("settings");
  };

  const handleSignOut = () => {
    document.body.classList.remove("dark-mode");
    onSignOut();
  };

  return (
    <div className={`app-shell ${sidebarOpen ? "" : "sidebar-collapsed"}`}>
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-name">FinGuide</div>
          <div className="brand-sub">Personal Financial Assistant</div>
          <button
            type="button"
            className="sidebar-toggle"
            onClick={toggleSidebar}
            aria-label="Close sidebar"
            aria-expanded="true"
          >
            <Menu size={18} />
          </button>
        </div>

        <nav className="sidebar-nav">
          {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              className={`nav-item ${activeTab === id ? "active" : ""}`}
              onClick={() => {
                setOpenConvId(null);
                setActiveTab(id);
              }}
            >
              <Icon size={17} />
              <span>{label}</span>
            </button>
          ))}
        </nav>
        
        <Finn
          tab={activeTab}
          userName={user.name.trim().split(" ")[0]}
          onNavigate={(id) => {
            setOpenConvId(null);
            setActiveTab(id);
          }}
        />

        <div className="sidebar-footer">
          <div className="sidebar-user">
            <div className="sidebar-avatar">
              {user.name.trim().charAt(0).toUpperCase()}
            </div>
            <div className="sidebar-user-text">
              <div className="sidebar-user-name">{user.name}</div>
              <div className="sidebar-user-sub">{user.email}</div>
            </div>
          </div>

          <button
            type="button"
            className={`nav-item ${activeTab === "settings" ? "active" : ""}`}
            onClick={() => openSettings(null)}
          >
            <SettingsIcon size={17} />
            <span>Settings</span>
          </button>

          <button type="button" className="nav-item logout-button" onClick={handleSignOut}>
            <LogOut size={17} />
            <span>Log Out</span>
          </button>
        </div>
      </aside>

      <div className="main-column">
        {!sidebarOpen && (
          <button
            type="button"
            className="sidebar-toggle sidebar-toggle-floating"
            onClick={toggleSidebar}
            aria-label="Open sidebar"
            aria-expanded="false"
          >
            <Menu size={18} />
          </button>
        )}

        <main className="content-area fade-in" key={`${activeTab}-${settingsModal}-${openConvId}`}>
          {activeTab === "assistant" && (
            <Assistant
              user={user}
              profileData={profileData}
              onProfileUpdated={onProfileUpdated}
              openConvId={openConvId}
            />
          )}

          {activeTab === "history" && (
            <History
              onOpenChat={(id) => {
                setOpenConvId(id);
                setActiveTab("assistant");
              }}
              onStartChat={() => {
                setOpenConvId(null);
                setActiveTab("assistant");
              }}
            />
          )}
          {activeTab === "market-insights" && <MarketInsights />}
          {activeTab === "market-news" && <MarketNews />}

          {activeTab === "settings" && (
            <Settings
              user={user}
              initialModal={settingsModal}
              onUserUpdated={onUserUpdated}
              onSignOut={handleSignOut}
            />
          )}
        </main>
      </div>
    </div>
  );
}