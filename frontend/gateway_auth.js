let currentUser = null;
let pendingPostLoginAction = null;
let loginBound = false;
let logoutBound = false;

/*** TOKEN MANAGEMENT ***/

function getToken() {
  return localStorage.getItem("gateway_jwt");
}

function saveToken(token) {
  localStorage.setItem("gateway_jwt", token);
}

function clearToken() {
  localStorage.removeItem("gateway_jwt");
}

function isAuthenticated() {
  return Boolean(currentUser);
}

function parseJwtPayload(token) {
  try {
    const base64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(base64));
  } catch {
    return null;
  }
}

function isTokenExpired(token) {
  const payload = parseJwtPayload(token);
  if (!payload || !payload.exp) return true;
  return Date.now() / 1000 > payload.exp - 10;
}

export function authHeaders() {
  const token = getToken();
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };
}

/*** AUTHENTICATION UI ***/

function refreshAuthUi() {
  const isAuth = isAuthenticated();

  const aiOverlay = document.getElementById("ai-auth-overlay");
  if (aiOverlay) {
    aiOverlay.classList.toggle("active", !isAuth);
    aiOverlay.setAttribute("aria-hidden", isAuth ? "true" : "false");
  }

  const loginSection = document.getElementById("login-section");
  if (loginSection) {
    loginSection.setAttribute(
      "aria-hidden",
      loginSection.classList.contains("active") ? "false" : "true",
    );
  }

  const loginBtn = document.getElementById("open-login-btn");
  const userProfile = document.getElementById("user-profile-section");
  const headerUsername = document.getElementById("header-username");

  if (loginBtn && userProfile) {
    if (isAuth) {
      loginBtn.style.display = "none";
      userProfile.style.display = "flex";
      if (headerUsername && currentUser) {
        headerUsername.textContent = currentUser.username;
      }
    } else {
      loginBtn.style.display = "inline-block";
      userProfile.style.display = "none";
      if (headerUsername) headerUsername.textContent = "";
    }
  }
}

function setAuthView(view) {
  const loginForm = document.getElementById("login-form");
  const registerPanel = document.getElementById("register-panel");
  const loginTab = document.getElementById("tab-login");
  const registerTab = document.getElementById("tab-register");

  const isRegister = view === "register";

  if (loginForm) loginForm.classList.toggle("active", !isRegister);
  if (registerPanel) registerPanel.classList.toggle("active", isRegister);
  if (loginTab) loginTab.classList.toggle("active", !isRegister);
  if (registerTab) registerTab.classList.toggle("active", isRegister);
}

function showLoginModal(options = {}) {
  if (typeof options.afterLoginAction === "function") {
    pendingPostLoginAction = options.afterLoginAction;
  }

  const loginSection = document.getElementById("login-section");
  const loginError = document.getElementById("login-error");
  if (loginError) {
    loginError.textContent = "";
    loginError.style.display = "none";
  }
  if (loginSection) loginSection.classList.add("active");
  setAuthView("login");
  refreshAuthUi();
}

function hideLoginModal() {
  const loginSection = document.getElementById("login-section");
  if (loginSection) loginSection.classList.remove("active");
  refreshAuthUi();
}

function showRegisterModal() {
  showLoginModal();
  const regError = document.getElementById("reg-error");
  if (regError) {
    regError.textContent = "";
    regError.style.display = "none";
  }
  setAuthView("register");
}

function hideRegisterModal() {
  setAuthView("login");
}

function requireAuth(action) {
  if (isAuthenticated()) {
    if (typeof action === "function") action();
    return true;
  }

  showLoginModal({ afterLoginAction: action });
  return false;
}

window.GatewayAuth = {
  isAuthenticated,
  showLoginModal,
  hideLoginModal,
  showRegisterModal,
  hideRegisterModal,
  requireAuth,
  refreshUi: refreshAuthUi,
};

/*** LOGIN HANDLER ***/

export function initLoginApp() {
  if (loginBound) return;
  const loginForm = document.getElementById("login-form");
  if (!loginForm) return;
  loginBound = true;

  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;
    const errorEl = document.getElementById("login-error");

    if (!username || !password) {
      errorEl.textContent = "Please enter username and password.";
      errorEl.style.display = "block";
      return;
    }

    try {
      const response = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (response.ok) {
        saveToken(data.access_token);
        currentUser = {
          user_id: data.user_id,
          username: data.username,
        };

        errorEl.style.display = "none";
        onLoginSuccess();
      } else {
        errorEl.textContent = data.error || "Login failed.";
        errorEl.style.display = "block";
      }
    } catch {
      errorEl.textContent = "Cannot connect to the server. Please try again.";
      errorEl.style.display = "block";
    }
  });
}

/*** LOGIN SUCCESS - INITIALIZE APP ***/

function onLoginSuccess() {
  const loginSection = document.getElementById("login-section");
  if (loginSection) loginSection.classList.remove("active");

  refreshAuthUi();

  const nameEl = document.getElementById("user-info-name");
  if (nameEl) nameEl.textContent = "👤 " + currentUser.username;

  if (typeof initChatApp === "function") initChatApp();

  if (typeof pendingPostLoginAction === "function") {
    const action = pendingPostLoginAction;
    pendingPostLoginAction = null;
    action();
  }
}

/*** LOGOUT HANDLER ***/

export function initLogoutApp() {
  if (logoutBound) return;
  const logoutBtn = document.getElementById("logout-btn");
  if (!logoutBtn) return;
  logoutBound = true;

  logoutBtn.addEventListener("click", (e) => {
    e.preventDefault();
    logout();
  });
}

function logout() {
  currentUser = null;
  clearToken();
  pendingPostLoginAction = null;

  const usernameEl = document.getElementById("username");
  const passwordEl = document.getElementById("password");
  if (usernameEl) usernameEl.value = "";
  if (passwordEl) passwordEl.value = "";

  const errorEl = document.getElementById("login-error");
  if (errorEl) errorEl.style.display = "none";

  const loginSection = document.getElementById("login-section");
  if (loginSection) loginSection.classList.remove("active");

  refreshAuthUi();
}

export function checkSession() {
  const token = getToken();
  if (!token) return false;

  if (isTokenExpired(token)) {
    clearToken();
    return false;
  }

  const payload = parseJwtPayload(token);
  if (payload) {
    currentUser = {
      user_id: payload.user_id,
      username: payload.username,
    };
    return true;
  }
  return false;
}

/*** PUBLIC REGISTRATION ***/

async function handleRegisterUser() {
  const regUsername = document.getElementById("reg-username");
  const regPassword = document.getElementById("reg-password");
  const username = regUsername ? regUsername.value.trim() : "";
  const password = regPassword ? regPassword.value.trim() : "";
  const regError = document.getElementById("reg-error");

  if (!username || !password) {
    regError.textContent = "Please fill in all fields.";
    regError.style.display = "block";
    return;
  }

  try {
    const response = await fetch("/api/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    const data = await response.json();

    if (response.ok) {
      alert("Registration successful!");
      if (regUsername) regUsername.value = "";
      if (regPassword) regPassword.value = "";
      hideRegisterModal();
      showLoginModal();
    } else {
      regError.textContent = data.error || "Registration failed.";
      regError.style.display = "block";
    }
  } catch {
    regError.textContent = "No connection to the server.";
    regError.style.display = "block";
  }
}

/*** BOOTSTRAP - PAGE LOAD ***/

document.addEventListener("DOMContentLoaded", () => {
  if (checkSession()) {
    onLoginSuccess();
  } else {
    refreshAuthUi();
  }

  initLoginApp();
  initLogoutApp();

  const saveRegBtn = document.getElementById("save-register-btn");
  if (saveRegBtn) {
    saveRegBtn.addEventListener("click", handleRegisterUser);
  }

  const closeLoginBtn = document.getElementById("close-login-btn");
  if (closeLoginBtn) {
    closeLoginBtn.addEventListener("click", (e) => {
      e.preventDefault();
      hideLoginModal();
    });
  }

  const loginSection = document.getElementById("login-section");
  if (loginSection) {
    loginSection.addEventListener("click", (e) => {
      if (e.target === loginSection) hideLoginModal();
    });
  }

  const tabLogin = document.getElementById("tab-login");
  if (tabLogin) {
    tabLogin.addEventListener("click", () => {
      setAuthView("login");
    });
  }

  const tabRegister = document.getElementById("tab-register");
  if (tabRegister) {
    tabRegister.addEventListener("click", () => {
      setAuthView("register");
    });
  }

  const goToReg = document.getElementById("go-to-register");
  if (goToReg) {
    goToReg.addEventListener("click", (e) => {
      e.preventDefault();
      setAuthView("register");
    });
  }

  const goToLogin = document.getElementById("go-to-login");
  if (goToLogin) {
    goToLogin.addEventListener("click", (e) => {
      e.preventDefault();
      setAuthView("login");
    });
  }
});
