# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, send_file, render_template_string
import trafilatura
from bs4 import BeautifulSoup
import csv
import io
import time
import requests
import os

app = Flask(__name__)

# Configuration visuelle
LOGO_URL = "https://monsieurclick.com/wp-content/uploads/2023/05/logo-monsieur-click.png"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Audit SEO | Monsieur Click</title>
    <style>
        :root { --mc-blue: #0056b3; --mc-light-blue: #eef4ff; --mc-dark: #1a1a1a; --green: #2ecc71; --red: #e74c3c; }
        body { font-family: sans-serif; background: #f8fafc; margin: 0; padding: 40px 20px; color: var(--mc-dark); }
        .container { max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); }
        .header { text-align: center; margin-bottom: 30px; }
        .header img { max-width: 200px; }
        .search-area { display: flex; gap: 10px; background: var(--mc-light-blue); padding: 20px; border-radius: 8px; margin-bottom: 30px; }
        input { flex: 1; padding: 12px; border: 1px solid #ddd; border-radius: 6px; }
        button { padding: 12px 24px; background: var(--mc-blue); color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }
        .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 30px; }
        .kpi-card { padding: 20px; border-radius: 10px; background: white; border: 1px solid #eee; border-top: 5px solid #ccc; text-align: center; }
        .good { border-top-color: var(--green); }
        .bad { border-top-color: var(--red); }
        .scroll-box { background: #fafafa; padding: 20px; border-radius: 8px; border: 1px solid #eee; max-height: 300px; overflow-y: auto; }
        .hn-item { padding: 8px; border-bottom: 1px solid #eee; display: flex; gap: 10px; font-size: 0.9em; }
        .hn-tag { font-weight: bold; color: var(--mc-blue); min-width: 35px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="{{ logo_url }}" alt="Monsieur Click">
            <h1>Audit Flash SEO</h1>
        </div>
        <div class="search-area">
            <input type="url" id="urlInput" placeholder="https://www.exemple.fr" required>
            <button onclick="runAudit()">Analyser</button>
        </div>
        <div id="results" style="display:none;">
            <div class="kpi-grid" id="kpiGrid"></div>
            <h3>Structure des titres (Hn)</h3>
            <div id="headingsBox" class="scroll-box"></div>
            <h3>Contenu extrait</h3>
            <div id="textBox" class="scroll-box"></div>
        </div>
    </div>
    <script>
        async function runAudit() {
            const url = document.getElementById('urlInput').value;
            const res = await fetch('/api/extract', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url})
            });
            const data = await res.json();
            document.getElementById('results').style.display = 'block';
            const m = data.metadata;
            const kpis = [
                {l: "SSL", v: m.is_https ? "OUI" : "NON", s: m.is_https ? 'good' : 'bad'},
                {l: "Vitesse", v: m.response_time + "s", s: m.response_time < 1.2 ? 'good' : 'bad'},
                {l: "Titre SEO", v: m.title_len, s: (m.title_len > 30 && m.title_len < 65) ? 'good' : 'bad'},
                {l: "Mots", v: m.word_count, s: m.word_count > 300 ? 'good' : 'bad'}
            ];
            document.getElementById('kpiGrid').innerHTML = kpis.map(k => `
                <div class="kpi-card ${k.s}"><h4>${k.l}</h4><span>${k.v}</span></div>
            `).join('');
            document.getElementById('headingsBox').innerHTML = data.headings.map(h => `
                <div class="hn-item"><span class="hn-tag">${h.type}</span><span>${h.text}</span></div>
            `).join('');
            document.getElementById('textBox').innerText = data.content;
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, logo_url=LOGO_URL)

@app.route('/api/extract', methods=['POST'])
def extract():
    url = request.json.get('url')
    try:
        start = time.time()
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'MC-Bot/1.0'})
        resp_time = round(time.time() - start, 2)
        
        soup = BeautifulSoup(resp.content, 'html.parser')
        title = soup.title.string if soup.title else ""
        main_text = trafilatura.extract(resp.text) or ""
        
        headings = []
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            for i, h in enumerate(soup.find_all(tag)):
                headings.append({
                    "type": tag.upper(), "text": h.get_text().strip()
                })

        return jsonify({
            "metadata": {
                "title_len": len(title),
                "word_count": len(main_text.split()),
                "response_time": resp_time,
                "is_https": url.startswith('https')
            },
            "headings": headings,
            "content": main_text
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
