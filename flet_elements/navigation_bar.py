from flet import NavigationBar, NavigationDestination, NavigationBarLabelBehavior
from .tabs import tabs_config

navbar = NavigationBar(
    destinations=[
        NavigationDestination(icon=tabs_config[0]['icon'], label=tabs_config[0]['title']),
        NavigationDestination(icon=tabs_config[1]['icon'], label=tabs_config[1]['title']),
        NavigationDestination(icon=tabs_config[2]['icon'], label=tabs_config[2]['title']),
        NavigationDestination(icon=tabs_config[3]['icon'], label=tabs_config[3]['title']),
    ],
    adaptive=True,
    # label_behavior=NavigationBarLabelBehavior.ONLY_SHOW_SELECTED
)
