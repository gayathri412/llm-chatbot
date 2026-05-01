import { mountFirebaseAuth } from "./firebase-auth-providers.mjs";

const firebaseConfig = {
  apiKey: "PASTE_YOUR_API_KEY_HERE",
  authDomain: "llm-chatbot-cb0ab.firebaseapp.com",
  projectId: "llm-chatbot-cb0ab",
  appId: "1:322149526966:web:43e03b95eb7a2f8b486517",
};

const authBox = document.getElementById("firebase-auth");
const appBox = document.getElementById("app");

if (appBox) {
  appBox.hidden = true;
}

mountFirebaseAuth({
  root: authBox,
  firebaseConfig,
  onUserChanged(user) {
    if (appBox) {
      appBox.hidden = !user;
    }
  },
});
