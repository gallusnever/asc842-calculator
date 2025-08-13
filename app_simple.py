"""
ASC 842 Calculator - Simple Demo Version
"""
from flask import Flask, render_template, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    """Main calculator interface"""
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    """Mock calculation endpoint"""
    return jsonify({
        'status': 'success',
        'message': 'Calculator is ready for deployment. Full functionality requires pandas installation.',
        'classification': 'Finance Lease (Demo)',
        'present_value': '$100,000',
        'note': 'This is a demo version. Install pandas for full calculations.'
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)