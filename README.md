# Sexual Health Screening Assistant

A multilingual Streamlit application that provides automated sexual health screening and appointment booking with AI-powered triage classification.

## Overview

This system assists patients in:
- Completing comprehensive sexual health questionnaires
- Getting AI-powered triage classification based on symptoms and risk factors
- Booking appointments at sexual health clinics
- Receiving care in multiple languages with translator support

## Features

### Patient Interface ([app.py](app.py))
- **Multi-step Registration**: Guided form collecting patient demographics, symptoms, and medical history
- **AI Triage Classification**: Uses Gemini LLM to classify patients into priority categories:
  - Urgent (severe symptoms requiring immediate attention)
  - Routine Symptoms (mild symptoms, non-urgent)
  - Routine No Symptoms (screening without symptoms)
  - Contraception Referral (emergency contraception needs)
- **Appointment Booking**: Matches patients with appropriate time slots based on priority and preferences
- **Multilingual Support**: Available in English and French with translator options
- **Emergency Contraception**: Direct guidance and NHS resource links

### Healthcare Provider Interface ([app_gp.py](app_gp.py))
- **Patient Summary View**: Access saved patient appointments and profiles
- **AI-Formatted Profiles**: Clean, professional patient summaries for healthcare providers
- **Multilingual Provider Support**: Switch between languages for diverse healthcare teams

### Database Management
- SQLite database storing patient appointments and available clinic slots
- Automatic slot generation for multiple clinic locations
- Booking management with slot availability tracking

## Supported Clinic Locations
- Jefferiss Wing Sexual Health Clinic, W2 1NY
- 56 Dean Street, W1D 6AQ  
- John Hunter Clinic, SW10 9NH

## Installation

1. Clone this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up your Gemini API key:

Linux/Mac:
```bash
export GEMINI_API_KEY=your_api_key_here
```

Windows:
```bash
set GEMINI_API_KEY=your_api_key_here
```

## Usage

### Patient Screening and Booking
```bash
streamlit run app.py
```

### Healthcare Provider Dashboard
```bash
streamlit run app_gp.py
```

## System Architecture

- **Frontend**: Streamlit web interface with multi-step forms
- **AI Integration**: Google Gemini API for triage classification and text formatting
- **Database**: SQLite for appointment and slot management
- **Languages**: Python with pandas for data handling

## Language Support

Currently supports:
- English
- Français (French)
- Additional language frameworks ready for: Español, Deutsch, العربية, 中文, हिंदी, Português

## Safety Notice

This is a demonstration system and not a substitute for professional medical care. In an emergency, call **999** or visit A&E immediately.