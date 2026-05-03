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

// SVG Icons
const icons = {
  email: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>`,
  lock: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>`,
  eye: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>`,
  eyeOff: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><line x1="2" x2="22" y1="2" y2="22"/></svg>`,
  google: `<svg width="20" height="20" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>`,
  github: `<svg width="20" height="20" viewBox="0 0 24 24" fill="#333"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>`,
  microsoft: `<svg width="20" height="20" viewBox="0 0 21 21"><path fill="#f25022" d="M1 1h9v9H1z"/><path fill="#00a4ef" d="M1 11h9v9H1z"/><path fill="#7fba00" d="M11 1h9v9h-9z"/><path fill="#ffb900" d="M11 11h9v9h-9z"/></svg>`,
  shield: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#9D174D" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`,
  zap: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#9D174D" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`,
  cloud: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#9D174D" stroke-width="2"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/></svg>`,
  logo: `<svg width="24" height="24" viewBox="0 0 24 24" fill="white"><rect x="3" y="3" width="18" height="18" rx="4"/><circle cx="9" cy="9" r="2" fill="#9D174D"/><circle cx="15" cy="9" r="2" fill="#9D174D"/><line x1="8" y1="15" x2="16" y2="15" stroke="#9D174D" stroke-width="2" stroke-linecap="round"/></svg>`,
};

export function mountAuthUI(auth, container, onUserChanged) {
  console.log("mountAuthUI called");
  let activeTab = 'signin';
  let error = '';
  let loading = false;

  function render() {
    console.log("Rendering auth UI, activeTab:", activeTab);
    const tabs = [
      { id: 'signin', label: 'Sign in' },
      { id: 'create', label: 'Create account' },
      { id: 'reset', label: 'Reset password' },
    ];

    container.innerHTML = `
      <div class="auth-container">
        <div class="auth-left">
          <div class="auth-logo">
            <div class="auth-logo-icon">${icons.logo}</div>
            <span class="auth-logo-text">SNTI AI</span>
          </div>
          <div class="auth-welcome">
            <div class="auth-welcome-label">WELCOME BACK</div>
            <h1>Sign in to <span class="highlight">SNTI AI</span> Assistant</h1>
            <p>Access your workspace to continue research, analyze data, write code, and more with your AI assistant.</p>
            <div class="auth-features">
              <div class="auth-feature">
                <div class="auth-feature-icon">${icons.shield}</div>
                <div class="auth-feature-text">
                  <h3>Secure & Private</h3>
                  <p>Enterprise-grade security to keep your data safe.</p>
                </div>
              </div>
              <div class="auth-feature">
                <div class="auth-feature-icon">${icons.zap}</div>
                <div class="auth-feature-text">
                  <h3>AI-Powered Productivity</h3>
                  <p>Research, code, analyze, and innovate faster.</p>
                </div>
              </div>
              <div class="auth-feature">
                <div class="auth-feature-icon">${icons.cloud}</div>
                <div class="auth-feature-text">
                  <h3>Sync Everywhere</h3>
                  <p>Access your workspace across all your devices.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="auth-right">
          <div class="auth-tabs">
            ${tabs.map(tab => `
              <button class="auth-tab ${tab.id === activeTab ? 'active' : ''}" data-tab="${tab.id}">
                ${tab.label}
              </button>
            `).join('')}
          </div>
          
          ${error ? `<div class="auth-error">${error}</div>` : ''}
          
          <form id="auth-form">
            ${activeTab === 'create' ? `
              <div class="input-group">
                <label>Display name</label>
                <div class="input-wrapper">
                  <input type="text" id="displayName" placeholder="Your name" required />
                </div>
              </div>
            ` : ''}
            
            <div class="input-group">
              <label>Email address</label>
              <div class="input-wrapper">
                <span class="input-icon">${icons.email}</span>
                <input type="email" id="email" placeholder="you@example.com" required />
              </div>
            </div>
            
            ${activeTab !== 'reset' ? `
              <div class="input-group">
                <label>Password</label>
                <div class="input-wrapper">
                  <span class="input-icon">${icons.lock}</span>
                  <input type="password" id="password" placeholder="${activeTab === 'signin' ? 'Enter your password' : 'Create a password'}" required />
                  <button type="button" class="password-toggle" id="togglePassword">
                    ${icons.eye}
                  </button>
                </div>
              </div>
            ` : ''}
            
            ${activeTab === 'signin' ? `
              <div class="checkbox-row">
                <label class="checkbox-label">
                  <input type="checkbox" id="rememberMe" />
                  <span>Keep me signed in</span>
                </label>
                <a href="#" class="forgot-link" id="forgotLink">Forgot password?</a>
              </div>
            ` : ''}
            
            ${activeTab === 'reset' ? `
              <p class="reset-text">Enter your email address and we'll send you a link to reset your password.</p>
            ` : ''}
            
            <button type="submit" class="submit-btn" ${loading ? 'disabled' : ''}>
              ${loading ? 'Processing...' : activeTab === 'signin' ? 'Sign in' : activeTab === 'create' ? 'Create account' : 'Send reset link'}
              <span class="arrow">→</span>
            </button>
          </form>
          
          <div class="divider"><span>or continue with</span></div>
          
          <button class="social-btn" id="google-btn">
            ${icons.google}
            <span>Continue with Google</span>
          </button>
          <button class="social-btn" id="github-btn">
            ${icons.github}
            <span>Continue with GitHub</span>
          </button>
          <button class="social-btn" id="microsoft-btn">
            ${icons.microsoft}
            <span>Continue with Microsoft</span>
          </button>
          
          <div class="auth-footer">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#9D174D" stroke-width="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
            <span>Protected by Firebase Authentication</span>
          </div>
        </div>
      </div>
    `;

    attachEventListeners();
  }

  function attachEventListeners() {
    // Tab switching
    container.querySelectorAll('.auth-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        activeTab = tab.dataset.tab;
        error = '';
        render();
      });
    });

    // Password toggle
    const toggleBtn = container.querySelector('#togglePassword');
    if (toggleBtn) {
      let showPassword = false;
      toggleBtn.addEventListener('click', () => {
        showPassword = !showPassword;
        const passwordInput = container.querySelector('#password');
        passwordInput.type = showPassword ? 'text' : 'password';
        toggleBtn.innerHTML = showPassword ? icons.eyeOff : icons.eye;
      });
    }

    // Forgot password link
    const forgotLink = container.querySelector('#forgotLink');
    if (forgotLink) {
      forgotLink.addEventListener('click', (e) => {
        e.preventDefault();
        activeTab = 'reset';
        error = '';
        render();
      });
    }

    // Form submission
    const form = container.querySelector('#auth-form');
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      error = '';
      loading = true;
      render();

      const email = container.querySelector('#email').value;
      const password = container.querySelector('#password')?.value;
      const displayName = container.querySelector('#displayName')?.value;

      try {
        if (activeTab === 'signin') {
          await signInWithEmailAndPassword(auth, email, password);
        } else if (activeTab === 'create') {
          const result = await createUserWithEmailAndPassword(auth, email, password);
          if (displayName?.trim()) {
            await updateProfile(result.user, { displayName: displayName.trim() });
          }
        } else if (activeTab === 'reset') {
          await sendPasswordResetEmail(auth, email);
          error = 'Password reset email sent!';
        }
      } catch (err) {
        error = err.message;
      }

      loading = false;
      render();
    });

    // Social auth
    container.querySelector('#google-btn').addEventListener('click', async () => {
      error = '';
      loading = true;
      render();
      try {
        await signInWithPopup(auth, new GoogleAuthProvider());
      } catch (err) {
        error = err.message;
        loading = false;
        render();
      }
    });

    container.querySelector('#github-btn').addEventListener('click', async () => {
      error = '';
      loading = true;
      render();
      try {
        await signInWithPopup(auth, new GithubAuthProvider());
      } catch (err) {
        error = err.message;
        loading = false;
        render();
      }
    });

    container.querySelector('#microsoft-btn').addEventListener('click', async () => {
      error = '';
      loading = true;
      render();
      try {
        await signInWithPopup(auth, new OAuthProvider('microsoft.com'));
      } catch (err) {
        error = err.message;
        loading = false;
        render();
      }
    });
  }

  render();
}
