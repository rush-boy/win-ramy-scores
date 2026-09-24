import streamlit as st
import pandas as pd
import numpy as np

# Configuration de la page
st.set_page_config(page_title="Win Ramy - Calculateur de Scores", layout="wide")
st.title("🏆 Win Ramy Force à la Miskine - Calculateur Automatique")

# Rappel des règles définies
st.sidebar.header("Règles des scores")
st.sidebar.markdown("""
- **`X`** (Win) : **2.0 pts**
- **`/`** (Présence) : **0.5 pt**
- **`msk`** (Défaite) : **-1.0 pt**
""")

# Définition du barème et nettoyage des entrées
SCORE_MAP = {'/': 0.5, 'x': 2.0, 'msk': -1.0}

# Initialisation d'un tableau d'exemple si aucun fichier n'est chargé
joueurs = ['MR', 'MT', 'Kathaï', 'Sissy', 'Maxou', 'Seb', 'Stéphanou', 'Mickaël', 'Céline']
dates = [f"Jour {i}" for i in range(1, 6)]

if 'df' not in st.session_state:
    # Création d'une matrice vide par défaut
    init_data = {j: [''] * len(dates) for j in joueurs}
    init_data['DATE'] = dates
    st.session_state.df = pd.DataFrame(init_data).set_index('DATE')

# Option 1 : Importer un fichier Excel ou CSV existant
uploaded_file = st.file_uploader("Importer votre tableau (CSV ou Excel)", type=["csv", "xlsx"])
if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            st.session_state.df = pd.read_csv(uploaded_file, index_index=0)
        else:
            st.session_state.df = pd.read_excel(uploaded_file, index_col=0)
    except Exception as e:
        st.error(f"Erreur lors du chargement du fichier : {e}")

st.subheader("📝 Saisie et modification des données")
st.write("Double-cliquez sur une case pour ajouter ou modifier un symbole (`/`, `X`, `msk`).")

# Éditeur de tableau interactif
edited_df = st.data_editor(st.session_state.df, use_container_width=True)

# Fonction de calcul automatique des scores
def calculer_scores(df):
    scores_totaux = {}
    for joueur in df.columns:
        total = 0.0
        # Nettoyage et uniformisation (gestion des minuscules/majuscules et espaces)
        valeurs = df[joueur].astype(str).str.strip().str.lower()
        
        # Remplacement des fautes de frappe courantes constatées (ex: msr ou mok -> msk)
        valeurs = valeurs.replace(['msr', 'mok', 'nsk'], 'msk')
        
        for symbole, points in SCORE_MAP.items():
            count = valeurs.str.count(symbole == '/' and r'/' or symbole).sum() if symbole == '/' else (valeurs == symbole).sum()
            total += count * points
            
        scores_totaux[joueur] = total
    return scores_totaux

# Calcul et affichage des totaux
if st.button("🔄 Calculer les scores totaux", type="primary"):
    scores = calculer_scores(edited_df)
    
    st.subheader("📊 Résultats du Groupe Orienté")
    
    # Présentation sous forme de jolies cartes de score
    cols = st.columns(len(scores))
    for idx, (joueur, total) in enumerate(scores.items()):
        with cols[idx]:
            # Couleur dynamique selon le score
            if total > 0:
                st.metric(label=joueur, value=f"{total} pts", delta="🔥")
            elif total < 0:
                st.metric(label=joueur, value=f"{total} pts", delta="💀", delta_color="inverse")
            else:
                st.metric(label=joueur, value=f"{total} pts")

    # Ajouter la ligne TOTAL au tableau édité pour l'export
    df_export = edited_df.copy()
    df_export.loc['TOTAL'] = [scores[j] for j in df_export.columns]
    
    # Option de téléchargement du résultat
    csv = df_export.to_csv().encode('utf-8')
    st.download_button(
        label="📥 Télécharger le tableau complet avec les totaux (CSV)",
        data=csv,
        file_name="win_ramy_scores_complets.csv",
        mime="text/csv",
    )
