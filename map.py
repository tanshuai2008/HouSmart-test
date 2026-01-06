import folium
from folium.features import DivIcon

# CSS for the pulsing effect and markers
MAP_CSS = """
<style>
@keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(26, 115, 232, 0.7); }
    70% { box-shadow: 0 0 0 15px rgba(26, 115, 232, 0); }
    100% { box-shadow: 0 0 0 0 rgba(26, 115, 232, 0); }
}
.target-pin {
    width: 20px;
    height: 20px;
    background-color: #1A73E8;
    border-radius: 50%;
    border: 3px solid white;
    box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    animation: pulse 2s infinite;
}
.amenity-pin {
    width: 24px;
    height: 24px;
    background-color: white;
    border-radius: 50%;
    border: 2px solid #555; /* Default fallback */
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
}
</style>
"""

def get_category_style(category_list):
    """
    Map Geoapify categories to (Emoji, BorderColor, Label).
    """
    # Default
    emoji = "📍"
    color = "#999999"
    label = "Other"

    cat_str = ",".join(category_list).lower()
    
    # Mapping: (Keyword, Emoji, HexColor, Label)
    mapping = [
        ("catering", "🍔", "#FF9800", "Food/Drink"), 
        ("education", "🎓", "#1A73E8", "Education"), 
        ("leisure", "🌳", "#4CAF50", "Park/Leisure"), 
        ("healthcare", "🏥", "#F44336", "Health"), 
        ("commercial.supermarket", "🛒", "#9C27B0", "Grocery"), 
        ("shopping", "🛍️", "#9C27B0", "Shopping"),
        ("commercial", "🏢", "#607D8B", "Commercial"), 
        ("worship", "⛪", "#795548", "Worship"), 
        ("financial", "🏦", "#3F51B5", "Bank"), 
        ("fuel", "⛽", "#212121", "Gas Station"),
        ("public_transport", "🚆", "#009688", "Transit"),
    ]

    for key, emo, col, lbl in mapping:
        if key in cat_str:
            return emo, col, lbl
            
    return emoji, color, label

def generate_map(lat, lon, pois):
    """
    Generate a Folium map with Custom Styled Markers.
    """
    # 1. Base Map
    m = folium.Map(location=[lat, lon], zoom_start=15, tiles="cartodbpositron")
    
    # Inject CSS into the map
    m.get_root().html.add_child(folium.Element(MAP_CSS))
    
    legend_items = {}

    # 2. Target Property Marker (Pulsing Blue Pin)
    folium.Marker(
        location=[lat, lon],
        popup="Target Property",
        icon=DivIcon(
            icon_size=(30,30),
            icon_anchor=(15,15),
            html='<div class="target-pin"></div>'
        )
    ).add_to(m)
    
    legend_items["Target Property"] = ("🏠", "#1A73E8")

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
                icon_size=(24,24),
                icon_anchor=(12,12),
                html=f'<div class="amenity-pin" style="border-color: {color};">{emoji}</div>'
            )
        ).add_to(m)
        
    return m, legend_items
