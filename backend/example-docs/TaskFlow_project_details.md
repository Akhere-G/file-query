# TaskFlow Engine

A high-performance task engine designed to turn raw productivity data into actionable insights. Visualise your workflow, track your progress, manage your energy, and master your time.

**🔗 [Live Deployment](https://taskflow-752853711822.europe-west2.run.app/addtask)**

---

## Core Features

* **Flexible Views:** Switch between a clean list and a full calendar. Use smart filters and sorting to see exactly what needs your attention right now.
* **Seamless Habits:** Set tasks to repeat daily, weekly, or monthly. The system projects 'ghost tasks' into your future calendar so you can plan for upcoming commitments.
* **Your Daily Brief (AI Coach):** Start your day with an AI coach that reviews pending and overdue tasks to suggest the best plan of action for a productive morning.
* **Break It Down (AI Subtasks):** Avoid being overwhelmed by large projects. The built-in AI splits single large tasks into a clear, manageable checklist of smaller steps.
* **Quick-Add Tools:** Add tasks instantly by typing naturally with our AI assistant, or upload a CSV file to migrate an entire project's worth of tasks in one go.
* **Pomodoro Timer:** Boost focus using timed work intervals. Completed sessions are automatically logged against your tasks for accurate, hands-free time-tracking.
* **Performance Summary:** Monitor progress with a year-long activity map, tracking your overall 'Backlog Health' and daily productivity metrics.
* **Planning & Deadlines:** Visualise the week ahead to review upcoming deadlines. Dedicated charts highlight how close your due dates are and flag overdue items.
* **Workload Insights:** Understand exactly where your time goes with detailed breakdowns of time spent on different categories (e.g., work, health, or hobbies) over a rolling seven-day window.

---

## Technical Architecture

The platform is engineered on a modern full-stack architecture designed for high performance, type safety, and snappy interface responses.

### Backend Layer

The backend handles the core computational heavy lifting, database state management, and AI-driven background logic.

* **Language:** Python
* **Framework:** Flask (Application Factory Pattern)
* **ORM:** SQLAlchemy 2.0 (Modern explicit execution models)
* **Authentication:** JWT (Secure HTTP-only cookie-based rotation sessions)

### Frontend Layer

The user interface operates as a highly responsive, single-page application (SPA) focused on asynchronous data processing.

* **Core Framework:** React with TypeScript (Type-safe component design)
* **Styling:** Tailwind CSS (Utility-first responsive layout design)
* **Network Client:** Axios (Configured for credentials-backed API routing)
* **State Management:** TanStack Query (Server-state caching and seamless optimistic updates)
* **Data Visualisation:** Recharts (Dynamic rendering of workload insights and performance history)

---

## Technology Matrix

| Component | Technology | Primary Purpose |
| :--- | :--- | :--- |
| **Backend** | Python / Flask | RESTful API service orchestration |
| **Database ORM** | SQLAlchemy 2.0 | High-performance relational state mapping |
| **UI Layer** | React / TypeScript | Type-safe declarative interface building |
| **Styles** | Tailwind CSS | Consistent, hardware-accelerated design tokens |
| **Data Fetching** | Axios / TanStack Query | Asynchronous API communication and caching |
| **Analytics** | Recharts | Interactive charting and productivity telemetry |
