from flask import Flask, request, jsonify
from flask_cors import CORS
import datetime
from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# --- MongoDB Connection Setup ---
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')

try:
    client = MongoClient(MONGODB_URI)
    db = client['survey_db']
    collection = db['reports']
    client.server_info() 
    print("Successfully connected to MongoDB.")
except Exception as e:
    print(f"Error: Could not connect to MongoDB. Please ensure it's running. Details: {e}")
    client = None

@app.route('/final-report', methods=['POST'])
def final_report():
    if not client:
        return jsonify({'status': 'error', 'message': 'Database connection is not available.'}), 500

    data = request.get_json(force=True)

    # === NEW: Get userId from the incoming JSON data ===
    user_id = data.get('userId', 'anonymous')  # Default to 'anonymous' if not provided

    # === Raw data from client ===
    option_logs = data.get('option_logs', [])   # [{question, value, time}, ...]
    answers = data.get('answers', {})           # {"q1": "3", "q2": "4", ...}
    feedback = data.get('feedback', "")

    # === Build event list (better schema for sequential analysis) ===
    events = []
    for log in option_logs:
        if 'question' in log and 'value' in log:
            events.append({
                'question': log['question'],
                'answer': log['value'],
                'timestamp': datetime.datetime.utcfromtimestamp(log.get('time', 0) / 1000.0)
            })

    # === Calculate total time ===
    total_time_sec = 0
    if events:
        timestamps = [ev['timestamp'] for ev in events]
        total_time_sec = (max(timestamps) - min(timestamps)).total_seconds()

    # --- Prepare Document for MongoDB ---
    report_document = {
        'userId': user_id,
        'formId': data.get('formId', None),   # Optional: form identifier
        'createdAt': datetime.datetime.utcnow(),
        'events': events,                     # <-- all sequential logs
        'final_answers': answers,             # <-- summary at the end
        'total_time_seconds': round(total_time_sec, 2),
        'feedback': feedback,
        'authentic':False,                 #or True
    }

    # --- Insert into MongoDB ---
    try:
        result = collection.insert_one(report_document)
        return jsonify({
            'status': 'success',
            'message': 'Report saved to MongoDB.',
            'report_id': str(result.inserted_id)
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Failed to save report to database. Details: {e}'}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
