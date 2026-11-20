# syntrix-AI

# Syntrix AI

### Your Intelligent AI Workspace

Syntrix AI is a full-stack AI-powered workspace designed to provide an integrated environment for intelligent conversations, user management, document handling, and productivity.

The platform combines a modern frontend with a Django backend to deliver an interactive AI experience with secure authentication, conversation history, database management, and AI usage monitoring.

## Features

- **AI Chat:** Interactive AI-powered conversations.
- **User Authentication:** User registration, login, and account management.
- **Conversation Management:** Create, store, and manage chat history.
- **Database Integration:** Store and manage application data.
- **Admin Dashboard:** Manage users, conversations, messages, and records.
- **Document Management:** Upload and manage documents.
- **AI Usage Analytics:** Track AI usage and activity.
- **Responsive Interface:** Modern dashboard for desktop and mobile devices.

## Technology Stack

- Frontend: React, JavaScript, HTML, CSS
- Backend: Python, Django
- Database: SQLite (development)
- AI Integration: OpenAI API
- Version Control: Git and GitHub

## Project Structure

```text
syntrix-AI/
├── backend/
│   ├── Django applications
│   ├── API endpoints
│   └── Database models
├── frontend/
│   ├── React application
│   ├── Components
│   └── Assets
├── .env.example
├── .gitignore
└── README.md
```

## Getting Started

Clone the repository:

```bash
git clone https://github.com/hari-unnikrishnan/syntrix-AI.git
cd syntrix-AI
```

### Backend Setup

```bash
cd backend
```

Create and activate a virtual environment, then install the backend dependencies:

```bash
python -m venv .venv
```

On Windows:

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
```

Configure the required environment variables using `.env.example`.

Run migrations:

```bash
python manage.py migrate
```

Start Django:

```bash
python manage.py runserver
```

### Frontend Setup

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local frontend URL displayed in the terminal.

## Django Admin

Access the administration dashboard locally:

```text
http://127.0.0.1:8000/admin/
```

Create an administrator account using:

```bash
python manage.py createsuperuser
```

## Environment Configuration

Configure your API credentials and application settings in your local `.env` file.

Never upload API keys, passwords, or other secrets to GitHub.

## Future Improvements

- Enhanced AI assistant capabilities
- Advanced analytics dashboard
- Improved document processing
- Production database integration
- Cloud deployment
- Additional productivity features

## Author

Developed by **Hari Unnikrishnan**.

## Repository

[Syntrix AI – GitHub](https://github.com/hari-unnikrishnan/syntrix-AI)
