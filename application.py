from flask import Flask, render_template

application = Flask(__name__)
app = application


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/ical', methods=['POST'])
def matches(results=None):
    results = results or []
    return render_template('ical.html', results=results)
