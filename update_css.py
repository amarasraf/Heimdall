import re

file_path = 'templates/index.html'

with open(file_path, 'r', encoding='utf-8') as f:
    html = f.read()

new_css = """
  :root {
    --bg-base: #fdf2f8;
    --bg-surface: #ffffff;
    --card-border: rgba(236, 72, 153, 0.15);
    --card-glow: rgba(236, 72, 153, 0.1);
    --primary: #ec4899;
    --primary-hover: #db2777;
    --primary-light: #fbcfe8;
    --secondary: #f1f5f9;
    --secondary-hover: #e2e8f0;
    --text-main: #1e293b;
    --text-muted: #64748b;
    --success: #10b981;
    --error: #ef4444;
    --info: #3b82f6;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }
  
  body {
    font-family: 'Outfit', sans-serif;
    background-color: var(--bg-base);
    background-image: 
      radial-gradient(circle at 15% 50%, rgba(244, 114, 182, 0.2) 0%, transparent 50%),
      radial-gradient(circle at 85% 30%, rgba(251, 146, 60, 0.15) 0%, transparent 50%);
    background-attachment: fixed;
    color: var(--text-main);
    min-height: 100vh;
    padding: 40px 20px;
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .header {
    text-align: center;
    margin-bottom: 50px;
    margin-top: 20px;
    animation: fadeInDown 0.8s ease;
  }
  .header h1 {
    font-size: 3.5rem;
    font-weight: 800;
    margin-bottom: 15px;
    letter-spacing: -1px;
    background: linear-gradient(135deg, #ec4899 0%, #f43f5e 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 15px;
  }
  .header p {
    color: var(--text-muted);
    font-size: 1.15rem;
    max-width: 500px;
    margin: 0 auto;
    font-weight: 500;
  }

  .container {
    width: 100%;
    max-width: 900px;
    animation: fadeInUp 0.8s ease 0.2s both;
  }

  .card {
    background: var(--bg-surface);
    border: 1px solid var(--card-border);
    border-radius: 20px;
    padding: 35px;
    margin-bottom: 30px;
    box-shadow: 0 10px 40px -10px rgba(236, 72, 153, 0.2);
    transition: transform 0.4s ease, box-shadow 0.4s ease;
    position: relative;
    overflow: hidden;
  }
  
  .card:hover {
    transform: translateY(-5px);
    box-shadow: 0 15px 50px -10px rgba(236, 72, 153, 0.3);
  }

  .card h2 {
    font-size: 1.5rem;
    margin-bottom: 25px;
    display: flex;
    align-items: center;
    gap: 10px;
    color: var(--text-main);
    font-weight: 700;
  }

  .auth-form {
    display: flex;
    flex-direction: column;
    gap: 16px;
    max-width: 400px;
    margin: 0 auto;
  }

  input[type="email"], input[type="password"], input[type="text"] {
    width: 100%;
    background: #f8fafc;
    border: 2px solid #e2e8f0;
    border-radius: 12px;
    color: var(--text-main);
    padding: 16px 20px;
    font-size: 1.05rem;
    transition: all 0.3s ease;
    font-family: inherit;
  }

  input:focus {
    outline: none;
    border-color: var(--primary);
    background: #ffffff;
    box-shadow: 0 0 0 4px rgba(236, 72, 153, 0.15);
  }

  textarea {
    width: 100%;
    min-height: 140px;
    background: #f8fafc;
    border: 2px solid #e2e8f0;
    border-radius: 14px;
    color: var(--text-main);
    padding: 20px;
    font-family: inherit;
    font-size: 1.05rem;
    line-height: 1.6;
    resize: vertical;
    transition: all 0.3s ease;
  }
  textarea:focus { 
    outline: none; 
    border-color: var(--primary); 
    background: #ffffff;
    box-shadow: 0 0 0 4px rgba(236, 72, 153, 0.15);
  }

  .btn {
    background: linear-gradient(135deg, var(--primary), #e11d48);
    color: white;
    border: none;
    border-radius: 12px;
    padding: 16px 28px;
    font-size: 1.1rem;
    font-family: inherit;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 4px 15px rgba(225, 29, 72, 0.3);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }
  .btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(225, 29, 72, 0.4);
  }
  .btn:active {
    transform: translateY(1px);
  }
  .btn.secondary {
    background: var(--secondary);
    color: var(--text-main);
    box-shadow: none;
    border: 2px solid #e2e8f0;
  }
  .btn.secondary:hover {
    background: var(--secondary-hover);
    border-color: #cbd5e1;
  }

  .actions {
    display: flex;
    gap: 15px;
    margin-top: 20px;
  }

  .sample-btn {
    display: inline-block;
    background: #fce7f3;
    color: #be185d;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 0.85rem;
    cursor: pointer;
    margin-right: 8px;
    margin-bottom: 8px;
    font-weight: 600;
    transition: all 0.2s ease;
  }
  .sample-btn:hover {
    background: #fbcfe8;
    transform: scale(1.05);
  }

  .status {
    margin-top: 20px;
    padding: 16px;
    border-radius: 12px;
    font-weight: 500;
    animation: fadeIn 0.4s ease;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .status.info { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
  .status.ok { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
  .status.err { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }

  .hidden { display: none !important; }

  .file-label {
    display: block;
    width: 100%;
    padding: 40px;
    border: 2px dashed #cbd5e1;
    border-radius: 14px;
    text-align: center;
    cursor: pointer;
    transition: all 0.3s ease;
    background: #f8fafc;
    margin-top: 20px;
  }
  .file-label:hover {
    background: #f1f5f9;
    border-color: var(--primary);
  }
  .file-label span {
    color: var(--primary);
    font-weight: 600;
    font-size: 1.1rem;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
  }

  .table-wrapper {
    overflow-x: auto;
    margin-top: 25px;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    text-align: left;
    background: white;
  }
  th {
    background: #fce7f3;
    padding: 18px;
    font-weight: 600;
    color: #be185d;
    font-size: 0.95rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  td {
    padding: 18px;
    border-top: 1px solid #e2e8f0;
    color: var(--text-main);
    font-size: 0.95rem;
  }
  tr:hover td {
    background: #fdf2f8;
  }

  .user-menu {
    position: absolute;
    top: 20px;
    right: 20px;
    display: flex;
    align-items: center;
    gap: 15px;
    background: white;
    padding: 10px 20px;
    border-radius: 30px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 4px 15px rgba(0,0,0,0.05);
  }

  .user-email {
    font-size: 0.95rem;
    color: var(--text-muted);
    font-weight: 500;
  }

  @keyframes fadeInUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
  }
  @keyframes fadeInDown {
    from { opacity: 0; transform: translateY(-20px); }
    to { opacity: 1; transform: translateY(0); }
  }
  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  
  .emoji-icon {
    display: inline-block;
    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
  }
"""

start_idx = html.find(':root {')
end_idx = html.find('</style>')

if start_idx != -1 and end_idx != -1:
    new_html = html[:start_idx] + new_css.strip() + '\n' + html[end_idx:]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_html)
    print("CSS Updated Successfully!")
else:
    print("Could not find style block")
