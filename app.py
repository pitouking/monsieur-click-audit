from flask import Flask, request, jsonify, send_file, render_template_string
import trafilatura
from bs4 import BeautifulSoup
import csv
import io
import time
import requests

app = Flask(__name__)

# --- CONFIGURATION CHARTE MONSIEUR CLICK ---
# Remplace l'URL du logo par le tien si nécessaire
LOGO_URL = "https://monsieurclick.com/wp-content/uploads/2023/05/logo-monsieur-click.png" 

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Audit SEO | Monsieur Click</title>
    <style>
        :root { 
            --mc-blue: #0056b3; 
            --mc-light-blue: #eef4ff;
            --mc-dark: #1a1a1a;
            --green: #2ecc71; 
            --red: #e74c3c; 
        }
        
        body { 
            font-family: 'Inter', -apple-system, sans-serif; 
            background: #f8fafc; 
            margin: 0; padding: 40px 20px; color: var(--mc-dark); 
        }

        .container { 
            max-width: 1100px; margin: 0 auto; background: white; 
            padding: 40px; border-radius: 16px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.05); 
        }

        .brand-header { text-align: center; margin-bottom: 40px; }
        .brand-header img { max-width: 220px; margin-bottom: 15px; }
        .brand-header h1 { font-size: 1.8rem; margin: 0; color: var(--mc-blue); }

        .search-area { 
            display: flex; gap: 12px; background: var(--mc-light-blue); 
            padding: 20px; border-radius: 12px; margin-bottom: 40px;
        }

        input { 
            flex: 1; padding: 16px; border: 2px solid white; 
            border-radius: 8px; font-size: 16px; outline: none;
            box-shadow: 0 2px 5px rgba(0,0,0,0.02);
        }

        button.btn-main { 
            padding: 16px 32px; background: var(--mc-blue); color: white; 
            border: none; border-radius: 8px; cursor: pointer; 
            font-weight: 700; transition: 0.2s;
        }

        button.btn-main:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,86,179,0.3); }

        .kpi-grid { 
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 20px; margin-bottom: 40px; 
        }

        .kpi-card { 
            padding: 25px; border-radius: 12px; background: white; 
            border: 1px solid #f0f0f0; text-align: center; 
            transition: 0.3s; position: relative; overflow: hidden;
        }

        .kpi-card::after { 
            content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 6px; background: #ddd; 
        }

        .kpi-card.good::after { background: var(--green); }
        .kpi-card.bad::after { background: var(--red); }

        .kpi-card h4 { margin: 0; color: #7f8c8d; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; }
        .kpi-card .value { font-size: 1.8rem; font-weight: 800; margin: 10px 0; display: block; }
        .kpi-card .status-text { font-size: 0.85rem; font-weight: 600; }

        .data-section { margin-top: 40px; }
        .data-header { 
            display: flex; justify-content: space-between; align-items: center; 
            border-bottom: 2px solid #f4f7f9; margin-bottom: 20px; padding-bottom: 10px;
        }

        .scroll-box { 
            background: #fdfdfd; padding: 25px; border-radius: 12px; 
            border: 1px solid #f1f1f1; max-height: 400px; overflow-y: auto; 
        }

        .hn-row { 
            display: flex; gap: 20px; padding: 12px 0; border-bottom: 1px solid #f5f5f5; 
            align-items: baseline;
        }

        .hn-badge { 
            background: var(--mc-light-blue); color: var(--mc-blue); 
            padding: 4px 10px; border-radius: 4px; font-weight: 800; font-size: 0.75rem;
        }

        #loader { display: none; text-align: center; padding: 20px; color: var(--mc-blue); font-weight: 600; }
    </style>
</head>
<body>

<div class="container">
    <div class="brand-header">
        <img src="{{ logo_url }}" alt="Monsieur Click">
        <h1>Analyseur de Performance SEO</h1>
    </div>

    <div class="search-area">
        <input type="url" id="urlInput" placeholder="https://www.exemple-client.fr" required>
        <button class="btn-main" onclick="runAudit()">Analyser maintenant</button>
    </div>

    <div id="loader">� Monsieur Click analyse la page...</div>

    <div id="results" style="display:none;">
        <div class="kpi-grid" id="kpiGrid"></div>

        <div class="data-section">
            <div class="data-header">
                <h3>Structure Sémantique (Hn)</h3>
                <button onclick="downloadCSV()" style="background:var(--green); color:white; border:none; padding:8px 15px; border-radius:5px; cursor:pointer;">Export CSV</button>
            </div>
            <div id="headingsBox" class="scroll-box"></div>
        </div>

        <div class="data-section">
            <div class="data-header"><h3>Contenu Principal Extrait</h3></div>
            <div id="textBox" class="scroll-box" style="color:#666; line-height:1.8;"></div>
        </div>
    </div>
</div>

<script>
    let lastData = null;

    async function runAudit() {
        const url = document.getElementById('urlInput').value;
        if(!url) return;

        document.getElementById('loader').style.display = 'block';
        document.getElementById('results').style.display = 'none';

        try {
            const res = await fetch('/api/extract', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url})
            });
            lastData = await res.json();
            renderUI(lastData);
        } catch (e) {
            alert("Erreur d'analyse. Vérifiez l'URL.");
        } finally {
            document.getElementById('loader').style.display = 'none';
        }
    }

    function renderUI(data) {
        const m = data.metadata;
        document.getElementById('results').style.display = 'block';
        
        const config = [
            {label: "SSL", val: m.is_https ? "Sécurisé" : "Non sécurisé", status: m.is_https ? 'good' : 'bad'},
            {label: "Chargement", val: m.response_time + "s", status: m.response_time < 1.2 ? 'good' : 'bad'},
            {label: "Titre SEO", val: m.title_len + " car.", status: (m.title_len > 30 && m.title_len < 65) ? 'good' : 'bad'},
            {label: "Contenu", val: m.word_count + " mots", status: m.word_count > 300 ? 'good' : 'bad'}
        ];

        document.getElementById('kpiGrid').innerHTML = config.map(c => `
            <div class="kpi-card ${c.status}">
                <h4>${c.label}</h4>
                <span class="value">${c.val}</span>
                <span class="status-text">${c.status === 'good' ? '✅ Optimal' : '⚠️ À corriger'}</span>
            </div>
        `).join('');

        document.getElementById('headingsBox').innerHTML = data.headings.map(h => `
            <div class="hn-row"><span class="hn-badge">${h.type}</span> <span>${h.text}</span></div>
        `).join('');

        document.getElementById('textBox').innerText = data.content;
    }

    async function downloadCSV() {
        const res = await fetch('/api/export', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({headings: lastData.headings})
        });
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = "audit-monsieur-click.csv"; a.click();
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
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'MonsieurClickBot/1.0'})
        resp_time = round(time.time() - start, 2)
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        title = soup.title.string if soup.title else ""
        desc_tag = soup.find('meta', attrs={'name': 'description'})
        desc = desc_tag.get('content', '') if desc_tag else ""
        
        main_text = trafilatura.extract(resp.text) or ""
        
        headings = []
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            for i, h in enumerate(soup.find_all(tag)):
                headings.append({
                    "url": url, "type": tag.upper(), 
                    "text": h.get_text().strip(), "position": i + 1
                })

        return jsonify({
            "metadata": {
                "title_len": len(title),
                "desc_len": len(desc),
                "word_count": len(main_text.split()),
                "response_time": resp_time,
                "is_https": url.startswith('https')
            },
            "headings": headings,
            "content": main_text
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/export', methods=['POST'])
def export():
    data = request.json.get('headings')
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["url", "type", "text", "position"])
    writer.writeheader()
    writer.writerows(data)
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    return send_file(mem, mimetype='text/csv', as_attachment=True, download_name="audit_monsieur_click.csv")

if __name__ == '__main__':
    app.run(debug=True, port=5000)
