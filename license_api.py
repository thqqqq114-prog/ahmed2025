from flask import Flask, request, jsonify
import uuid
import hashlib

app = Flask(__name__)
licenses = {}  # تخزين التراخيص في الذاكرة (يمكن استبداله بقاعدة بيانات)

# دالة توليد بصمة الجهاز
def get_device_fingerprint(data):
    # مثال: استخدم رقم الهارد أو MAC Address أو بيانات يرسلها البرنامج
    return hashlib.sha256(data.encode()).hexdigest()

@app.route('/activate', methods=['POST'])
def activate():
    device_id = request.json.get('device_id')
    user = request.json.get('user')
    # توليد كود ترخيص فريد
    license_code = str(uuid.uuid4())
    fingerprint = get_device_fingerprint(device_id)
    licenses[license_code] = {
        'user': user,
        'device': fingerprint,
        'active': True
    }
    return jsonify({'license_code': license_code, 'status': 'activated'})

@app.route('/verify', methods=['POST'])
def verify():
    license_code = request.json.get('license_code')
    device_id = request.json.get('device_id')
    fingerprint = get_device_fingerprint(device_id)
    lic = licenses.get(license_code)
    if lic and lic['active'] and lic['device'] == fingerprint:
        return jsonify({'status': 'valid'})
    return jsonify({'status': 'invalid'})

@app.route('/deactivate', methods=['POST'])
def deactivate():
    license_code = request.json.get('license_code')
    lic = licenses.get(license_code)
    if lic:
        lic['active'] = False
        return jsonify({'status': 'deactivated'})
    return jsonify({'status': 'not_found'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
