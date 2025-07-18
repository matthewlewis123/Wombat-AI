import re
import os
import random
import sqlite3
import pandas as pd
import streamlit as st
from openai import OpenAI
from datetime import datetime

#############################
# Global Constants & Setup
#############################

CLINIC_LOCATIONS = [
    "Jefferiss Wing Sexual Health Clinic, W2 1NY",
    "56 Dean Street, W1D 6AQ",
    "John Hunter Clinic, SW10 9NH"
]

CONSULTATION_MODES = ["Face-to-Face"]
gemini_model = "gemini-2.0-flash"
gemini_api_key = os.getenv("GEMINI_API_KEY")
google_client = OpenAI(api_key=gemini_api_key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")

##############################################
# Database Functions
##############################################
def init_db():
    conn = sqlite3.connect('appointments.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS appointments (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT,
                 priority TEXT,
                 clinic TEXT,
                 time_preference TEXT,
                 mode_of_consultation TEXT,
                 phone_number TEXT,
                 symptoms_summary TEXT,
                 severity_classification TEXT,
                 date_of_birth TEXT,
                 has_symptoms TEXT,
                 emergency_contraception TEXT,
                 needs_translator TEXT,
                 translator_language TEXT
                 )''')
    c.execute('''CREATE TABLE IF NOT EXISTS available_slots (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 clinic TEXT,
                 time TEXT,
                 priority TEXT,
                 mode_of_consultation TEXT,
                 is_booked INTEGER DEFAULT 0
                 )''')
    conn.commit()
    conn.close()

def populate_slots():
    conn = sqlite3.connect('appointments.db')
    c = conn.cursor()
    c.execute("DELETE FROM available_slots")
    slots = []
    priorities = ["Urgent", "Routine No Symptoms", "Routine Symptoms", "Contraception Referral"]
    mode = "Face-to-Face"  # Only one consultation mode
    clinics = CLINIC_LOCATIONS
    start_time = 8 * 60  # 8 AM in minutes
    end_time = 19 * 60   # 7 PM in minutes
    for clinic in clinics:
        for t in range(start_time, end_time, 15):
            hour = t // 60
            minute = t % 60
            time_str = f"{hour:02}:{minute:02}"
            for priority in priorities:
                slots.append((clinic, time_str, priority, mode))
    c.executemany('''INSERT INTO available_slots (clinic, time, priority, mode_of_consultation)
                     VALUES (?, ?, ?, ?)''', slots)
    conn.commit()
    conn.close()

##############################################
# OpenAI Helper Function
##############################################
def generate_openai_response(prompt, messages):
    """Appends prompt to messages, calls OpenAI, appends and returns the response."""
    messages.append({"role": "user", "content": prompt})
    completion = google_client.chat.completions.create(
        model=gemini_model,
        messages=messages,
        max_tokens=150,
        temperature=0.5,
    )
    response = completion.choices[0].message.content.strip()
    messages.append({"role": "assistant", "content": response})
    return response

##############################################
# Language Support
##############################################
TRANSLATIONS = {
    "English": {
        # Page titles
        "page_title": "Sexual Health Screening Assistant",
        "sidebar_title": "Sexual Health Service",
        "warning": "This is a demonstration system and not a substitute for professional medical care. In an emergency, call **999** or visit A&E immediately.",
        
        # Form steps
        "registration": "Patient Registration",
        "full_name": "What is your full name?",
        "date_of_birth": "What is your date of birth?",
        "has_symptoms": "Do you have symptoms?",
        "symptoms_desc": "What are your symptoms?",
        "symptoms_duration": "How long have you had your symptoms?",
        "last_period": "When was your last menstrual period?",
        "medical_history": "What medical conditions are you diagnosed to have? Are you taking any medications? Do you have any allergies?",
        "smoking": "Do you smoke?",
        "drugs": "Do you take recreational drugs?",
        "prefer_not_say": "Prefer not to say",
        "alcohol": "How much alcohol do you drink a week in units?",
        "emergency_contraception": "Do you need emergency contraception?",
        "days_since_period_label": "Days Since Last Period",

        
        # Summary and booking
        "summary": "Patient Summary",
        "triage_classification": "Triage Classification",
        "determined_priority": "Determined Priority:",
        "recommended_mode": "Recommended Consultation Mode:",
        "booking_details": "Additional Booking Details",
        "booking_details_text": "Please select additional details for your appointment:",
        "clinic_location": "Choose a clinic location:",
        "time_preference": "Preferred time of day:",
        "consultation_mode": "Preferred consultation mode:",
        "appointment_booking": "Appointment Booking",
        "choose_slot": "Choose your appointment slot:",
        "available_slots": "Available appointment slots:",
        "select_slot": "Select Slot:",
        "no_slots": "No available slots matching your criteria.",
        "booking_success": "Appointment booked successfully for slot ID {slot_id}!",
        
        # Buttons
        "next": "Next",
        "confirm": "Confirm Summary",
        "submit": "Submit Booking Details",
        "book": "Book Appointment",
        
        # Summary labels
        "name_label": "Name",
        "dob_label": "Date of Birth",
        "has_symptoms_label": "Has Symptoms",
        "symptoms_label": "Symptoms",
        "symptoms_duration_label": "Symptoms Duration",
        "last_period_label": "Last Menstrual Period",
        "medical_history_label": "Medical History",
        "smoking_label": "Smoking Status",
        "drugs_label": "Recreational Drugs",
        "alcohol_label": "Alcohol (units/week)",
        "emergency_contraception_label": "Needs Emergency Contraception",
        
        # Yes/No options
        "yes": "Yes",
        "no": "No",
        
        # Phone number
        "phone_number": "Phone Number",
        "phone_placeholder": "Enter your phone number",


        # Translator options
        "needs_translator": "Do you need a translator for your appointment?",
        "translator_language": "Which language do you need translation for?",
        
    },
        "Français": {
        # Page titles
        "page_title": "Assistant de Dépistage de Santé Sexuelle",
        "sidebar_title": "Service de Santé Sexuelle",
        "warning": "Ceci est un système de démonstration et ne remplace pas les soins médicaux professionnels. En cas d'urgence, appelez le **999** ou rendez-vous immédiatement aux urgences.",
        
        # Form steps
        "registration": "Inscription du Patient",
        "full_name": "Quel est votre nom complet?",
        "date_of_birth": "Quelle est votre date de naissance?",
        "has_symptoms": "Avez-vous des symptômes?",
        "symptoms_desc": "Quels sont vos symptômes?",
        "symptoms_duration": "Depuis combien de temps avez-vous ces symptômes?",
        "last_period": "Combien de jours depuis le premier jour de vos dernières règles?",
        "medical_history": "De quelles conditions médicales êtes-vous diagnostiqué? Prenez-vous des médicaments? Avez-vous des allergies?",
        "smoking": "Fumez-vous?",
        "drugs": "Prenez-vous des drogues récréatives?",
        "prefer_not_say": "Préfère ne pas dire",
        "alcohol": "Combien d'unités d'alcool consommez-vous par semaine?",
        "emergency_contraception": "Avez-vous besoin d'une contraception d'urgence?",
        "days_since_period_label": "Jours Depuis les Dernières Règles",
        # Summary and booking
        "summary": "Résumé du Patient",
        "triage_classification": "Classification de Triage",
        "determined_priority": "Priorité Déterminée:",
        "recommended_mode": "Mode de Consultation Recommandé:",
        "booking_details": "Détails Supplémentaires de Réservation",
        "booking_details_text": "Veuillez sélectionner des détails supplémentaires pour votre rendez-vous:",
        "clinic_location": "Choisissez un lieu de clinique:",
        "time_preference": "Moment préféré de la journée:",
        "consultation_mode": "Mode de consultation préféré:",
        "appointment_booking": "Réservation de Rendez-vous",
        "choose_slot": "Choisissez votre créneau de rendez-vous:",
        "available_slots": "Créneaux de rendez-vous disponibles:",
        "select_slot": "Sélectionnez votre créneau:",
        "no_slots": "Aucun créneau disponible correspondant à vos critères.",
        "booking_success": "Rendez-vous réservé avec succès pour le créneau ID {slot_id}!",
        
        # Buttons
        "next": "Suivant",
        "confirm": "Confirmer le Résumé",
        "submit": "Soumettre les Détails de Réservation",
        "book": "Réserver le Rendez-vous",
        
        # Summary labels
        "name_label": "Nom",
        "dob_label": "Date de Naissance",
        "has_symptoms_label": "A des Symptômes",
        "symptoms_label": "Symptômes",
        "symptoms_duration_label": "Durée des Symptômes",
        "last_period_label": "Dernières Règles",
        "medical_history_label": "Antécédents Médicaux",
        "smoking_label": "Statut Tabagique",
        "drugs_label": "Drogues Récréatives",
        "alcohol_label": "Alcool (unités/semaine)",
        "emergency_contraception_label": "Besoin de Contraception d'Urgence",
        
        # Yes/No options
        "yes": "Oui",
        "no": "Non",
        
        # Phone number
        "phone_number": "Numéro de Téléphone",
        "phone_placeholder": "Entrez votre numéro de téléphone",

        "needs_translator": "Avez-vous besoin d'un traducteur pour votre rendez-vous?",
        "translator_language": "Pour quelle langue avez-vous besoin d'une traduction?",
        
    },
    "Español": {
        # Add Spanish translations here
    },
    "Deutsch": {
        # Add German translations here
    },
    "العربية": {
        # Add Arabic translations here
    },
    "中文": {
        # Add Chinese translations here
    },
    "हिंदी": {
        # Add Hindi translations here
    },
    "Português": {
        # Add Portuguese translations here
    }
}

# Function to get translated text
def t(key):
    return TRANSLATIONS[st.session_state.language].get(key, key)

##############################################
# Streamlit UI - Integrated Multi-Step Triage & Booking
##############################################

# Session state initialization
if "language" not in st.session_state:
    st.session_state.language = "English"

if "current_step" not in st.session_state:
    st.session_state.current_step = 1  # Multi-step form tracker
    
if "responses" not in st.session_state:
    st.session_state.responses = {}  # Store user responses per step
    
if "confirmed_summary" not in st.session_state:
    st.session_state.confirmed_summary = False
    
if "triage_severity" not in st.session_state:
    st.session_state.triage_severity = None
    
if "priority" not in st.session_state:
    st.session_state.priority = None  # To store parsed priority from GPT

# Sidebar and header
st.sidebar.image(
    r"Logo.png",
    use_container_width=True,
    output_format="PNG",  # Ensure PNG format to preserve transparency
)

# Add custom CSS to make the sidebar background match with image
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
    "Language / Langue / Idioma / Sprache / لغة / 语言 / भाषा / Língua:",
    list(TRANSLATIONS.keys()),  # Use keys from TRANSLATIONS dictionary
    key="language_selector",
    on_change=lambda: setattr(st.session_state, "language", st.session_state.language_selector)
)
st.title(t("page_title"))
st.warning(t("warning"))


# Function to calculate age from date of birth
def calculate_age(dob):
    today = datetime.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


# -----------------------------
# MULTI-STEP FORM LOGIC
# -----------------------------

# Step 1: Patient Name
if st.session_state.current_step == 1:
    st.header(t("registration"))
    name = st.text_input(t("full_name"), key="patient_name")
    if st.button(t("next")) and name:
        st.session_state.responses["name"] = name
        st.session_state.current_step = 2
        st.rerun()

# Step 2: Gender
elif st.session_state.current_step == 2:
    st.header(t("registration"))
    gender = st.radio("What is your gender?", ["Male", "Female", "Other"], key="gender")
    if st.button(t("next")) and gender:
        st.session_state.responses["gender"] = gender
        st.session_state.current_step = 3
        st.rerun()

# Step 3: Date of Birth
elif st.session_state.current_step == 3:
    st.header(t("registration"))
    dob = st.date_input(
        t("date_of_birth"), 
        help="Please select your date of birth",
        format="DD/MM/YYYY",
        min_value=datetime(1900, 1, 1),  # Allow dates from 1900 onwards
        max_value=datetime.today()  # Allow dates up to today
    )
    if st.button(t("next")):
        st.session_state.responses["date_of_birth"] = dob.strftime("%d/%m/%Y")
        st.session_state.responses["age"] = calculate_age(dob)
        st.session_state.current_step = 4
        st.rerun()

# Step 4: Has Symptoms
elif st.session_state.current_step == 4:
    st.header(t("registration"))
    has_symptoms = st.radio(t("has_symptoms"), [t("yes"), t("no")], key="has_symptoms")
    if st.button(t("next")) and has_symptoms:
        st.session_state.responses["has_symptoms"] = has_symptoms
        if has_symptoms == t("yes"):
            st.session_state.current_step = 5  # Go to symptoms description
        else:
            st.session_state.current_step = 7  # Skip to emergency contraception
        st.rerun()

# Step 5: Symptoms Description (only if has symptoms)
elif st.session_state.current_step == 5:
    st.header(t("registration"))
    symptoms = st.text_area(t("symptoms_desc"), key="symptoms")
    if st.button(t("next")) and symptoms:
        st.session_state.responses["symptoms"] = symptoms
        st.session_state.current_step = 6
        st.rerun()

# Step 6: Symptoms Duration
elif st.session_state.current_step == 6:
    st.header(t("registration"))
    duration = st.text_input(t("symptoms_duration"), key="symptoms_duration")
    if st.button(t("next")) and duration:
        st.session_state.responses["symptoms_duration"] = duration
        st.session_state.current_step = 7
        st.rerun()

# Step 7: Emergency Contraception
elif st.session_state.current_step == 7:
    st.header(t("registration"))
    emergency_contraception = st.radio(t("emergency_contraception"), [t("yes"), t("no")], key="emergency_contraception")
    if st.button(t("next")) and emergency_contraception:
        st.session_state.responses["emergency_contraception"] = emergency_contraception
        if st.session_state.responses["gender"] == "Female":
            st.session_state.current_step = 8  # Go to last period question
        else:
            st.session_state.current_step = 9  # Skip to medical history
        st.rerun()

# Step 8: Last Period (only if female)
elif st.session_state.current_step == 8:
    st.header(t("registration"))
    last_period_date = st.date_input(
        t("last_period"), 
        help="This information helps assess pregnancy risk and certain conditions",
        format="DD/MM/YYYY"
    )
    if st.button(t("next")):
        days_since_period = (datetime.now().date() - last_period_date).days
        st.session_state.responses["last_period"] = f"{days_since_period} days ago"
        st.session_state.current_step = 9
        st.rerun()

# Step 9: Medical History
elif st.session_state.current_step == 9:
    st.header(t("registration"))
    medical_history = st.text_area(t("medical_history"), key="medical_history")
    if st.button(t("next")) and medical_history:
        st.session_state.responses["medical_history"] = medical_history
        # If no symptoms, skip smoking, drugs, alcohol
        if st.session_state.responses.get("has_symptoms") == t("no"):
            st.session_state.current_step = 13  # Skip to summary confirmation
        else:
            st.session_state.current_step = 10  # Continue with smoking
        st.rerun()

# Step 10: Smoking Status (only if has symptoms)
elif st.session_state.current_step == 10:
    st.header(t("registration"))
    smoking = st.radio(t("smoking"), [t("yes"), t("no")], key="smoking")
    if st.button(t("next")) and smoking:
        st.session_state.responses["smoking"] = smoking
        st.session_state.current_step = 11
        st.rerun()

# Step 11: Recreational Drugs (only if has symptoms)
elif st.session_state.current_step == 11:
    st.header(t("registration"))
    drugs_options = [t("yes"), t("no"), t("prefer_not_say")]
    drugs = st.radio(t("drugs"), drugs_options, key="drugs")
    if st.button(t("next")) and drugs:
        st.session_state.responses["drugs"] = drugs
        st.session_state.current_step = 12
        st.rerun()

# Step 12: Alcohol Consumption (only if has symptoms)
elif st.session_state.current_step == 12:
    st.header(t("registration"))
    alcohol = st.text_input(t("alcohol"), key="alcohol")
    if st.button(t("next")) and alcohol:
        st.session_state.responses["alcohol"] = alcohol
        st.session_state.current_step = 13
        st.rerun()

# Step 13: Summary Confirmation
elif st.session_state.current_step == 13:
    st.header(t("summary"))
    
    # Build summary based on provided answers (handle conditional questions)
    summary_items = [
        f"{t('name_label')}: {st.session_state.responses.get('name')}",
        f"{t('dob_label')}: {st.session_state.responses.get('date_of_birth')}",
        f"Age: {st.session_state.responses.get('age')}",
        f"{t('has_symptoms_label')}: {st.session_state.responses.get('has_symptoms')}"
    ]
    
    # Add symptoms details if patient has symptoms
    if st.session_state.responses.get("has_symptoms") == t("yes"):
        summary_items.extend([
            f"{t('symptoms_label')}: {st.session_state.responses.get('symptoms')}",
            f"{t('symptoms_duration_label')}: {st.session_state.responses.get('symptoms_duration')}",
            f"{t('smoking_label')}: {st.session_state.responses.get('smoking')}",
            f"{t('drugs_label')}: {st.session_state.responses.get('drugs')}",
            f"{t('alcohol_label')}: {st.session_state.responses.get('alcohol')}"
        ])
    
    # Add last period if female
    if st.session_state.responses.get("gender") == "Female":
        summary_items.append(f"{t('last_period_label')}: {st.session_state.responses.get('last_period')}")
    
    # Add remaining common items
    summary_items.extend([
        f"{t('medical_history_label')}: {st.session_state.responses.get('medical_history')}",
        f"{t('emergency_contraception_label')}: {st.session_state.responses.get('emergency_contraception')}"
    ])
    
    # Join all items with newlines
    summary = "\n".join(summary_items)
    
    st.text_area(t("summary"), value=summary, height=300)
    if st.button(t("confirm")):
        st.session_state.confirmed_summary = True
        st.session_state.current_step = 14
        st.rerun()

# Step 14: Triage Classification via LLM
elif st.session_state.current_step == 14:
    st.header(t("triage_classification"))
    
    # Build prompt for priority determination
    has_symptoms = st.session_state.responses.get("has_symptoms") == t("yes")
    needs_contraception = st.session_state.responses.get("emergency_contraception") == t("yes")
    
    # Build patient summary for LLM
    summary_items = [
        f"Name: {st.session_state.responses.get('name')}",
        f"Date of Birth: {st.session_state.responses.get('date_of_birth')}",
        f"Age: {st.session_state.responses.get('age')}",
        f"Has Symptoms: {st.session_state.responses.get('has_symptoms')}"
    ]
    
    if has_symptoms:
        summary_items.extend([
            f"Symptoms: {st.session_state.responses.get('symptoms')}",
            f"Symptoms Duration: {st.session_state.responses.get('symptoms_duration')}",
            f"Last Period: {st.session_state.responses.get('last_period')}",
            f"Smoking: {st.session_state.responses.get('smoking')}",
            f"Recreational Drugs: {st.session_state.responses.get('drugs')}",
            f"Alcohol: {st.session_state.responses.get('alcohol')}"
        ])
    
    summary_items.extend([
        f"Medical History: {st.session_state.responses.get('medical_history')}",
        f"Needs Emergency Contraception: {st.session_state.responses.get('emergency_contraception')}"
    ])
    
    patient_summary = "\n".join(summary_items)
    
    prompt_priority = (
        f"Patient's information summary:\n{patient_summary}\n\n"
        f"Based on this information, classify the patient into exactly one of these priority categories:\n"
        f"1. 'Urgent' - for patients with severe symptoms requiring immediate attention\n"
        f"2. 'Routine Symptoms' - for patients with mild symptoms that are not urgent\n"
        f"3. 'Routine No Symptoms' - for patients seeking screening with no symptoms\n"
        f"4. 'Contraception Referral' - for patients primarily needing emergency contraception\n\n"
        f"Provide only the priority level in this format: 'Priority Level: [Category]'"
    )
    
    system_role = "You are a sexual health triage assistant. Classify patients based on their symptoms and needs."
    messages = [{"role": "system", "content": system_role}]
    
    # Only call the API if we haven't done it already
    if "classification_response" not in st.session_state:
        with st.spinner("Analyzing patient information..."):
            messages.append({"role": "user", "content": prompt_priority})
            classification_response = generate_openai_response("", messages)
            st.session_state.classification_response = classification_response
    else:
        classification_response = st.session_state.classification_response
    
    st.write(f"{t('triage_classification')}:")
    
    try:
        # Parse the response
        response_text = classification_response.lower()
        
        # Extract priority
        priority = None
        priority_terms = ["urgent", "routine symptoms", "routine no symptoms", "contraception referral"]
        
        for term in priority_terms:
            if term in response_text:
                priority = term.title()
                break
                
        # Set default Face-to-Face mode
        mode = "Face-to-Face"
            
        if not priority:
            # Fallback logic
            if needs_contraception:
                priority = "Contraception Referral"
            elif has_symptoms:
                priority = "Routine Symptoms"
            else:
                priority = "Routine No Symptoms"
            
    except Exception as e:
        st.write(f"Error parsing classification: {e}")
        # Fallback logic
        if needs_contraception:
            priority = "Contraception Referral"
        elif has_symptoms:
            priority = "Routine Symptoms"
        else:
            priority = "Routine No Symptoms"
        
        mode = "Face-to-Face"  # Default consultation mode
    
    # Display the results
    st.write(f"{t('determined_priority')} {priority}")
    
    # Store for later use
    st.session_state.priority = priority
    st.session_state.recommended_mode = "Face-to-Face"
    
    # Add a button to continue to the next step
    if st.button(t("next")):
        st.session_state.current_step = 15
        # Clear the stored response for future use
        if "classification_response" in st.session_state:
            del st.session_state.classification_response
        st.rerun()

# Step 15: Additional Booking Details
elif st.session_state.current_step == 15:
    st.header(t("booking_details"))
    st.write(t("booking_details_text"))
    clinic = st.selectbox(t("clinic_location"), CLINIC_LOCATIONS)
    time_preference = st.selectbox(t("time_preference"), ["Morning", "Day", "Evening"])
    
    # Modified: Setting Face-to-Face as default without offering selection
    mode_of_consultation = CONSULTATION_MODES[0]  # Always "Face-to-Face"
    
    # Add translator option
    needs_translator = st.radio(t("needs_translator"), [t("yes"), t("no")], key="needs_translator_input")
    
    # If translator is needed, show language selection
    translator_language = None
    if needs_translator == t("yes"):
        translator_language = st.selectbox(t("translator_language"), ["English", "Français", "Español", "Deutsch", "العربية", "中文", "हिंदी", "Português"], key="translator_language_input")
    
    # Add phone number field
    phone_number = st.text_input(t("phone_number"), placeholder=t("phone_placeholder"))
    
    if st.button(t("submit")):
        st.session_state.clinic = clinic
        st.session_state.time_preference = time_preference
        st.session_state.mode_of_consultation = mode_of_consultation
        st.session_state.phone_number = phone_number
        st.session_state.needs_translator = needs_translator
        st.session_state.translator_language = translator_language if needs_translator == t("yes") else None
        st.session_state.current_step = 16
        st.rerun()

# Step 16: Appointment Slot Selection & Booking
elif st.session_state.current_step == 16:
    st.header(t("appointment_booking"))
    # Initialize and populate DB
    init_db()
    populate_slots()
    conn = sqlite3.connect('appointments.db')
    c = conn.cursor()

    # Save appointment in the database with all collected data
    symptoms_summary = ""
    for key, value in st.session_state.responses.items():
        symptoms_summary += f"{key}: {value}\n"

    c.execute('''INSERT INTO appointments 
                (name, priority, clinic, time_preference, mode_of_consultation, phone_number, 
                 symptoms_summary, severity_classification, date_of_birth, has_symptoms, 
                 emergency_contraception, needs_translator, translator_language)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (st.session_state.responses.get('name'),
               st.session_state.priority,
               st.session_state.clinic,
               st.session_state.time_preference,
               st.session_state.mode_of_consultation,
               st.session_state.phone_number,
               symptoms_summary.strip(),
               st.session_state.priority,  # Using priority as severity classification
               st.session_state.responses.get('date_of_birth'),
               st.session_state.responses.get('has_symptoms'),
               st.session_state.responses.get('emergency_contraception'),
               st.session_state.needs_translator,
               st.session_state.translator_language))
    conn.commit()

    st.write(t("choose_slot"))
    # Determine time range based on time preference
    if st.session_state.time_preference == "Morning":
        start_hour, end_hour = 8, 11
    elif st.session_state.time_preference == "Day":
        start_hour, end_hour = 11, 17
    elif st.session_state.time_preference == "Evening":
        start_hour, end_hour = 17, 19
    else:
        start_hour, end_hour = 8, 19

    available_slots = []
    for hour in range(start_hour, end_hour):
        for minute in range(0, 60, 15):
            time_str = f"{hour:02}:{minute:02}"
            # Match by priority and consultation mode
            c.execute('''SELECT id, clinic, time FROM available_slots 
                        WHERE clinic = ? AND time = ? 
                          AND priority = ? 
                          AND mode_of_consultation = ? 
                          AND is_booked = 0''',
                      (st.session_state.clinic, time_str, 
                       st.session_state.priority, 
                       st.session_state.mode_of_consultation))
            slots = c.fetchall()
            available_slots.extend(slots)

    if available_slots:
        st.write(t("available_slots"))
        slot_options = {slot[0]: f"Clinic: {slot[1]}, Time: {slot[2]}" for slot in available_slots}
        selected_slot_id = st.selectbox(t("select_slot"), list(slot_options.keys()),
                                        format_func=lambda x: slot_options[x])
        if st.button(t("book")):
            c.execute("UPDATE available_slots SET is_booked = 1 WHERE id = ?", (selected_slot_id,))
            conn.commit()
            st.success(t("booking_success").format(slot_id=selected_slot_id))
            if st.session_state.responses.get('emergency_contraception') == t("yes"):
                st.markdown("[Click here for more information on emergency contraception](https://www.nhs.uk/contraception/emergency-contraception/)")
    else:
        st.warning(t("no_slots"))
    conn.close()