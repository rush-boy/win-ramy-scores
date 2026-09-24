import streamlit as st
import pandas as pd
from github import Github
import io
import datetime

st.set_page_config(page_title="Win Ramy - Historique Mensuel", layout="wide")
st.title("🏆 Win Ramy Force à la Miskine - Gestionnaire Multimois")

# Configuration de l'accès à GitHub
try:
    REPO_NAME = st.secrets["GITHUB_REPO"]
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
except Exception as e:
    st.error("⚠️ Les configurations de sauvegarde (Secrets) ne sont pas prêtes.")
    repo = None

# --- SECTION : SÉLECTION DU MOIS ---
st.sidebar.header("📅 Navigation Temporelle")

# Liste des mois pour le menu déroulant
MOIS_OPTIONS = {
    "01": "Janvier", "02": "Février", "03": "Mars", "04": "Avril", 
    "05": "Mai", "06": "Juin", "07": "Juillet", "08": "Août", 
    "09": "Septembre", "10": "Octobre", "11": "Novembre", "12": "Décembre"
}

# Année actuelle et mois actuel par défaut
now = datetime.datetime.now()
annee_actuelle = st.sidebar.selectbox("Année", [now.year, now.year - 1], index=0)
mois_cle = st.sidebar.selectbox(
    "Mois", 
    list(MOIS_OPTIONS.keys()), 
    index=list(MOIS_OPTIONS.keys()).index(f"{now.month:02d}")
)

# Nom du fichier unique pour le mois sélectionné (ex: scores_09_2026.csv)
FILE_PATH = f"scores_{mois_cle}_{annee_actuelle}.csv"
st.sidebar.info(f"📂 Fichier actif : `{FILE_PATH}`")

# --- FONCTION DE CHARGEMENT DES DONNÉES ---
@st.cache_data(ttl=5)
def charger_donnees_mensuelles(file_name):
    if repo:
        try:
            # Tenter de lire le fichier spécifique sur GitHub
            file_content = repo.get_contents(file_name)
            csv_data = file_content.decoded_content.decode('utf-8')
            return repo, file_content.sha, pd.read_csv(io.StringIO(csv_data), index_col=0)
        except Exception:
            # Si le fichier n'existe pas encore pour ce mois, on crée une structure vide par défaut
            joueurs = ['MR', 'MT', 'Kathaï', 'Sissy', 'Maxou', 'Seb', 'Stéphanou', 'Mickaël', 'Céline']
            # Générer les jours du mois de 01 à 31 (ou 30 selon le besoin)
            dates = [f"{i:02d}/{mois_cle}" for i in range(1, 32)]
            init_data = {j: [''] * len(dates) for j in joueurs}
            init_data['DATE'] = dates
            df_vierge = pd.DataFrame(init_data).set_index('DATE')
            return repo, None, df_vierge
    return None, None, pd.DataFrame()

# Charger les données spécifiques au mois choisi
current_repo, file_sha, df_mois = charger_donnees_mensuelles(FILE_PATH)

if not df_mois.empty:
    st.subheader(f"📝 Tableau de {MOIS_OPTIONS[mois_cle]} {annee_actuelle}")
    
    if file_sha is None:
        st.warning(f"ℹ️ Aucun historique trouvé pour ce mois. Un nouveau tableau vierge a été généré ci-dessous.")

    # Éditeur interactif
    edited_df = st.data_editor(df_mois, use_container_width=True)

    # Bouton de sauvegarde persistante
    if st.button(f"💾 Sauvegarder {MOIS_OPTIONS[mois_cle]} sur GitHub", type="primary"):
        if current_repo:
            try:
                csv_buffer = io.StringIO()
                edited_df.to_csv(csv_buffer)
                nouveau_contenu = csv_buffer.getvalue()
                
                if file_sha:
                    # Mettre à jour le fichier existant
                    current_repo.update_file(
                        path=FILE_PATH,
                        message=f"Mise à jour des scores pour {MOIS_OPTIONS[mois_cle]} {annee_actuelle}",
                        content=nouveau_contenu,
                        sha=file_sha
                    )
                else:
                    # Créer un tout nouveau fichier s'il n'existait pas
                    current_repo.create_file(
                        path=FILE_PATH,
                        message=f"Initialisation de l'historique pour {MOIS_OPTIONS[mois_cle]} {annee_actuelle}",
                        content=nouveau_contenu
                    )
                
                st.success(f"✅ Historique de {MOIS_OPTIONS[mois_cle]} enregistré avec succès !")
                st.cache_data.clear()
            except Exception as error:
                st.error(f"Erreur lors de la sauvegarde : {error}")

    # Section Calcul des scores
    st.markdown("---")
    if st.button("🔄 Calculer les totaux du mois sélectionné"):
        SCORE_MAP = {'/': 0.5, 'x': 2.0, 'msk': -1.0}
        scores_totaux = {}
        
        for joueur in edited_df.columns:
            total = 0.0
            valeurs = edited_df[joueur].astype(str).str.strip().str.lower()
            valeurs = valeurs.replace(['msr', 'mok', 'nsk'], 'msk')
            
            for symbole, points in SCORE_MAP.items():
                count = valeurs.str.count(symbole == '/' and r'/' or symbole).sum() if symbole == '/' else (valeurs == symbole).sum()
                total += count * points
            scores_totaux[joueur] = total
            
        st.subheader(f"📊 Résultats du mois : {MOIS_OPTIONS[mois_cle]}")
        cols = st.columns(len(scores_totaux))
        for idx, (joueur, total) in enumerate(scores_totaux.items()):
            with cols[idx]:
                if total > 0:
                    st.metric(label=joueur, value=f"{total} pts", delta="🔥")
                elif total < 0:
                    st.metric(label=joueur, value=f"{total} pts", delta="💀", delta_color="inverse")
                else:
                    st.metric(label=joueur, value=f"{total} pts")
