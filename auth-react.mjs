import React, { useState } from "https://esm.sh/react@18.2.0";
import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  sendPasswordResetEmail,
  updateProfile,
  GoogleAuthProvider,
  GithubAuthProvider,
  OAuthProvider,
  signInWithPopup,
} from "https://www.gstatic.com/firebasejs/10.12.5/firebase-auth.js";

const { createElement: h } = React;

// SVG Icons as components
const EmailIcon = () =>
  h("svg", { width: "18", height: "18", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "2" },
    h("rect", { x: "2", y: "4", width: "20", height: "16", rx: "2" }),
    h("path", { d: "m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" })
  );

const LockIcon = () =>
  h("svg", { width: "18", height: "18", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "2" },
    h("rect", { x: "3", y: "11", width: "18", height: "11", rx: "2", ry: "2" }),
    h("path", { d: "M7 11V7a5 5 0 0 1 10 0v4" })
  );

const EyeIcon = () =>
  h("svg", { width: "18", height: "18", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "2" },
    h("path", { d: "M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" }),
    h("circle", { cx: "12", cy: "12", r: "3" })
  );

const EyeOffIcon = () =>
  h("svg", { width: "18", height: "18", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "2" },
    h("path", { d: "M9.88 9.88a3 3 0 1 0 4.24 4.24" }),
    h("path", { d: "M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" }),
    h("path", { d: "M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" }),
    h("line", { x1: "2", x2: "22", y1: "2", y2: "22" })
  );

const GoogleIcon = () =>
  h("svg", { width: "20", height: "20", viewBox: "0 0 24 24" },
    h("path", { fill: "#4285F4", d: "M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" }),
    h("path", { fill: "#34A853", d: "M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" }),
    h("path", { fill: "#FBBC05", d: "M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" }),
    h("path", { fill: "#EA4335", d: "M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" })
  );

const GithubIcon = () =>
  h("svg", { width: "20", height: "20", viewBox: "0 0 24 24", fill: "#333" },
    h("path", { d: "M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" })
  );

const MicrosoftIcon = () =>
  h("svg", { width: "20", height: "20", viewBox: "0 0 21 21" },
    h("path", { fill: "#f25022", d: "M1 1h9v9H1z" }),
    h("path", { fill: "#00a4ef", d: "M1 11h9v9H1z" }),
    h("path", { fill: "#7fba00", d: "M11 1h9v9h-9z" }),
    h("path", { fill: "#ffb900", d: "M11 11h9v9h-9z" })
  );

const ShieldIcon = () =>
  h("svg", { width: "22", height: "22", viewBox: "0 0 24 24", fill: "none", stroke: "#9D174D", strokeWidth: "2" },
    h("path", { d: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" })
  );

const ZapIcon = () =>
  h("svg", { width: "22", height: "22", viewBox: "0 0 24 24", fill: "none", stroke: "#9D174D", strokeWidth: "2" },
    h("polygon", { points: "13 2 3 14 12 14 11 22 21 10 12 10 13 2" })
  );

const CloudIcon = () =>
  h("svg", { width: "22", height: "22", viewBox: "0 0 24 24", fill: "none", stroke: "#9D174D", strokeWidth: "2" },
    h("path", { d: "M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z" })
  );

const LogoIcon = () =>
  h("svg", { width: "24", height: "24", viewBox: "0 0 24 24", fill: "white" },
    h("rect", { x: "3", y: "3", width: "18", height: "18", rx: "4" }),
    h("circle", { cx: "9", cy: "9", r: "2", fill: "#9D174D" }),
    h("circle", { cx: "15", cy: "9", r: "2", fill: "#9D174D" }),
    h("line", { x1: "8", y1: "15", x2: "16", y2: "15", stroke: "#9D174D", strokeWidth: "2", strokeLinecap: "round" })
  );

// Feature Component
const Feature = ({ icon, title, description }) =>
  h("div", { className: "auth-feature" },
    h("div", { className: "auth-feature-icon" }, icon),
    h("div", { className: "auth-feature-text" },
      h("h3", null, title),
      h("p", null, description)
    )
  );

// Left Panel Component
const LeftPanel = () =>
  h("div", { className: "auth-left" },
    h("div", { className: "auth-logo" },
      h("div", { className: "auth-logo-icon" }, h(LogoIcon)),
      h("span", { className: "auth-logo-text" }, "SNTI AI")
    ),
    h("div", { className: "auth-welcome" },
      h("div", { className: "auth-welcome-label" }, "WELCOME BACK"),
      h("h1", null,
        "Sign in to ",
        h("span", { className: "highlight" }, "SNTI AI"),
        " Assistant"
      ),
      h("p", null, "Access your workspace to continue research, analyze data, write code, and more with your AI assistant."),
      h("div", { className: "auth-features" },
        h(Feature, { icon: h(ShieldIcon), title: "Secure & Private", description: "Enterprise-grade security to keep your data safe." }),
        h(Feature, { icon: h(ZapIcon), title: "AI-Powered Productivity", description: "Research, code, analyze, and innovate faster." }),
        h(Feature, { icon: h(CloudIcon), title: "Sync Everywhere", description: "Access your workspace across all your devices." })
      )
    )
  );

// Input Field Component
const InputField = ({ label, type, value, onChange, placeholder, icon: Icon, showPasswordToggle }) => {
  const [showPassword, setShowPassword] = useState(false);
  const inputType = showPasswordToggle && showPassword ? "text" : type;

  return h("div", { className: "input-group" },
    h("label", null, label),
    h("div", { className: "input-wrapper" },
      Icon && h("span", { className: "input-icon" }, h(Icon)),
      h("input", {
        type: inputType,
        value,
        onChange: (e) => onChange(e.target.value),
        placeholder
      }),
      showPasswordToggle &&
        h("button", {
          type: "button",
          className: "password-toggle",
          onClick: () => setShowPassword(!showPassword)
        }, showPassword ? h(EyeOffIcon) : h(EyeIcon))
    )
  );
};

// Social Button Component
const SocialButton = ({ icon, text, onClick }) =>
  h("button", { className: "social-btn", onClick }, icon, h("span", null, text));

// Main Auth Component
export function AuthApp({ auth, onUserChanged }) {
  const [activeTab, setActiveTab] = useState("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSignIn = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await signInWithEmailAndPassword(auth, email, password);
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  const handleCreateAccount = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const result = await createUserWithEmailAndPassword(auth, email, password);
      if (displayName.trim()) {
        await updateProfile(result.user, { displayName: displayName.trim() });
      }
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await sendPasswordResetEmail(auth, email);
      setError("Password reset email sent!");
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  const handleSocialSignIn = async (provider) => {
    setError("");
    setLoading(true);
    try {
      await signInWithPopup(auth, provider);
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  const tabs = [
    { id: "signin", label: "Sign in" },
    { id: "create", label: "Create account" },
    { id: "reset", label: "Reset password" },
  ];

  return h("div", { className: "auth-container" },
    h(LeftPanel),
    h("div", { className: "auth-right" },
      h("div", { className: "auth-tabs" },
        tabs.map((tab) =>
          h("button", {
            key: tab.id,
            className: `auth-tab ${activeTab === tab.id ? "active" : ""}`,
            onClick: () => {
              setActiveTab(tab.id);
              setError("");
            }
          }, tab.label)
        )
      ),

      error && h("div", { className: "auth-error" }, error),

      activeTab === "signin" &&
        h("form", { onSubmit: handleSignIn },
          h(InputField, { label: "Email address", type: "email", value: email, onChange: setEmail, placeholder: "you@example.com", icon: EmailIcon }),
          h(InputField, { label: "Password", type: "password", value: password, onChange: setPassword, placeholder: "Enter your password", icon: LockIcon, showPasswordToggle: true }),
          h("div", { className: "checkbox-row" },
            h("label", { className: "checkbox-label" },
              h("input", { type: "checkbox", checked: rememberMe, onChange: (e) => setRememberMe(e.target.checked) }),
              h("span", null, "Keep me signed in")
            ),
            h("a", { href: "#", className: "forgot-link" }, "Forgot password?")
          ),
          h("button", { type: "submit", className: "submit-btn", disabled: loading },
            loading ? "Signing in..." : "Sign in",
            h("span", { className: "arrow" }, "→")
          )
        ),

      activeTab === "create" &&
        h("form", { onSubmit: handleCreateAccount },
          h(InputField, { label: "Display name", type: "text", value: displayName, onChange: setDisplayName, placeholder: "Your name" }),
          h(InputField, { label: "Email address", type: "email", value: email, onChange: setEmail, placeholder: "you@example.com", icon: EmailIcon }),
          h(InputField, { label: "Password", type: "password", value: password, onChange: setPassword, placeholder: "Create a password", icon: LockIcon, showPasswordToggle: true }),
          h("button", { type: "submit", className: "submit-btn", disabled: loading },
            loading ? "Creating..." : "Create account",
            h("span", { className: "arrow" }, "→")
          )
        ),

      activeTab === "reset" &&
        h("form", { onSubmit: handleResetPassword },
          h("p", { className: "reset-text" }, "Enter your email address and we'll send you a link to reset your password."),
          h(InputField, { label: "Email address", type: "email", value: email, onChange: setEmail, placeholder: "you@example.com", icon: EmailIcon }),
          h("button", { type: "submit", className: "submit-btn", disabled: loading },
            loading ? "Sending..." : "Send reset link",
            h("span", { className: "arrow" }, "→")
          )
        ),

      h("div", { className: "divider" }, h("span", null, "or continue with")),

      h(SocialButton, { icon: h(GoogleIcon), text: "Continue with Google", onClick: () => handleSocialSignIn(new GoogleAuthProvider()) }),
      h(SocialButton, { icon: h(GithubIcon), text: "Continue with GitHub", onClick: () => handleSocialSignIn(new GithubAuthProvider()) }),
      h(SocialButton, {
        icon: h(MicrosoftIcon),
        text: "Continue with Microsoft",
        onClick: () => handleSocialSignIn(new OAuthProvider("microsoft.com"))
      }),

      h("div", { className: "auth-footer" },
        h("svg", { width: "14", height: "14", viewBox: "0 0 24 24", fill: "none", stroke: "#9D174D", strokeWidth: "2" },
          h("path", { d: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" })
        ),
        h("span", null, "Protected by Firebase Authentication")
      )
    )
  );
}
