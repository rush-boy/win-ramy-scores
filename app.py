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

# Bouton d'urgence pour vider le cache
if st.sidebar.button("🔄 Forcer la synchronisation (Vider le cache)"):
    st.cache_data.clear()
    st.rerun()

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
            csv_data = file_content.decoded_content.decode('utf-8-sig')
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

# --- ZONE D'IMPORTATION CORRIGÉE ---
st.markdown("### 📥 Importer un fichier de scores fourni par l'IA")
fichier_importe = st.file_uploader(f"Glissez ici le fichier CSV pour {MOIS_OPTIONS[mois_cle]} {annee_actuelle}", type=["csv"])

if fichier_importe is not None and current_repo:
    if st.button("🚀 Valider l'importation et écraser le tableau actuel", type="secondary"):
        try:
            bytes_data = fichier_importe.read()
            texte_decode = bytes_data.decode("utf-8-sig", errors="ignore")
            df_imp = pd.read_csv(io.StringIO(texte_decode), index_col=0)
            csv_buffer = io.StringIO()
            df_imp.to_csv(csv_buffer)
            contenu_imp = csv_buffer.getvalue()
            
            # CORRECTION DU BUG 422 : Récupérer le SHA frais du fichier s'il existe déjà sur GitHub avant de l'écraser
            sha_actuel = None
            try:
                fichier_existant = current_repo.get_contents(FILE_PATH)
                sha_actuel = fichier_existant.sha
            except Exception:
                pass # Le fichier n'existe pas encore, sha reste à None
            
            if sha_actuel:
                current_repo.update_file(path=FILE_PATH, message="Importation et écrasement sécurisé", content=contenu_imp, sha=sha_actuel)
            else:
                current_repo.create_file(path=FILE_PATH, message="Création par importation sécurisée", content=contenu_imp)
                
            st.success("✅ Fichier importé avec succès ! Rechargement...")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Erreur lors de l'importation : {e}")

st.markdown("---")

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
                    current_repo.update_file(path=FILE_PATH, message="Forçage calendrier", content=csv_buffer.getvalue(), sha=file_sha)
                    st.success("⚡ Calendrier mis à jour !")
                    st.cache_data.clear()
                    st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")

    configuration_colonnes = {joueur: st.column_config.TextColumn(label=joueur, default="") for joueur in df_mois.columns}
    widget_key = f"editor_{mois_cle}_{annee_actuelle}_{len(df_mois)}"
    
    edited_df = st.data_editor(df_mois, column_config=configuration_colonnes, use_container_width=True, key=widget_key)

    if st.button(f"💾 Enregistrer les modifications", type="primary"):
        if current_repo:
            try:
                # Récupérer le SHA le plus récent pour la sauvegarde manuelle également
                try:
                    fichier_existant = current_repo.get_contents(FILE_PATH)
                    sha_maj = fichier_existant.sha
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
                st.success("✅ Enregistré !")
                st.cache_data.clear()
                st.rerun()
            except Exception as error:
                st.error(f"Erreur de sauvegarde : {error}")

    # --- SECTION CALCUL ---
    st.markdown("---")
    if st.button("🔄 Calculer les scores du mois"):
        SCORE_MAP = {'/': 0.5, 'x': 2.0, 'msk': -1.0}
        scores_qualifies = {}
        scores_disqualifies = {}
        tous_les_scores = {}
        total_jours_ouvres = len(edited_df)
        seuil_minimum = total_jours_ouvres / 2
        
        for joueur in edited_df.columns:
            total = 0.0
            valeurs = edited_df[joueur].astype(str).str.strip().str.lower()
            valeurs = valeurs.replace(['msr', 'mok', 'nsk', 'none', 'nan'], 'msk')
            jours_joues = valeurs.apply(lambda x: x in ['/', 'x', 'msk']).sum()
            
            for symbole, points in SCORE_MAP.items():
                if symbole == '/':
                    count = valeurs.str.count(r'/').sum()
                else:
                    count = (valeurs == symbole).sum()
                total += count * points
            
            tous_les_scores[joueur] = (total, jours_joues)
            if jours_joues >= seuil_minimum:
                scores_qualifies[joueur] = (total, jours_joues)
            else:
                scores_disqualifies[joueur] = (total, jours_joues)
        
        st.subheader("📊 Scores Totaux en Cours (Tout le monde)")
        cols = st.columns(len(tous_les_scores))
        for idx, (joueur, (total, jours)) in enumerate(tous_les_scores.items()):
            with cols[idx]:
                statut_text = f"{jours}/{total_jours_ouvres}j"
                if jours < seuil_minimum:
                    st.metric(label=f"{joueur} ⚠️", value=f"{total} pts", delta=f"Incomplet ({statut_text})", delta_color="inverse")
                else:
                    st.metric(label=joueur, value=f"{total} pts", delta=f"Qualifié ({statut_text})", delta_color="normal" if total > 0 else "off")

        st.markdown("---")
        st.subheader(f"🏆 Le Podium Officiel (≥ 50% du mois)")
        classement_trie = sorted(scores_qualifies.items(), key=lambda item: item, reverse=True)
        
        if len(classement_trie) > 0:
            pod1, pod2, pod3 = st.columns(3)
            if len(classement_trie) >= 1:
                p1_name, (p1_score, p1_j) = classement_trie[0]
                pod1.metric(label=f"🥇 1ère Place : {p1_name}", value=f"{p1_score} pts", delta=f"{p1_j} jours")
