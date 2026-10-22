# TripTrack

Travel planning, simplified. TripTrack replaces messy spreadsheets and endless browser tabs with a single unified platform to plan routes, collaborate with friends, and let AI handle the logistical heavy lifting.

**🔗 [Live Deployment](https://tripapp-752853711822.europe-west2.run.app/)**

---

## Why Use TripTrack?

* **Map & Calendar View:** See your schedule and your map simultaneously on one clean interface. Eliminate the friction of switching between separate apps to understand your itinerary.
* **AI Plan Day:** Stuck for inspiration? The built-in AI assistant instantly populates your day with smart local suggestions, taking the guesswork out of building a travel itinerary.
* **AI Optimise Day:** The intelligent routing engine automatically reorders events to resolve timing clashes and group nearby spots together, ensuring you spend less time travelling and more time exploring.
* **Real-time Collaboration:** Invite your group to plan trips together. Updates sync instantaneously across all devices, keeping everyone on the same page without chaotic group chats.
* **Admin & Viewer Roles:** Maintain structural control by assigning specific permissions. Grant co-planners full editing access as Admins, or keep others as Viewers so they can follow the itinerary without altering details.
* **Google Event Search:** Seamlessly query restaurants, museums, and hidden landmarks using Google's comprehensive database, adding them to your trip configuration with a single click.
* **AI Travel Tips:** Access context-aware, hyper-local advice tailored dynamically to your destination—ranging from optimal visiting hours to must-try local delicacies.
* **Calendar Export:** Carry plans everywhere. Export entire trip itineraries to your native personal calendar to keep track of schedules effortlessly, even when offline.

---

## Technical Architecture

TripTrack is engineered as a decoupled, modern full-stack web application optimised for rapid geodata rendering and real-time client state synchronisation.

### Frontend Client

The presentation layer operates as a highly responsive single-page application built around structured validation and strict type safety.

* **Core Framework:** React with TypeScript
* **State Management:** Redux (Global trip and itinerary syncing)
* **Data Validation:** Yup (Client-side schema validation prior to API transmission)
* **Mapping Integration:** Google Maps API (Spatial visualisations and path planning)

### Backend Services

The backend API handles core business logic, strict relational database mapping, and conversational AI prompt parsing.

* **Language & Framework:** Python with Flask (Application Factory Pattern)
* **Database ORM:** SQLAlchemy (Modern relational schemas)
* **Serialization/Parsing:** Marshmallow (Strict data type marshalling and clean API contracts)
* **AI Engine:** Gemini AI (Powering day planning, itinerary optimization, and travel tips)

---

## Technology Matrix

| Layer | Component | Primary Objective |
| :--- | :--- | :--- |
| **Frontend** | React / TypeScript | Component layout architecture and type safety |
| **State & Validation** | Redux / Yup | Real-time state synchronization and form validation |
| **Backend API** | Python / Flask | Scalable RESTful endpoint orchestration |
| **Database ORM** | SQLAlchemy | Relational state structure and transaction mapping |
| **Serialization** | Marshmallow | API input validation and JSON formatting schemas |
| **Integrations** | Google Maps / Gemini | Interactive geo-tracking and automated AI intelligence |
