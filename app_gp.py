import sqlite3
import pandas as pd
import streamlit as st
from openai import OpenAI
import os

def get_db_connection():
    return sqlite3.connect('appointments.db')

def fetch_appointments():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM appointments", conn)
    conn.close()
    return df

def fetch_appointment_by_id(appointment_id):
    conn = get_db_connection()
    df = pd.read_sql_query(f"SELECT * FROM appointments WHERE id = {appointment_id}", conn)
    conn.close()
    return df

gemini_model = "gemini-2.0-flash"
gemini_api_key = os.getenv("GEMINI_API_KEY")
google_client = OpenAI(api_key=gemini_api_key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")

# Language Support
TRANSLATIONS = {
    "English": {
        "page_title": "Saved Appointments",
        "sidebar_title": "Appointment Service",
        "select_patient": "Select a patient",
        "patient_summary": "Patient Summary",
        "format_profile": "Format Patient Profile",
        "formatted_profile": "Formatted Patient Profile",
        "no_appointments": "No appointments found."
    },
    "Français": {
        "page_title": "Rendez-vous Enregistrés",
        "sidebar_title": "Service de Rendez-vous",
        "select_patient": "Sélectionnez un patient",
        "patient_summary": "Résumé du Patient",
        "format_profile": "Formater le Profil du Patient",
        "formatted_profile": "Profil du Patient Formaté",
        "no_appointments": "Aucun rendez-vous trouvé."
    }
}

def t(key):
    return TRANSLATIONS[st.session_state.language].get(key, key)

# Session state initialization
if "language" not in st.session_state:
    st.session_state.language = "English"

if "confirmed_summary" not in st.session_state:
    st.session_state.confirmed_summary = False

# Sidebar and header
st.sidebar.image(
    r"Logo.png",
    use_container_width=True,
    output_format="PNG",
)

st.sidebar.markdown("""
    <style>
        [data-testid="stSidebar"] {
            background-color: transparent;
        }
        [data-testid="stImage"] {
            background-color: transparent;
            margin-top: -20px;
            margin-bottom: -20px;
        }
    </style>
    """, 
    unsafe_allow_html=True
)

st.sidebar.title(t("sidebar_title"))

# Language selector
language_selector = st.sidebar.selectbox(
    "Language / Langue / Idioma / Sprache:",
    list(TRANSLATIONS.keys()),
    key="language_selector",
    on_change=lambda: setattr(st.session_state, "language", st.session_state.language_selector)
)

if not st.session_state.confirmed_summary:
    st.title(t("page_title"))

appointments_df = fetch_appointments()
if not appointments_df.empty:
    if "confirmed_summary" not in st.session_state:
        st.session_state.confirmed_summary = False

    if not st.session_state.confirmed_summary:
        appointment_id = st.selectbox(t("select_patient"), appointments_df['id'])
        if appointment_id:
            selected_appointment = fetch_appointment_by_id(appointment_id)
            st.subheader(t("patient_summary"))
            st.write(selected_appointment)
            
            if st.button(t("format_profile")):
                patient_summary = selected_appointment.to_string(index=False)
                prompt = f"Format the following patient's profile in a neat and concise way:\n{patient_summary}"
                if st.session_state.language == "Français":
                    prompt = f"Formatez le profil du patient suivant de manière soignée et concise:\n{patient_summary}"
                response = google_client.chat.completions.create(
                    model=gemini_model,
                    messages=[{"role": "user", "content": prompt}]
                )
                st.session_state.formatted_profile = response.choices[0].message.content.strip()
                st.session_state.confirmed_summary = True
                st.rerun()
    else:
        st.subheader(t("formatted_profile"))
        st.write(st.session_state.formatted_profile)
else:
    st.write(t("no_appointments"))
