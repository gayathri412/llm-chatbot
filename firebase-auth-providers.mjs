import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.5/firebase-app.js";
import {
  browserLocalPersistence,
  createUserWithEmailAndPassword,
  getAuth,
  onAuthStateChanged,
  sendPasswordResetEmail,
  setPersistence,
  signInWithEmailAndPassword,
  signOut,
  updateProfile,
} from "https://www.gstatic.com/firebasejs/10.12.5/firebase-auth.js";

let appInstance;
let authInstance;

export function initFirebaseAuth(firebaseConfig) {
  if (!firebaseConfig || !firebaseConfig.apiKey) {
    throw new Error("Firebase web config is missing.");
  }

  if (!appInstance) {
    appInstance = initializeApp(firebaseConfig);
    authInstance = getAuth(appInstance);
  }

  return authInstance;
}

export function mountFirebaseAuth({
  root,
  firebaseConfig,
  onUserChanged = () => {},
}) {
  const auth = initFirebaseAuth(firebaseConfig);

  root.innerHTML = `
    <div>
      <p id="auth-status"></p>

      <div id="auth-form">
        <input id="auth-name" type="text" placeholder="Display name" />
        <input id="auth-email" type="email" placeholder="Email" />
        <input id="auth-password" type="password" placeholder="Password" />

        <button id="auth-signin">Sign in</button>
        <button id="auth-create">Create account</button>
        <button id="auth-reset">Reset password</button>
      </div>
    </div>
  `;

  const status = root.querySelector("#auth-status");
  const form = root.querySelector("#auth-form");
  const nameInput = root.querySelector("#auth-name");
  const emailInput = root.querySelector("#auth-email");
  const passwordInput = root.querySelector("#auth-password");

  setPersistence(auth, browserLocalPersistence);

  root.querySelector("#auth-signin").addEventListener("click", async () => {
    try {
      status.textContent = "Signing in...";
      await setPersistence(auth, browserLocalPersistence);
      await signInWithEmailAndPassword(
        auth,
        emailInput.value.trim(),
        passwordInput.value
      );
      status.textContent = "Signed in.";
    } catch (error) {
      status.textContent = error.message;
    }
  });

  root.querySelector("#auth-create").addEventListener("click", async () => {
    try {
      status.textContent = "Creating account...";
      await setPersistence(auth, browserLocalPersistence);

      const result = await createUserWithEmailAndPassword(
        auth,
        emailInput.value.trim(),
        passwordInput.value
      );

      if (nameInput.value.trim()) {
        await updateProfile(result.user, {
          displayName: nameInput.value.trim(),
        });
      }

      status.textContent = "Account created.";
    } catch (error) {
      status.textContent = error.message;
    }
  });

  root.querySelector("#auth-reset").addEventListener("click", async () => {
    try {
      await sendPasswordResetEmail(auth, emailInput.value.trim());
      status.textContent = "Password reset email sent.";
    } catch (error) {
      status.textContent = error.message;
    }
  });

  return onAuthStateChanged(auth, (user) => {
    form.hidden = !!user;
    root.hidden = !!user;
    onUserChanged(user);
  });
}

export function logout() {
  if (authInstance) {
    return signOut(authInstance);
  }
}
