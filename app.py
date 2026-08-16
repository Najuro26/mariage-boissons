from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import uuid
import os
from werkzeug.utils import secure_filename


app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mariage.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# ============================================================
# CONFIGURATION DES PHOTOS
# ============================================================

UPLOAD_FOLDER = os.path.join(
    app.static_folder,
    "boissons"
)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp",
    "gif"
}


def fichier_autorise(nom_fichier):
    return (
        "." in nom_fichier
        and nom_fichier.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# ============================================================
# TABLE DES COMMANDES
# ============================================================

class Commande(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    numero_commande = db.Column(
        db.String(50),
        nullable=True
    )

    table_numero = db.Column(
        db.String(20)
    )

    boisson = db.Column(
        db.String(100)
    )

    quantite = db.Column(
        db.Integer
    )

    statut = db.Column(
        db.String(20),
        default="Nouvelle"
    )


# ============================================================
# TABLE DU CATALOGUE
# ============================================================

class Produit(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    nom = db.Column(
        db.String(100),
        nullable=False,
        unique=True
    )

    categorie = db.Column(
        db.String(50),
        nullable=False,
        default="Boisson"
    )

    photo = db.Column(
        db.String(200),
        nullable=True
    )

    disponible = db.Column(
        db.Boolean,
        default=True
    )


# ============================================================
# ANCIEN CATALOGUE
# Conservé pour compatibilité
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
# PAGE DES INVITES
# ============================================================

@app.route("/", methods=["GET", "POST"])
def accueil():

    produits = Produit.query.filter_by(
        disponible=True
    ).order_by(
        Produit.categorie,
        Produit.nom
    ).all()

    if request.method == "POST":

        table = request.form["table"]

        numero_commande = str(
            uuid.uuid4()
        )[:8].upper()

        commande_creee = False

        for produit in produits:

            quantite = int(
                request.form.get(
                    f"quantite_{produit.id}",
                    0
                )
            )

            if quantite > 0:

                commande = Commande(
                    numero_commande=numero_commande,
                    table_numero=table,
                    boisson=produit.nom,
                    quantite=quantite,
                    statut="Nouvelle"
                )

                db.session.add(commande)

                commande_creee = True

        if commande_creee:

            db.session.commit()

            return redirect(
                url_for("confirmation")
            )

    return render_template(
        "index.html",
        produits=produits
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
# PAGE DES HOTESSES
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
# CHANGEMENT DU STATUT
# ============================================================

@app.route(
    "/commande/<numero_commande>/statut/<nouveau_statut>",
    methods=["GET", "POST"]
)
def changer_statut(
    numero_commande,
    nouveau_statut
):

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

        return redirect(
            url_for("bar")
        )

    commandes = Commande.query.filter_by(
        numero_commande=numero_commande
    ).all()

    if not commandes:

        if request.method == "POST":

            return {
                "success": False,
                "message": "Commande introuvable"
            }, 404

        return redirect(
            url_for("bar")
        )

    for commande in commandes:

        commande.statut = nouveau_statut

    db.session.commit()

    if request.method == "POST":

        return {
            "success": True,
            "numero": numero_commande,
            "statut": nouveau_statut
        }

    return redirect(
        url_for("bar")
    )


# ============================================================
# API COMMANDES
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
        "commandes": list(
            commandes_groupees.values()
        )
    }


# ============================================================
# ADMINISTRATION
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
# AJOUTER UN PRODUIT AVEC PHOTO
# ============================================================

@app.route(
    "/admin/produit/ajouter",
    methods=["POST"]
)
def ajouter_produit():

    nom = request.form.get(
        "nom",
        ""
    ).strip()

    categorie = request.form.get(
        "categorie",
        "Boisson"
    )

    fichier = request.files.get(
        "photo"
    )

    if not nom:

        return redirect(
            url_for("admin")
        )

    produit_existant = Produit.query.filter_by(
        nom=nom
    ).first()

    if produit_existant:

        return redirect(
            url_for("admin")
        )

    photo = None

    # --------------------------------------------------------
    # ENREGISTREMENT DE LA PHOTO
    # --------------------------------------------------------

    if fichier and fichier.filename:

        if fichier_autorise(
            fichier.filename
        ):

            nom_securise = secure_filename(
                fichier.filename
            )

            extension = nom_securise.rsplit(
                ".",
                1
            )[1].lower()

            nom_unique = (
                str(uuid.uuid4())
                + "."
                + extension
            )

            chemin = os.path.join(
                app.config["UPLOAD_FOLDER"],
                nom_unique
            )

            fichier.save(chemin)

            photo = (
                "boissons/"
                + nom_unique
            )

    # --------------------------------------------------------
    # CREATION DU PRODUIT
    # --------------------------------------------------------

    produit = Produit(

        nom=nom,

        categorie=categorie,

        photo=photo,

        disponible=True

    )

    db.session.add(
        produit
    )

    db.session.commit()

    return redirect(
        url_for("admin")
    )


# ============================================================
# SUPPRIMER UN PRODUIT
# ============================================================

@app.route(
    "/admin/produit/<int:produit_id>/supprimer",
    methods=["POST"]
)
def supprimer_produit(
    produit_id
):

    produit = Produit.query.get_or_404(
        produit_id
    )

    # --------------------------------------------------------
    # SUPPRESSION DE LA PHOTO
    # --------------------------------------------------------

    if produit.photo:

        chemin_photo = os.path.join(

            app.static_folder,

            produit.photo

        )

        if os.path.exists(
            chemin_photo
        ):

            try:

                os.remove(
                    chemin_photo
                )

            except OSError:

                pass

    # --------------------------------------------------------
    # SUPPRESSION DU PRODUIT
    # --------------------------------------------------------

    db.session.delete(
        produit
    )

    db.session.commit()

    return redirect(
        url_for("admin")
    )


# ============================================================
# PAGE DE CONFIRMATION
# ============================================================

@app.route("/confirmation")
def confirmation():

    return render_template(
        "confirmation.html"
    )




# ============================================================
# REINITIALISER LES COMMANDES
# ============================================================

@app.route("/commandes/reset", methods=["POST"])
def reset_commandes():

    Commande.query.delete()
    db.session.commit()

    return redirect(url_for("bar"))

# ============================================================
# DEMARRAGE
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

