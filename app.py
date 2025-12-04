from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import datetime
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='static')
CORS(app)

# ---------------- MONGODB CONNECTION ----------------
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')

try:
    client = MongoClient(MONGODB_URI)
    db = client['survey_db']
    collection = db['reports']
    client.server_info()
    print("Successfully connected to MongoDB.")
except Exception as e:
    print(f"Error: Could not connect to MongoDB. Details: {e}")
    client = None


# ---------------- SERVE FRONT-END ----------------
@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html')


# ---------------- API ENDPOINT ----------------
@app.route('/final-report', methods=['POST'])
def final_report():
    if not client:
        return jsonify({
            'status': 'error',
            'message': 'Database connection is not available.'
        }), 500

    data = request.get_json(force=True)

    user_id = data.get('userId', 'anonymous')
    option_logs = data.get('option_logs', [])
    answers = data.get('answers', {})
    feedback = data.get('feedback', "")

    events = []
    for log in option_logs:
        if 'question' in log and 'value' in log:
            events.append({
                'question': log['question'],
                'answer': log['value'],
                'timestamp': datetime.datetime.utcfromtimestamp(
                    log.get('time', 0) / 1000.0
                )
            })

    total_time_sec = 0
    if events:
        timestamps = [ev['timestamp'] for ev in events]
        total_time_sec = (max(timestamps) - min(timestamps)).total_seconds()

    report_document = {
        'userId': user_id,
        'formId': data.get('formId', None),
        'createdAt': datetime.datetime.utcnow(),
        'events': events,
        'final_answers': answers,
        'total_time_seconds': round(total_time_sec, 2),
        'feedback': feedback,
        #'authentic': False,
    }

    try:
        result = collection.insert_one(report_document)
        return jsonify({
            'status': 'success',
            'message': 'Report saved to MongoDB.',
            'report_id': str(result.inserted_id)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to save report to database. Details: {e}'
        }), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

