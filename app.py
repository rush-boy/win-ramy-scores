import streamlit as st
import pandas as pd
from github import Github
import io

st.set_page_config(page_title="Win Ramy - Sauvegarde Automatique", layout="wide")
st.title("🏆 Win Ramy Force à la Miskine - Gestionnaire des Scores")

# Configurer l'accès à GitHub sécurisé via Streamlit Secrets
# Nous allons configurer ces 3 variables à l'étape suivante
try:
    REPO_NAME = st.secrets["GITHUB_REPO"]       # Exemple: "votre-pseudo/win-ramy-scores"
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]   # Votre clé d'accès privée
    FILE_PATH = "scores.csv"                    # Le nom du fichier de données sur GitHub
    
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
except Exception as e:
    st.error("⚠️ Les configurations de sauvegarde (Secrets) ne sont pas encore prêtes.")
    repo = None

# 1. Chargement des données depuis GitHub (ou données par défaut)
@st.cache_data(ttl=10) # Rafraîchir le cache toutes les 10 secondes
def charger_donnees_github():
    if repo:
        try:
            file_content = repo.get_contents(FILE_PATH)
            csv_data = file_content.decoded_content.decode('utf-8')
            return pd.read_csv(io.StringIO(csv_data), index_col=0)
        except Exception:
            # Si le fichier n'existe pas encore sur GitHub, créer une structure vide
            joueurs = ['MR', 'MT', 'Kathaï', 'Sissy', 'Maxou', 'Seb', 'Stéphanou', 'Mickaël', 'Céline']
            dates = [f"Jour {i}" for i in range(1, 31)]
            init_data = {j: [''] * len(dates) for j in joueurs}
            init_data['DATE'] = dates
            return pd.DataFrame(init_data).set_index('DATE')
    return pd.DataFrame()

# Charger les données courantes
df_actuel = charger_donnees_github()

if not df_actuel.empty:
    st.subheader("📝 Saisie et modification des données")
    st.write("Modifiez les cases, puis cliquez sur le bouton vert tout en bas pour sauvegarder vos modifications.")

    # Éditeur interactif
    edited_df = st.data_editor(df_actuel, use_container_width=True)

    # Bouton de sauvegarde persistante
    if st.button("💾 Sauvegarder les modifications sur GitHub", type="primary"):
        if repo:
            try:
                # Convertir le tableau modifié en texte CSV
                csv_buffer = io.StringIO()
                edited_df.to_csv(csv_buffer)
                nouveau_contenu = csv_buffer.getvalue()
                
                # Récupérer l'ancien fichier pour avoir son identifiant unique (sha)
                contents = repo.get_contents(FILE_PATH)
                
                # Mettre à jour le fichier sur GitHub
                repo.update_file(
                    path=FILE_PATH,
                    message="Mise à jour automatique des scores via l'application Streamlit",
                    content=nouveau_contenu,
                    sha=contents.sha
                )
                st.success("✅ Données enregistrées avec succès sur GitHub ! Vos amis verront le tableau mis à jour.")
                st.cache_data.clear() # Forcer le rechargement de la page
            except Exception as error:
                st.error(f"Erreur lors de la sauvegarde : {error}")
        else:
            st.error("Impossible de sauvegarder : la connexion à GitHub n'est pas configurée.")

    # Section Calcul des scores
    st.markdown("---")
    if st.button("🔄 Calculer les scores totaux"):
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
            
        st.subheader("📊 Résultats en direct")
        cols = st.columns(len(scores_totaux))
        for idx, (joueur, total) in enumerate(scores_totaux.items()):
            with cols[idx]:
                if total > 0:
                    st.metric(label=joueur, value=f"{total} pts", delta="🔥")
                elif total < 0:
                    st.metric(label=joueur, value=f"{total} pts", delta="💀", delta_color="inverse")
                else:
                    st.metric(label=joueur, value=f"{total} pts")
