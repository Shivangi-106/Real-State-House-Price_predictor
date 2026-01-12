🏠 Real Estate House Price Predictor
A Live-Learning Real Estate Valuation System

🚀 Overview
This project is an end-to-end web application that provides real-time house price predictions. While the core is a house price predictor, the real focus of this project was building a resilient, automated data pipeline that allows the system to learn and improve autonomously from live user interactions.
+1

🛠️ The "Same-Same, but Different" Journey
Unlike standard static predictors, this project was a journey of solving real-world deployment challenges:


Phase 1 (CSVs): Started with local CSV storage, which failed silently upon cloud deployment.

Phase 2 (SQL): Migrated to a MySQL backend (PlanetScale). While technically sound, it faced free-tier limitations and connection issues in production.
+1

Phase 3 (Google Sheets): Developed a secure, persistent cloud backend using the Google Sheets API. This provided a scalable, cost-effective, and highly reliable solution for a live app.
+1

✨ Key Features

Live Data Feedback Loop: Every user prediction is captured in real-time and stored in a cloud database.


Automated Model Retraining: The system features a custom logic trigger: once 10 new valid rows are collected, the model automatically retrains on the updated dataset to adapt to new trends.
+1


Data Integrity Management: Uses two separate database tabs—one for raw user input and one for the master training data—to prevent "pollution" or corruption of the model.


Secure Credential Handling: Implemented secure authentication using Google Cloud service accounts and .toml configuration for production safety.

⚙️ Tech Stack & Skills

Systems & Frontend: Streamlit (UI), Python, Google Sheets API (Backend DB), gspread.


Deployment: GitHub & Streamlit Cloud with secure credential management.


The ML Corner (Implementation): * Data Processing: Pandas, NumPy, StandardScaler pipelines.
+1


Modeling: Scikit-learn (Random Forest Regressor) with joblib for model persistence.
+1


Logic: Automated batch retraining and model versioning.

📂 Project Structure
Plaintext

├── app.py              # Main Streamlit interface and routing logic
├── model.pkl           # The 'brain' - automatically updated after every 10 inputs
├── utils.py            # Backend logic: Google Sheets API & database triggers
├── requirements.txt    # Project dependencies
└── README.md           # Project documentation
🏁 How to Run Locally
Clone the repo: git clone https://github.com/Shivangi-106/Real-State-House-Price_predictor.git

Install dependencies: pip install -r requirements.txt

Set up your Google Cloud Service Account credentials.

Run: streamlit run app.py

Developed as a case study in building independent, self-learning automated systems.
