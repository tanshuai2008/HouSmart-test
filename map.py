import folium
from folium.features import DivIcon

def get_category_style(category_list):
    """
    Map Geoapify categories to (Emoji, ColorName, Label).
    """
    # Default
    emoji = "📍"
    color = "gray"
    label = "Other"

    cat_str = ",".join(category_list).lower()
    
    mapping = [
        ("catering", "🍔", "orange", "Food/Drink"), 
        ("education", "🎓", "blue", "Education"), 
        ("leisure", "🌳", "green", "Park/Leisure"), 
        ("healthcare", "🏥", "red", "Health"), 
        ("commercial.supermarket", "🛒", "purple", "Grocery"), 
        ("commercial", "🏢", "cadetblue", "Commercial"), 
        ("worship", "⛪", "beige", "Worship"), 
        ("financial", "🏦", "darkblue", "Bank"), 
        ("fuel", "⛽", "darkpurple", "Gas Station"),
    ]

    for key, emo, col, lbl in mapping:
        if key in cat_str:
            return emo, col, lbl
            
    return emoji, color, label

def generate_map(lat, lon, pois):
    """
    Generate a Folium map with Emoji Markers.
    """
    # 1. Base Map (CartoDB Positron for Light Theme)
    m = folium.Map(location=[lat, lon], zoom_start=15, tiles="cartodbpositron")
    
    legend_items = {}

    # 2. Target Property Marker (Star ⭐)
    folium.Marker(
        location=[lat, lon],
        popup="Target Property",
        icon=DivIcon(
            icon_size=(150,36),
            icon_anchor=(15,15),
            html='<div style="font-size: 24pt;">⭐</div>'
        )
    ).add_to(m)
    
    legend_items["Target Property"] = ("⭐", "gold")

    # 3. POI Markers
    for p in pois:
        props = p.get('properties', {})
        cat = props.get('categories', [])
        if isinstance(props.get('category'), str):
            cat = [props.get('category')]
            
        emoji, color, label = get_category_style(cat)
        
        # Add to Legend (unique)
        if label not in legend_items:
            legend_items[label] = (emoji, color)
        
        # Plot
        folium.Marker(
            location=[props.get('lat'), props.get('lon')],
            tooltip=f"{props.get('name', 'Unknown')} ({label})",
            icon=DivIcon(
                icon_size=(30,30),
                icon_anchor=(15,15),
                html=f'<div style="font-size: 16pt;">{emoji}</div>'
            )
        ).add_to(m)
        
    return m, legend_items
