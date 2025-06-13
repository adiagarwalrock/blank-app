# 🎈 Uptik

This application is a web dashboard that helps you monitor the current status of several popular cloud services, including:

- Google Cloud Platform (GCP) services (like Cloud Run, Cloud Storage, Compute Engine, etc.)
- OpenAI services (like Chat and Embeddings)
- Netlify (a website hosting service)
- Cloudflare (an internet security and performance service)

What it does:

- When you open the dashboard, it automatically checks the official status pages of these services.
- It shows you, clearly and easily, whether each service is working normally (green), having problems (yellow), or experiencing an outage (red).
- If there are any major incidents or problems, it lists details about them.
- You can refresh the dashboard at any time to get the latest updates by clicking a button.
- At the top, you’ll see an overall summary, so you immediately know if everything is running smoothly or if something is wrong.
- For each service, you can see:
  - Its current status
  - A short message about its condition
  - Any ongoing incidents affecting it
  - A link to its official status page for more details
- The dashboard focuses on incidents that affect North America for Google Cloud services.

The goal is to give you real-time, trustworthy information about whether these major online services are working or having issues, all in one place. This can be useful for anyone who relies on these services for their work or business, so you can quickly see if there’s a wider problem if you’re experiencing issues.

---

Let me know if you’d like a more detailed explanation of any part!
[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://uptime.streamlit.app/)

### How to run it on your own machine

1. Install the requirements

   ```
   $ pip install -r requirements.txt
   ```

2. Run the app

   ```
   $ streamlit run streamlit_app.py
   ```
