# aiPHeed setup guide

This guide is for the person who looks after the aiPHeed system. You do not
need to be a programmer. It explains:

1. [The settings file and what to put in it](#1-the-settings-file)
2. [Updating the database](#2-updating-the-database)
3. [Creating the first administrator](#3-creating-the-first-administrator)
4. [Approving new administrators](#4-approving-new-administrators)
5. [Turning the demo account on and off for presentations](#5-the-demo-account-for-presentations)
6. [When someone forgets their password](#6-when-someone-forgets-their-password)
7. [What must be done before going live](#7-before-going-live)
8. [Common problems](#8-common-problems)

All commands below are typed in **PowerShell**, inside the `backend` folder of
the project. To get there, open PowerShell and type (adjust the path if the
project is somewhere else):

```powershell
cd C:\aipheed-updated\backend
```

---

## 1. The settings file

The settings live in a text file called **`.env`** inside the `backend` folder.
Open it with Notepad. If it does not exist yet, copy `backend\.env.example`
and rename the copy to `.env`.

Each line looks like `NAME=value`. Lines starting with `#` are notes and are
ignored. **After changing anything in `.env`, stop the aiPHeed server and
start it again** — it only reads the file when it starts.

> Never share the `.env` file or put it on GitHub. It contains passwords.

### Settings you must fill in

| Setting | What it means | What to put |
|---|---|---|
| `SECRET_KEY` | A long secret the server uses to sign people in securely. | A long random text. Create one with the command below and paste it in. Never reuse the example value `changeme`. |
| `FRONTEND_BASE_URL` | The web address people use to open aiPHeed. The links in emails point here. | For example `https://aipheed.example.gov.ph`. During local testing: `http://localhost:8080`. |
| `SMTP_HOST` | The email server that sends verification and password-reset emails. | Ask your IT office (for example `smtp.office365.com` or `smtp.gmail.com`). **Leave it empty while testing on your own computer** — emails are then shown in the server window instead of being sent. |
| `SMTP_PORT` | The email server's port number. | Usually `587`. |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | The email account that sends the messages. | From your IT office. |
| `SMTP_FROM` | The "From" name and address people see. | For example `aiPHeed <no-reply@calabarzon.da.gov.ph>`. |
| `SMTP_USE_TLS` / `SMTP_USE_SSL` | How the connection to the email server is protected. | Usually `SMTP_USE_TLS=true` and `SMTP_USE_SSL=false`. If your IT office says "port 465 / SSL", use `SMTP_PORT=465`, `SMTP_USE_SSL=true`. |

To create a `SECRET_KEY`:

```powershell
.\venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Settings you can usually leave as they are

| Setting | What it means |
|---|---|
| `DATABASE_URL` | Where the database file is. Default: `aipheed.db` in the `backend` folder. |
| `ADMIN_EMAIL_DOMAIN` | Only email addresses ending in `@calabarzon.da.gov.ph` can have an administrator account. Do not change it. |
| `REFRESH_TOKEN_IDLE_TTL_SECONDS` | How long an administrator stays signed in without doing anything. Default 8 hours (`28800`). |
| `REFRESH_TOKEN_MAX_TTL_SECONDS` | The longest anyone stays signed in, however active. Default 7 days (`604800`). |
| `REFRESH_COOKIE_SAMESITE` | Leave as `strict`. See [section 7](#7-before-going-live). |
| `REFRESH_COOKIE_SECURE` | Leave as `true`. |
| `ENABLE_API_DOCS` | Shows a technical page listing every server address. Keep `false`. |
| `ENABLE_DEMO_ACCOUNT`, `DEMO_ADMIN_EMAIL`, `DEMO_ADMIN_PASSWORD` | The presentation account. See [section 5](#5-the-demo-account-for-presentations). |

---

## 2. Updating the database

The database is a single file, `backend\aipheed.db`. When aiPHeed is installed
for the first time, or after an update, the database must be brought up to
date. **Stop the aiPHeed server first**, then:

```powershell
# 1. Make a dated backup copy (keep it somewhere safe)
Copy-Item aipheed.db "aipheed.db.backup-$(Get-Date -Format yyyy-MM-dd)"

# 2. Update the database
.\venv\Scripts\python.exe -m alembic upgrade head

# 3. Check it worked: this should end with "(head)"
.\venv\Scripts\python.exe -m alembic current
```

Existing administrator accounts keep working after the update. If something
goes wrong, stop the server and copy the backup back over `aipheed.db`.

---

## 3. Creating the first administrator

New people normally sign up on the website and are approved by an existing
administrator (section 4). The **first** administrator has to be created by
hand, on the server:

```powershell
.\venv\Scripts\python.exe scripts\create_admin.py --email juan.delacruz@calabarzon.da.gov.ph --name "Juan Dela Cruz"
```

It asks for the password twice (nothing appears on screen while you type —
that is normal). The password must be **at least 12 characters** and not a
common password. A few unrelated words make a good one, for example
`kalesa-ilog-bundok-tinapay`.

Other useful commands:

```powershell
# See all accounts and their status
.\venv\Scripts\python.exe scripts\create_admin.py --list

# Give an account a new password (it is signed out everywhere;
# this also switches a deactivated account back on)
.\venv\Scripts\python.exe scripts\create_admin.py --email juan.delacruz@calabarzon.da.gov.ph --name "Juan Dela Cruz"

# Switch an account off (it is signed out everywhere at once)
.\venv\Scripts\python.exe scripts\create_admin.py --email juan.delacruz@calabarzon.da.gov.ph --deactivate
```

---

## 4. Approving new administrators

1. The new person opens the sign-in page and clicks **Create an account**.
   They enter their name, their `@calabarzon.da.gov.ph` email, their office or
   unit, and a password.
2. They receive an email with a link. Opening it confirms their email address.
   (The link works once and expires after 24 hours; they can ask for a new one.)
3. **You approve them.** Sign in, open the **☰ menu** (top right) and choose
   **Accounts**. The number next to "Accounts" shows how many requests are
   waiting.
4. Under **Waiting for approval**, check the name, email and office, then click
   **Approve** — they get an email saying they can sign in — or **Reject**.
5. Under **Active admins** you can **Deactivate** someone who should no longer
   have access. They are signed out everywhere immediately. You cannot
   deactivate your own account.

Every approval, rejection and deactivation is recorded with who did it, to
whom, and when.

If someone tries to sign in before these steps are done, the sign-in page
tells them **"Verify your email to continue."** (with a button to resend the
email) or **"Your account is waiting for approval."**

---

## 5. The demo account (for presentations)

The demo account lets you show the administrator pages to an audience
**without any risk of changes**. It can look at everything except the Accounts
page, every button that would change something is greyed out, survey
respondents' names and emails are hidden, and the server refuses any change
even if someone tries another way. A **"Demo account"** label is shown at the
top of the page.

### Set it up once

1. In `.env`, set an address and a password for it:
   ```
   DEMO_ADMIN_EMAIL=demo.account@calabarzon.da.gov.ph
   DEMO_ADMIN_PASSWORD=a-long-passphrase-only-you-know
   ```
   The address must end in `@calabarzon.da.gov.ph`, and it must not be a real
   person's administrator account.
2. Create the account:
   ```powershell
   .\venv\Scripts\python.exe scripts\create_admin.py --demo
   ```
   Running the same command again later updates the password.

### Turn it on before a presentation

1. In `.env`, set `ENABLE_DEMO_ACCOUNT=true`.
2. Restart the aiPHeed server.
3. Sign in with the demo email and password.

### Turn it off afterwards

1. In `.env`, set `ENABLE_DEMO_ACCOUNT=false`.
2. Restart the aiPHeed server.

While it is off, the demo account cannot sign in at all, and anyone still
signed in with it is signed out. **Always turn it off after a presentation.**

---

## 6. When someone forgets their password

They click **Forgot password?** on the sign-in page and enter their email. If
the address has an active account, they receive a link (it works once and
expires after 1 hour). After they choose a new password, they are signed out
on every other device.

You can also set a new password for them yourself with `create_admin.py`
(section 3).

---

## 7. Before going live

Go through this list before real users rely on the system:

- [ ] **`SECRET_KEY`** is a long random value (section 1), not `changeme`.
- [ ] **Email works.** `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD` and
  `SMTP_FROM` are filled in, and `FRONTEND_BASE_URL` is the real web address.
  Test it: sign up with a test address and check that the email arrives.
- [ ] **`ENABLE_DEMO_ACCOUNT=false`.**
- [ ] **`ENABLE_API_DOCS=false`.**
- [ ] **HTTPS.** The website and the server must both be reached through
  `https://` addresses (with a padlock in the browser), never plain `http://`.
  Your hosting provider or IT office sets this up.
- [ ] **The website and the server are on the same site.** Administrators stay
  signed in when they refresh the page thanks to a protected cookie, and with
  the default setting (`REFRESH_COOKIE_SAMESITE=strict`) the browser only
  sends that cookie when the website and the server share the same main
  address — for example `aipheed.example.gov.ph` and
  `api.aipheed.example.gov.ph`. If they are on unrelated addresses (for
  example the website on `something.vercel.app` and the server elsewhere),
  administrators would be signed out on every refresh. Ask the developers to
  either put both under one address (recommended) or switch the setting — the
  second option needs a security fix first (QA report item SEC-08).
- [ ] **The first administrator** exists (section 3) and has signed in.
- [ ] **A backup** of `aipheed.db` is made regularly (section 2).

---

## 8. Common problems

**No emails arrive.** If `SMTP_HOST` is empty, emails are not sent — they are
printed in the window where the server runs (useful for testing). Otherwise
check the SMTP settings with your IT office, and look in the spam folder.

**Administrators are signed out every time they refresh the page.** The website
and the server are probably on different sites, or one of them is on `http://`.
See the "same site" item in section 7.

**"Your account is waiting for approval."** An administrator still needs to
approve the account (section 4).

**"Verify your email to continue."** The person has not opened the link in the
verification email yet. They can click **Resend verification email**.

**The demo account cannot sign in.** Check that `ENABLE_DEMO_ACCOUNT=true` in
`.env` and that the server was restarted afterwards.
