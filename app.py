from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import uuid

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mariage.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# ============================================================
# TABLE DES COMMANDES
# ============================================================

class Commande(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_commande = db.Column(db.String(50), nullable=True)
    table_numero = db.Column(db.String(20))
    boisson = db.Column(db.String(50))
    quantite = db.Column(db.Integer)
    statut = db.Column(db.String(20), default="Nouvelle")


# ============================================================
# TABLE DU CATALOGUE
# ============================================================

class Produit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False, unique=True)
    categorie = db.Column(db.String(50), nullable=False, default="Boisson")
    photo = db.Column(db.String(200), nullable=True)
    disponible = db.Column(db.Boolean, default=True)


# ============================================================
# ANCIEN CATALOGUE
# Conservé temporairement pour ne pas casser l'application
# ============================================================

BOISSONS = [
    "Guinness",
    "Kadji",
    "Isenbeck",
    "Heineken",
    "Castel",
    "33 Export",
    "Top Grenadine",
    "Top Ananas"
]


# ============================================================
# INITIALISATION DU CATALOGUE
# ============================================================

def initialiser_catalogue():

    produits = [
        "Guinness",
        "Kadji",
        "Isenbeck",
        "Heineken",
        "Castel",
        "33 Export",
        "Top Grenadine",
        "Top Ananas"
    ]

    for nom in produits:

        produit_existant = Produit.query.filter_by(
            nom=nom
        ).first()

        if not produit_existant:

            produit = Produit(
                nom=nom,
                categorie="Boisson",
                disponible=True
            )

            db.session.add(produit)

    db.session.commit()


# ============================================================
# PAGE DES INVITÉS
# ============================================================

@app.route("/", methods=["GET", "POST"])
def accueil():

    if request.method == "POST":

        table = request.form["table"]

        # Création d'un numéro unique pour la commande
        numero_commande = str(uuid.uuid4())[:8].upper()

        commande_creee = False

        for boisson in BOISSONS:

            quantite = int(
                request.form.get(
                    f"quantite_{boisson}",
                    0
                )
            )

            if quantite > 0:

                commande = Commande(
                    numero_commande=numero_commande,
                    table_numero=table,
                    boisson=boisson,
                    quantite=quantite,
                    statut="Nouvelle"
                )

                db.session.add(commande)

                commande_creee = True

        if commande_creee:
            db.session.commit()

        return """
        <div style="text-align:center; margin-top:50px;">
            <h2>✅ Commande enregistrée avec succès !</h2>
            <p>Votre commande a bien été envoyée au bar.</p>
            <br>
            <a href="/">Nouvelle commande</a>
        </div>
        """

    return render_template(
        "index.html",
        boissons=BOISSONS
    )


# ============================================================
# PAGE DU BAR
# ============================================================

@app.route("/bar")
def bar():

    commandes = Commande.query.order_by(
        Commande.id.desc()
    ).all()

    commandes_groupees = {}

    for commande in commandes:

        if commande.numero_commande:
            cle = commande.numero_commande
        else:
            cle = f"ancienne_{commande.id}"

        if cle not in commandes_groupees:

            commandes_groupees[cle] = {
                "numero": commande.numero_commande,
                "table": commande.table_numero,
                "statut": commande.statut or "Nouvelle",
                "boissons": []
            }

        commandes_groupees[cle]["boissons"].append({
            "nom": commande.boisson,
            "quantite": commande.quantite
        })

    return render_template(
        "bar.html",
        commandes=commandes_groupees.values()
    )


# ============================================================
# PAGE DES HÔTESSES
# ============================================================

@app.route("/hotesses")
def hotesses():

    commandes = Commande.query.order_by(
        Commande.id.desc()
    ).all()

    commandes_groupees = {}

    for commande in commandes:

        if commande.numero_commande:
            cle = commande.numero_commande
        else:
            cle = f"ancienne_{commande.id}"

        if cle not in commandes_groupees:

            commandes_groupees[cle] = {
                "numero": commande.numero_commande,
                "table": commande.table_numero,
                "statut": commande.statut or "Nouvelle",
                "boissons": []
            }

        commandes_groupees[cle]["boissons"].append({
            "nom": commande.boisson,
            "quantite": commande.quantite
        })

    # Les hôtesses ne voient que les commandes préparées
    commandes_pretes = [
        commande
        for commande in commandes_groupees.values()
        if commande["statut"] == "Préparée"
    ]

    return render_template(
        "hotesses.html",
        commandes=commandes_pretes
    )


# ============================================================
# CHANGEMENT DU STATUT D'UNE COMMANDE
# ============================================================

@app.route(
    "/commande/<numero_commande>/statut/<nouveau_statut>",
    methods=["GET", "POST"]
)
def changer_statut(numero_commande, nouveau_statut):

    statuts_autorises = [
        "Nouvelle",
        "Préparée",
        "Livrée"
    ]

    if nouveau_statut not in statuts_autorises:

        if request.method == "POST":
            return {
                "success": False,
                "message": "Statut invalide"
            }, 400

        return redirect(url_for("bar"))

    commandes = Commande.query.filter_by(
        numero_commande=numero_commande
    ).all()

    if not commandes:

        if request.method == "POST":
            return {
                "success": False,
                "message": "Commande introuvable"
            }, 404

        return redirect(url_for("bar"))

    for commande in commandes:
        commande.statut = nouveau_statut

    db.session.commit()

    if request.method == "POST":

        return {
            "success": True,
            "numero": numero_commande,
            "statut": nouveau_statut
        }

    return redirect(url_for("bar"))


# ============================================================
# API DES COMMANDES
# ============================================================

@app.route("/api/commandes")
def api_commandes():

    commandes = Commande.query.order_by(
        Commande.id.desc()
    ).all()

    commandes_groupees = {}

    for commande in commandes:

        if commande.numero_commande:
            cle = commande.numero_commande
        else:
            cle = f"ancienne_{commande.id}"

        if cle not in commandes_groupees:

            commandes_groupees[cle] = {
                "numero": commande.numero_commande,
                "table": commande.table_numero,
                "statut": commande.statut or "Nouvelle",
                "boissons": []
            }

        commandes_groupees[cle]["boissons"].append({
            "nom": commande.boisson,
            "quantite": commande.quantite
        })

    return {
        "commandes": list(commandes_groupees.values())
    }


# ============================================================
# ADMINISTRATION DU CATALOGUE
# ============================================================

@app.route("/admin")
def admin():

    produits = Produit.query.order_by(
        Produit.categorie,
        Produit.nom
    ).all()

    return render_template(
        "admin.html",
        produits=produits
    )


# ============================================================
# AJOUTER UN PRODUIT
# ============================================================

@app.route(
    "/admin/produit/ajouter",
    methods=["POST"]
)
def ajouter_produit():

    nom = request.form["nom"].strip()
    categorie = request.form["categorie"]

    if nom:

        produit_existant = Produit.query.filter_by(
            nom=nom
        ).first()

        if not produit_existant:

            produit = Produit(
                nom=nom,
                categorie=categorie,
                disponible=True
            )

            db.session.add(produit)
            db.session.commit()

    return redirect(url_for("admin"))


# ============================================================
# SUPPRIMER UN PRODUIT
# ============================================================

@app.route(
    "/admin/produit/<int:produit_id>/supprimer",
    methods=["POST"]
)
def supprimer_produit(produit_id):

    produit = Produit.query.get_or_404(
        produit_id
    )

    db.session.delete(produit)
    db.session.commit()

    return redirect(url_for("admin"))


# ============================================================
# LANCEMENT DE L'APPLICATION
# ============================================================

if __name__ == "__main__":

    with app.app_context():

        db.create_all()

        initialiser_catalogue()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )