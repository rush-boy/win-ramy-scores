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

# Fonction pour générer la liste exacte des jours ouvrés (Lun au Ven)
def generer_jours_ouvres():
    debut_mois = f"{annee_actuelle}-{mois_cle}-01"
    if mois_cle == "12":
        fin_mois = f"{annee_actuelle}-12-31"
    else:
        prochain_mois = f"{int(mois_cle)+1:02d}"
        fin_mois = (pd.to_datetime(f"{annee_actuelle}-{prochain_mois}-01") - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    
    jours_ouvres = pd.bdate_range(start=debut_mois, end=fin_mois)
    jours_fr = {0: "Lun", 1: "Mar", 2: "Mer", 3: "Jeu", 4: "Ven"}
    return [f"{jours_fr[d.dayofweek]} {d.strftime('%d/%m')}" for d in jours_ouvres]

dates_semaine_attendues = generer_jours_ouvres()

# --- FONCTION DE CHARGEMENT DES DONNÉES ---
@st.cache_data(ttl=2)
def charger_donnees_mensuelles(file_name):
    if repo:
        try:
            file_content = repo.get_contents(file_name)
            csv_data = file_content.decoded_content.decode('utf-8')
            df = pd.read_csv(io.StringIO(csv_data), index_col=0)
            
            for j in df.columns:
                df[j] = df[j].fillna('').astype(str).str.replace('None', '').str.replace('nan', '')
            
            return repo, file_content.sha, df
        except Exception:
            init_data = {j: [''] * len(dates_semaine_attendues) for j in liste_joueurs}
            init_data['DATE'] = dates_semaine_attendues
            df_vierge = pd.DataFrame(init_data).set_index('DATE')
            return repo, None, df_vierge
    return None, None, pd.DataFrame()

current_repo, file_sha, df_mois = charger_donnees_mensuelles(FILE_PATH)

if not df_mois.empty:
    st.subheader(f"📝 Tableau de {MOIS_OPTIONS[mois_cle]} {annee_actuelle}")
    
    besoin_mise_a_niveau = list(df_mois.index) != dates_semaine_attendues
    if besoin_mise_a_niveau:
        st.warning("⚙️ Le format des dates de ce mois a besoin d'être synchronisé du Lundi au Vendredi.")
        if st.button("🔧 Appliquer le calendrier de la semaine (Conserve vos données)", type="secondary"):
            df_aligne = pd.DataFrame(index=dates_semaine_attendues, columns=liste_joueurs).fillna('')
            for i, (idx_ancien, row) in enumerate(df_mois.iterrows()):
                if i < len(dates_semaine_attendues):
                    date_cible = dates_semaine_attendues[i]
                    df_aligne.loc[date_cible] = row
            try:
                csv_buffer = io.StringIO()
                df_aligne.to_csv(csv_buffer)
                if file_sha:
                    current_repo.update_file(
                        path=FILE_PATH,
                        message="Forçage du calendrier Lundi-Vendredi",
                        content=csv_buffer.getvalue(),
                        sha=file_sha
                    )
                    st.success("⚡ Calendrier mis à jour ! Rechargement de la page...")
                    st.cache_data.clear()
                    st.rerun()
            except Exception as e:
                st.error(f"Erreur lors de la mise à niveau : {e}")

    configuration_colonnes = {
        joueur: st.column_config.TextColumn(label=joueur, default="") 
        for joueur in df_mois.columns
    }

    widget_key = f"editor_{mois_cle}_{annee_actuelle}_{len(df_mois)}"
    edited_df = st.data_editor(
        df_mois, 
        column_config=configuration_colonnes,
        use_container_width=True,
        key=widget_key
    )

    if st.button(f"💾 Enregistrer les modifications", type="primary"):
        if current_repo:
            try:
                df_sauvegarde = edited_df.copy()
                for col in df_sauvegarde.columns:
                    df_sauvegarde[col] = df_sauvegarde[col].astype(str).str.replace('None', '').str.replace('nan', '')
                
                csv_buffer = io.StringIO()
                df_sauvegarde.to_csv(csv_buffer)
                
                if file_sha:
                    current_repo.update_file(
                        path=FILE_PATH,
                        message=f"Mise à jour des scores pour {MOIS_OPTIONS[mois_cle]}",
                        content=csv_buffer.getvalue(),
                        sha=file_sha
                    )
                else:
                    current_repo.create_file(
                        path=FILE_PATH,
                        message=f"Création du tableau pour {MOIS_OPTIONS[mois_cle]}",
                        content=csv_buffer.getvalue()
                    )
                
                st.success(f"✅ Enregistré !")
                st.cache_data.clear()
                st.rerun()
            except Exception as error:
                st.error(f"Erreur lors de la sauvegarde : {error}")

    # --- CALCUL ET PODIUM TRAITÉS SANS ERREUR ---
    st.markdown("---")
    if st.button("🔄 Calculer les totaux et afficher le classement"):
        SCORE_MAP = {'/': 0.5, 'x': 2.0, 'msk': -1.0}
        scores_totaux = {}
        
        for joueur in edited_df.columns:
            total = 0.0
            valeurs = edited_df[joueur].astype(str).str.strip().str.lower()
            # Séparation de la ligne problématique en une syntaxe classique universelle
            valeurs = valeurs.replace(['msr', 'mok', 'nsk', 'none', 'nan'], 'msk')
            
            for symbole, points in SCORE_MAP.items():
                if symbole == '/':
                    count = valeurs.str.count(r'/').sum()
                else:
                    count = (valeurs == symbole).sum()
                total += count * points
            scores_totaux[joueur] = total
            
        # Trier les joueurs par score décroissant
        classement_trie = sorted(scores_totaux.items(), key=lambda item: item[1], reverse=True)
        
        # 1. Affichage du TOP 3 (Le Podium)
        st.subheader(f"🏆 Le Podium de {MOIS_OPTIONS[mois_cle]}")
        
        pod1, pod2, pod3 = st.columns(3)
        
        if len(classement_trie) >= 1:
            with pod1:
                st.markdown(f"### 🥇 1ère Place")
                st.metric(label=classement_trie[0][0], value=f"{classement_trie[0][1]} pts", delta="🔥")
        if len(classement_trie) >= 2:
            with pod2:
                st.markdown(f"### 🥈 2ème Place")
                st.metric(label=classement_trie[1][0], value=f"{classement_trie[1][1]} pts")
        if len(classement_trie) >= 3:
            with pod3:
                st.markdown(f"### 🥉 3ème Place")
                st.metric(label=classement_trie[2][0], value=f"{classement_trie[2][1]} pts")
                
        # 2. Affichage du classement général complet
        st.markdown("---")
        st.subheader("📊 Classement Général Complet")
        
        donnees_classement = []
        for rang, (joueur, score) in enumerate(classement_trie, start=1):
            if rang == 1: icone = "🥇"
            elif rang == 2: icone = "🥈"
            elif rang == 3: icone = "🥉"
            elif rang == len(classement_trie): icone = "💀 (Miskine)"
            else: icone = "👤"
            
            donnees_classement.append({
                "Rang": rang,
                "Statut": icone,
                "Joueur": joueur,
                "Score Total": f"{score} pts"
            })
            
        df_classement = pd.DataFrame(donnees_classement)
        st.dataframe(df_classement.set_index("Rang"), use_container_width=True)
