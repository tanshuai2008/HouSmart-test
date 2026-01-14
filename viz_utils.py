
import plotly.express as px
import pandas as pd

def generate_rent_table(rent_data):
    """
    Generates an HTML table for rent comparables.
    """
    if not rent_data or "comparables" not in rent_data:
        return "<p>No comparable rental data available.</p>"

    comps = rent_data["comparables"]
    if not comps:
        return "<p>No comparable rental data available.</p>"

    # CSS Style Block (Inline for Email)
    style_block = """
    <style>
        .comp-table{width:100%;border-collapse:collapse;font-family:'Inter',sans-serif;font-size:0.9rem;color:#202124;}
        .comp-table th{text-align:left;text-transform:uppercase;font-size:0.75rem;color:#5F6368;border-bottom:1px solid #E0E0E0;padding:10px 5px;font-weight:600;}
        .comp-table td{padding:12px 5px;border-bottom:1px solid #F1F3F4;vertical-align:top;}
        .comp-num{display:inline-block;width:24px;height:24px;background-color:#5F6368;color:white;border-radius:50%;text-align:center;line-height:24px;font-size:0.8rem;font-weight:bold;}
        .addr-main{font-weight:600;font-size:0.95rem;}
        .addr-sub{color:#5F6368;font-size:0.85rem;}
        .price-main{font-weight:700;color:#333;}
        .price-sub{color:#5F6368;font-size:0.85rem;}
    </style>
    """

    rows_html = ""
    # LIMIT TO TOP 5
    for i, c in enumerate(comps[:5]):
        price_fmt = f"${c.get('price', 0):,}"
        ppsf_fmt = f"${c.get('ppsf', 0):.2f} /ft²" if c.get('ppsf') else "-"
        dist_fmt = f"{c.get('distance', 0):.2f} mi"
        beds = c.get('bedrooms', '-')
        baths = c.get('bathrooms', '-')
        sqft = f"{c.get('squareFootage', 0):,}"
        p_type = c.get('propertyType', 'Single Family')
        y_built = f"Built {c.get('yearBuilt')}" if c.get('yearBuilt') else ""
        
        addr1 = c.get('address_line1', 'Unknown')
        addr2 = c.get('address_line2', '')
        
        rows_html += f"""
        <tr>
            <td><span class="comp-num">{i+1}</span></td>
            <td><div class="addr-main">{addr1}</div><div class="addr-sub">{addr2}</div></td>
            <td><div class="price-main">{price_fmt}</div><div class="price-sub">{ppsf_fmt}</div></td>
            <td style="color:#5F6368;">{dist_fmt}</td>
            <td style="color:#3C4043;">{beds}</td>
            <td style="color:#3C4043;">{baths}</td>
            <td style="color:#3C4043;">{sqft}</td>
            <td><div class="type-main">{p_type}</div><div class="type-sub">{y_built}</div></td>
        </tr>
        """

    full_table = f"""
    {style_block}
    <div style="overflow-x:auto;">
    <table class="comp-table">
        <thead>
            <tr>
                <th style="width:5%;"></th>
                <th style="width:30%;">ADDRESS</th>
                <th style="width:20%;">LISTED RENT</th>
                <th style="width:10%;">DISTANCE</th>
                <th style="width:5%;">BEDS</th>
                <th style="width:5%;">BATHS</th>
                <th style="width:10%;">SQ.FT.</th>
                <th style="width:15%;">TYPE</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    </div>
    """
    return full_table

def generate_census_charts(census_data, address_input=""):
    """
    Generates Plotly figures for Income, Age, Race, and Education.
    Returns a dictionary of figures.
    """
    if not census_data or "metrics" not in census_data:
        return {}

    c_data = census_data["metrics"]
    bench = census_data.get("benchmarks", {})
    
    # helper
    def safe_parse(v):
        if isinstance(v, dict): 
            v = v.get('local', 0)
        if isinstance(v, (int, float)): return float(v)
        if isinstance(v, str):
            clean = v.replace('$', '').replace(',', '').replace('%', '')
            try: return float(clean)
            except: return 0.0
        return 0.0

    # INCOME
    # Local
    vp_inc_low = safe_parse(c_data.get("income_below_50k", 0))
    vp_inc_mid = safe_parse(c_data.get("income_50k_150k", 0)) 
    vp_inc_high = safe_parse(c_data.get("income_above_150k", 0))
    
    # Benchmarks
    s_inc = bench.get("state_income_dist", [0,0,0])
    u_inc = bench.get("us_income_dist", [0,0,0])

    inc_title = f"Household Income (Median: ${c_data.get('median_income_str', 'N/A')})"

    df_income = pd.DataFrame({
        "Range": ["<50k", "<50k", "<50k", "50k-150k", "50k-150k", "50k-150k", ">150k", ">150k", ">150k"],
        "Scope": ["Local", "State", "National"] * 3,
        "Value": [
            vp_inc_low, s_inc[0], u_inc[0],
            vp_inc_mid, s_inc[1], u_inc[1],
            vp_inc_high, s_inc[2], u_inc[2]
        ]
    })

    # AGE
    # Local
    vp_u18 = safe_parse(c_data.get("age_under_18", 0))
    vp_18_24 = safe_parse(c_data.get("age_18_24", 0))
    vp_25_44 = safe_parse(c_data.get("age_25_44", 0))
    vp_45_64 = safe_parse(c_data.get("age_45_64", 0))
    vp_65_plus = safe_parse(c_data.get("age_65_plus", 0))
    # Bench
    s_age = bench.get("state_age_dist", [0,0,0,0,0])
    u_age = bench.get("us_age_dist", [0,0,0,0,0])

    age_title = f"Age Distribution (Median: {c_data.get('median_age', 'N/A')})"

    df_age = pd.DataFrame({
        "Range": ["<18", "<18", "<18", "18-24", "18-24", "18-24", "25-44", "25-44", "25-44", 
                  "45-64", "45-64", "45-64", "65+", "65+", "65+"],
        "Scope": ["Local", "State", "National"] * 5,
        "Value": [
            vp_u18, s_age[0], u_age[0],
            vp_18_24, s_age[1], u_age[1],
            vp_25_44, s_age[2], u_age[2],
            vp_45_64, s_age[3], u_age[3],
            vp_65_plus, s_age[4], u_age[4]
        ]
    })

    # RACE
    # Local
    vp_white = safe_parse(c_data.get("race_white", 0))
    vp_black = safe_parse(c_data.get("race_black", 0))
    vp_asian = safe_parse(c_data.get("race_asian", 0))
    vp_hisp = safe_parse(c_data.get("race_hispanic", 0))
    vp_oth = safe_parse(c_data.get("race_other", 0))
    # Bench
    s_race = bench.get("state_race_dist", [0,0,0,0,0])
    u_race = bench.get("us_race_dist", [0,0,0,0,0])

    df_race = pd.DataFrame({
        "Group": ["White", "White", "White", "Hispanic", "Hispanic", "Hispanic", "Black", "Black", "Black", "Asian", "Asian", "Asian", "Other", "Other", "Other"],
        "Scope": ["Local", "State", "National"] * 5,
        "Value": [
            vp_white, s_race[0], u_race[0],
            vp_hisp, s_race[1], u_race[1],
            vp_black, s_race[2], u_race[2],
            vp_asian, s_race[3], u_race[3],
            vp_oth, s_race[4], u_race[4]
        ]
    })

    # EDUCATION
    # Local
    vp_hs = safe_parse(c_data.get("edu_high_school", 0))
    vp_bach = safe_parse(c_data.get("edu_bachelor", 0))
    vp_grad = safe_parse(c_data.get("edu_graduate", 0))
    # Bench
    s_hs = bench.get("state_edu_dist", [0.0, 0.0])[0] if len(bench.get("state_edu_dist", [])) > 0 else 0
    s_bach = 0 # Not strictly mapped in original app, simplifying
    s_adv = 0 
    # Actually original app had hardcoded or partial mapping. Let's try to do best effort matching
    # Original: s_hs, s_bach, s_adv = bench.get("state_edu_dist", [0,0,0]) ... wait the original code used s_hs, s_bach, s_adv from `s_edu`
    s_edu = bench.get("state_edu_dist", [0,0,0])
    u_edu = bench.get("us_edu_dist", [0,0,0])
    
    s_hs, s_bach, s_adv = (s_edu + [0]*(3-len(s_edu)))[:3]
    u_hs, u_bach, u_adv = (u_edu + [0]*(3-len(u_edu)))[:3]

    df_edu = pd.DataFrame({
        "Level": ["HighSchool", "HighSchool", "HighSchool", "Bachelor", "Bachelor", "Bachelor", "Adv-Degree", "Adv-Degree", "Adv-Degree"],
        "Scope": ["Local", "State", "National"] * 3,
        "Value": [
            vp_hs, s_hs, u_hs, 
            vp_bach, s_bach, u_bach, 
            vp_grad, s_adv, u_adv
        ]
    })

    # State Label Logic
    state_label = "State"
    if bench and "state_name" in bench:
         state_label = bench["state_name"]
    else:
        import re
        match = re.search(r'\b([A-Z]{2})\b\s+\d{5}', address_input)
        if match:
             state_label = f"{match.group(1)} State"

    # Update Dataframes
    for df in [df_income, df_age, df_race, df_edu]:
        df["Scope"] = df["Scope"].replace("State", state_label)

    # Layout Helper
    def update_chart_layout(fig):
        fig.update_layout(
            margin=dict(l=0,r=0,t=40,b=0), 
            legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="right", x=1),
            title_font=dict(size=13),
            xaxis_title=None,
            template="plotly_white" # Ensure white background for email images
        )
        return fig

    # Colors
    color_map = {"Local": "#1A73E8", state_label: "#9AA0A6", "National": "#DADCE0"}
    color_map_age = {"Local": "#34A853", state_label: "#9AA0A6", "National": "#DADCE0"}
    color_map_race = {"Local": "#FBBC04", state_label: "#9AA0A6", "National": "#DADCE0"}
    color_map_edu = {"Local": "#EA4335", state_label: "#9AA0A6", "National": "#DADCE0"}

    # Generate Figures
    # Explicit Category Orders to prevent alphabetical sorting
    order_inc = ["<50k", "50k-150k", ">150k"]
    order_age = ["<18", "18-24", "25-44", "45-64", "65+"]
    order_race = ["White", "Hispanic", "Black", "Asian", "Other"]
    order_edu = ["HighSchool", "Bachelor", "Adv-Degree"]

    fig_inc = px.bar(
        df_income, x="Range", y="Value", color="Scope", barmode="group", 
        title=inc_title, height=250, text_auto='.1f',
        color_discrete_map=color_map, labels={"Value": "%"},
        category_orders={"Range": order_inc}
    )
    update_chart_layout(fig_inc)

    fig_age = px.bar(
        df_age, x="Range", y="Value", color="Scope", barmode="group", 
        title=age_title, height=250, text_auto='.1f',
        color_discrete_map=color_map_age, labels={"Value": "%"},
        category_orders={"Range": order_age}
    )
    update_chart_layout(fig_age)

    fig_race = px.bar(
        df_race, x="Group", y="Value", color="Scope", barmode="group", 
        title="Race", height=250, text_auto='.1f',
        color_discrete_map=color_map_race, labels={"Value": "%"},
        category_orders={"Group": order_race}
    )
    update_chart_layout(fig_race)

    fig_edu = px.bar(
        df_edu, x="Level", y="Value", color="Scope", barmode="group", 
        title="Education", height=250, text_auto='.1f',
        color_discrete_map=color_map_edu, labels={"Value": "%"},
        category_orders={"Level": order_edu}
    )
    update_chart_layout(fig_edu)

    return {
        "income": fig_inc,
        "age": fig_age,
        "race": fig_race,
        "education": fig_edu
    }
