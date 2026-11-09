# BrainBridge – Peer-to-Peer Knowledge Exchange

BrainBridge connects learners with people who can teach the topics they want to understand. A user can be a student, a student-teacher, or a teacher/mentor.

## Features
- Student and teacher/mentor registration and login
- Learning profile: topics you can teach and topics you want to learn
- Topic-based matching in both directions
- Send, accept, and decline learning requests
- Dashboard showing profile details and suggested matches
- SQLite database for user accounts and requests

## Requirements
- Python 3.9 or newer
- Internet connection for the Google Fonts used in the stylesheet (the app itself runs locally)

## Run the project
1. Extract the ZIP file.
2. Open a terminal in the `BrainBridge` folder.
3. Create and activate a virtual environment (recommended):
   - Windows: `py -m venv venv` then `venv\\Scripts\\activate`
   - macOS/Linux: `python3 -m venv venv` then `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Start the website: `python app.py`
6. Open `http://127.0.0.1:5000` in your browser.

The SQLite database `brainbridge.db` is created automatically on the first run.

## Try the matching feature
1. Register two different accounts using different email addresses.
2. Log in as the first user and set:
   - Can teach: `BEE, Mathematics`
   - Wants to learn: `PPS, AEP`
3. Log in as the second user and set:
   - Can teach: `PPS, AEP`
   - Wants to learn: `BEE`
4. Open **Find partners**. The users should appear as a match.
5. Send a learning request and test accepting or declining it from the other account.

## Notes and limitations
- This is a student mini-project prototype, not a production service.
- Matching compares comma-separated topic names. Use consistent spelling (for example, `PPS - loops` on both profiles) for best results.
- Learning sessions are arranged by the users; live video calling and real-time chat are not included.
- The app does not verify college email addresses. For a real deployment, add email verification, CSRF protection, stronger secret-key management, privacy controls, and secure hosting.
- Change `app.secret_key` before deploying publicly. Do not use the development server for production.
