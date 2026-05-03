import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.5/firebase-app.js";
import { getAuth, onAuthStateChanged } from "https://www.gstatic.com/firebasejs/10.12.5/firebase-auth.js";
import { mountAuthUI } from "./auth-vanilla.mjs";

console.log("App.js loading...");

const firebaseConfig = {
  apiKey: "PASTE_YOUR_API_KEY_HERE",
  authDomain: "llm-chatbot-cb0ab.firebaseapp.com",
  projectId: "llm-chatbot-cb0ab",
  appId: "1:322149526966:web:43e03b95eb7a2f8b486517",
};

try {
  // Initialize Firebase
  const app = initializeApp(firebaseConfig);
  const auth = getAuth(app);
  console.log("Firebase initialized");

  const authBox = document.getElementById("firebase-auth");
  const appBox = document.getElementById("app");

  console.log("authBox:", authBox);
  console.log("appBox:", appBox);

  if (appBox) {
    appBox.style.display = "none";
  }

  // Mount auth UI
  if (authBox) {
    console.log("Mounting auth UI...");
    mountAuthUI(auth, authBox, (user) => {
      console.log("User changed:", user);
      if (appBox) {
        appBox.style.display = user ? "block" : "none";
      }
    });
    console.log("Auth UI mounted");
  } else {
    console.error("authBox not found!");
  }

  // Listen for auth state changes
  onAuthStateChanged(auth, (user) => {
    console.log("Auth state changed:", user);
    if (user) {
      authBox.style.display = "none";
      if (appBox) appBox.style.display = "block";
    } else {
      authBox.style.display = "block";
      if (appBox) appBox.style.display = "none";
    }
  });
} catch (err) {
  console.error("Error initializing app:", err);
  document.body.innerHTML = `<div style="color:red; padding:20px;">Error: ${err.message}</div>`;
}
