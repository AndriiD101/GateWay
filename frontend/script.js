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

  window.GatewayApp = {
    activatePage,
  };

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
      if (targetId === "ai-section") {
        gateAiAccess();
        return;
      }

      activatePage(targetId);
    });
  });

  if (startBtn) {
    startBtn.addEventListener("click", (event) => {
      event.preventDefault();
      gateAiAccess();
    });
  }

  if (loginButton) {
    loginButton.addEventListener("click", (event) => {
      event.preventDefault();
      openAuthModal();
    });
  }

  if (aiAuthOpenBtn) {
    aiAuthOpenBtn.addEventListener("click", (event) => {
      event.preventDefault();
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

  /*** CHAT & IMAGE UPLOAD ***/

  const userInput = document.getElementById("user-input");
  const chatMessages = document.getElementById("chat-messages");
  const sendBtn = document.getElementById("send-btn");
  const imageUpload = document.getElementById("image-upload");
  const imagePreviewContainer = document.getElementById(
    "image-preview-container",
  );
  const imagePreview = document.getElementById("image-preview");
  const removeImageBtn = document.getElementById("remove-image-btn");

  let currentImageFile = null;

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

  /*** IMAGE UPLOAD LISTENERS ***/

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
      img.onload = () => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
      };
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
  }

  /*** SEND MESSAGE ***/

  function handleSend() {
    if (!isAuthenticated()) {
      openAuthModal(() => activatePage("ai-section"));
      return;
    }

    const text = userInput.value.trim();

    if (!text && !currentImageFile) return;

    addMessage(text, currentImageFile, true);

    userInput.value = "";
    userInput.style.height = "auto";
    clearImage();

    setTimeout(() => {
      addMessage("One moment, analyzing your request... 🌍", null, false);
    }, 1000);
  }

  /*** EVENT LISTENERS ***/

  sendBtn.addEventListener("click", handleSend);

  userInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });

  if (
    window.GatewayAuth &&
    typeof window.GatewayAuth.refreshUi === "function"
  ) {
    window.GatewayAuth.refreshUi();
  }
});
