# 📧 Gmail Email Cleanup Script

Automatically deletes old emails while protecting custom-labeled, starred, and important emails.

---

## ⚡ What It Does

✅ Deletes emails older than 3 months
✅ Protects custom labels YOU created
✅ Protects starred & important emails
✅ Protects receipts (by default)
✅ Logs all activity
✅ Runs monthly automatically

---

## 🚀 Setup (20 minutes)

### 1. Create Folder & Install Packages

```bash
mkdir ~/gmail-cleanup
cd ~/gmail-cleanup
pip3 install google-auth-oauthlib google-auth-httplib2 googleapiclient
```

### 2. Create Google Cloud Project

1. Go to: **https://console.cloud.google.com/**
2. Top left: Click project dropdown → **NEW PROJECT**
3. Name: `Gmail Cleanup` → **CREATE**

### 3. Enable Gmail API

1. Top search bar → Type: `Gmail API`
2. Click it → **ENABLE**

### 4. Create OAuth Credentials

1. Top left: **≡ (hamburger menu)**
2. **APIs & Services** → **Credentials**
3. Click **"Configure consent screen"**
4. Choose **"External"** → **CREATE**
5. Fill in:
   - App name: `Gmail Cleanup Tool`
   - User support email: Your email
   - Developer contact: Your email
6. Click **SAVE AND CONTINUE** (skip scopes page)
7. **BACK TO DASHBOARD**

### 5. Add Test User

1. Left menu: **Audience**
2. Click **"Add users"**
3. Enter your email
4. **ADD**

### 6. Create OAuth Client ID

1. Left menu: **≡ (hamburger menu)**
2. **APIs & Services** → **Credentials**
3. **+ CREATE CREDENTIALS**
4. Select **"OAuth client ID"**
5. Application type: **"Desktop application"**
6. Name: `Gmail Cleanup Tool`
7. **CREATE**
8. **DOWNLOAD** the JSON file
9. Rename to: **`credentials.json`**

### 7. Download & Run Script

Move both `credentials.json` and `gmail_cleanup.py` to `~/gmail-cleanup/`:

```bash
mv ~/Downloads/credentials.json ~/gmail-cleanup/
mv ~/Downloads/gmail_cleanup.py ~/gmail-cleanup/
```

Run the script:

```bash
cd ~/gmail-cleanup
python3 gmail_cleanup.py
```

A browser will open asking for authorization. Click **ALLOW**.

---

## ⚙️ Customize (Optional)

Run with options:

```bash
# Delete emails older than 6 months instead of 3
python3 gmail_cleanup.py --months 6

# Preview first without deleting
python3 gmail_cleanup.py --dry-run

# Exclude specific senders
python3 gmail_cleanup.py --exclude-from newsletter@example.com,notifications@app.com

# Protect specific labels
python3 gmail_cleanup.py --protect-labels Important,Family,Work

# Skip emails with certain keywords
python3 gmail_cleanup.py --protect-keywords invoice,contract,receipt

# Only clean specific labels
python3 gmail_cleanup.py --cleanup-labels Promotions,Newsletters

# Send summary email after cleanup
python3 gmail_cleanup.py --notify your-email@gmail.com

# More verbose logging
python3 gmail_cleanup.py --debug
```

---

## 📅 Schedule Monthly (Optional)

### Mac/Linux (Cron):
```bash
crontab -e
# Add this line:
0 3 1 * * cd ~/gmail-cleanup && python3 gmail_cleanup.py
```

### Windows (Task Scheduler):
1. `Win + R` → `taskscheduler.msc`
2. **Create Basic Task** → Name: `Gmail Cleanup`
3. Trigger: Monthly, 1st, 3:00 AM
4. Action: Run `python3` with script path
5. **Finish**

### ❌ Stop Monthly Cleanup

**Mac/Linux:**
```bash
crontab -e
# Delete the line you added
```

**Windows:**
Open Task Scheduler → Right-click task → **Delete**

---

## 📝 Check Logs

```bash
cat gmail_cleanup.log
```
