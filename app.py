import os
import csv
import json
from flask import Flask, request, jsonify, render_template
import google.generativeai as genai

app = Flask(__name__)

# Configure Gemini API using the provided key
API_KEY = "AIzaSyAi_PRBLRF0Mwt9yPFEUXJrhbMru8MN-G0"
genai.configure(api_key=API_KEY)

def select_model():
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        print(f"Available models: {available_models}")
        
        # Priority list
        for target in ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro']:
            if target in available_models:
                print(f"Selecting model: {target}")
                return genai.GenerativeModel(target)
        
        # Fallback to the first available if none of the priority list match
        if available_models:
            print(f"Selecting fallback model: {available_models[0]}")
            return genai.GenerativeModel(available_models[0])
            
    except Exception as e:
        print(f"Error listing models: {e}")
    
    # Ultimate fallback (classic name)
    return genai.GenerativeModel('gemini-pro')

model = select_model()

CSV_FILE = 'output.csv'
CSV_HEADERS = ['Name', 'Age', 'Profession', 'Skills', 'Location', 'Other Notes']

def initialize_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(CSV_HEADERS)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/extract', methods=['POST'])
def extract_profile():
    data = request.json
    profile_text = data.get('profile_text')
    
    if not profile_text:
        return jsonify({'error': 'Profile text is required'}), 400

    prompt = f"""
    You are an expert data extractor. Extract the following information from the provided unstructured profile text and return ONLY a valid JSON object with the following exact keys (case-sensitive):
    "Name", "Age", "Profession", "Skills", "Location", "Other Notes".
    
    Rules:
    - Return ONLY the raw JSON object.
    - If a field is not found, return an empty string "" for its value.
    - Skills should be provided as a comma-separated string if there are multiple.
    - Do not wrap the JSON in Markdown formatting (no ```json).

    Profile Text:
    {profile_text}
    """
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean up markdown code blocks if any exist despite instructions
        if response_text.startswith("```"):
            lines = response_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            response_text = "\n".join(lines).strip()
            
        extracted_data = json.loads(response_text)
        
        # Ensure all columns are present
        row = [extracted_data.get(key, "") for key in CSV_HEADERS]
        
        # Append to CSV
        with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(row)
            
        return jsonify({
            'success': True,
            'extracted_data': extracted_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    initialize_csv()
    app.run(debug=True, port=5000)
