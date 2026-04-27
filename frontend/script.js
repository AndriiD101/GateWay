document.addEventListener("DOMContentLoaded", () => {
  /*** NAVIGATION & PAGE ROUTING ***/

  const navLinks = document.querySelectorAll(".header-item");
  const pages = document.querySelectorAll(".page-section");
  const startBtn = document.querySelector(".start");
  const aiSection = document.getElementById("ai-section");
  const aiAuthOpenBtn = document.getElementById("ai-auth-open-btn");
  const logoButtons = document.querySelectorAll(
    ".header-logo-container .header-logo",
  );
  const loginButton = document.getElementById("open-login-btn");

  function isAuthenticated() {
    return Boolean(
      window.GatewayAuth &&
      typeof window.GatewayAuth.isAuthenticated === "function" &&
      window.GatewayAuth.isAuthenticated(),
    );
  }

  function openAuthModal(afterLoginAction = null) {
    if (
      window.GatewayAuth &&
      typeof window.GatewayAuth.showLoginModal === "function"
    ) {
      window.GatewayAuth.showLoginModal({ afterLoginAction });
    }
  }

  function gateAiAccess() {
    if (isAuthenticated()) {
      activatePage("ai-section");
      return true;
    }
    openAuthModal(() => activatePage("ai-section"));
    return false;
  }

  window.GatewayApp = { activatePage };

  function activatePage(targetId) {
    if (!targetId) return;
    pages.forEach((page) => page.classList.remove("active"));
    navLinks.forEach((navLink) => navLink.classList.remove("active"));

    const targetPage = document.getElementById(targetId);
    if (!targetPage) return;
    targetPage.classList.add("active");

    const activeNavLink = document.querySelector(
      `.header-item[data-target="${targetId}"]`,
    );
    if (activeNavLink) activeNavLink.classList.add("active");

    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  navLinks.forEach((link) => {
    link.addEventListener("click", function (event) {
      event.preventDefault();
      const targetId = this.getAttribute("data-target");
      if (targetId === "ai-section") { gateAiAccess(); return; }
      activatePage(targetId);
    });
  });

  if (startBtn) {
    startBtn.addEventListener("click", (e) => { e.preventDefault(); gateAiAccess(); });
  }
  if (loginButton) {
    loginButton.addEventListener("click", (e) => { e.preventDefault(); openAuthModal(); });
  }
  if (aiAuthOpenBtn) {
    aiAuthOpenBtn.addEventListener("click", (e) => {
      e.preventDefault();
      openAuthModal(() => activatePage("ai-section"));
    });
  }
  if (aiSection) {
    aiSection.addEventListener("click", (event) => {
      if (!isAuthenticated() && event.target.closest(".chat-wrapper")) {
        event.preventDefault();
        openAuthModal(() => activatePage("ai-section"));
      }
    });
  }

  logoButtons.forEach((logo) => {
    logo.addEventListener("click", () => activatePage("home-page"));
  });

  /*** USER DROPDOWN ***/

  const userDropdown = document.getElementById("user-dropdown");
  const userDropdownToggle = document.getElementById("user-dropdown-toggle");

  if (userDropdownToggle && userDropdown) {
    userDropdownToggle.addEventListener("click", (e) => {
      e.stopPropagation();
      userDropdown.classList.toggle("open");
      const isOpen = userDropdown.classList.contains("open");
      userDropdownToggle.setAttribute("aria-expanded", isOpen);
    });

    document.addEventListener("click", (e) => {
      if (!userDropdown.contains(e.target)) {
        userDropdown.classList.remove("open");
        userDropdownToggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  /*** CHAT & IMAGE UPLOAD ***/

  const userInput = document.getElementById("user-input");
  const chatMessages = document.getElementById("chat-messages");
  const sendBtn = document.getElementById("send-btn");
  const imageUpload = document.getElementById("image-upload");
  const imagePreviewContainer = document.getElementById("image-preview-container");
  const imagePreview = document.getElementById("image-preview");
  const removeImageBtn = document.getElementById("remove-image-btn");

  let currentImageFile = null;
  let isWaitingForResponse = false;

  /*** AUTH TOKEN HELPER ***/

  function getAuthHeaders() {
    const token = localStorage.getItem("gateway_jwt");
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  /*** IMAGE HANDLING ***/

  function handleImage(file) {
    if (!file || !file.type.startsWith("image/")) return;
    currentImageFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
      imagePreview.src = e.target.result;
      imagePreviewContainer.style.display = "flex";
    };
    reader.readAsDataURL(file);
  }

  function clearImage() {
    imageUpload.value = "";
    currentImageFile = null;
    imagePreviewContainer.style.display = "none";
    imagePreview.src = "";
  }

  imageUpload.addEventListener("change", function () {
    if (this.files && this.files[0]) handleImage(this.files[0]);
  });

  userInput.addEventListener("paste", function (e) {
    const items = (e.clipboardData || window.clipboardData).items;
    for (let i = 0; i < items.length; i++) {
      if (items[i].kind === "file" && items[i].type.startsWith("image/")) {
        handleImage(items[i].getAsFile());
        break;
      }
    }
  });

  removeImageBtn.addEventListener("click", clearImage);

  /*** TEXTAREA AUTO-HEIGHT ***/

  userInput.addEventListener("input", function () {
    this.style.height = "auto";
    if (this.scrollHeight < 200) {
      this.style.height = this.scrollHeight + "px";
      this.style.overflowY = "hidden";
    } else {
      this.style.height = "200px";
      this.style.overflowY = "auto";
    }
  });

  /*** MESSAGE DISPLAY ***/

  function addMessage(text, imageFile, isUser) {
    if (!text && !imageFile) return;

    const messageDiv = document.createElement("div");
    messageDiv.classList.add("message", isUser ? "user" : "bot");

    const avatarDiv = document.createElement("div");
    avatarDiv.classList.add("msg-avatar");
    if (isUser) {
      avatarDiv.textContent = "👤";
    } else {
      const avatarImg = document.createElement("img");
      avatarImg.src = "/styles/pictures/gateway_logo_svg.svg";
      avatarImg.alt = "AI";
      avatarImg.width = 30;
      avatarDiv.appendChild(avatarImg);
    }

    const bubbleDiv = document.createElement("div");
    bubbleDiv.classList.add("msg-bubble");

    if (imageFile) {
      const img = document.createElement("img");
      img.classList.add("chat-image");
      img.src = URL.createObjectURL(imageFile);
      img.alt = "Uploaded image";
      img.style.maxWidth = "100%";
      img.style.borderRadius = "8px";
      img.style.display = "block";
      img.style.marginBottom = text ? "8px" : "0";
      img.onload = () => { chatMessages.scrollTop = chatMessages.scrollHeight; };
      bubbleDiv.appendChild(img);
    }

    if (text) {
      const textSpan = document.createElement("span");
      textSpan.innerHTML = text.replace(/\n/g, "<br>");
      bubbleDiv.appendChild(textSpan);
    }

    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(bubbleDiv);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return messageDiv;
  }

  /*** TYPING INDICATOR ***/

  function showTypingIndicator() {
    const messageDiv = document.createElement("div");
    messageDiv.classList.add("message", "bot");
    messageDiv.id = "typing-indicator";

    const avatarDiv = document.createElement("div");
    avatarDiv.classList.add("msg-avatar");
    const avatarImg = document.createElement("img");
    avatarImg.src = "/styles/pictures/gateway_logo_svg.svg";
    avatarImg.alt = "AI";
    avatarImg.width = 30;
    avatarDiv.appendChild(avatarImg);

    const bubbleDiv = document.createElement("div");
    bubbleDiv.classList.add("msg-bubble");
    bubbleDiv.innerHTML = "<em>Analyzing your request\u2026 \uD83C\uDF0D</em>";

    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(bubbleDiv);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function removeTypingIndicator() {
    const indicator = document.getElementById("typing-indicator");
    if (indicator) indicator.remove();
  }

  /*** PERSIST MESSAGE TO BACKEND ***/

  async function persistMessage(role, message) {
    try {
      await fetch("/api/chat/message", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({ role, message }),
      });
    } catch { /* non-critical */ }
  }

  /*** FORMAT AI RESPONSE ***/

  function formatAiResponse(parsed, trip) {
    const city = parsed.city || trip?.detected_city || "your destination";
    const budget = parsed.budget_estimate || trip?.budget_estimate || "N/A";
    const itinerary = parsed.itinerary || [];
    const tips = parsed.tips || [];

    let text = `\uD83C\uDFD9\uFE0F ${city}\n`;
    text += `\uD83D\uDCB0 Estimated budget: $${budget}\n\n`;

    if (itinerary.length > 0) {
      text += `\uD83D\uDCC5 Itinerary:\n`;
      itinerary.forEach((item, i) => { text += `${i + 1}. ${item}\n`; });
    }

    if (tips.length > 0) {
      text += `\n\uD83D\uDCA1 Travel Tips:\n`;
      tips.forEach((tip) => { text += `\u2022 ${tip}\n`; });
    }

    return text.trim();
  }

  /*** CALL AI BACKEND ***/

  async function callAiBackend(text, imageFile) {
    const formData = new FormData();
    if (text) formData.append("prompt", text);
    if (imageFile) formData.append("image", imageFile);

    const response = await fetch("/ai/process", {
      method: "POST",
      headers: getAuthHeaders(),
      body: formData,
    });

    if (response.status === 401) {
      openAuthModal(() => activatePage("ai-section"));
      throw new Error("Not authenticated");
    }

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || "AI service error. Please try again.");
    }

    return response.json();
  }

  async function loadChatHistory() {
    try {
      const response = await fetch("/api/chat/history", {
        headers: getAuthHeaders(),
      });
      if (!response.ok) return;

      const messages = await response.json();
      if (!messages || messages.length === 0) return;

      chatMessages.innerHTML = "";
      addMessage(
        "Hi! I\u2019m your AI travel assistant. Tell me about your dream trip - where you want to go, for how many days, and what your budget is. I\u2019ll help you plan the perfect itinerary!",
        null,
        false,
      );

      messages.forEach((msg) => {
        addMessage(msg.message, null, msg.role === "user");
      });
    } catch { /* silently skip */ }
  }


  window.initChatApp = function () {
    loadChatHistory();
  };

  /*** SEND MESSAGE ***/

  async function handleSend() {
    if (!isAuthenticated()) {
      openAuthModal(() => activatePage("ai-section"));
      return;
    }

    if (isWaitingForResponse) return;

    const text = userInput.value.trim();
    if (!text && !currentImageFile) return;

    addMessage(text, currentImageFile, true);
    const sentImage = currentImageFile;

    userInput.value = "";
    userInput.style.height = "auto";
    clearImage();

    if (text) await persistMessage("user", text);

    isWaitingForResponse = true;
    sendBtn.disabled = true;
    showTypingIndicator();

    try {
      const result = await callAiBackend(text, sentImage);
      removeTypingIndicator();

      const aiText = formatAiResponse(result.parsed || {}, result.trip);
      addMessage(aiText, null, false);
      await persistMessage("assistant", aiText);

      if (result.pdf_url) {
        addMessage(
          `\uD83D\uDCC4 <a href="${result.pdf_url}" target="_blank" rel="noopener" style="color:#fab85c;">Download your trip report (PDF)</a>`,
          null,
          false,
        );
      }
    } catch (err) {
      removeTypingIndicator();
      if (err.message !== "Not authenticated") {
        addMessage(`\u274C ${err.message || "Something went wrong. Please try again."}`, null, false);
      }
    } finally {
      isWaitingForResponse = false;
      sendBtn.disabled = false;
    }
  }

  /*** EVENT LISTENERS ***/

  sendBtn.addEventListener("click", handleSend);

  userInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });

  if (window.GatewayAuth && typeof window.GatewayAuth.refreshUi === "function") {
    window.GatewayAuth.refreshUi();
  }
});

  document.addEventListener("DOMContentLoaded", function () {
    var burgerBtn = document.getElementById("burger-btn");
    var mobileMenu = document.getElementById("mobile-menu");
    var mobileClose = document.getElementById("mobile-menu-close");

    function openMenu() {
      burgerBtn.classList.add("open");
      mobileMenu.classList.add("open");
      mobileMenu.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
    }

    function closeMenu() {
      burgerBtn.classList.remove("open");
      mobileMenu.classList.remove("open");
      mobileMenu.setAttribute("aria-hidden", "true");
      document.body.style.overflow = "";
    }

    if (burgerBtn) burgerBtn.addEventListener("click", openMenu);
    if (mobileClose) mobileClose.addEventListener("click", closeMenu);

    // Close on nav link click
    if (mobileMenu) {
      mobileMenu.querySelectorAll("a[href]").forEach(function (link) {
        link.addEventListener("click", closeMenu);
      });
    }

    var mobileLoginBtn = document.getElementById("mobile-open-login-btn");
    var desktopLoginBtn = document.getElementById("open-login-btn");
    if (mobileLoginBtn && desktopLoginBtn) {
      mobileLoginBtn.addEventListener("click", function (e) {
        e.preventDefault();
        closeMenu();
        setTimeout(function () {
          desktopLoginBtn.click();
        }, 300);
      });
    }

    document.addEventListener("keydown", function (e) {
      if (
        e.key === "Escape" &&
        mobileMenu &&
        mobileMenu.classList.contains("open")
      ) {
        closeMenu();
      }
    });
  });