import re
import random
import sqlite3
import pandas as pd
import streamlit as st
from openai import OpenAI


#############################
# Global Constants & Setup
#############################

CLINIC_LOCATIONS = [
    "Riverside Clinic, SE1 2RT",
    "Highgate Health Center, N6 5HG",
    "Greenwich Medical Hub, SE10 9LS"
]
CONSULTATION_MODES = ["Telephone", "Face-to-Face"]
openai_model = "gpt-4o-mini"

# Initialize OpenAI client
client = OpenAI()

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
    completion = client.chat.completions.create(
        model=openai_model,
        messages=messages,
        max_tokens=150,
        temperature=0.7,
    )
    response = completion.choices[0].message.content.strip()
    messages.append({"role": "assistant", "content": response})
    return response
















##############################################
# Streamlit UI - Integrated Multi-Step Triage & Booking
##############################################

# -----------------------------
# 1. PAGE CONFIG & STYLING
# -----------------------------
st.set_page_config(
    page_title="Wombat GP Virtual Healthcare Assistant",
    layout="centered",
    initial_sidebar_state="expanded"
)
st.markdown("""
<style>
/* Center page and limit width */
.main > .block-container {
    max-width: 900px;
    margin: 0 auto;
}
/* Chat messages styling */
.chat-message {
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 0.5rem 0;
}
.assistant-message {
    background-color: #f0f2f6;
}
.user-message {
    background-color: #dbefff;
    margin-left: 20%;
}
/* Headings in NHS Blue */
h1, h2, h3, h4 {
    color: #005EB8;
}
/* Scrollable chat container */
#chat-container {
    max-height: 300px;
    overflow-y: auto;
    margin-bottom: 1rem;
    padding-right: 1rem;
    border: 1px solid #ddd;
    border-radius: 0.5rem;
    background-color: #fff;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# 2. SIDEBAR & HEADER
# -----------------------------
st.sidebar.image(
    r"NHS Logo.png",
    use_container_width=True
)
st.sidebar.title("Wombat GP Practice")
st.sidebar.markdown("""
- **Start** a new consultation  
- **View** medical history (demo)  
- **Emergency** contact info  
""")
st.title("Wombat GP Virtual Healthcare Assistant")
st.warning("This is a demonstration system and not a substitute for professional medical care. In an emergency, call **999** or visit A&E immediately.")

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

# -----------------------------
# 4. MULTI-STEP FORM LOGIC
# -----------------------------
# Step 1: Patient Name
if st.session_state.current_step == 1:
    st.header("Patient Registration")
    name = st.text_input("Enter your full name:", key="patient_name")
    if st.button("Next") and name:
        st.session_state.responses["name"] = name
        st.session_state.current_step = 2
        st.rerun()

# Step 2: Presenting Complaint
if st.session_state.current_step == 2:
    st.header("Triage: Presenting Complaint")
    complaint = st.text_area("Describe your symptoms and duration:", key="presenting_complaint")
    if st.button("Next") and complaint:
        st.session_state.responses["presenting_complaint"] = complaint
        st.session_state.current_step = 3
        st.rerun()

# Step 3: Follow-up Question (via GPT)
if st.session_state.current_step == 3:
    st.header("Triage: Follow-up Question")
    messages = [
        {"role": "system", "content": "Generate one relevant follow-up question for a patient with this complaint."},
        {"role": "user", "content": f"Presenting complaint: {st.session_state.responses['presenting_complaint']}"}
    ]
    followup_q = generate_openai_response("", messages)
    st.write(f"Follow-up: {followup_q}")
    followup_ans = st.text_area("Your Answer:", key="followup_answer")
    if st.button("Next") and followup_ans:
        st.session_state.responses["followup_answer"] = followup_ans
        st.session_state.current_step = 4
        st.rerun()

# Step 4: Patient Age
if st.session_state.current_step == 4:
    st.header("Triage: Patient Demographics")
    age = st.text_input("What is your age?", key="patient_age")
    if st.button("Next") and age:
        st.session_state.responses["age"] = age
        st.session_state.current_step = 5
        st.rerun()

# Step 5: Patient Sex
if st.session_state.current_step == 5:
    st.header("Triage: Patient Demographics")
    sex = st.text_input("What is your sex?", key="patient_sex")
    if st.button("Next") and sex:
        st.session_state.responses["sex"] = sex
        st.session_state.current_step = 6
        st.rerun()

# Step 6: Past Medical/Surgical History
if st.session_state.current_step == 6:
    st.header("Triage: Medical History")
    history = st.text_area("Do you have any past medical or surgical history?", key="past_history")
    if st.button("Next") and history:
        st.session_state.responses["past_history"] = history
        st.session_state.current_step = 7
        st.rerun()

# Step 7: Family History
if st.session_state.current_step == 7:
    st.header("Triage: Family History")
    family = st.text_area("Do you have any relevant family history?", key="family_history")
    if st.button("Next") and family:
        st.session_state.responses["family_history"] = family
        st.session_state.current_step = 8
        st.rerun()

# Step 8: Medications
if st.session_state.current_step == 8:
    st.header("Triage: Medications")
    meds = st.text_area("Do you take any regular medications?", key="medications")
    if st.button("Next") and meds:
        st.session_state.responses["medications"] = meds
        st.session_state.current_step = 9
        st.rerun()

# Step 9: Allergies
if st.session_state.current_step == 9:
    st.header("Triage: Allergies")
    allergies = st.text_area("Do you have any allergies?", key="allergies")
    if st.button("Next") and allergies:
        st.session_state.responses["allergies"] = allergies
        st.session_state.current_step = 10
        st.rerun()

# Step 10: Investigations
if st.session_state.current_step == 10:
    st.header("Triage: Investigations")
    inv = st.text_area("Have you had any relevant imaging, blood tests, or investigations?", key="investigations")
    if st.button("Next") and inv:
        st.session_state.responses["investigations"] = inv
        st.session_state.current_step = 11
        st.rerun()

# Step 11: Summary Confirmation
if st.session_state.current_step == 11:
    st.header("Patient Summary")
    summary = (
        f"Name: {st.session_state.responses.get('name')}\n"
        f"Age: {st.session_state.responses.get('age')}\n"
        f"Sex: {st.session_state.responses.get('sex')}\n"
        f"Presenting Complaint: {st.session_state.responses.get('presenting_complaint')}\n"
        f"Follow-up Answer: {st.session_state.responses.get('followup_answer')}\n"
        f"Past History: {st.session_state.responses.get('past_history')}\n"
        f"Family History: {st.session_state.responses.get('family_history')}\n"
        f"Medications: {st.session_state.responses.get('medications')}\n"
        f"Allergies: {st.session_state.responses.get('allergies')}\n"
        f"Investigations: {st.session_state.responses.get('investigations')}\n"
    )
    st.text_area("Summary", value=summary, height=300)
    if st.button("Confirm Summary"):
        st.session_state.confirmed_summary = True
        st.session_state.current_step = 12
        st.rerun()

# Step 12: Triage Classification via GPT
if st.session_state.current_step == 12:
    st.header("Triage Classification")
    summary = (
        f"Name: {st.session_state.responses.get('name')}\n"
        f"Age: {st.session_state.responses.get('age')}\n"
        f"Sex: {st.session_state.responses.get('sex')}\n"
        f"Presenting Complaint: {st.session_state.responses.get('presenting_complaint')}\n"
        f"Follow-up Answer: {st.session_state.responses.get('followup_answer')}\n"
        f"Past History: {st.session_state.responses.get('past_history')}\n"
        f"Family History: {st.session_state.responses.get('family_history')}\n"
        f"Medications: {st.session_state.responses.get('medications')}\n"
        f"Allergies: {st.session_state.responses.get('allergies')}\n"
        f"Investigations: {st.session_state.responses.get('investigations')}\n"
    )
    prompt_priority = (
        f"Patient's symptoms summary:\n{summary}\n"
        "Based on this information, what is the priority level (Low, Medium, High) and the recommended consultation mode (Telephone, Face-to-Face)? "
        "Provide only the priority level and consultation mode in a short format. "
        "For example: 'Priority Level: Medium, Consultation Mode: Telephone'."
    )
    messages = [{"role": "system", "content": "You are a triage assistant."}]
    messages.append({"role": "user", "content": prompt_priority})
    classification_response = generate_openai_response("", messages)
    st.write("Triage Classification Response:")
    st.text(classification_response)
    try:
        priority_lines = classification_response.split("\n")
        priority = next(line.split(":")[1].strip() for line in priority_lines if "priority level" in line.lower())
        recommended_mode = next(line.split(":")[1].strip() for line in priority_lines if "consultation mode" in line.lower())
    except Exception as e:
        st.write(f"Error parsing classification: {e}")
        priority = "Medium"
        recommended_mode = "Telephone"
    st.write(f"Determined Priority: {priority}")
    st.write(f"Recommended Consultation Mode: {recommended_mode}")
    # Store parsed priority in session state for later use
    st.session_state.priority = priority
    # Use priority to determine triage severity
    if priority.lower() in ["high", "urgent"]:
        st.session_state.triage_severity = "urgent"
    elif priority.lower() in ["low", "medium"]:
        st.session_state.triage_severity = "routine"
    else:
        st.session_state.triage_severity = "routine"
    st.session_state.current_step = 13
    st.rerun()

# Step 13: Additional Booking Details
if st.session_state.current_step == 13:
    st.header("Additional Booking Details")
    st.write("Please select additional details for your appointment:")
    clinic = st.selectbox("Choose a clinic location:", CLINIC_LOCATIONS)
    time_preference = st.selectbox("Preferred time of day:", ["Morning", "Day", "Evening"])
    mode_of_consultation = st.selectbox("Preferred consultation mode:", CONSULTATION_MODES)
    if st.button("Submit Booking Details"):
        st.session_state.clinic = clinic
        st.session_state.time_preference = time_preference
        st.session_state.mode_of_consultation = mode_of_consultation
        st.session_state.current_step = 14
        st.rerun()

# Step 14: Appointment Slot Selection & Booking
if st.session_state.current_step == 14:
    st.header("Appointment Booking")
    # Initialize and populate DB
    init_db()
    populate_slots()
    conn = sqlite3.connect('appointments.db')
    c = conn.cursor()

    # Save appointment in the database
    symptoms_summary = (
        f"Name: {st.session_state.responses.get('name')}\n"
        f"Age: {st.session_state.responses.get('age')}\n"
        f"Sex: {st.session_state.responses.get('sex')}\n"
        f"Presenting Complaint: {st.session_state.responses.get('presenting_complaint')}\n"
        f"Follow-up Answer: {st.session_state.responses.get('followup_answer')}\n"
        f"Past History: {st.session_state.responses.get('past_history')}\n"
        f"Family History: {st.session_state.responses.get('family_history')}\n"
        f"Medications: {st.session_state.responses.get('medications')}\n"
        f"Allergies: {st.session_state.responses.get('allergies')}\n"
        f"Investigations: {st.session_state.responses.get('investigations')}\n"
    )

    # We still store priority in the appointments table (in case we want to keep track),
    # but we won't match it in the SELECT query below.
    c.execute('''INSERT INTO appointments (name, symptoms_summary, severity_classification, priority)
                 VALUES (?, ?, ?, ?)''',
              (st.session_state.responses.get('name'),
               symptoms_summary.strip(),
               st.session_state.triage_severity,
               st.session_state.priority))
    conn.commit()

    st.write("Choose your appointment slot:")
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
        st.write("Available appointment slots:")
        slot_options = {slot[0]: f"Slot ID: {slot[0]}, Clinic: {slot[1]}, Time: {slot[2]}" for slot in available_slots}
        selected_slot_id = st.selectbox("Select Slot ID:", list(slot_options.keys()),
                                        format_func=lambda x: slot_options[x])
        if st.button("Book Appointment"):
            c.execute("UPDATE available_slots SET is_booked = 1 WHERE id = ?", (selected_slot_id,))
            conn.commit()
            st.success(f"Appointment booked successfully for slot ID {selected_slot_id}!")
    else:
        st.warning("No available slots matching your criteria.")
    conn.close()
