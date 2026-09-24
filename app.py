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

# --- BASE DE DONNÉES INJECTÉE POUR SEPTEMBRE ---
def generer_tableau_defaut():
    if mois_cle == "09" and str(annee_actuelle) == "2026":
        donnees_septembre = {
            'MR': ['/', '/', 'msk', 'msk', 'X', '/', 'msk', '/', 'X', '/', 'msk', '/', 'msk', '/', '', 'X', '/', 'X', '', '', '', ''],
            'MT': ['msk', 'X', 'X', 'X', '/', '/', '', '', 'msk', '', 'X', 'X', '', '', '', '/', 'X', 'msk', '', '', '', ''],
            'Kathaï': ['X', '/', '', 'X', '/', 'X', 'X', '', 'X', '/', '', 'X', '/', '', '', '', 'X', 'msk', '', '', '', ''],
            'Sissy': ['X', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
            'Maxou': ['', '', '', '', 'msk', 'msk', 'X', '', '', '', 'X', '/', '', '', '', 'msk', '', '', '', '', '', ''],
            'Seb': ['', 'msk', '', '', '', '', '/', '', '', 'msk', 'msk', 'msk', '/', '', '', '/', '', '', '', '', '', ''],
            'Stéphanou': ['msk', 'X', '/', '', 'msk', '', '', 'msk', '', '', '', '', 'X', 'msk', '', 'msk', 'msk', '/', '', '', '', ''],
            'Mickaël': ['', '', '', '', '', '/', '', '', '', '/', '', '', 'X', '/', '', '', 'msk', '', '', '', '', ''],
            'Céline': ['/', 'msk', '/', 'msk', 'X', '/', '/', 'X', '/', 'X', '/', 'msk', 'msk', 'X', '', 'X', '/', 'X', '', '', '', '']
        }
        df = pd.DataFrame(donnees_septembre, index=dates_semaine_attendues)
        df.index.name = 'DATE'
        return df
    else:
        init_data = {j: [''] * len(dates_semaine_attendues) for j in liste_joueurs}
        init_data['DATE'] = dates_semaine_attendues
        return pd.DataFrame(init_data).set_index('DATE')

if st.sidebar.button("🔄 Forcer la synchronisation (Vider le cache)"):
    st.cache_data.clear()
    st.rerun()

# --- FONCTION DE CHARGEMENT ---
@st.cache_data(ttl=2)
def charger_donnees_mensuelles(file_name):
    if not repo:
        return None, None, generer_tableau_defaut()
    try:
        file_content = repo.get_contents(file_name)
        csv_data = file_content.decoded_content.decode('utf-8-sig')
        
        if not csv_data.strip():
            return repo, file_content.sha, generer_tableau_defaut()
            
        df = pd.read_csv(io.StringIO(csv_data), index_col=0)
        
        if df.empty or len(df.columns) == 0:
            return repo, file_content.sha, generer_tableau_defaut()
            
        for j in df.columns:
            df[j] = df[j].fillna('').astype(str).str.replace('None', '').str.replace('nan', '')
        
        return repo, file_content.sha, df
    except Exception:
        return repo, None, generer_tableau_defaut()

current_repo, file_sha, df_mois = charger_donnees_mensuelles(FILE_PATH)

st.markdown("---")

# --- AFFICHAGE DE LA GRILLE ---
if df_mois is not None and not df_mois.empty:
    st.subheader(f"📝 Tableau de {MOIS_OPTIONS[mois_cle]} {annee_actuelle}")
    
    df_mois.index.name = "DATE"
    
    if list(df_mois.index) != dates_semaine_attendues:
        df_mois = generer_tableau_defaut()

    configuration_colonnes = {}
    for joueur in liste_joueurs:
        if joueur in df_mois.columns:
            configuration_colonnes[joueur] = st.column_config.TextColumn(label=joueur, default="")

    widget_key = f"grid_editor_{mois_cle}_{annee_actuelle}_{len(df_mois)}"
    
    edited_df = st.data_editor(
        df_mois, 
        column_config=configuration_colonnes,
        use_container_width=True,
        key=widget_key
    )

    if st.button(f"💾 Enregistrer les modifications", type="primary"):
        if current_repo:
            try:
                try:
                    fe = current_repo.get_contents(FILE_PATH)
                    sha_maj = fe.sha
                except Exception:
                    sha_maj = file_sha

                df_sauvegarde = edited_df.copy()
                for col in df_sauvegarde.columns:
                    df_sauvegarde[col] = df_sauvegarde[col].astype(str).str.replace('None', '').str.replace('nan', '')
                
                csv_buffer = io.StringIO()
                df_sauvegarde.to_csv(csv_buffer)
                
                if sha_maj:
                    current_repo.update_file(path=FILE_PATH, message="Mise à jour manuelle", content=csv_buffer.getvalue(), sha=sha_maj)
                else:
                    current_repo.create_file(path=FILE_PATH, message="Création manuelle", content=csv_buffer.getvalue())
                st.success("✅ Enregistré avec succès !")
                st.cache_data.clear()
                st.rerun()
            except Exception as error:
                st.error(f"Erreur de sauvegarde : {error}")
        else:
            st.warning("⚠️ Mode local : Modifications éditées à l'écran mais non sauvegardées sur GitHub (Vérifiez vos secrets Streamlit).")

    # --- SECTION CALCULS ---
    st.markdown("---")
    if st.button("🔄 Calculer les scores du mois"):
        scores_qualifies = {}
        scores_disqualifies = {}
        tous_les_scores = {}
        total_jours_ouvres = len(edited_df)
        seuil_minimum = total_jours_ouvres / 2
        
        for joueur in edited_df.columns:
            valeurs = edited_df[joueur].astype(str).str.strip().str.lower()
            valeurs = valeurs.replace(['msr', 'mok', 'nsk', 'none', 'nan'], 'msk')
            
            nb_win = (valeurs == 'x').sum()
            nb_pres = valeurs.str.count(r'/').sum()
            nb_msk = (valeurs == 'msk').sum()
            
            total = (nb_win * 2.0) + (nb_pres * 0.5) + (nb_msk * -1.0)
            jours_joues = nb_win + nb_pres + nb_msk
            
            tous_les_scores[joueur] = (total, jours_joues)
            if jours_joues >= seuil_minimum:
                scores_qualifies[joueur] = (total, jours_joues)
            else:
                scores_disqualifies[joueur] = (total, jours_joues)
        
        st.subheader("📊 Scores Totaux en Cours (Tout le monde)")
        cols_scores = st.columns(len(tous_les_scores))
        
        for i, (joueur, (total, jours)) in enumerate(tous_les_scores.items()):
            with cols_scores[i]:
                txt_j = f"{jours}/{total_jours_ouvres}j"
                if jours < seuil_minimum:
                    st.metric(label=f"{joueur} ⚠️", value=f"{total} pts", delta=f"Incomplet ({txt_j})", delta_color="inverse")
                else:
                    st.metric(label=joueur, value=f"{total} pts", delta=f"Qualifié ({txt_j})", delta_color="normal" if total > 0 else "off")

        st.markdown("---")
        st.subheader("🏆 Le Podium Officiel (≥ 50% du mois)")
        classement_trie = sorted(scores_qualifies.items(), key=lambda item: item[1][0], reverse=True)
        
        if len(classement_trie) > 0:
            pod1, pod2, pod3 = st.columns(3)
            
            if len(classement_trie) >= 1:
                p1_name = classement_trie[0][0]
                p1_score = classement_trie[0][1][0]
                p1_j = classement_trie[0][1][1]
                pod1.metric(label=f"🥇 1er : {p1_name}", value=f"{p1_score} pts", delta=f"{p1_j} jours")
                
            if len(classement_trie) >= 2:
                p2_name = classement_trie[1][0]
                p2_score = classement_trie[1][1][0]
                p2_j = classement_trie[1][1][1]
                pod2.metric(label=f"🥈 2e : {p2_name}", value=f"{p2_score} pts", delta=f"{p2_j} jours")
                
            if len(classement_trie) >= 3:
                p3_name = classement_trie[2][0]
                p3_score = classement_trie[2][1][0]
                p3_j = classement_trie[2][1][1]
                pod3.metric(label=f"🥉 3e : {p3_name}", value=f"{p3_score} pts", delta=f"{p3_j} jours")
        else:
            st.info("Aucun joueur qualifié pour le moment.")
                
        st.markdown("---")
        st.subheader("📋 Classement Général des Qualifiés")
        if len(classement_trie) > 0:
            donnees_classement = []
