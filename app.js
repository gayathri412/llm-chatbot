import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.5/firebase-app.js";
import { getAuth, onAuthStateChanged } from "https://www.gstatic.com/firebasejs/10.12.5/firebase-auth.js";
import { AuthApp } from "./auth-react.mjs";
import React from "https://esm.sh/react@18.2.0";
import ReactDOM from "https://esm.sh/react-dom@18.2.0/client";

const firebaseConfig = {
  apiKey: "PASTE_YOUR_API_KEY_HERE",
  authDomain: "llm-chatbot-cb0ab.firebaseapp.com",
  projectId: "llm-chatbot-cb0ab",
  appId: "1:322149526966:web:43e03b95eb7a2f8b486517",
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

const authBox = document.getElementById("firebase-auth");
const appBox = document.getElementById("app");

if (appBox) {
  appBox.style.display = "none";
}

// Mount React auth component
const root = ReactDOM.createRoot(authBox);
root.render(
  React.createElement(AuthApp, {
    auth,
    onUserChanged: (user) => {
      if (appBox) {
        appBox.style.display = user ? "block" : "none";
      }
    },
  })
);

// Listen for auth state changes
onAuthStateChanged(auth, (user) => {
  if (user) {
    authBox.style.display = "none";
    if (appBox) appBox.style.display = "block";
  } else {
    authBox.style.display = "block";
    if (appBox) appBox.style.display = "none";
  }
});
