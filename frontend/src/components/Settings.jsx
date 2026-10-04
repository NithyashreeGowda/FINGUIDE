import { useEffect, useRef, useState } from "react";
import {
  User,
  Lock,
  Moon,
  LogOut,
  ChevronRight,
  X,
} from "lucide-react";
import { changePassword, saveSettings, updateMe } from "../api";

export default function Settings({
  user,
  initialModal = null,
  onUserUpdated,
  onSignOut,
}) {
  const [activeModal, setActiveModal] = useState(initialModal);
  const [notice, setNotice] = useState(null);

  const [darkMode, setDarkMode] = useState(
    localStorage.getItem("darkMode") === "true"
  );

  const [account, setAccount] = useState({
    name: user?.name || "",
    username: user?.username || "",
    email: user?.email || "",
  });

  const [passwords, setPasswords] = useState({
    current: "",
    newPassword: "",
    confirm: "",
  });

  const showNotice = (type, text) => {
    setNotice({ type, text });
    setTimeout(() => setNotice(null), 3000);
  };

  // Apply dark mode, and save it to the database when the user toggles it
  const firstRun = useRef(true);
  useEffect(() => {
    document.body.classList.toggle("dark-mode", darkMode);
    localStorage.setItem("darkMode", darkMode);
    if (firstRun.current) {
      firstRun.current = false;
      return;
    }
    saveSettings({ dark_mode: darkMode }).catch(() => {});
  }, [darkMode]);

  const handleAccountSave = async () => {
    try {
      const updated = await updateMe({
        name: account.name,
        username: account.username,
        email: account.email,
      });
      localStorage.setItem("userName", updated.name);
      localStorage.setItem("username", updated.username);
      localStorage.setItem("email", updated.email);
      onUserUpdated?.(updated);
      setActiveModal(null);
      showNotice("success", "Profile updated successfully.");
    } catch (e) {
      showNotice("error", e.message);
    }
  };

  const handlePasswordSave = async () => {
    if (!passwords.current || !passwords.newPassword || !passwords.confirm) {
      showNotice("error", "Please fill in all password fields.");
      return;
    }

    if (passwords.newPassword !== passwords.confirm) {
      showNotice("error", "New passwords do not match.");
      return;
    }

    try {
      await changePassword({
        current_password: passwords.current,
        new_password: passwords.newPassword,
      });
    } catch (e) {
      showNotice("error", e.message);
      return;
    }

    setPasswords({ current: "", newPassword: "", confirm: "" });
    setActiveModal(null);
    showNotice("success", "Password changed successfully.");
  };

  return (
    <div className="settings-page">

      {notice && <div className={`st-notice ${notice.type}`}>{notice.text}</div>}

      {/* HEADER */}
      <div className="settings-header">
        <h1>Settings</h1>
        <p>
          Manage your account and FinGuide preferences.
        </p>
      </div>


      {/* ACCOUNT */}
      <div className="settings-card">

        <div className="settings-card-title">
          Account
        </div>

        <button
          className="settings-row settings-row-button"
          onClick={() => setActiveModal("account")}
        >
          <div className="settings-row-icon">
            <User size={17} />
          </div>

          <div className="settings-row-content">
            <div className="settings-row-title">
              Profile Information
            </div>

            <div className="settings-row-description">
              Edit your name, username, and email
            </div>
          </div>

          <ChevronRight
            size={18}
            className="settings-arrow"
          />
        </button>


        <button
          className="settings-row settings-row-button"
          onClick={() => setActiveModal("password")}
        >
          <div className="settings-row-icon">
            <Lock size={17} />
          </div>

          <div className="settings-row-content">
            <div className="settings-row-title">
              Password
            </div>

            <div className="settings-row-description">
              Change your account password
            </div>
          </div>

          <ChevronRight
            size={18}
            className="settings-arrow"
          />
        </button>

      </div>


      {/* APPEARANCE */}
      <div className="settings-card">

        <div className="settings-card-title">
          Appearance
        </div>

        <div className="settings-row">

          <div className="settings-row-icon">
            <Moon size={17} />
          </div>

          <div className="settings-row-content">
            <div className="settings-row-title">
              Dark Mode
            </div>

            <div className="settings-row-description">
              Change the appearance of FinGuide
            </div>
          </div>

          <label className="settings-switch">

            <input
              type="checkbox"
              checked={darkMode}
              onChange={(e) =>
                setDarkMode(e.target.checked)
              }
            />

            <span className="settings-slider"></span>

          </label>

        </div>

      </div>


      {/* SESSION */}
      <div className="settings-card settings-actions-card">

        <div className="settings-card-title">
          Session
        </div>

        <button
          className="settings-signout"
          onClick={onSignOut}
        >
          <LogOut size={17} />

          <div>
            <div className="settings-row-title">
              Sign Out
            </div>

            <div className="settings-row-description">
              Sign out of your FinGuide account
            </div>
          </div>
        </button>

      </div>


      {/* ACCOUNT MODAL */}
      {activeModal === "account" && (
        <div className="settings-modal-overlay">

          <div className="settings-modal">

            <div className="settings-modal-header">
              <div>
                <h2>Profile Information</h2>
                <p>
                  Update your account information.
                </p>
              </div>

              <button
                className="settings-modal-close"
                onClick={() => setActiveModal(null)}
              >
                <X size={18} />
              </button>
            </div>


            <div className="settings-form">

              <label>
                Name
                <input
                  type="text"
                  value={account.name}
                  onChange={(e) =>
                    setAccount({
                      ...account,
                      name: e.target.value,
                    })
                  }
                  placeholder="Your name"
                />
              </label>


              <label>
                Username
                <input
                  type="text"
                  value={account.username}
                  onChange={(e) =>
                    setAccount({
                      ...account,
                      username: e.target.value,
                    })
                  }
                  placeholder="Username"
                />
              </label>


              <label>
                Email
                <input type="email" value={account.email} disabled />
                <span className="settings-hint">Email can't be changed.</span>
              </label>

            </div>


            <div className="settings-modal-actions">

              <button
                className="settings-cancel-btn"
                onClick={() => setActiveModal(null)}
              >
                Cancel
              </button>

              <button
                className="settings-save-btn"
                onClick={handleAccountSave}
              >
                Save Changes
              </button>

            </div>

          </div>

        </div>
      )}


      {/* PASSWORD MODAL */}
      {activeModal === "password" && (
        <div className="settings-modal-overlay">

          <div className="settings-modal">

            <div className="settings-modal-header">

              <div>
                <h2>Change Password</h2>

                <p>
                  Update your FinGuide account password.
                </p>
              </div>

              <button
                className="settings-modal-close"
                onClick={() => setActiveModal(null)}
              >
                <X size={18} />
              </button>

            </div>


            <div className="settings-form">

              <label>
                Current Password
                <input
                  type="password"
                  value={passwords.current}
                  onChange={(e) =>
                    setPasswords({
                      ...passwords,
                      current: e.target.value,
                    })
                  }
                  placeholder="Current password"
                />
              </label>


              <label>
                New Password
                <input
                  type="password"
                  value={passwords.newPassword}
                  onChange={(e) =>
                    setPasswords({
                      ...passwords,
                      newPassword: e.target.value,
                    })
                  }
                  placeholder="New password"
                />
              </label>


              <label>
                Confirm New Password
                <input
                  type="password"
                  value={passwords.confirm}
                  onChange={(e) =>
                    setPasswords({
                      ...passwords,
                      confirm: e.target.value,
                    })
                  }
                  placeholder="Confirm new password"
                />
              </label>

            </div>


            <div className="settings-modal-actions">

              <button
                className="settings-cancel-btn"
                onClick={() => setActiveModal(null)}
              >
                Cancel
              </button>

              <button
                className="settings-save-btn"
                onClick={handlePasswordSave}
              >
                Update Password
              </button>

            </div>

          </div>

        </div>
      )}

    </div>
  );
}