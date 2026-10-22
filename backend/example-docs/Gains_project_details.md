# Gains

Elevate your training. Track your progress. Gains is the ultimate fitness companion built to design custom workout routines, effortlessly log live training sessions, and beautifully visualise training volume and consistency over time.

**🔗 [Live Deployment](https://exercise-tracker-frontend-752853711822.europe-west1.run.app/exercises/2330)**

---

## Core Features

* **Customise Routines:** Design tailored training programmes that perfectly fit your current macrocycle. Seamlessly organise your favourite movements and set explicit targets before hitting the gym floor.
* **Live Workout Execution:** Execute active training sessions with an intuitive, clutter-free logging interface. Track reps, working loads, and rest periods dynamically in real time without missing a beat.
* **Advanced Analytics:** Keep an eye on key physiological metrics. Watch your estimated 1-Rep Max (1RM) scale up over historical timelines, view explicit rep zone distributions, and monitor absolute volume changes across training cycles.

---

## Architecture Overview

The application features a modern frontend stack designed around performance, micro-interactions, and clear data visualisation.

### Presentation & Routing Layer

* **Core Framework:** Next.js (Utilising modern routing paradigms and optimised client-side transitions)
* **Styling & Design Tokens:** Tailwind CSS (Configured with dynamic semantic design variables such as `bg-background`, `text-primary`, and custom functional opacity modifiers)
* **Iconography:** Lucide React (Clean, scalable vector icons ensuring immediate visual context)

### Functional Segments

* **`/routines` (The Dashboard):** Central hub for macrocycle planning, workout composition, and target specification.
* **`/exercises` (The Library):** Workspace dedicated to tracking particular movements and past progression steps.
* **`/stats` (The Telemetry Engine):** Dedicated data-visualisation sector tracking estimated 1RM growth, absolute volume, and rep distribution models.

---

## Technology Matrix

| Component | Technology | Primary Purpose |
| :--- | :--- | :--- |
| **Framework Engine** | Next.js | Unified routing architecture and optimized component rendering |
| **Styling Tokens** | Tailwind CSS | Utility-first responsive design implementation |
| **Icon Set** | Lucide React | Contextual visual cues and layout accents |
| **Data Tracking** | Live Session Log | Real-time capturing of load, reps, and pacing |
| **Analytics Layer** | Telemetry Subsystem | Calculated metrics for 1RM estimations and volumetric monitoring |
