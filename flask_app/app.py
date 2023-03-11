from flask import Flask, jsonify, render_template

app = Flask(__name__)

@app.route('/')
def hello_world():
    # return jsonify({"message": "Hello, World!"})
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
