from flask import Flask, request, redirect
from auth import Auth
from database import Database
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
db = Database()
auth = Auth(db)

@app.route('/verify/<token>')
def verify_email(token):
    success, message = auth.verify_email(token)
    if success:
        return redirect('http://localhost:5000/verified.html')
    else:
        return f'Doğrulama hatası: {message}', 400

@app.route('/verified.html')
def verified():
    return '''
    <html>
        <head>
            <title>Email Doğrulandı</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background-color: #f5f5f5;
                }
                .container {
                    text-align: center;
                    padding: 2rem;
                    background-color: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                h1 {
                    color: #4CAF50;
                }
                p {
                    color: #666;
                }
                .button {
                    display: inline-block;
                    background-color: #4CAF50;
                    color: white;
                    padding: 10px 20px;
                    text-decoration: none;
                    border-radius: 4px;
                    margin-top: 1rem;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Email Adresiniz Doğrulandı!</h1>
                <p>Artık DigiCollect'i kullanmaya başlayabilirsiniz.</p>
                <a href="/" class="button">Giriş Yap</a>
            </div>
        </body>
    </html>
    '''

if __name__ == '__main__':
    app.run(port=5000)
