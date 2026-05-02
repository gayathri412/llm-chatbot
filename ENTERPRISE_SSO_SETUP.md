# Enterprise SSO Setup

The app supports Enterprise SSO through generic OpenID Connect (OIDC). Use the
same code path for Azure AD or Okta by changing the discovery URL and client
credentials.

## 1. Enable OIDC In The App

Set these values in `.env`:

```env
AUTH_PROVIDER=oidc
OIDC_PROVIDER_NAME=Azure AD
OIDC_DISCOVERY_URL=https://login.microsoftonline.com/<tenant-id>/v2.0/.well-known/openid-configuration
OIDC_CLIENT_ID=<application-client-id>
OIDC_CLIENT_SECRET=<client-secret>
OIDC_REDIRECT_URI=http://localhost:8501
OIDC_SCOPES=openid profile email
OIDC_ALLOWED_DOMAINS=yourcompany.com
OIDC_ALLOWED_EMAILS=
```

For Okta:

```env
AUTH_PROVIDER=oidc
OIDC_PROVIDER_NAME=Okta
OIDC_DISCOVERY_URL=https://<your-okta-domain>/oauth2/default/.well-known/openid-configuration
OIDC_CLIENT_ID=<okta-client-id>
OIDC_CLIENT_SECRET=<okta-client-secret>
OIDC_REDIRECT_URI=http://localhost:8501
OIDC_SCOPES=openid profile email
OIDC_ALLOWED_DOMAINS=yourcompany.com
OIDC_ALLOWED_EMAILS=
```

For deployed Cloud Run, set `OIDC_REDIRECT_URI` to the deployed app URL, for
example:

```env
OIDC_REDIRECT_URI=https://your-cloud-run-url.run.app
```

## 2. Register The Redirect URI

In Azure AD or Okta, register the exact same redirect URI:

```text
http://localhost:8501
```

and for production:

```text
https://your-cloud-run-url.run.app
```

## 3. Azure AD Notes

Create an app registration in Microsoft Entra ID:

1. Go to **Microsoft Entra ID > App registrations**.
2. Create or select an app.
3. Add a **Web** redirect URI.
4. Create a client secret.
5. Use the tenant-specific discovery URL:

```text
https://login.microsoftonline.com/<tenant-id>/v2.0/.well-known/openid-configuration
```

## 4. Okta Notes

Create an OIDC web app integration:

1. Go to **Applications > Create App Integration**.
2. Choose **OIDC - OpenID Connect** and **Web Application**.
3. Add the redirect URI.
4. Copy the client ID and client secret.
5. Use the authorization server discovery URL:

```text
https://<your-okta-domain>/oauth2/default/.well-known/openid-configuration
```

## 5. Access Control

Use one or both allow lists to map enterprise identity to app access:

```env
OIDC_ALLOWED_DOMAINS=yourcompany.com,partner.com
OIDC_ALLOWED_EMAILS=admin@yourcompany.com,qa@yourcompany.com
```

If both values are empty, any user who can authenticate with the configured
SSO provider can enter the app.

## 6. Data Access Mapping

The app can also map OIDC `roles`, `groups`, email addresses, domains, or user
IDs to allowed RAG/BigQuery context sources. Source names come from the document
`source` field. Local JSON docs default to `docs.json` or `sample.json`; BigQuery
context rows use the `source` column.

```env
DATA_ACCESS_CONTROL_ENABLED=true
DATA_ACCESS_RULES=role:admin=*;group:finance=finance_docs;domain:yourcompany.com=docs.json,sample.json
DATA_ACCESS_DEFAULT_SOURCES=
```

Rule format:

```text
selector:value=source1,source2
```

Supported selectors are `role`, `group`, `email`, `domain`, and `user_id`.
Use `*` as the source list to grant all sources. If rules are configured and a
user matches none of them, the user receives no managed context unless
`DATA_ACCESS_DEFAULT_SOURCES` is set.

Restricted users can still ask questions, but retrieved RAG/BigQuery context is
limited to their approved sources. Direct arbitrary BigQuery SQL is blocked for
restricted users.

## 7. Firebase Fallback

To switch back to Firebase Email/Password, set:

```env
AUTH_PROVIDER=firebase
```
