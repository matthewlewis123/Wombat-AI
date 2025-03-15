import re
import os
import random
import sqlite3
import pandas as pd
import streamlit as st
from openai import OpenAI


#############################
# Global Constants & Setup
#############################

CLINIC_LOCATIONS = [
    "Mortimer Market Sexual Health Centre, WC1E 6JB",
    "Dean Street Sexual Health Clinic, W1D 6AQ",
    "Archway Sexual Health Clinic, N19 5NF"
]
CONSULTATION_MODES = ["Telephone", "Face-to-Face"]
#openai_model = "gpt-4o-mini"
gemini_model = "gemini-2.0-flash"
#gemini_model = "gemini-2.0-pro-exp-02-05"
# Initialize OpenAI client
#client = OpenAI()
gemini_api_key = os.getenv("GEMINI_API_KEY")
google_client = OpenAI(api_key=gemini_api_key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")


##############################################
# Database Functions (from Sam and Matthew)
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
                 symptoms_summary TEXT,
                 severity_classification TEXT
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
    priorities = ["High", "Medium", "Low"]
    modes = CONSULTATION_MODES
    clinics = CLINIC_LOCATIONS
    start_time = 8 * 60  # 8 AM in minutes
    end_time = 19 * 60   # 7 PM in minutes
    for clinic in clinics:
        for t in range(start_time, end_time, 15):
            hour = t // 60
            minute = t % 60
            time_str = f"{hour:02}:{minute:02}"
            for priority in priorities:
                for mode in modes:
                    slots.append((clinic, time_str, priority, mode))
    c.executemany('''INSERT INTO available_slots (clinic, time, priority, mode_of_consultation)
                     VALUES (?, ?, ?, ?)''', slots)
    conn.commit()
    conn.close()

def get_appointments():
    conn = sqlite3.connect('appointments.db')
    c = conn.cursor()
    c.execute('SELECT * FROM appointments')
    rows = c.fetchall()
    conn.close()
    appointments = [
        {
            'id': row[0],
            'name': row[1],
            'priority': row[2],
            'clinic': row[3],
            'time_preference': row[4],
            'mode_of_consultation': row[5],
            'symptoms_summary': row[6],
            'severity_classification': row[7]
        } for row in rows
    ]
    return appointments

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
# Streamlit UI - Integrated Multi-Step Triage & Booking
##############################################


# -----------------------------
# 2. SIDEBAR & HEADER
# -----------------------------
st.sidebar.image(
    r"NHS Logo.png",
    use_container_width=True
)

# -----------------------------
# 3. SESSION STATE INIT
# -----------------------------
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





# Add after SESSION STATE INIT section

# -----------------------------
# 3.1 LANGUAGE SUPPORT
# -----------------------------
# Dictionary of translations
TRANSLATIONS = {
    "English": {
        # Page titles
        "page_title": "Wombat GP Virtual Healthcare Assistant",
        "sidebar_title": "Wombat GP Practice",
        "warning": "This is a demonstration system and not a substitute for professional medical care. In an emergency, call **999** or visit A&E immediately.",
        
        # Form steps
        "registration": "Patient Registration",
        "full_name": "Enter your full name:",
        "presenting_complaint_header": "Triage: Presenting Complaint",
        "symptoms_desc": "Describe your symptoms and duration:",
        "followup_header": "Triage: Follow-up Question",
        "followup_label": "Your Answer:",
        "demographics": "Triage: Patient Demographics",
        "age": "What is your age?",
        "sex": "What is your sex?",
        "medical_history": "Triage: Medical History",
        "past_history": "Do you have any past medical or surgical history?",
        "family_history_header": "Triage: Family History",
        "family_history": "Do you have any relevant family history?",
        "medications_header": "Triage: Medications",
        "medications": "Do you take any regular medications?",
        "allergies_header": "Triage: Allergies",
        "allergies": "Do you have any allergies?",
        "investigations_header": "Triage: Investigations",
        "investigations": "Have you had any relevant imaging, blood tests, or investigations?",
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
        "select_slot": "Select Slot ID:",
        "no_slots": "No available slots matching your criteria.",
        "booking_success": "Appointment booked successfully for slot ID {slot_id}!",
        
        # Buttons
        "next": "Next",
        "confirm": "Confirm Summary",
        "submit": "Submit Booking Details",
        "book": "Book Appointment",
    },
    "French": {
        # Page titles
        "page_title": "Assistant Virtuel de Santé Wombat GP",
        "sidebar_title": "Cabinet Médical Wombat GP",
        "warning": "Ceci est un système de démonstration et ne remplace pas les soins médicaux professionnels. En cas d'urgence, appelez le **999** ou rendez-vous immédiatement aux urgences.",
        
        # Form steps
        "registration": "Inscription du Patient",
        "full_name": "Entrez votre nom complet :",
        "presenting_complaint_header": "Triage : Motif de Consultation",
        "symptoms_desc": "Décrivez vos symptômes et leur durée :",
        "followup_header": "Triage : Question Complémentaire",
        "followup_label": "Votre Réponse :",
        "demographics": "Triage : Données Démographiques",
        "age": "Quel est votre âge ?",
        "sex": "Quel est votre sexe ?",
        "medical_history": "Triage : Antécédents Médicaux",
        "past_history": "Avez-vous des antécédents médicaux ou chirurgicaux ?",
        "family_history_header": "Triage : Antécédents Familiaux",
        "family_history": "Avez-vous des antécédents familiaux pertinents ?",
        "medications_header": "Triage : Médicaments",
        "medications": "Prenez-vous des médicaments régulièrement ?",
        "allergies_header": "Triage : Allergies",
        "allergies": "Avez-vous des allergies ?",
        "investigations_header": "Triage : Examens",
        "investigations": "Avez-vous eu des examens d'imagerie, des analyses de sang ou d'autres examens pertinents ?",
        "summary": "Résumé du Patient",
        "triage_classification": "Classification du Triage",
        "determined_priority": "Priorité Déterminée :",
        "recommended_mode": "Mode de Consultation Recommandé :",
        "booking_details": "Détails Supplémentaires du Rendez-vous",
        "booking_details_text": "Veuillez sélectionner les détails supplémentaires pour votre rendez-vous :",
        "clinic_location": "Choisissez un lieu de clinique :",
        "time_preference": "Moment de la journée préféré :",
        "consultation_mode": "Mode de consultation préféré :",
        "appointment_booking": "Prise de Rendez-vous",
        "choose_slot": "Choisissez votre créneau de rendez-vous :",
        "available_slots": "Créneaux de rendez-vous disponibles :",
        "select_slot": "Sélectionnez l'ID du créneau :",
        "no_slots": "Aucun créneau disponible correspondant à vos critères.",
        "booking_success": "Rendez-vous réservé avec succès pour l'ID de créneau {slot_id} !",
        
        # Buttons
        "next": "Suivant",
        "confirm": "Confirmer le Résumé",
        "submit": "Soumettre les Détails",
        "book": "Réserver le Rendez-vous",
    }
}

# Add language selector to session state
if "language" not in st.session_state:
    st.session_state.language = "English"

# Function to get translated text
def t(key):
    return TRANSLATIONS[st.session_state.language].get(key, key)

# Add after SIDEBAR & HEADER section, before the title
language_selector = st.sidebar.selectbox(
    "Language / Langue:",
    ["English", "French"],
    key="language_selector",
    on_change=lambda: setattr(st.session_state, "language", st.session_state.language_selector)
)

# Now update the title and warning to use translations
st.title(t("page_title"))
st.warning(t("warning"))

# Modify the sidebar title to use translation
st.sidebar.title(t("sidebar_title"))









# Replace all steps in MULTI-STEP FORM LOGIC section with:

# -----------------------------
# 4. MULTI-STEP FORM LOGIC
# -----------------------------
# Step 1: Patient Name
if st.session_state.current_step == 1:
    st.header(t("registration"))
    name = st.text_input(t("full_name"), key="patient_name")
    if st.button(t("next")) and name:
        st.session_state.responses["name"] = name
        st.session_state.current_step = 2
        st.rerun()

# Step 2: Presenting Complaint - modify to go directly to step 3 (previously step 4)
if st.session_state.current_step == 2:
    st.header(t("presenting_complaint_header"))
    complaint = st.text_area(t("symptoms_desc"), key="presenting_complaint")
    if st.button(t("next")) and complaint:
        st.session_state.responses["presenting_complaint"] = complaint
        # Change to step 3 (previously step 4)
        st.session_state.current_step = 3
        st.rerun()

# Step 3: Patient Age (previously step 4)
if st.session_state.current_step == 3:
    st.header(t("demographics"))
    age = st.text_input(t("age"), key="patient_age")
    if st.button(t("next")) and age:
        st.session_state.responses["age"] = age
        st.session_state.current_step = 4
        st.rerun()

# Add under the "English" section:
TRANSLATIONS["English"]["male"] = "Male"
TRANSLATIONS["English"]["female"] = "Female" 
TRANSLATIONS["English"]["other"] = "Other"

# Add under the "French" section:
TRANSLATIONS["French"]["male"] = "Homme"
TRANSLATIONS["French"]["female"] = "Femme"
TRANSLATIONS["French"]["other"] = "Autre"

# Then modify Step 4 to use a selectbox instead of a text input
# Step 4: Patient Sex
if st.session_state.current_step == 4:
    st.header(t("demographics"))
    sex_options = [t("male"), t("female"), t("other")]
    sex = st.selectbox(t("sex"), sex_options, key="patient_sex")
    if st.button(t("next")) and sex:
        st.session_state.responses["sex"] = sex
        st.session_state.current_step = 5
        st.rerun()

# Step 5: Past Medical/Surgical History (previously step 6)
if st.session_state.current_step == 5:
    st.header(t("medical_history"))
    history = st.text_area(t("past_history"), key="past_history")
    if st.button(t("next")) and history:
        st.session_state.responses["past_history"] = history
        st.session_state.current_step = 6
        st.rerun()

# Step 6: Family History
if st.session_state.current_step == 6:
    st.header(t("family_history_header"))
    family = st.text_area(t("family_history"), key="family_history")
    if st.button(t("next")) and family:
        st.session_state.responses["family_history"] = family
        st.session_state.current_step = 7
        st.rerun()

# Step 7: Medications
if st.session_state.current_step == 7:
    st.header(t("medications_header"))
    meds = st.text_area(t("medications"), key="medications")
    if st.button(t("next")) and meds:
        st.session_state.responses["medications"] = meds
        st.session_state.current_step = 8
        st.rerun()

# Step 8: Allergies
if st.session_state.current_step == 8:
    st.header(t("allergies_header"))
    allergies = st.text_area(t("allergies"), key="allergies")
    if st.button(t("next")) and allergies:
        st.session_state.responses["allergies"] = allergies
        st.session_state.current_step = 9
        st.rerun()

# Step 9: Investigations
if st.session_state.current_step == 9:
    st.header(t("investigations_header"))
    inv = st.text_area(t("investigations"), key="investigations")
    if st.button(t("next")) and inv:
        st.session_state.responses["investigations"] = inv
        st.session_state.current_step = 10
        st.rerun()


# Add these translations to the English section
TRANSLATIONS["English"]["name_label"] = "Name"
TRANSLATIONS["English"]["age_label"] = "Age"
TRANSLATIONS["English"]["sex_label"] = "Sex"
TRANSLATIONS["English"]["complaint_label"] = "Presenting Complaint"
TRANSLATIONS["English"]["past_history_label"] = "Past History"
TRANSLATIONS["English"]["family_history_label"] = "Family History"
TRANSLATIONS["English"]["medications_label"] = "Medications"
TRANSLATIONS["English"]["allergies_label"] = "Allergies"
TRANSLATIONS["English"]["investigations_label"] = "Investigations"

# Add these translations to the French section
TRANSLATIONS["French"]["name_label"] = "Nom"
TRANSLATIONS["French"]["age_label"] = "Âge"
TRANSLATIONS["French"]["sex_label"] = "Sexe"
TRANSLATIONS["French"]["complaint_label"] = "Motif de Consultation"
TRANSLATIONS["French"]["past_history_label"] = "Antécédents Médicaux"
TRANSLATIONS["French"]["family_history_label"] = "Antécédents Familiaux"
TRANSLATIONS["French"]["medications_label"] = "Médicaments"
TRANSLATIONS["French"]["allergies_label"] = "Allergies"
TRANSLATIONS["French"]["investigations_label"] = "Examens"


# Step 10: Summary Confirmation
if st.session_state.current_step == 10:
    st.header(t("summary"))
    summary = (
        f"{t('name_label')}: {st.session_state.responses.get('name')}\n"
        f"{t('age_label')}: {st.session_state.responses.get('age')}\n"
        f"{t('sex_label')}: {st.session_state.responses.get('sex')}\n"
        f"{t('complaint_label')}: {st.session_state.responses.get('presenting_complaint')}\n"
        f"{t('past_history_label')}: {st.session_state.responses.get('past_history')}\n"
        f"{t('family_history_label')}: {st.session_state.responses.get('family_history')}\n"
        f"{t('medications_label')}: {st.session_state.responses.get('medications')}\n"
        f"{t('allergies_label')}: {st.session_state.responses.get('allergies')}\n"
        f"{t('investigations_label')}: {st.session_state.responses.get('investigations')}\n"
    )
    st.text_area(t("summary"), value=summary, height=300)
    if st.button(t("confirm")):
        st.session_state.confirmed_summary = True
        st.session_state.current_step = 11
        st.rerun()

# Step 11: Triage Classification via GPT
if st.session_state.current_step == 11:
    st.header(t("triage_classification"))
    summary = (
        f"{t('name_label')}: {st.session_state.responses.get('name')}\n"
        f"{t('age_label')}: {st.session_state.responses.get('age')}\n"
        f"{t('sex_label')}: {st.session_state.responses.get('sex')}\n"
        f"{t('complaint_label')}: {st.session_state.responses.get('presenting_complaint')}\n"
        f"{t('past_history_label')}: {st.session_state.responses.get('past_history')}\n"
        f"{t('family_history_label')}: {st.session_state.responses.get('family_history')}\n"
        f"{t('medications_label')}: {st.session_state.responses.get('medications')}\n"
        f"{t('allergies_label')}: {st.session_state.responses.get('allergies')}\n"
        f"{t('investigations_label')}: {st.session_state.responses.get('investigations')}\n"
    )
    
    # Adjust prompt and system role based on language
    if st.session_state.language == "French":
        prompt_priority = (
            f"Résumé des symptômes du patient:\n{summary}\n"
            "Sur la base de ces informations, quel est le niveau de priorité (Faible, Moyen, Élevé) et le mode de consultation recommandé (Téléphone, En personne)? "
            "Fournissez uniquement le niveau de priorité et le mode de consultation dans un format court. "
            "Par exemple: 'Niveau de Priorité: Moyen, Mode de Consultation: Téléphone'."
        )
        system_role = "Vous êtes un assistant de triage médical."
    else:
        prompt_priority = (
            f"Patient's symptoms summary:\n{summary}\n"
            "Based on this information, what is the priority level (Low, Medium, High) and the recommended consultation mode (Telephone, Face-to-Face)? "
            "Provide only the priority level and consultation mode in a short format. "
            "For example: 'Priority Level: Medium, Consultation Mode: Telephone'."
        )
        system_role = "You are a triage assistant."
    
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
        # Completely different approach to parsing the response
        response_text = classification_response.lower()
        
        # Extract priority
        priority = None
        if st.session_state.language == "French":
            priority_terms = ["faible", "moyen", "élevé", "haut", "urgent", "basse"]
        else:
            priority_terms = ["low", "medium", "high", "urgent"]
            
        for term in priority_terms:
            if term in response_text:
                priority = term.capitalize()
                # Map to standardized terms
                if priority.lower() in ["élevé", "haut", "high"]:
                    priority = "High" if st.session_state.language == "English" else "Élevé"
                elif priority.lower() in ["moyen", "medium"]:
                    priority = "Medium" if st.session_state.language == "English" else "Moyen"
                elif priority.lower() in ["faible", "low", "basse"]:
                    priority = "Low" if st.session_state.language == "English" else "Faible"
                break
                
        # Extract consultation mode
        mode = None
        if "telephone" in response_text or "téléphone" in response_text:
            mode = "Telephone" if st.session_state.language == "English" else "Téléphone"
        elif "face" in response_text or "personne" in response_text or "en personne" in response_text:
            mode = "Face-to-Face" if st.session_state.language == "English" else "En personne"
            
        if not priority or not mode:
            raise Exception("Could not parse response")
            
    except Exception as e:
        st.write(f"Error parsing classification: {e}")
        priority = "Medium" if st.session_state.language == "English" else "Moyen"
        mode = "Telephone" if st.session_state.language == "English" else "Téléphone"
    
    # Clear display - show only the relevant information
    st.write(f"{t('determined_priority')} {priority}")
    st.write(f"{t('recommended_mode')} {mode}")
    
    # Store parsed priority in session state for later use
    st.session_state.priority = priority
    st.session_state.recommended_mode = mode
    
    # Map French priority terms to English for internal processing
    priority_lower = priority.lower()
    if st.session_state.language == "French":
        if priority_lower in ["élevé", "haut", "urgent"]:
            st.session_state.triage_severity = "urgent"
        else:
            st.session_state.triage_severity = "routine"
    else:
        if priority_lower in ["high", "urgent"]:
            st.session_state.triage_severity = "urgent"
        else:
            st.session_state.triage_severity = "routine"
    
    # Add a button to continue to the next step
    if st.button(t("next")):
        st.session_state.current_step = 12
        # Clear the stored response for future use
        if "classification_response" in st.session_state:
            del st.session_state.classification_response
        st.rerun()

# Step 12: Additional Booking Details
if st.session_state.current_step == 12:
    st.header(t("booking_details"))
    st.write(t("booking_details_text"))
    clinic = st.selectbox(t("clinic_location"), CLINIC_LOCATIONS)
    time_preference = st.selectbox(t("time_preference"), ["Morning", "Day", "Evening"])
    mode_of_consultation = st.selectbox(t("consultation_mode"), CONSULTATION_MODES)
    if st.button(t("submit")):
        st.session_state.clinic = clinic
        st.session_state.time_preference = time_preference
        st.session_state.mode_of_consultation = mode_of_consultation
        st.session_state.current_step = 13
        st.rerun()

# Step 13: Appointment Slot Selection & Booking
if st.session_state.current_step == 13:
    st.header(t("appointment_booking"))
    # Initialize and populate DB
    init_db()
    populate_slots()
    conn = sqlite3.connect('appointments.db')
    c = conn.cursor()

    # Save appointment in the database with translated labels
    symptoms_summary = (
        f"{t('name_label')}: {st.session_state.responses.get('name')}\n"
        f"{t('age_label')}: {st.session_state.responses.get('age')}\n"
        f"{t('sex_label')}: {st.session_state.responses.get('sex')}\n"
        f"{t('complaint_label')}: {st.session_state.responses.get('presenting_complaint')}\n"
        f"{t('past_history_label')}: {st.session_state.responses.get('past_history')}\n"
        f"{t('family_history_label')}: {st.session_state.responses.get('family_history')}\n"
        f"{t('medications_label')}: {st.session_state.responses.get('medications')}\n"
        f"{t('allergies_label')}: {st.session_state.responses.get('allergies')}\n"
        f"{t('investigations_label')}: {st.session_state.responses.get('investigations')}\n"
    )

    c.execute('''INSERT INTO appointments (name, symptoms_summary, severity_classification, priority)
                 VALUES (?, ?, ?, ?)''',
              (st.session_state.responses.get('name'),
               symptoms_summary.strip(),
               st.session_state.triage_severity,
               st.session_state.priority))
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
            # IMPORTANT: We removed priority matching here:
            c.execute('''SELECT id, clinic, time FROM available_slots 
                         WHERE clinic = ? AND time = ? 
                           AND mode_of_consultation = ? 
                           AND is_booked = 0''',
                      (st.session_state.clinic, time_str, st.session_state.mode_of_consultation))
            slots = c.fetchall()
            available_slots.extend(slots)

    if available_slots:
        st.write(t("available_slots"))
        slot_options = {slot[0]: f"Slot ID: {slot[0]}, Clinic: {slot[1]}, Time: {slot[2]}" for slot in available_slots}
        selected_slot_id = st.selectbox(t("select_slot"), list(slot_options.keys()),
                                        format_func=lambda x: slot_options[x])
        if st.button(t("book")):
            c.execute("UPDATE available_slots SET is_booked = 1 WHERE id = ?", (selected_slot_id,))
            conn.commit()
            st.success(t("booking_success").format(slot_id=selected_slot_id))
    else:
        st.warning(t("no_slots"))
    conn.close()