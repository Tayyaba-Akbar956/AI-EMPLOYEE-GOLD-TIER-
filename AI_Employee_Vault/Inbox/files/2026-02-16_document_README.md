# TaskPilot - Advanced Task Management Application

TaskPilot is a modern task management application featuring a sleek dark-themed UI with 3D motion effects, built with Next.js 16 and FastAPI. The application enables users to efficiently manage their tasks with features like due dates, priority levels, and real-time updates.

## 🌟 Features

- **AI-Powered Chatbot**: Natural language task management using **OpenAI Agents SDK**
- **Modern UI/UX**: Sleek dark-themed interface with glassmorphism and 3D motion effects
- **Full CRUD Operations**: Create, Read, Update, and Delete tasks
- **Advanced Dashboard**: Visual statistics and progress tracking
- **Calendar View**: Interactive schedule management
- **User Profiles**: Personalized accounts and settings
- **Task Prioritization**: Set priority levels (Low, Medium, High) for tasks
- **Due Dates**: Assign due dates to tasks for better time management
- **Real-time Updates**: See creation and modification timestamps
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Type Safety**: Built with TypeScript for enhanced reliability

## 🛠️ Tech Stack

### Frontend
- **Framework**: Next.js 16 (App Router)
- **Library**: React 19
- **Styling**: Tailwind CSS with custom dark theme
- **Animations**: Framer Motion for 3D effects and micro-interactions
- **State Management**: Zustand
- **Forms**: React Hook Form with Zod validation
- **Icons**: Lucide React
- **HTTP Client**: Axios

### Backend
- **Framework**: FastAPI
- **AI Agent**: OpenAI Agents SDK (Experimental Agent implementation)
- **Provider**: OpenAI / OpenRouter (supporting Gemini 2.0, GPT-4o, etc.)
- **ORM**: SQLModel (SQLAlchemy + Pydantic)
- **Database**: PostgreSQL (Neon) with SQLite fallback
- **Validation**: Pydantic v2
- **ASGI Server**: Uvicorn

## 🚀 Quick Start

### Prerequisites
- Node.js (v18 or higher)
- Python (v3.13 or higher)
- uv (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd taskpilot_phase_3
   ```

2. **Set up the backend (FastAPI server)**

   Navigate to the backend directory:
   ```bash
   cd backend
   ```

   Create and activate a Python virtual environment:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

   Install dependencies:
   ```bash
   uv sync
   ```

   Configure the database (for development, we use SQLite):
   Update your `.env` file to use SQLite:
   ```
   DATABASE_URL=sqlite+aiosqlite:///./taskpilot.db
   SECRET_KEY=your-secret-key-here
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   ALLOWED_ORIGINS=http://localhost:3000
   ```

   Initialize the database (recommended):
   ```bash
   uv run python init_db.py
   ```

   Start the backend server:
   ```bash
   uv run dev
   ```
   Or alternatively:
   ```bash
   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```

   The backend will be available at `http://localhost:8000`

   **Note**: The server automatically creates all necessary database tables on startup. If you encounter database errors, run the initialization script first.

3. **Set up the frontend (Next.js application)**

   Open a new terminal window/tab and navigate to the frontend directory:
   ```bash
   cd frontend  # From the project root
   ```

   Install dependencies:
   ```bash
   npm install
   ```

   Create environment configuration file `.env.local`:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

   Start the development server:
   ```bash
   npm run dev
   ```

   The frontend will be available at `http://localhost:3000`

## 📖 Usage

1. **Access the Application**
   - Open your browser and navigate to `http://localhost:3000`
   - You'll see the TaskPilot dashboard with a dark-themed interface

2. **Creating Tasks**
   - Click the "Create Task" button
   - Fill in the task details:
     - Title (required)
     - Description (optional)
     - Due Date (optional)
     - Priority (Low/Medium/High)
   - Click "Create Task" to save

3. **Managing Tasks**
   - View all tasks in the task list
   - Mark tasks as complete/incomplete using the checkbox
   - Edit tasks by clicking the pencil icon
   - Delete tasks by clicking the trash icon (with confirmation)

4. **Task Details**
   - Each task card displays:
     - Title
     - Description
     - Creation date
     - Last updated date (if modified)
     - Due date (if set)
     - Priority level (with color coding)

## 🏗️ Project Structure

```
taskpilot_phase_3/
├── backend/                # FastAPI backend
│   ├── src/
│   │   ├── main.py         # Application entry point
│   │   ├── models/         # Database models (Task, User, etc.)
│   │   ├── services/       # Business logic (TaskService, AuthService)
│   │   ├── agents/         # AI Agent implementation (OpenAI Agents SDK)
│   │   ├── api/            # API routes (Chatbot, Tasks, Auth)
│   │   ├── database/       # Database configuration
│   │   └── config/         # Configuration settings
│   ├── .env               # Environment variables
│   └── pyproject.toml     # Python dependencies (managed by uv)
├── frontend/               # Next.js frontend
│   ├── app/               # Next.js 16 App Router
│   │   ├── dashboard/
│   │   │   └── tasks/     # Task management pages
│   │   └── page.tsx       # Landing page
│   ├── components/        # Reusable UI components
│   ├── store/             # Zustand stores
│   ├── lib/               # Utilities, Auth service, and API client
│   ├── hooks/             # Custom React hooks
│   ├── types/             # TypeScript type definitions
│   └── .env.local         # Frontend environment variables
├── specs/                 # Specification documents
├── history/               # Development history
└── README.md              # This file
```

## 🔧 Configuration

### Environment Variables

**Backend (.env):**
```
DATABASE_URL=sqlite+aiosqlite:///./taskpilot.db
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALLOWED_ORIGINS=http://localhost:3000
OPENAI_API_KEY=your-api-key
```

**Frontend (.env.local):**
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Commit your changes (`git commit -m 'Add some amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

If you encounter any issues or have questions:

1. Check the API documentation at `http://localhost:8000/docs`
2. Review the browser console for frontend errors
3. Check the backend server logs for API errors
4. Create an issue in the repository

## 🚀 Production Deployment

For production deployment:

1. **Backend**: Deploy the FastAPI application to a cloud provider (AWS, Azure, GCP)
2. **Database**: Use PostgreSQL or another production-ready database
3. **Frontend**: Build and deploy the Next.js application (use `npm run build`)

---

Made with ❤️ using Next.js 16, FastAPI, and OpenAI Agents SDK.
