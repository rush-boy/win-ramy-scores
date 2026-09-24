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

# Liste officielle des joueurs
liste_joueurs = ['MR', 'MT', 'Kathaï', 'Sissy', 'Maxou', 'Seb', 'Stéphanou', 'Mickaël', 'Céline']

# --- FONCTION DE CHARGEMENT DES DONNÉES ---
@st.cache_data(ttl=5)
def charger_donnees_mensuelles(file_name):
    if repo:
        try:
            file_content = repo.get_contents(file_name)
            csv_data = file_content.decoded_content.decode('utf-8')
            df = pd.read_csv(io.StringIO(csv_data), index_col=0)
            for j in df.columns:
                df[j] = df[j].fillna('').astype(str)
            return repo, file_content.sha, df
        except Exception:
            # --- MODIFICATION : EXCLUSION DES WEEK-ENDS ---
            # 1. Définir le premier et le dernier jour du mois sélectionné
            debut_mois = f"{annee_actuelle}-{mois_cle}-01"
            # Trouver le dernier jour du mois en passant au mois suivant puis en retirant 1 jour
            if mois_cle == "12":
                fin_mois = f"{annee_actuelle}-12-31"
            else:
                prochain_mois = f"{int(mois_cle)+1:02d}"
                fin_mois = (pd.to_datetime(f"{annee_actuelle}-{prochain_mois}-01") - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
            
            # 2. Générer uniquement les jours de la semaine (Lundi au Vendredi)
            jours_ouvres = pd.bdate_range(start=debut_mois, end=fin_mois)
            
            # 3. Formater les dates en "JJ/MM" ou "Lun 01/09" pour coller au style de votre feuille d'origine
            # Table de correspondance pour les jours en français
            jours_fr = {0: "Lun", 1: "Mar", 2: "Mer", 3: "Jeu", 4: "Ven"}
            dates_formatees = [f"{jours_fr[d.dayofweek]} {d.strftime('%d/%m')}" for d in jours_ouvres]
            
            # 4. Initialisation de la structure avec les jours filtrés
            init_data = {j: [''] * len(dates_formatees) for j in liste_joueurs}
            init_data['DATE'] = dates_formatees
            df_vierge = pd.DataFrame(init_data).set_index('DATE')
            return repo, None, df_vierge
    return None, None, pd.DataFrame()

current_repo, file_sha, df_mois = charger_donnees_mensuelles(FILE_PATH)

if not df_mois.empty:
    st.subheader(f"📝 Tableau de {MOIS_OPTIONS[mois_cle]} {annee_actuelle} (Sans les week-ends)")
    
    if file_sha is None:
        st.warning(f"ℹ️ Aucun historique trouvé pour ce mois. Un nouveau tableau vierge (du lundi au vendredi) a été généré.")

    # Configuration pour bloquer les zéros et forcer le texte
    configuration_colonnes = {
        joueur: st.column_config.TextColumn(label=joueur, default="") 
        for joueur in df_mois.columns
    }

    # Éditeur interactif
    edited_df = st.data_editor(
        df_mois, 
        column_config=configuration_colonnes,
        use_container_width=True
    )

    # Bouton de sauvegarde persistante
    if st.button(f"💾 Sauvegarder {MOIS_OPTIONS[mois_cle]} sur GitHub", type="primary"):
        if current_repo:
            try:
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
