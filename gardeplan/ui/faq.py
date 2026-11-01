"""Searchable, offline help. Opening it never changes a schedule."""
import unicodedata
from PySide6.QtCore import Qt,QSize,Signal
from PySide6.QtGui import QKeySequence,QShortcut
from PySide6.QtWidgets import (QFrame,QHBoxLayout,QLabel,QLineEdit,QPushButton,
                              QScrollArea,QSizePolicy,QVBoxLayout,QWidget)
from .appearance import set_themed_style
from .visuals import icon


FAQ_ENTRIES=(
    ('Commencer','Comment créer une journée pédagogique ?',
     'Depuis l’accueil, cliquez sur Nouvelle journée pédagogique. La date du jour est proposée ; vous pouvez ensuite la changer avec le champ de date et les flèches. Le panneau Inscriptions s’ouvre pour saisir le nombre d’enfants. Une journée existante n’est jamais remplacée automatiquement.'),
    ('Commencer','Comment modifier le nom ou retrouver une journée ?',
     'Cliquez sur le nom de la journée dans la planification. Entrée ou un clic ailleurs enregistre ; Échap annule. Ce nom apparaît à l’accueil et dans le PDF. Pour retrouver une journée, utilisez Journées récentes ou Dossier → Ouvrir une journée.'),
    ('Navigation','Comment accéder à l’équipe, aux inscriptions et aux vérifications ?',
     'Les icônes à gauche restent accessibles depuis l’accueil, la planification et la FAQ. Équipe, Inscriptions et Vérifier ouvrent leur panneau dans la planification. Ratio affiche la couverture. Sur un petit écran, la barre latérale peut défiler ; Tab permet aussi de parcourir ses boutons. Accueil ramène à la liste des journées.'),
    ('Inscriptions et couverture','Combien d’éducatrices faut-il prévoir ?',
     'Saisissez le nombre d’enfants dans Inscriptions. Le ratio de départ est de 1 éducatrice pour 20 enfants et reste configurable : il ne constitue pas une affirmation réglementaire. De 7 h à 17 h, chaque groupe ouvert nécessite au moins deux éducatrices. Un effectif plus important peut en exiger davantage. Les besoins affichés sont calculés avec les règles de la journée.'),
    ('Inscriptions et couverture','Quelles sont les règles d’ouverture, de fermeture et de relève ?',
     'Par défaut, le personnel est présent de 6 h 50 à 17 h 35. De 6 h 50 à 7 h et de 17 h à 17 h 35, il faut au moins deux personnes au total, tous groupes confondus ; le ratio peut en demander davantage. De 7 h à 17 h, il faut au moins deux personnes par groupe ouvert. La relève prévoit 15 minutes communes. Les anciennes journées publiées ou archivées conservent leurs propres règles.'),
    ('Planification','Comment ajouter, déplacer ou redimensionner un quart ?',
     'Glissez une éducatrice depuis L’équipe dans la grille, ou double-cliquez sur une plage vide. Glissez un quart pour le déplacer. Tirez la poignée du haut ou du bas pour ajuster son début ou sa fin. Un double-clic sur le quart permet de saisir les heures exactes. Le magnétisme se règle à 1, 5 ou 15 minutes, ou sans magnétisme. Les informations restent précises à la minute.'),
    ('Planification','Comment compter les pauses, les dîners et les heures payées ?',
     'Ouvrez le quart pour régler les pauses, leur heure, leur durée et leur rémunération. Une pause retire l’éducatrice de la couverture, même si elle est payée. Une pause non payée est aussi déduite du total rémunéré. Les buffers payés comptent dans les heures sans couvrir automatiquement les enfants. Les dîners ne sont pas affichés dans les blocs. Dans le PDF, les pauses et interruptions restent vides.'),
    ('Planification','Quel est le maximum d’heures par personne ?',
     'Le plafond quotidien est de 8 h rémunérées par personne, tous quarts cumulés. Les buffers payés sont inclus et les pauses non payées sont déduites. Un maximum individuel plus bas reste prioritaire. Une cible dépassée apparaît en orange ; un maximum obligatoire dépassé apparaît en rouge et bloque la publication.'),
    ('Planification','À quoi sert le rang d’ancienneté ?',
     'Le rang 1 est prioritaire, puis 2, 3 et ainsi de suite, jusqu’à 11. Les rangs intermédiaires peuvent rester libres ; deux profils ne peuvent pas utiliser le même rang. La génération tient compte des rangs pour les quarts continus, les heures et les préférences, après les contraintes obligatoires et les objectifs communs de participation et de continuité.'),
    ('Génération','Comment générer et examiner une proposition ?',
     'Cliquez sur Générer l’horaire. La recherche porte sur tous les groupes et respecte les disponibilités, les absences, les pauses, les relèves, les maximums et les quarts verrouillés. La grille Proposition s’affiche avant toute application. L’onglet Bilan compare la couverture, les heures, les interruptions et les préférences. Cliquez sur Appliquer pour retenir la proposition, ou conservez l’horaire actuel.'),
    ('Génération','Pourquoi reste-t-il parfois des trous ou des personnes sans heures ?',
     'La recherche essaie de faire travailler le plus de personnes disponibles et d’éviter les horaires coupés inutiles. Les disponibilités, les quarts verrouillés, les besoins des groupes ou le maximum de 8 h peuvent imposer une interruption. Le temps de recherche peut aussi limiter l’optimisation ; le logiciel le précise. Le bilan identifie les personnes sans heures et les horaires coupés. La génération ne supprime pas une pause pour rendre un quart continu.'),
    ('Vérifications','Que faire lorsqu’une alerte apparaît ?',
     'Cliquez sur Vérifier dans la barre latérale. Les alertes précisent la plage et le problème ; sélectionnez-en une pour surligner la zone dans la grille. Pour un manque de personnel, Proposer une correction peut ajouter ou prolonger un quart compatible. Une proposition peut conserver des erreurs déjà présentes : elle reste alors un brouillon. Les erreurs bloquantes empêchent la publication, mais pas la sauvegarde.'),
    ('Vérifications','Comment signaler une absence ou annuler une modification ?',
     'Dans L’équipe, cliquez sur Signaler une absence. Cela concerne uniquement la journée ; le profil reste actif. Les quarts non verrouillés sont retirés et les quarts verrouillés restent à corriger. Annuler restaure l’action précédente ; Rétablir la réapplique. Les boutons sont près du nom de la journée. Sur Mac, utilisez Cmd+Z et Cmd+Maj+Z ; sur Windows, Ctrl+Z et Ctrl+Maj+Z. L’historique contient 50 actions.'),
    ('Fichiers et impression','Où sont les données et comment faire une sauvegarde ?',
     'En mode portable, les journées, les profils et les versions restent dans le sous-dossier donnees, à côté du programme. Gardez le dossier complet et fermez le logiciel avant de le déplacer. Dossier regroupe Enregistrer, Ouvrir, Dupliquer, Historique et les exports ou imports de sauvegarde. Les sauvegardes automatiques restent locales ; conservez aussi une copie de sécurité séparée.'),
    ('Fichiers et impression','Comment exporter ou imprimer l’horaire ?',
     'Cliquez sur Exporter PDF pour produire l’horaire général de la journée, au format lettre paysage. Chaque page contient au maximum huit éducatrices. Les couleurs identifient les groupes, les heures restent exactes et les interruptions restent vides. Le nom de la journée apparaît dans le document. Le PDF ne contient ni bande de ratio ni panneau d’alertes.'),
    ('Fichiers et impression','Comment mettre le logiciel à jour sans perdre les horaires ?',
     'Depuis la version 0.5.0, ouvrez Dossier → Mettre à jour depuis un ZIP et choisissez un ZIP portable officiel plus récent, pour le même système et la même architecture. L’assistant prépare un dossier séparé avec une copie des données et conserve l’ancien. Fermez l’ancienne version avant le premier lancement de la nouvelle. Le retour reprend les données d’avant mise à jour et conserve le travail plus récent séparément. Depuis 0.4.0 ou avant, fermez, sauvegardez puis transférez donnees dans le nouveau dossier extrait.'),
    ('Affichage','Puis-je changer les couleurs ou désactiver les animations ?',
     'Ouvrez Réglages → Affichage pour choisir un thème prédéfini ou un accent personnalisé. Le contraste des boutons reste protégé. Vous pouvez désactiver les animations discrètes ; les retours statiques au survol et le focus clavier restent visibles. Les préférences sont locales. Elles ne changent pas les couleurs des éducatrices, les règles ou le PDF.'),
)

STYLE='''
QWidget#faqBody {background:#F7F9F8;color:#203D32;}
QWidget#faqBody QLabel,QWidget#faqBody QPushButton,QWidget#faqBody QLineEdit {font-size:16px;color:#203D32;}
QWidget#faqBody QLabel#faqTitle {font-size:30px;font-weight:700;}
QWidget#faqBody QLabel#faqCategory {font-size:19px;font-weight:700;margin-top:12px;}
QWidget#faqBody QFrame#faqCard {background:white;border:1px solid #D9E3DD;border-radius:10px;}
QWidget#faqBody QPushButton#faqQuestion {background:transparent;border:1px solid transparent;border-radius:9px;padding:0;}
QWidget#faqBody QPushButton#faqQuestion:hover {background:#EDF5F0;}
QWidget#faqBody QPushButton#faqQuestion:checked {background:#F0F7F3;}
QWidget#faqBody QPushButton#faqQuestion:focus {border-color:#214F40;}
QWidget#faqBody QLineEdit {background:white;border:1px solid #64786D;border-radius:8px;padding:10px;}
QWidget#faqBody QLineEdit:focus {border:2px solid #214F40;padding:9px;}
'''


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFD',value) if not unicodedata.combining(c)).casefold()


class QuestionButton(QPushButton):
    def __init__(self,question):
        super().__init__();self.setObjectName('faqQuestion');self.setCheckable(True)
        self.setMinimumHeight(48);self.setAccessibleName(question)
        policy=QSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Preferred)
        policy.setHeightForWidth(True);self.setSizePolicy(policy)
        self.row=QHBoxLayout(self);self.row.setContentsMargins(14,12,14,12)
        title=QLabel(question);title.setWordWrap(True);title.setMinimumWidth(0)
        title.setTextFormat(Qt.TextFormat.PlainText);self.row.addWidget(title,1)
        self.symbol=QLabel();self.symbol.setFixedSize(20,20);self.row.addWidget(self.symbol)
        for child in self.findChildren(QWidget):child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def heightForWidth(self,width):return max(48,self.row.totalHeightForWidth(width))
    def minimumSizeHint(self):return QSize(0,48)
    def sizeHint(self):return QSize(650,self.heightForWidth(max(200,self.width())))

    def keyPressEvent(self,event):
        if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter):
            self.click();event.accept();return
        super().keyPressEvent(event)


class FaqEntry(QFrame):
    def __init__(self,category,question,answer):
        super().__init__();self.setObjectName('faqCard');self.setMinimumWidth(0)
        self.category=category;self.searchable=normalized(' '.join((category,question,answer)))
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0)
        self.button=QuestionButton(question);layout.addWidget(self.button)
        self.answer=QLabel(answer);self.answer.setWordWrap(True);self.answer.setMinimumWidth(0)
        self.answer.setTextFormat(Qt.TextFormat.PlainText);self.answer.setContentsMargins(15,12,15,16)
        self.answer.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse|Qt.TextInteractionFlag.TextSelectableByKeyboard)
        layout.addWidget(self.answer);self.button.toggled.connect(self.expand);self.expand(False)

    def expand(self,expanded):
        self.answer.setVisible(expanded)
        self.button.symbol.setPixmap(icon('minus' if expanded else 'plus',color='#52655E').pixmap(20,20))
        self.button.setAccessibleDescription('Réponse affichée. Entrée ou Espace pour replier.' if expanded else 'Entrée ou Espace pour afficher la réponse.')


class FaqPage(QScrollArea):
    go_home=Signal()

    def __init__(self,parent=None):
        super().__init__(parent);self.setWidgetResizable(True);self.setFrameShape(QFrame.Shape.NoFrame)
        self.setMinimumSize(0,0);self.setAccessibleName('FAQ — Aide et questions fréquentes')
        self.body=QWidget();self.body.setObjectName('faqBody');set_themed_style(self.body,STYLE)
        self.setWidget(self.body);outer=QVBoxLayout(self.body);outer.setContentsMargins(28,24,28,24);outer.setSpacing(12)
        title=QLabel('FAQ — Questions fréquentes');title.setObjectName('faqTitle');title.setWordWrap(True);outer.addWidget(title)
        intro=QLabel('Des réponses pour préparer vos journées pédagogiques. Cette aide fonctionne entièrement hors ligne.')
        intro.setWordWrap(True);outer.addWidget(intro)
        back=QPushButton('Retour à l’accueil');back.setMinimumHeight(44);back.clicked.connect(self.go_home.emit);outer.addWidget(back,0,Qt.AlignmentFlag.AlignLeft)
        self.search=QLineEdit();self.search.setPlaceholderText('Rechercher : inscriptions, pauses, PDF…')
        self.search.setAccessibleName('Rechercher dans la FAQ');self.search.setClearButtonEnabled(True)
        self.search.setMaxLength(200);self.search.setMinimumHeight(44);outer.addWidget(self.search)
        self.results=QLabel();outer.addWidget(self.results)
        self.entries=[];self.categories={}
        for category,question,answer in FAQ_ENTRIES:
            if category not in self.categories:
                heading=QLabel(category);heading.setObjectName('faqCategory');heading.setWordWrap(True)
                self.categories[category]=heading;outer.addWidget(heading)
            entry=FaqEntry(category,question,answer);self.entries.append(entry);outer.addWidget(entry)
        self.empty=QLabel('Aucune réponse trouvée. Essayez un autre mot ou effacez la recherche.')
        self.empty.setWordWrap(True);outer.addWidget(self.empty);outer.addStretch()
        self.search.textChanged.connect(self.filter);self.filter('')
        self.find_shortcut=QShortcut(QKeySequence(QKeySequence.StandardKey.Find),self)
        self.find_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.find_shortcut.activated.connect(self.focus_search)

    def focus_search(self):
        self.search.setFocus();self.search.selectAll();self.ensureWidgetVisible(self.search)

    def filter(self,query):
        words=normalized(query).split();count=0;visible_categories=set()
        for entry in self.entries:
            match=all(word in entry.searchable for word in words)
            entry.setVisible(match)
            entry.button.setChecked(bool(words) and match)
            if match:count+=1;visible_categories.add(entry.category)
        for category,heading in self.categories.items():heading.setVisible(category in visible_categories)
        self.results.setText(f'{count} réponse'+('s' if count!=1 else '')+(' trouvée'+('s' if count!=1 else '') if words else ' disponible'+('s' if count!=1 else '')))
        self.empty.setVisible(count==0)
