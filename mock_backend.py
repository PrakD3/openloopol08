from flask import Flask, request, jsonify, Response
import time
import json
import random

app = Flask(__name__)

@app.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/analyze', methods=['POST', 'OPTIONS'])
def analyze():
    if request.method == 'OPTIONS':
        return '', 200
    
    data = request.json
    video_url = data.get('video_url', 'unknown')
    
    # Simulate processing time
    time.sleep(2)
    
    return jsonify({
        "verdict": "misleading",
        "credibility_score": 75,
        "summary": "Mock Analysis: This video appears to be a recirculated clip from 2021. Not a current disaster.",
        "key_flags": ["Recirculation Detected", "Date Inconsistency"]
    })

@app.route('/live-feed', methods=['GET'])
def live_feed():
    def generate():
        while True:
            # Send a fake alert every 10 seconds
            verdict = random.choice(["real", "misleading", "ai-generated"])
            data = {
                "video_id": f"mock_{int(time.time())}",
                "url": "https://youtube.com/watch?v=demo",
                "platform": "youtube",
                "verdict": verdict,
                "score": random.randint(60, 95),
                "summary": f"Live Demo: {verdict.upper()} event detected near monitoring zone.",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(10)

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    print("--- STARTING MOCK VIGILENS BACKEND (Flask) ---")
    print("Listening on http://localhost:8000")
    app.run(host='0.0.0.0', port=8000)
