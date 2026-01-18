"""
CHATBOT DOUBLE MODE - Version fonctionnelle avec importation
=============================================================
"""

from flask import Flask, render_template, request, jsonify
import json
import os
import random
import csv
import unicodedata
import re
from datetime import datetime

# =============================================
# CONFIGURATION
# =============================================

os.makedirs('templates', exist_ok=True)
print("✅ Dossiers créés")

app = Flask(__name__)
app.secret_key = 'chatbot_double_mode_secret'


# =============================================
# CLASSE CHATBOT
# =============================================

class ChatBotDoubleMode:
    def __init__(self, fichier_memoire="mon_chatbot_double.json", tolerance=0.6):
        self.fichier_memoire = fichier_memoire
        self.memoire = {}
        self.scores = {}
        self.mode = "apprentissage"
        self.derniere_question = ""
        self.derniere_reponse = ""
        self.tolerance = tolerance

        print("🤖 Initialisation ChatBot...")
        self.charger_memoire()

        if not self.memoire:
            self.initialiser_base()
            print("✅ Base initialisée")
        else:
            print(f"📚 Mémoire chargée ({len(self.memoire)} questions)")

    def initialiser_base(self):
        """Connaissances de base"""
        self.memoire = {
            "bonjour": ["Bonjour ! Je suis un chatbot avec deux modes !"],
            "aide": [
                "Je suis en mode apprentissage : tu peux m'apprendre avec les boutons 👍/👎",
                "Je suis en mode utilisation : je te réponds sans feedback"
            ],
            "mode": [
                "Change de mode avec les boutons Apprentissage et Utilisation en haut !"
            ]
        }
        self.scores = {
            "bonjour": [1],
            "aide": [1, 1],
            "mode": [1]
        }
        self.sauvegarder()

    def importer_csv(self, fichier_csv):
        """Importe des questions-réponses depuis un fichier CSV"""
        try:
            with open(fichier_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                compteur = 0

                for ligne in reader:
                    question = ligne.get('question', '').strip()
                    reponse = ligne.get('reponse', '').strip()

                    if question and reponse:
                        self.apprendre_reponse(question, reponse)
                        compteur += 1

            self.sauvegarder()
            print(f"✅ Importé {compteur} questions-réponses depuis {fichier_csv}")
            return compteur
        except Exception as e:
            print(f"❌ Erreur lors de l'import: {e}")
            return 0

    def normaliser_texte(self, texte):
        """Normalise le texte pour la recherche"""
        if not texte:
            return ""

        texte = texte.lower()
        texte = unicodedata.normalize('NFD', texte)
        texte = ''.join(c for c in texte if unicodedata.category(c) != 'Mn')
        texte = re.sub(r'[^\w\s]', ' ', texte)
        texte = re.sub(r'\s+', ' ', texte).strip()
        return texte

    def trouver_variantes_proches(self, question_normalisee):
        """Trouve des questions similaires"""
        variantes = []

        for question_memoire in self.memoire.keys():
            question_memoire_norm = self.normaliser_texte(question_memoire)

            if question_normalisee == question_memoire_norm:
                variantes.append((question_memoire, 1.0))
                continue

            if question_normalisee in question_memoire_norm or question_memoire_norm in question_normalisee:
                variantes.append((question_memoire, 0.8))
                continue

            mots_question = set(question_normalisee.split())
            mots_memoire = set(question_memoire_norm.split())

            if mots_question and mots_memoire:
                intersection = mots_question.intersection(mots_memoire)
                union = mots_question.union(mots_memoire)

                if union:
                    similarite = len(intersection) / len(union)
                    if similarite >= self.tolerance:
                        variantes.append((question_memoire, similarite))

        variantes.sort(key=lambda x: x[1], reverse=True)
        return variantes

    def trouver_reponse(self, question):
        """Trouve la meilleure réponse"""
        question_originale = question.strip()
        self.derniere_question = question_originale

        question_normalisee = self.normaliser_texte(question_originale)

        # Recherche exacte
        for question_memoire, reponses in self.memoire.items():
            question_memoire_norm = self.normaliser_texte(question_memoire)

            if question_normalisee == question_memoire_norm:
                scores = self.scores.get(question_memoire, [])

                if self.mode == "utilisation":
                    if scores:
                        meilleur_score = max(scores)
                        meilleures_indices = [i for i, s in enumerate(scores) if s == meilleur_score]
                        idx = random.choice(meilleures_indices) if meilleures_indices else 0
                    else:
                        idx = 0
                    self.derniere_reponse = reponses[idx] if reponses else ""
                    return {'reponse': self.derniere_reponse, 'type': 'reponse'}
                else:
                    self.derniere_reponse = random.choice(reponses) if reponses else ""
                    return {'reponse': self.derniere_reponse, 'type': 'reponse'}

        # Recherche de variantes
        variantes = self.trouver_variantes_proches(question_normalisee)

        if variantes:
            meilleure_variante, similarite = variantes[0]
            reponses = self.memoire[meilleure_variante]
            scores = self.scores.get(meilleure_variante, [])

            if self.mode == "utilisation":
                if scores:
                    meilleur_score = max(scores)
                    meilleures_indices = [i for i, s in enumerate(scores) if s == meilleur_score]
                    idx = random.choice(meilleures_indices) if meilleures_indices else 0
                else:
                    idx = 0
                self.derniere_reponse = reponses[idx] if reponses else ""

                if similarite >= 0.9:
                    return {'reponse': self.derniere_reponse, 'type': 'reponse'}
                else:
                    return {
                        'reponse': f"Je pense que vous voulez dire : '{meilleure_variante}'\n\n{self.derniere_reponse}",
                        'type': 'variante'}
            else:
                self.derniere_reponse = random.choice(reponses) if reponses else ""
                return {'reponse': f"Je pense que vous voulez dire : '{meilleure_variante}'\n\n{self.derniere_reponse}",
                        'type': 'variante'}

        self.derniere_reponse = ""
        return None

    def donner_feedback(self, positif=True):
        """Donne un feedback"""
        if not self.derniere_question or not self.derniere_reponse:
            return False

        question = self.derniere_question.lower().strip()

        if question not in self.memoire:
            self.memoire[question] = [self.derniere_reponse]
            self.scores[question] = [2 if positif else 0]
        else:
            if self.derniere_reponse in self.memoire[question]:
                idx = self.memoire[question].index(self.derniere_reponse)
                if positif:
                    self.scores[question][idx] += 1
                else:
                    self.scores[question][idx] = max(0, self.scores[question][idx] - 1)
            else:
                self.memoire[question].append(self.derniere_reponse)
                self.scores[question].append(2 if positif else 0)

        self.sauvegarder()
        return True

    def apprendre_reponse(self, question, reponse):
        """Apprend une nouvelle réponse"""
        question_lower = question.lower().strip()

        if question_lower not in self.memoire:
            self.memoire[question_lower] = []
            self.scores[question_lower] = []

        if reponse not in self.memoire[question_lower]:
            self.memoire[question_lower].append(reponse)
            self.scores[question_lower].append(1)
            self.sauvegarder()
            return True

        return False

    def changer_mode(self, nouveau_mode):
        """Change de mode"""
        if nouveau_mode in ["apprentissage", "utilisation"]:
            self.mode = nouveau_mode
            self.sauvegarder()
            return True
        return False

    def charger_memoire(self):
        """Charge la mémoire"""
        try:
            if os.path.exists(self.fichier_memoire):
                with open(self.fichier_memoire, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memoire = data.get('memoire', {})
                    self.scores = data.get('scores', {})
                    self.mode = data.get('mode', 'apprentissage')
        except:
            self.memoire = {}
            self.scores = {}

    def sauvegarder(self):
        """Sauvegarde la mémoire"""
        try:
            data = {
                'memoire': self.memoire,
                'scores': self.scores,
                'mode': self.mode,
                'derniere_maj': datetime.now().isoformat()
            }
            with open(self.fichier_memoire, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except:
            return False

    def get_statistiques(self):
        """Retourne les statistiques"""
        total_questions = len(self.memoire)
        total_reponses = sum(len(r) for r in self.memoire.values())
        return {
            'questions': total_questions,
            'reponses': total_reponses,
            'mode': self.mode
        }


# =============================================
# INITIALISATION
# =============================================

bot = ChatBotDoubleMode()

# =============================================
# HTML COMPLET AVEC IMPORTATION ET POP-UP AUTOMATIQUE
# =============================================

HTML_INTERFACE = '''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🤖 ChatBot Personnel</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: Arial, sans-serif; }
        body { background: #667eea; min-height: 100vh; padding: 20px; display: flex; justify-content: center; align-items: center; }
        .container { width: 100%; max-width: 800px; background: white; border-radius: 20px; box-shadow: 0 20px 40px rgba(0,0,0,0.2); overflow: hidden; }
        .header { background: #4facfe; color: white; padding: 25px; text-align: center; }
        .header h1 { font-size: 2.2em; margin-bottom: 10px; }
        .mode-selector { margin-top: 15px; display: flex; justify-content: center; gap: 15px; flex-wrap: wrap; }
        .mode-btn { padding: 10px 20px; border: none; border-radius: 25px; cursor: pointer; font-weight: bold; transition: all 0.3s; }
        .mode-btn.active { background: white; color: #4facfe; }
        .mode-btn.inactive { background: rgba(255,255,255,0.2); color: white; }
        .stats { background: #f8f9fa; padding: 15px; display: flex; justify-content: space-around; border-bottom: 1px solid #e9ecef; }
        .stat-item { text-align: center; }
        .stat-number { font-size: 1.8em; font-weight: bold; color: #4facfe; }
        .chat-area { height: 350px; overflow-y: auto; padding: 20px; background: #f8f9fa; }
        .message { margin-bottom: 15px; display: flex; flex-direction: column; }
        .message.user { align-items: flex-end; }
        .bubble { max-width: 75%; padding: 12px 18px; border-radius: 18px; animation: fadeIn 0.3s; }
        .user .bubble { background: #4facfe; color: white; }
        .bot .bubble { background: white; color: #333; border: 1px solid #e9ecef; }
        .feedback-buttons { display: flex; gap: 10px; margin-top: 8px; justify-content: flex-start; }
        .feedback-btn { padding: 6px 12px; border: none; border-radius: 12px; cursor: pointer; font-size: 14px; }
        .btn-good { background: #28a745; color: white; }
        .btn-bad { background: #dc3545; color: white; }
        .input-area { padding: 20px; background: white; border-top: 1px solid #e9ecef; }
        .input-group { display: flex; gap: 10px; }
        #messageInput { flex: 1; padding: 15px; border: 2px solid #e9ecef; border-radius: 25px; font-size: 16px; }
        #sendButton { padding: 15px 25px; background: #4facfe; color: white; border: none; border-radius: 25px; cursor: pointer; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); justify-content: center; align-items: center; z-index: 1000; }
        .modal-content { background: white; padding: 30px; border-radius: 15px; max-width: 500px; width: 90%; text-align: center; }
        .import-modal .modal-content { max-width: 600px; }
        pre { font-family: 'Courier New', monospace; font-size: 14px; margin: 10px 0; background: #f8f9fa; padding: 10px; border-radius: 5px; overflow-x: auto; border: 1px solid #e9ecef; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 ChatBot Personnel</h1>
            <div class="mode-selector">
                <button id="modeApprentissage" class="mode-btn active">🎓 Apprentissage</button>
                <button id="modeUtilisation" class="mode-btn inactive">🚀 Utilisation</button>
                <button id="importerButton" class="mode-btn" style="background: #ffa726; color: white;">📥 Importer Base</button>
            </div>
            <p id="modeDescription">Tu peux m'apprendre avec les boutons 👍/👎</p>
        </div>

        <div class="stats">
            <div class="stat-item">
                <div class="stat-number" id="statQuestions">0</div>
                <div>Questions</div>
            </div>
            <div class="stat-item">
                <div class="stat-number" id="statReponses">0</div>
                <div>Réponses</div>
            </div>
            <div class="stat-item">
                <div class="stat-number" id="statMode">🎓</div>
                <div>Mode</div>
            </div>
        </div>

        <div class="chat-area" id="chatContainer">
            <div class="message bot">
                <div class="bubble">
                    <strong>Bonjour !</strong><br><br>
                    Je suis un chatbot avec recherche intelligente :<br>
                    • J'ignore les accents et les articles (le, la, les...)<br>
                    • Je trouve des variantes similaires<br>
                    • En mode 🎓, boutons 👍/👎<br>
                    • En mode 🚀, je réponds directement<br>
                    • 📥 Importer une base de connaissances<br><br>
                    <em>Quand je ne sais pas, un pop-up s'ouvre automatiquement !</em>
                </div>
            </div>
        </div>

        <div class="input-area">
            <div class="input-group">
                <input type="text" id="messageInput" placeholder="Tapez votre message..." autocomplete="off">
                <button id="sendButton">Envoyer</button>
            </div>
        </div>
    </div>

    <!-- Modal d'apprentissage -->
    <div class="modal" id="learningModal">
        <div class="modal-content">
            <h3>🎓 Apprentissage</h3>
            <p id="modalMessage"></p>
            <p><strong>Question :</strong> "<span id="modalQuestion"></span>"</p>
            <textarea id="learningInput" placeholder="Enseigne-moi la réponse..." rows="4" style="width: 100%; padding: 12px; font-size: 16px; margin: 15px 0; border: 2px solid #4facfe; border-radius: 10px; resize: vertical;"></textarea>
            <div style="margin-top: 20px; display: flex; gap: 10px;">
                <button id="learnButton" style="padding: 10px 20px; background: #4facfe; color: white; border: none; border-radius: 8px; cursor: pointer;">Apprendre</button>
                <button id="cancelButton" style="padding: 10px 20px; background: #6c757d; color: white; border: none; border-radius: 8px; cursor: pointer;">Annuler</button>
            </div>
        </div>
    </div>

    <!-- Modal d'importation -->
    <div class="modal import-modal" id="importModal">
        <div class="modal-content">
            <h3>📥 Importer une base de connaissances</h3>

            <div style="margin: 20px 0;">
                <h4>Format CSV attendu :</h4>
                <pre>question,reponse
"Quelle est la capitale de la France ?","Paris"
"Qui a peint la Joconde ?","Léonard de Vinci"
"Combien font 2+2 ?","4"</pre>

                <div style="margin-top: 15px; padding: 15px; background: #f8f9fa; border-radius: 10px;">
                    <p><strong>Base par défaut :</strong></p>
                    <p>Un fichier <code>base_connaissances.csv</code> avec des questions générales sera créé automatiquement.</p>
                </div>
            </div>

            <div style="display: flex; gap: 10px; justify-content: center;">
                <button id="importerBaseBtn" style="padding: 12px 24px; background: #4caf50; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 16px;">
                    📥 Importer la base
                </button>
                <button id="annulerImportBtn" style="padding: 12px 24px; background: #f44336; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 16px;">
                    ✖ Annuler
                </button>
            </div>

            <div id="importResult" style="margin-top: 20px; display: none;">
                <p id="importMessage"></p>
            </div>
        </div>
    </div>

    <script>
        // Variables globales
        var modeActuel = 'apprentissage';
        var questionEnCours = '';

        // Fonction pour charger le mode
        function chargerMode() {
            fetch('/get_mode')
                .then(function(response) {
                    return response.json();
                })
                .then(function(data) {
                    modeActuel = data.mode;
                    mettreAJourAffichageMode();
                })
                .catch(function(error) {
                    console.log('Erreur:', error);
                    modeActuel = 'apprentissage';
                    mettreAJourAffichageMode();
                });
        }

        // Mettre à jour l'affichage du mode
        function mettreAJourAffichageMode() {
            var btnApp = document.getElementById('modeApprentissage');
            var btnUtil = document.getElementById('modeUtilisation');
            var desc = document.getElementById('modeDescription');
            var statMode = document.getElementById('statMode');

            if (modeActuel === 'apprentissage') {
                btnApp.className = 'mode-btn active';
                btnUtil.className = 'mode-btn inactive';
                desc.textContent = 'Tu peux m\\'apprendre avec les boutons 👍/👎';
                statMode.textContent = '🎓';
            } else {
                btnApp.className = 'mode-btn inactive';
                btnUtil.className = 'mode-btn active';
                desc.textContent = 'Teste mes connaissances sans feedback';
                statMode.textContent = '🚀';
            }
        }

        // Changer de mode
        function changerMode(nouveauMode) {
            if (nouveauMode === modeActuel) return;

            fetch('/changer_mode', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ mode: nouveauMode })
            })
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                if (data.success) {
                    modeActuel = nouveauMode;
                    mettreAJourAffichageMode();
                    ajouterMessage('Mode changé : ' + (nouveauMode === 'apprentissage' ? '🎓 Apprentissage' : '🚀 Utilisation'), 'bot');
                } else {
                    alert('Erreur: ' + data.message);
                }
            })
            .catch(function(error) {
                alert('Erreur de connexion');
            });
        }

        // Envoyer un message - CORRIGÉ POUR OUVRIR LE POP-UP
        function envoyerMessage() {
            var input = document.getElementById('messageInput');
            var message = input.value.trim();

            if (!message) {
                alert('Veuillez entrer un message');
                return;
            }

            ajouterMessage(message, 'user');
            input.value = '';

            fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            })
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                if (data.error) {
                    ajouterMessage('Erreur : ' + data.error, 'bot');
                } else if (data.reponse) {
                    // CORRECTION ICI : Vérifier si c'est le message d'apprentissage
                    if (data.reponse.includes("Je ne sais pas répondre") || data.type === 'apprentissage') {
                        // Ouvrir le modal d'apprentissage automatiquement
                        questionEnCours = message;
                        ouvrirModalApprentissage(data.reponse, message);
                    } else if (data.type === 'variante' && modeActuel === 'apprentissage') {
                        // Afficher la variante avec boutons feedback
                        ajouterMessageAvecFeedback(data.reponse, message);
                    } else {
                        // Réponse normale
                        ajouterMessageAvecFeedback(data.reponse, message);
                    }
                }

                if (data.statistiques) {
                    mettreAJourStatistiques(data.statistiques);
                }
            })
            .catch(function(error) {
                ajouterMessage('Erreur de connexion', 'bot');
            });
        }

        // Ajouter un message avec feedback
        function ajouterMessageAvecFeedback(texte, question) {
            var container = document.getElementById('chatContainer');
            var messageDiv = document.createElement('div');
            messageDiv.className = 'message bot';

            var bubble = document.createElement('div');
            bubble.className = 'bubble';
            bubble.textContent = texte;
            messageDiv.appendChild(bubble);

            if (modeActuel === 'apprentissage' && texte && question) {
                var feedbackDiv = document.createElement('div');
                feedbackDiv.className = 'feedback-buttons';

                var btnGood = document.createElement('button');
                btnGood.className = 'feedback-btn btn-good';
                btnGood.textContent = '👍 Bonne';
                btnGood.onclick = function() {
                    donnerFeedback(question, texte, true);
                };

                var btnBad = document.createElement('button');
                btnBad.className = 'feedback-btn btn-bad';
                btnBad.textContent = '👎 Mauvaise';
                btnBad.onclick = function() {
                    donnerFeedback(question, texte, false);
                };

                feedbackDiv.appendChild(btnGood);
                feedbackDiv.appendChild(btnBad);
                messageDiv.appendChild(feedbackDiv);
            }

            container.appendChild(messageDiv);
            container.scrollTop = container.scrollHeight;
        }

        // Ajouter un message simple
        function ajouterMessage(texte, type) {
            var container = document.getElementById('chatContainer');
            var messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + type;

            var bubble = document.createElement('div');
            bubble.className = 'bubble';
            bubble.textContent = texte;

            messageDiv.appendChild(bubble);
            container.appendChild(messageDiv);
            container.scrollTop = container.scrollHeight;
        }

        // Donner un feedback
        function donnerFeedback(question, reponse, positif) {
            fetch('/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    question: question,
                    reponse: reponse,
                    positif: positif
                })
            })
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                if (data.success) {
                    ajouterMessage(data.message, 'bot');
                    if (data.statistiques) {
                        mettreAJourStatistiques(data.statistiques);
                    }
                } else {
                    alert('Erreur: ' + data.message);
                }
            })
            .catch(function(error) {
                alert('Erreur de connexion');
            });
        }

        // Modal d'apprentissage
        function ouvrirModalApprentissage(message, question) {
            document.getElementById('modalMessage').textContent = message;
            document.getElementById('modalQuestion').textContent = question;
            document.getElementById('learningModal').style.display = 'flex';
            document.getElementById('learningInput').focus();
        }

        function fermerModal() {
            document.getElementById('learningModal').style.display = 'none';
            document.getElementById('learningInput').value = '';
            questionEnCours = '';
        }

        function apprendreReponse() {
            var reponse = document.getElementById('learningInput').value.trim();

            if (!reponse) {
                alert('Veuillez entrer une reponse');
                return;
            }

            fetch('/apprendre', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    question: questionEnCours,
                    reponse: reponse
                })
            })
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                if (data.success) {
                    ajouterMessage(data.message, 'bot');
                    if (data.statistiques) {
                        mettreAJourStatistiques(data.statistiques);
                    }
                } else {
                    alert('Erreur: ' + data.message);
                }
                fermerModal();
            })
            .catch(function(error) {
                alert('Erreur de connexion');
                fermerModal();
            });
        }

        // Modal d'importation
        function ouvrirModalImportation() {
            document.getElementById('importModal').style.display = 'flex';
            document.getElementById('importResult').style.display = 'none';
        }

        function fermerModalImportation() {
            document.getElementById('importModal').style.display = 'none';
        }

        function importerBase() {
            document.getElementById('importResult').style.display = 'block';
            document.getElementById('importMessage').textContent = 'Importation en cours...';
            document.getElementById('importMessage').style.color = '#4caf50';

            fetch('/importer_base', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                if (data.success) {
                    document.getElementById('importMessage').textContent = data.message;
                    document.getElementById('importMessage').style.color = '#4caf50';

                    mettreAJourStatistiques(data.statistiques);

                    setTimeout(function() {
                        ajouterMessage(data.message, 'bot');
                        setTimeout(fermerModalImportation, 2000);
                    }, 1000);
                } else {
                    document.getElementById('importMessage').textContent = 'Erreur: ' + data.message;
                    document.getElementById('importMessage').style.color = '#f44336';
                }
            })
            .catch(function(error) {
                document.getElementById('importMessage').textContent = 'Erreur de connexion';
                document.getElementById('importMessage').style.color = '#f44336';
            });
        }

        // Statistiques
        function chargerStatistiques() {
            fetch('/statistiques')
                .then(function(response) {
                    return response.json();
                })
                .then(mettreAJourStatistiques)
                .catch(function(error) {
                    mettreAJourStatistiques({questions: 0, reponses: 0, mode: modeActuel});
                });
        }

        function mettreAJourStatistiques(stats) {
            document.getElementById('statQuestions').textContent = stats.questions || 0;
            document.getElementById('statReponses').textContent = stats.reponses || 0;
            document.getElementById('statMode').textContent = stats.mode === 'apprentissage' ? '🎓' : '🚀';
        }

        // Initialisation
        function initialiserApp() {
            // Attacher les événements
            document.getElementById('modeApprentissage').onclick = function() {
                changerMode('apprentissage');
            };

            document.getElementById('modeUtilisation').onclick = function() {
                changerMode('utilisation');
            };

            document.getElementById('importerButton').onclick = ouvrirModalImportation;

            document.getElementById('sendButton').onclick = envoyerMessage;

            document.getElementById('messageInput').onkeypress = function(e) {
                if (e.key === 'Enter') {
                    envoyerMessage();
                }
            };

            document.getElementById('learnButton').onclick = apprendreReponse;
            document.getElementById('cancelButton').onclick = fermerModal;

            document.getElementById('importerBaseBtn').onclick = importerBase;
            document.getElementById('annulerImportBtn').onclick = fermerModalImportation;

            // Fermer les modals en cliquant à l'extérieur
            document.getElementById('learningModal').onclick = function(e) {
                if (e.target === this) {
                    fermerModal();
                }
            };

            document.getElementById('importModal').onclick = function(e) {
                if (e.target === this) {
                    fermerModalImportation();
                }
            };

            // Charger les données initiales
            chargerMode();
            chargerStatistiques();

            // Focus sur l'input
            document.getElementById('messageInput').focus();

            console.log('Application initialisée avec pop-up automatique');
        }

        // Démarrer quand la page est chargée
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initialiserApp);
        } else {
            initialiserApp();
        }
    </script>
</body>
</html>'''


# =============================================
# ROUTES FLASK AVEC IMPORTATION
# =============================================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/get_mode')
def get_mode():
    return jsonify({'mode': bot.mode})


@app.route('/changer_mode', methods=['POST'])
def changer_mode():
    try:
        data = request.get_json()
        nouveau_mode = data.get('mode', '')

        if bot.changer_mode(nouveau_mode):
            return jsonify({
                'success': True,
                'message': f'Mode changé en: {nouveau_mode}'
            })
        return jsonify({'success': False, 'message': 'Mode invalide'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})


@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        message = data.get('message', '').strip()

        if not message:
            return jsonify({'error': 'Message vide'}), 400

        resultat = bot.trouver_reponse(message)

        if resultat:
            return jsonify({
                'reponse': resultat['reponse'],
                'type': resultat['type'],
                'statistiques': bot.get_statistiques()
            })
        else:
            return jsonify({
                'reponse': "Je ne sais pas répondre à ça. Peux-tu m'apprendre ?",
                'type': 'apprentissage',
                'statistiques': bot.get_statistiques()
            })
    except Exception as e:
        return jsonify({'error': f'Erreur: {str(e)}'}), 500


@app.route('/feedback', methods=['POST'])
def feedback():
    try:
        data = request.get_json()
        question = data.get('question', '')
        reponse = data.get('reponse', '')
        positif = data.get('positif', True)

        if question and reponse:
            if bot.donner_feedback(positif):
                message = "Merci ! J'ai noté ton feedback." if positif else "D'accord, je vais éviter cette réponse."
                return jsonify({
                    'success': True,
                    'message': message,
                    'statistiques': bot.get_statistiques()
                })
        return jsonify({'success': False, 'message': 'Données invalides'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})


@app.route('/apprendre', methods=['POST'])
def apprendre():
    try:
        data = request.get_json()
        question = data.get('question', '')
        reponse = data.get('reponse', '')

        if question and reponse:
            if bot.apprendre_reponse(question, reponse):
                return jsonify({
                    'success': True,
                    'message': 'Super ! J\'ai appris quelque chose de nouveau !',
                    'statistiques': bot.get_statistiques()
                })
        return jsonify({'success': False, 'message': 'Question ou réponse manquante'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})


@app.route('/importer_base', methods=['POST'])
def importer_base():
    """Importe une base de connaissances initiale"""
    try:
        # Chemin vers le fichier CSV d'importation
        fichier_csv = 'base_connaissances.csv'

        # Créer le fichier CSV d'exemple s'il n'existe pas
        if not os.path.exists(fichier_csv):
            with open(fichier_csv, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['question', 'reponse'])
                # Questions de base
                writer.writerow(['Les Misérables', 'Victor Hugo'])
                writer.writerow(['Quelle est la capitale de la France ?', 'Paris'])
                writer.writerow(['Qui a peint la Joconde ?', 'Léonard de Vinci'])
                writer.writerow(['Combien font 2+2 ?', '4'])
                writer.writerow(['Le plus grand océan', 'Océan Pacifique'])
                writer.writerow(['La planète rouge', 'Mars'])
                writer.writerow(["L'auteur des Misérables", 'Victor Hugo'])
                writer.writerow(['La langue officielle du Brésil', 'Portugais'])
                writer.writerow(['Le roi de la jungle', 'Le lion'])
                writer.writerow(['La Révolution française', '1789'])

        # Importer les données
        nb_importes = bot.importer_csv(fichier_csv)

        return jsonify({
            'success': True,
            'message': f'Base importée avec succès ! {nb_importes} questions-réponses ajoutées.',
            'statistiques': bot.get_statistiques()
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})


@app.route('/statistiques')
def get_statistiques():
    return jsonify(bot.get_statistiques())


# =============================================
# DÉMARRAGE
# =============================================

def demarrer():
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(HTML_INTERFACE)

    print("\n" + "=" * 60)
    print("🚀 CHATBOT AVEC POP-UP AUTOMATIQUE - PRÊT !")
    print("=" * 60)
    print("\n🎯 FONCTIONNALITÉS :")
    print("   • Pop-up automatique quand le chatbot ne sait pas")
    print("   • Recherche intelligente (accents/articles ignorés)")
    print("   • Mode 🎓 Apprentissage : Boutons 👍/👎")
    print("   • Mode 🚀 Utilisation : Réponses directes")
    print("   • 📥 Importation de base CSV")
    print("\n📁 Fichier CSV : base_connaissances.csv")
    print("🌐 Accédez à : http://localhost:5027")
    print("🛑 Ctrl+C pour arrêter")
    print("=" * 60)

    app.run(debug=False, host='0.0.0.0', port=5027)


if __name__ == '__main__':
    demarrer()
    port = int(os.environ.get('PORT', 5027))  # NOUVEAU
    app.run(debug=False, host='0.0.0.0', port=port)  # MODIFIÉ