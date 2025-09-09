# secAIAgent
**Hack Smarter. Share Faster. Stay Secure.**
An AI-powered assistant that automates daily updates, task tracking, and collaboration by securely connecting with **Slack, Notion, GitHub, and Google Calendar** using **Descope Outbound Apps**.

## Project Overview
`secAIAgent` is a purposeful AI agent designed to help teams streamline their daily workflows:
- Post daily updates to **Slack** channels
- Append notes to **Notion** pages
- Create and track **GitHub issues**
- Schedule meetings in **Google Calendar** and get notified if any conflicts.

Authentication and token management are handled securely by **Descope Outbound Apps** — no hardcoded tokens, no custom OAuth logic. This makes the project both **secure** and **easy to extend**.


## MCP Hackathon Theme
**Theme 1: Build a Purposeful AI Agent**

## Demo Video 
https://youtu.be/riBAveHhfRI

## Team Members
**Tejaswini Oruganti**

This project solves a **real-world problem** by acting as an automation assistant for daily standups, onboarding, and task updates — all with minimal setup.

## Tech Stack
- **Frontend**: HTML, CSS, JavaScript
- **Backend**: Python, Flask
- **Authentication**: Descope Outbound Apps
- **Integrations**:
  - Slack API
  - Notion API
  - GitHub API
  - Google Calendar API

## Set Up
1. Login to Google Gemini AI and create API key and store ID
2. Create App in slack and store Client ID and Secret.
3. Create Integration App in Notion and store CLient ID and Secret.
4. Create Repository to create issues and in developer settings store Client ID and Secret.
5. Create APIs & services -> library and create Credentials and store Client ID and Secret.
6. Create outbound app in Descope [Slaack, Notion, Git Hub, Google calender] by adding client ID, client secret.
7. Create Project in Descope and Management keys in Company.
8. Clone the repo
9. cd Hackathon_Project
10. pip install -r requirements.txt
11. Get the IDs for 1st, 7th and 8th step and save it in .env file
12. Run the app either using python app.py or flask run
13.  Can see application with 4 tabs
   <img width="1423" height="846" alt="image" src="https://github.com/user-attachments/assets/020be1d8-87de-41d0-bd32-b10139ab09b6" />

