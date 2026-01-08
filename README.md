# Energy App

A Python application for visualizing energy consumption data. This project can be run in two modes: 

- **Flask**: as a traditional web server 

- **Streamlit**: as an interactive data app

 ## 📂 Project Structure
 ```markdown
 energy_app/
├── flask_app/      
│   ├── app.py
│   ├── requirements.txt
│   └── templates/
│       └── index.html
│
├── streamlit_app/   
│   ├── app.py
│   ├── requirements.txt
│   └── dashboard.py
│
└── README.md         
```

 ## 🚀 Run with Flask

1. Navigate to the Flask folder:
   ```bash
   cd flask_app
   pip install -r requirements.txt
   ```
2. Set Environment Variables
   ```bash
   set FLASK_APP=app.py
   ```
3. Start Server
   ```bash
   flask run
   ```

 ## 🚀 Run with Streamlit
1. Navigate to the Flask folder:
   ```bash
   cd streamlit_app
   pip install -r requirements.txt
   ```   
2. Start Server
   ```
   streamlit run visual.py
   ```
