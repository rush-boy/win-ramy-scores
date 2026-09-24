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

MOIS_OPTIONS = {
    "01": "Janvier", "02": "Février", "03": "Mars", "04": "Avril", 
    "05": "Mai", "06": "Juin", "07": "Juillet", "08": "Août", 
    "09": "Septembre", "10": "Octobre", "11": "Novembre", "12": "Décembre"
}

now = datetime.datetime.now()
annee_actuelle = st.sidebar.selectbox("Année", [now.year, now.year - 1], index=0)
mois_cle = st.sidebar.selectbox(
    "Mois", 
    list(MOIS_OPTIONS.keys()), 
    index=list(MOIS_OPTIONS.keys()).index(f"{now.month:02d}")
)

FILE_PATH = f"scores_{mois_cle}_{annee_actuelle}.csv"
st.sidebar.info(f"📂 Fichier actif : `{FILE_PATH}`")

# Liste officielle des joueurs pour s'assurer qu'ils restent au format texte
liste_joueurs = ['MR', 'MT', 'Kathaï', 'Sissy', 'Maxou', 'Seb', 'Stéphanou', 'Mickaël', 'Céline']

# --- FONCTION DE CHARGEMENT DES DONNÉES ---
@st.cache_data(ttl=5)
def charger_donnees_mensuelles(file_name):
    if repo:
        try:
            file_content = repo.get_contents(file_name)
            csv_data = file_content.decoded_content.decode('utf-8')
            # On force pandas à lire toutes les colonnes des joueurs comme des chaînes de caractères (str)
            df = pd.read_csv(io.StringIO(csv_data), index_col=0)
            for j in df.columns:
                df[j] = df[j].fillna('').astype(str)
            return repo, file_content.sha, df
        except Exception:
            # Générer les jours du mois de 01 à 31
            dates = [f"{i:02d}/{mois_cle}" for i in range(1, 32)]
            init_data = {j: [''] * len(dates) for j in liste_joueurs}
            init_data['DATE'] = dates
            df_vierge = pd.DataFrame(init_data).set_index('DATE')
            return repo, None, df_vierge
    return None, None, pd.DataFrame()

current_repo, file_sha, df_mois = charger_donnees_mensuelles(FILE_PATH)

if not df_mois.empty:
    st.subheader(f"📝 Tableau de {MOIS_OPTIONS[mois_cle]} {annee_actuelle}")
    
    if file_sha is None:
        st.warning(f"ℹ️ Aucun historique trouvé pour ce mois. Un nouveau tableau vierge a été généré ci-dessous.")

    # --- CORRECTION DU BUG DES ZÉROS ---
    # On crée une configuration qui force chaque colonne de joueur à être un champ de texte libre (TextColumn)
    configuration_colonnes = {
        joueur: st.column_config.TextColumn(label=joueur, default="") 
        for joueur in df_mois.columns
    }

    # Éditeur interactif avec la configuration forcée en texte
    edited_df = st.data_editor(
        df_mois, 
        column_config=configuration_colonnes,
        use_container_width=True
    )

    # Bouton de sauvegarde persistante
    if st.button(f"💾 Sauvegarder {MOIS_OPTIONS[mois_cle]} sur GitHub", type="primary"):
        if current_repo:
            try:
                # Nettoyage final des données avant sauvegarde pour éviter les valeurs parasites
                df_sauvegarde = edited_df.copy()
                for col in df_sauvegarde.columns:
                    df_sauvegarde[col] = df_sauvegarde[col].astype(str).str.replace('None', '').str.replace('nan', '')
                
                csv_buffer = io.StringIO()
                df_sauvegarde.to_csv(csv_buffer)
                nouveau_contenu = csv_buffer.getvalue()
                
                if file_sha:
                    current_repo.update_file(
                        path=FILE_PATH,
                        message=f"Mise à jour des scores pour {MOIS_OPTIONS[mois_cle]} {annee_actuelle}",
                        content=nouveau_contenu,
                        sha=file_sha
                    )
                else:
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
            # Nettoyage des chaînes textuelles pour le calcul
            valeurs = edited_df[joueur].astype(str).str.strip().str.lower()
            valeurs = valeurs.replace(['msr', 'mok', 'nsk', 'none', 'nan'], 'msk')
            
            for symbole, points in SCORE_MAP.items():
                if symbole == '/':
                    count = valeurs.str.count(r'/').sum()
                else:
                    count = (valeurs == symbole).sum()
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
