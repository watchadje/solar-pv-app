"""
Application de Dimensionnement Solaire Photovoltaïque
Version Mobile Optimisée
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests

st.set_page_config(
    page_title="☀️ Solar PV",
    page_icon="☀️",
    layout="wide"
)

# Ajout du CSS pour mobile
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    h1 {
        font-size: 1.8rem !important;
    }
    h2 {
        font-size: 1.4rem !important;
    }
</style>
""", unsafe_allow_html=True)

APPAREILS_DEFAULT = {
    "Chauffe-eau": {"puissance_w": 2000, "heures_jour": 3},
    "Réfrigérateur": {"puissance_w": 150, "heures_jour": 24},
    "Climatisation": {"puissance_w": 2500, "heures_jour": 4},
    "Chauffage électrique": {"puissance_w": 3000, "heures_jour": 6},
    "Four": {"puissance_w": 2500, "heures_jour": 1},
    "Lave-linge": {"puissance_w": 2000, "heures_jour": 0.5},
    "Télévision": {"puissance_w": 100, "heures_jour": 5},
    "Éclairage": {"puissance_w": 300, "heures_jour": 5},
    "Véhicule électrique": {"puissance_w": 3000, "heures_jour": 2}
}

@st.cache_data(ttl=3600)
def get_pvgis_data(lat, lon, pente, azimut, puissance_kwc):
    try:
        url = "https://re.jrc.ec.europa.eu/api/v5_2/PVcalc"
        params = {
            "lat": lat, "lon": lon, "peakpower": puissance_kwc,
            "loss": 14, "angle": pente, "aspect": azimut,
            "outputformat": "json"
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        monthly_data = data['outputs']['monthly']['fixed']
        df = pd.DataFrame(monthly_data)
        df['mois'] = ['Jan', 'Fev', 'Mar', 'Avr', 'Mai', 'Jun', 
                      'Jul', 'Aou', 'Sep', 'Oct', 'Nov', 'Dec']
        return df
    except:
        return generate_fallback_solar_data(lat, puissance_kwc)

def generate_fallback_solar_data(lat, puissance_kwc):
    base_irradiation = [2.0, 2.8, 4.0, 5.2, 6.0, 6.5, 6.8, 6.0, 4.8, 3.2, 2.2, 1.8]
    lat_factor = 1 + (45 - abs(lat)) / 100
    monthly_prod = []
    mois_noms = ['Jan', 'Fev', 'Mar', 'Avr', 'Mai', 'Jun', 
                 'Jul', 'Aou', 'Sep', 'Oct', 'Nov', 'Dec']
    jours_mois = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
    for i, irr in enumerate(base_irradiation):
        prod = irr * lat_factor * puissance_kwc * 0.75 * jours_mois[i]
        monthly_prod.append(prod)
    
    return pd.DataFrame({
        'month': range(1, 13),
        'E_m': monthly_prod,
        'mois': mois_noms
    })

def calculer_consommation_appareils(appareils_selectionnes):
    conso_totale = 0
    for appareil, data in appareils_selectionnes.items():
        if data['quantite'] > 0:
            conso_annuelle = (data['puissance_w'] * data['heures_jour'] * 365 * data['quantite']) / 1000
            conso_totale += conso_annuelle
    return conso_totale

def calculer_scenarios(conso_annuelle, lat, lon, pente, azimut):
    scenarios = {
        "Budget": max(3, round(conso_annuelle / 1000 * 0.4, 1)),
        "Confort": max(5, round(conso_annuelle / 1000 * 0.7, 1)),
        "Producteur": max(8, round(conso_annuelle / 1000 * 1.2, 1))
    }
    resultats = {}
    for nom, puissance in scenarios.items():
        df_prod = get_pvgis_data(lat, lon, pente, azimut, puissance)
        production_annuelle = df_prod['E_m'].sum()
        resultats[nom] = {
            'puissance_kwc': puissance,
            'production_annuelle': production_annuelle,
            'df_mensuel': df_prod
        }
    return resultats

def calculer_rentabilite(scenario_data, conso_annuelle, prix_kwc, prix_achat_kwh, 
                        prix_vente_kwh, taux_autoconso):
    puissance = scenario_data['puissance_kwc']
    production = scenario_data['production_annuelle']
    
    cout_installation = puissance * prix_kwc * 1000
    kwh_autoconso = production * taux_autoconso
    kwh_autoconso_effectif = min(kwh_autoconso, conso_annuelle)
    kwh_surplus = production - kwh_autoconso_effectif
    
    economie_facture = kwh_autoconso_effectif * prix_achat_kwh
    revenu_vente = kwh_surplus * prix_vente_kwh
    gain_annuel = economie_facture + revenu_vente
    
    roi_annees = cout_installation / gain_annuel if gain_annuel > 0 else 999
    gain_20ans = (gain_annuel * 20) - cout_installation
    
    return {
        'cout_installation': cout_installation,
        'production_annuelle': production,
        'kwh_autoconso': kwh_autoconso_effectif,
        'kwh_surplus': kwh_surplus,
        'economie_facture': economie_facture,
        'revenu_vente': revenu_vente,
        'gain_annuel': gain_annuel,
        'roi_annees': roi_annees,
        'gain_20ans': gain_20ans
    }

def main():
    st.title("☀️ Solar PV")
    st.caption("Dimensionnement installation solaire")
    
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        st.subheader("📍 Localisation")
        lat = st.number_input("Latitude", value=48.8566, format="%.4f")
        lon = st.number_input("Longitude", value=2.3522, format="%.4f")
        
        st.subheader("🏠 Toiture")
        pente = st.slider("Pente (°)", 0, 90, 30)
        azimut = st.slider("Orientation", -180, 180, 0, help="0°=Sud")
        
        st.subheader("⚡ Consommation")
        mode_conso = st.radio("Mode", ["Consommation annuelle", "Appareils"])
        
        if mode_conso == "Consommation annuelle":
            conso_annuelle = st.number_input("Consommation (kWh/an)", value=5000, min_value=1000, max_value=50000, step=500)
        else:
            appareils_user = {}
            for appareil, specs in APPAREILS_DEFAULT.items():
                qte = st.number_input(f"{appareil}", value=0, min_value=0, max_value=5, key=f"qte_{appareil}")
                if qte > 0:
                    appareils_user[appareil] = {
                        'quantite': qte,
                        'puissance_w': specs['puissance_w'],
                        'heures_jour': specs['heures_jour']
                    }
            conso_annuelle = calculer_consommation_appareils(appareils_user)
            st.metric("Total estimé", f"{int(conso_annuelle)} kWh/an")
        
        st.subheader("💰 Paramètres")
        prix_kwc = st.number_input("Prix (€/kWc)", value=2300, min_value=1000, max_value=5000, step=100)
        prix_achat_kwh = st.number_input("Achat (€/kWh)", value=0.20, min_value=0.10, max_value=0.50, step=0.01)
        prix_vente_kwh = st.number_input("Vente (€/kWh)", value=0.13, min_value=0.05, max_value=0.30, step=0.01)
        taux_autoconso = st.slider("Autoconso (%)", 20, 80, 40) / 100
    
    with st.spinner("🔄 Calcul..."):
        scenarios_data = calculer_scenarios(conso_annuelle, lat, lon, pente, azimut)
    
    st.header("🎯 Scénarios")
    
    scenarios_rentabilite = {}
    
    for nom, data in scenarios_data.items():
        with st.expander(f"🔹 {nom} - {data['puissance_kwc']} kWc", expanded=(nom=="Confort")):
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Production", f"{int(data['production_annuelle'])} kWh/an")
            
            rent = calculer_rentabilite(data, conso_annuelle, prix_kwc, 
                                       prix_achat_kwh, prix_vente_kwh, taux_autoconso)
            scenarios_rentabilite[nom] = rent
            
            with col2:
                st.metric("ROI", f"{rent['roi_annees']:.1f} ans")
            
            col3, col4 = st.columns(2)
            with col3:
                st.metric("Coût", f"{int(rent['cout_installation']):,}€".replace(',', ' '))
            with col4:
                st.metric("Gain 20 ans", f"{int(rent['gain_20ans']):,}€".replace(',', ' '))
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=data['df_mensuel']['mois'],
                y=data['df_mensuel']['E_m'],
                marker_color='orange'
            ))
            fig.update_layout(
                title="Production mensuelle",
                height=250,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.header("💶 Comparaison")
    
    df_comparaison = pd.DataFrame({
        'Scénario': list(scenarios_rentabilite.keys()),
        'Coût (€)': [int(r['cout_installation']) for r in scenarios_rentabilite.values()],
        'ROI (ans)': [f"{r['roi_annees']:.1f}" for r in scenarios_rentabilite.values()],
        'Gain 20 ans (€)': [int(r['gain_20ans']) for r in scenarios_rentabilite.values()]
    })
    
    st.dataframe(df_comparaison, use_container_width=True, hide_index=True)
    
    gains_20ans = {nom: rent['gain_20ans'] for nom, rent in scenarios_rentabilite.items()}
    meilleur_scenario = max(gains_20ans, key=gains_20ans.get)
    
    st.success(f"✅ Scénario recommandé : **{meilleur_scenario}**")
    
    st.caption("📡 Données PVGIS (EU Science Hub)")
    st.caption("⚠️ Estimations - Consultez un installateur RGE")

if __name__ == "__main__":
    main()
