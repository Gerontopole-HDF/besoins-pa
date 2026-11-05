import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Trophées du bien-vieillir", layout="wide")

# ---------------------------------------------------------------- Référentiels
VARIABLES = {
    "Public": "public",
    "Structure (pros)": "structure",
    "Milieu": "milieu",
    "Situation d'aidant (pros)": "situation_aidant",
    "Âge (PA)": "age",
    "Mode de vie (PA)": "mode_de_vie",
    "Logement (PA)": "logement",
    "Situation vis-à-vis d'un proche (PA)": "situation_proche",
}
PROFIL_PAR_PUBLIC = {
    "Professionnels": ["structure", "milieu", "situation_aidant"],
    "Personnes âgées": ["age", "mode_de_vie", "milieu", "logement", "situation_proche"],
}
NOMS_PROFIL = {v: k.split(" (")[0] for k, v in VARIABLES.items()}

DOMAINES = {
    "1": "Sortir, se déplacer, voyager", "2": "Faire ses courses, bien manger",
    "3": "Prendre soin de soi en autonomie", "4": "Se déplacer chez soi en sécurité",
    "5": "Entretenir et adapter son logement", "6": "Démarches, internet, téléphone",
    "7": "Suivre sa santé et ses traitements", "8": "Choisir et coordonner les professionnels",
    "9": "Garder une vie sociale", "10": "Se sentir en sécurité",
    "11": "Accompagner un proche (pros)",
}
NIVEAUX = {  # ordre d'empilement : les difficultés d'abord
    "Des difficultés régulières": "#C8553D",
    "Quelques contraintes": "#F2B880",
    "Aucune difficulté, mais à anticiper": "#9CC5A1",
    "Pas concerné / pas un sujet": "#C9C9C9",
}
TYPOLOGIES = {
    "Technologie": ["Aides techniques", "Maison connectée", "Objets connectés portés",
                    "Détection de chute", "Robots et assistants"],
    "Numérique": ["Applications mobiles", "Plateformes en ligne", "Visio et messagerie",
                  "Tablettes simplifiées", "Aide et formation au numérique"],
    "Santé et prévention": ["Consultations à distance", "Suivi de santé à distance",
                            "Prévention des chutes", "Stimulation de la mémoire",
                            "Coordination des soins"],
    "Habitat": ["Adaptation du logement", "Habitat partagé ou inclusif", "Habitat intermédiaire",
                "Aménagement quartiers", "Rénovation et confort"],
    "Services et mobilité": ["Services à domicile", "Livraison et commerces",
                             "Transports et mobilité partagée",
                             "Accompagnement humain et conciergerie", "Accès simplifié aux aides"],
    "Lien social": ["Entraide entre voisins", "Activités collectives",
                    "Projets intergénérationnels", "Lieux de rencontre", "Bénévolat et engagement"],
}
TYPO_DE = {s: t for t, liste in TYPOLOGIES.items() for s in liste}
NOUVEAUTE = {
    "Enthousiaste (aime essayer)": "#3B8B5E", "Prêt si présenté et accompagné": "#9CC5A1",
    "Attentiste": "#F2B880", "Réticent": "#C8553D",
}
COULEURS_PUBLIC = {"Professionnels": "#B23A48", "Personnes âgées": "#2E64A8"}
PALETTE = ["#2E64A8", "#B23A48", "#3B8B5E", "#E09F3E", "#7A5C99", "#5DA9C9", "#9E9E9E"]


def eclater(df, col):
    """Une ligne par valeur : une double coche « a|b » compte pour a et pour b."""
    df = df.copy()
    df[col] = df[col].fillna("Non renseigné").str.split("|")
    return df.explode(col)


def pct(x):
    return f"{x:.0%}".replace("%", " %")


# ---------------------------------------------------------------- Données
reponses = pd.read_csv("reponses.csv", sep=";", encoding="utf-8-sig")
profils = reponses[["id"] + list(VARIABLES.values())].drop_duplicates("id")

# ---------------------------------------------------------------- Barre latérale
st.sidebar.title("Trophées du bien-vieillir")
PAGES = ["Vue d'ensemble", "Profil des répondants", "1 · Bien vieillir, c'est…",
         "2 · Difficultés par domaine", "3 · Difficulté prioritaire", "4 · Solutions attendues",
         "5 · Ressources pour les aidants", "6 · Face à la nouveauté",
         "7 · Critères d'adoption", "Verbatim"]
page = st.sidebar.radio("Question", PAGES, label_visibility="collapsed")
st.sidebar.divider()
publics = st.sidebar.multiselect("Public", list(COULEURS_PUBLIC), default=list(COULEURS_PUBLIC))
var = "public"  # comparaison toujours entre les deux publics

profils = profils[profils["public"].isin(publics)]
reponses = reponses[reponses["id"].isin(profils["id"])]
if profils.empty:
    st.warning("Sélectionnez au moins un public.")
    st.stop()

groupes = eclater(profils[["id", var]], var).rename(columns={var: "groupe"})
bases = groupes.groupby("groupe")["id"].nunique()
ordre_groupes = [g for g in COULEURS_PUBLIC if g in bases.index] if var == "public" \
    else sorted(bases.index, key=lambda g: (g == "Non renseigné", g))
couleurs = [COULEURS_PUBLIC[g] for g in ordre_groupes] if var == "public" \
    else PALETTE[:len(ordre_groupes)]
COULEUR_GROUPE = alt.Scale(domain=ordre_groupes, range=couleurs)
coul_de = dict(zip(ordre_groupes, couleurs))


def theme_df(theme):
    """Réponses d'un thème, rattachées au groupe de comparaison."""
    return reponses.loc[reponses["theme"] == theme, ["id", "modalite", "valeur"]].merge(groupes, on="id")


def parts(theme, base="tous"):
    """Effectif et part par réponse et par groupe.
    base="tous" : tous les répondants du groupe ; base="repondants" : ceux qui ont répondu."""
    df = theme_df(theme)
    n = df.groupby(["modalite", "groupe"])["id"].nunique().rename("n").reset_index()
    b = bases if base == "tous" else df.groupby("groupe")["id"].nunique()
    n["base"] = n["groupe"].map(b)
    n["part"] = n["n"] / n["base"]
    n["etiquette"] = n["part"].map(pct)
    return n


def barres(df, ordre=None, hauteur_ligne=20):
    """Barres horizontales groupées : une barre par groupe, triées par fréquence globale."""
    if ordre is None:
        ordre = df.groupby("modalite")["part"].mean().sort_values(ascending=False).index.tolist()
    ng = df["groupe"].nunique()
    y = alt.Y("modalite:N", sort=ordre, title=None,
              axis=alt.Axis(labelLimit=320, labelFontSize=13))
    base = alt.Chart(df).encode(
        y=y, yOffset=alt.YOffset("groupe:N", sort=ordre_groupes),
        x=alt.X("part:Q", title=None, scale=alt.Scale(domain=[0, 1]),
                axis=alt.Axis(format="%", tickCount=5, grid=True)),
        color=alt.Color("groupe:N", scale=COULEUR_GROUPE, sort=ordre_groupes,
                        legend=alt.Legend(title=None, orient="top")),
        tooltip=[alt.Tooltip("modalite:N", title="Réponse"), alt.Tooltip("groupe:N", title="Groupe"),
                 alt.Tooltip("n:Q", title="Répondants"), alt.Tooltip("base:Q", title="Sur"),
                 alt.Tooltip("part:Q", title="Part", format=".0%")])
    chart = base.mark_bar(cornerRadiusEnd=3) + \
        base.mark_text(align="left", dx=4, fontSize=11).encode(text="etiquette:N", color=alt.value("#666"))
    return chart.properties(height=len(ordre) * max(ng, 1) * hauteur_ligne + 30)


def legende_html(couleurs_par_libelle):
    """Légende partagée, en HTML, pour qu'aucun libellé ne soit coupé."""
    puces = "".join(
        f"<span style='display:inline-flex;align-items:center;margin:0 18px 6px 0'>"
        f"<span style='width:14px;height:14px;border-radius:3px;background:{c};margin-right:6px'></span>"
        f"{lib}</span>" for lib, c in couleurs_par_libelle.items())
    return f"<div style='font-size:.9rem;margin:4px 0 8px'>{puces}</div>"


def entete(titre, question, note=None):
    st.header(titre)
    st.markdown(f"*« {question} »*")



# ---------------------------------------------------------------- Pages
if page == "Vue d'ensemble":
    st.title("Trophées du bien-vieillir")
    st.markdown("Remontée des besoins en innovation : questionnaire **professionnels et aidants** "
                "(rouge) et questionnaire **personnes âgées** (bleu).")
    c = st.columns(3)
    c[0].metric("Répondants", len(profils))
    for col, pub in zip(c[1:], COULEURS_PUBLIC):
        col.metric(pub, int((profils["public"] == pub).sum()))
    st.divider()
    g, d = st.columns(2)
    with g:
        st.subheader("Bien vieillir, c'est avant tout…")
        top = theme_df("Bien vieillir").groupby("modalite")["id"].nunique().nlargest(3)
        for m, n in top.items():
            st.markdown(f"**{pct(n / len(profils))}** · {m}")
        st.subheader("Difficulté la plus citée en priorité")
        pr = theme_df("Priorité").groupby("modalite")["id"].nunique().nlargest(1)
        for m, n in pr.items():
            st.markdown(f"**{n} répondants** · {DOMAINES[m.split('.')[0]]}")
    with d:
        st.subheader("Solutions les plus attendues")
        top = theme_df("Solutions").groupby("modalite")["id"].nunique().nlargest(3)
        for m, n in top.items():
            st.markdown(f"**{pct(n / len(profils))}** · {m} *({TYPO_DE[m]})*")
        st.subheader("Ce qui compte pour adopter")
        top = theme_df("Adoption").groupby("modalite")["id"].nunique().nlargest(3)
        for m, n in top.items():
            st.markdown(f"**{pct(n / len(profils))}** · {m}")

elif page == "Profil des répondants":
    st.header("Profil des répondants")
    for pub, cols_profil in PROFIL_PAR_PUBLIC.items():
        if pub not in publics:
            continue
        p = profils[profils["public"] == pub]
        st.subheader(f"{pub} (n = {len(p)})")
        cols = st.columns(len(cols_profil))
        for col, v in zip(cols, cols_profil):
            df = eclater(p, v).groupby(v)["id"].nunique().reset_index(name="n")
            ch = alt.Chart(df).mark_bar(color=COULEURS_PUBLIC[pub], cornerRadiusEnd=3).encode(
                y=alt.Y(f"{v}:N", sort="-x", title=None, axis=alt.Axis(labelLimit=160)),
                x=alt.X("n:Q", title=None, axis=alt.Axis(tickMinStep=1)),
                tooltip=[alt.Tooltip(f"{v}:N", title=NOMS_PROFIL[v]), alt.Tooltip("n:Q", title="Répondants")])
            col.markdown(f"**{NOMS_PROFIL[v]}**")
            col.altair_chart(ch.properties(height=len(df) * 36 + 30), use_container_width=True)

elif page == "1 · Bien vieillir, c'est…":
    entete("Bien vieillir, c'est avant tout…",
           "Pour vous / les personnes que vous accompagnez, bien vieillir c'est avant tout…")
    st.altair_chart(barres(parts("Bien vieillir")), use_container_width=True)

elif page == "2 · Difficultés par domaine":
    entete("Difficultés par domaine",
           "Dans chacun de ces domaines, que constatez-vous / où en êtes-vous aujourd'hui ?",
           "Chaque barre se lit à 100 % des réponses données pour le domaine : les difficultés "
           "sont à gauche. Le domaine 11 n'existe que dans le questionnaire des pros.")
    df = theme_df("Domaine")
    df["domaine"] = df["modalite"].str.split(".").str[0].map(DOMAINES)
    ordre_dom = list(DOMAINES.values())
    st.markdown(legende_html(NIVEAUX), unsafe_allow_html=True)
    cols = st.columns(min(len(ordre_groupes), 2))
    for i, g in enumerate(ordre_groupes):
        sous = df[df["groupe"] == g].groupby(["domaine", "valeur"])["id"].nunique().reset_index(name="n")
        if sous.empty:
            continue
        sous["ordre"] = sous["valeur"].map({k: i for i, k in enumerate(NIVEAUX)})
        ch = alt.Chart(sous).mark_bar().encode(
            y=alt.Y("domaine:N", sort=[d for d in ordre_dom if d in set(sous["domaine"])], title=None,
                    axis=alt.Axis(labelLimit=260)),
            x=alt.X("n:Q", stack="normalize", title=None, axis=alt.Axis(format="%")),
            color=alt.Color("valeur:N", title=None, sort=list(NIVEAUX),
                            scale=alt.Scale(domain=list(NIVEAUX), range=list(NIVEAUX.values())),
                            legend=None),
            order=alt.Order("ordre:Q"),
            tooltip=[alt.Tooltip("domaine:N", title="Domaine"), alt.Tooltip("valeur:N", title="Réponse"),
                     alt.Tooltip("n:Q", title="Répondants")])
        with cols[i % 2]:
            st.subheader(f"{g} (n = {bases[g]})")
            st.altair_chart(ch.properties(height=sous["domaine"].nunique() * 30 + 40),
                            use_container_width=True)

elif page == "3 · Difficulté prioritaire":
    entete("Difficulté prioritaire",
           "Pros : la difficulté qui revient le plus souvent (n°) · Personnes âgées : principal "
           "irritant qui n'apparaît pas dans la liste",
           "Les réponses libres des personnes âgées ont été rattachées au domaine le plus proche ; "
           "le texte d'origine est à droite. Part calculée sur tous les répondants du groupe, "
           "y compris ceux qui n'ont pas désigné de priorité.")
    g, d = st.columns([3, 2])
    df = parts("Priorité")
    df["modalite"] = df["modalite"].str.split(".").str[0].map(DOMAINES)
    with g:
        st.altair_chart(barres(df, hauteur_ligne=24), use_container_width=True)
        sans = bases - theme_df("Priorité").groupby("groupe")["id"].nunique().reindex(bases.index, fill_value=0)
    with d:
        st.markdown("**Ce qu'ont écrit les personnes âgées**")
        v = reponses[(reponses["theme"] == "Verbatim") & (reponses["modalite"] == "Irritant hors liste")]
        for _, r in v.iterrows():
            st.info(f"« {r['valeur']} » — {r['id']}")
        if v.empty:
            st.caption("Aucun texte pour la sélection.")

elif page == "4 · Solutions attendues":
    entete("Solutions attendues",
           "Pour cette priorité, quels types de solutions répondraient le mieux aux besoins, "
           "maintenant ou à l'avenir ?")
    df = theme_df("Solutions")
    df["typologie"] = df["modalite"].map(TYPO_DE)

    st.subheader("Par typologie")
    t = df.groupby(["typologie", "groupe"])["id"].nunique().rename("n").reset_index()
    t["base"] = t["groupe"].map(bases)
    t["part"] = t["n"] / t["base"]
    t["etiquette"] = t["part"].map(pct)
    t = t.rename(columns={"typologie": "modalite"})
    st.altair_chart(barres(t, ordre=list(TYPOLOGIES), hauteur_ligne=22), use_container_width=True)

    st.subheader("Dans le tableau du questionnaire")
    p = parts("Solutions").set_index(["modalite", "groupe"])
    onglets = st.tabs([f"{g} (n = {bases[g]})" for g in ordre_groupes])
    for onglet, g in zip(onglets, ordre_groupes):
        h = coul_de[g].lstrip("#")
        rgb = ", ".join(str(int(h[i:i + 2], 16)) for i in (0, 2, 4))
        lignes = []
        for rang in range(5):
            cellules = []
            for typo, liste in TYPOLOGIES.items():
                s = liste[rang]
                part = p["part"].get((s, g), 0.0)
                n = int(p["n"].get((s, g), 0))
                fond = f"rgba({rgb}, {0.06 + 0.9 * part:.2f})"
                texte = "#fff" if part >= 0.6 else "inherit"
                cellules.append(f'<td style="background:{fond};color:{texte}" title="{n} sur {bases[g]}">'
                                f'{s}<br><b>{pct(part)}</b></td>')
            lignes.append("<tr>" + "".join(cellules) + "</tr>")
        entetes = "".join(f"<th style='background:{coul_de[g]}'>{t}</th>" for t in TYPOLOGIES)
        style = (
            ".grille{border-collapse:separate;border-spacing:4px;width:100%;table-layout:fixed;font-size:.85rem}"
            ".grille th{color:#fff;padding:6px;border-radius:4px}"
            ".grille td{padding:8px;border-radius:4px;vertical-align:top;height:70px}"
            ".grille .famille th{background:transparent;color:inherit;font-weight:500;font-size:.75rem}")
        html = (f"<style>{style}</style><div style='overflow-x:auto'><table class='grille'>"
                "<tr class='famille'><th colspan='4'>Équipements et outils</th>"
                "<th colspan='2'>Services et façons de s'organiser</th></tr>"
                f"<tr>{entetes}</tr>{''.join(lignes)}</table></div>")
        onglet.markdown(html, unsafe_allow_html=True)

elif page == "5 · Ressources pour les aidants":
    entete("Ressources pour les aidants",
           "Pros : quelles ressources manquent le plus souvent aux aidants ? · Personnes âgées : "
           "si vous accompagnez un proche, quelles ressources vous seraient utiles ?",
           "Question conditionnelle chez les personnes âgées : la part est calculée sur ceux qui "
           "ont répondu. « Non concerné(e) » n'existe que chez les pros (et un ajout manuscrit).")
    df = parts("Aidants", base="repondants")
    ordre = df[df["modalite"] != "Non concerné(e)"].groupby("modalite")["part"].mean() \
        .sort_values(ascending=False).index.tolist() + ["Non concerné(e)"]
    st.altair_chart(barres(df, ordre=[o for o in ordre if o in set(df["modalite"])]),
                    use_container_width=True)
    rep = theme_df("Aidants").groupby("groupe")["id"].nunique()

elif page == "6 · Face à la nouveauté":
    entete("Face à la nouveauté",
           "Face à une nouveauté, vous êtes / les personnes accompagnées sont plutôt…",
           "Une seule réponse attendue : chaque barre fait 100 % des réponses du groupe, "
           "de la plus ouverte (à gauche) à la plus réticente.")
    df = theme_df("Nouveauté").groupby(["groupe", "modalite"])["id"].nunique().reset_index(name="n")
    df["ordre"] = df["modalite"].map({k: i for i, k in enumerate(NOUVEAUTE)})
    df = df.sort_values(["groupe", "ordre"])
    df["part"] = df["n"] / df.groupby("groupe")["n"].transform("sum")
    df["fin"] = df.groupby("groupe")["part"].cumsum()
    df["debut"] = df["fin"] - df["part"]
    df["milieu"] = (df["debut"] + df["fin"]) / 2
    df["etiquette"] = df["part"].map(pct)
    st.markdown(legende_html(NOUVEAUTE), unsafe_allow_html=True)
    y = alt.Y("groupe:N", sort=ordre_groupes, title=None,
              axis=alt.Axis(labelLimit=220, labelFontSize=13))
    ch = alt.Chart(df).mark_bar(cornerRadius=2).encode(
        y=y, x=alt.X("debut:Q", title=None, scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%")),
        x2="fin:Q",
        color=alt.Color("modalite:N", scale=alt.Scale(domain=list(NOUVEAUTE), range=list(NOUVEAUTE.values())),
                        legend=None),
        tooltip=[alt.Tooltip("groupe:N", title="Groupe"), alt.Tooltip("modalite:N", title="Réponse"),
                 alt.Tooltip("n:Q", title="Répondants"), alt.Tooltip("part:Q", title="Part", format=".0%")])
    txt = alt.Chart(df).mark_text(fontSize=12, fontWeight="bold").encode(
        y=y, x="milieu:Q", text="etiquette:N",
        color=alt.condition("datum.ordre == 0 || datum.ordre == 3", alt.value("white"), alt.value("#222")))
    st.altair_chart((ch + txt).properties(height=len(ordre_groupes) * 55 + 30), use_container_width=True)

elif page == "7 · Critères d'adoption":
    entete("Critères d'adoption",
           "Pour adopter une nouveauté, ce qui compte le plus…")
    st.altair_chart(barres(parts("Adoption")), use_container_width=True)

elif page == "Verbatim":
    st.header("Verbatim")
    verb = reponses[(reponses["theme"] == "Verbatim") & (reponses["modalite"] != "Annotation")]
    for question, bloc in verb.groupby("modalite", sort=False):
        st.subheader(question)
        cols = st.columns(2)
        for i, (_, r) in enumerate(bloc.iterrows()):
            details = [str(r[c]).replace("|", " / ") for c in PROFIL_PAR_PUBLIC[r["public"]] if pd.notna(r[c])]
            with cols[i % 2].container(border=True):
                st.markdown(f"« {r['valeur']} »")
                st.caption(f"{r['id']} · {r['public']} · " + ", ".join(details))
