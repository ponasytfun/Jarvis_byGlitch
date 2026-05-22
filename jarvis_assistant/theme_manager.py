from __future__ import annotations

from PySide6.QtGui import QFontDatabase


SURFACE_THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "name": "dark",
        "windowBackground": "#060B14",
        "windowGradientStart": "#09101B",
        "windowGradientEnd": "#03060D",
        "cardBackground": "#0E1623D8",
        "cardBackgroundStrong": "#111B2AF0",
        "cardBorder": "#5F7CA61E",
        "cardShadow": "#01040A",
        "panelGlow": "#D8F3FF12",
        "textPrimary": "#F2F7FF",
        "textSecondary": "#B0C1D8",
        "textMuted": "#74839A",
        "buttonPrimaryFill": "#172638",
        "buttonSecondaryFill": "#101927",
        "buttonQuietFill": "#0C1420",
        "buttonPrimaryText": "#F2F7FF",
        "danger": "#E96B78",
        "success": "#7DF2C7",
        "line": "#162637",
        "glass": "#D6EBFF12",
        "heroSurface": "#09111DBA",
        "heroLine": "#2A3F5926",
    },
    "light": {
        "name": "light",
        "windowBackground": "#EEF3F8",
        "windowGradientStart": "#FCFDFF",
        "windowGradientEnd": "#E3EAF2",
        "cardBackground": "#FFFFFFD9",
        "cardBackgroundStrong": "#FFFFFFF0",
        "cardBorder": "#9CB2C78A",
        "cardShadow": "#C8D4E0",
        "panelGlow": "#6AA7C814",
        "textPrimary": "#182738",
        "textSecondary": "#4A6177",
        "textMuted": "#728495",
        "buttonPrimaryFill": "#DCE9F5",
        "buttonSecondaryFill": "#EDF2F7",
        "buttonQuietFill": "#F7FAFD",
        "buttonPrimaryText": "#16354F",
        "danger": "#C64556",
        "success": "#2D9C69",
        "line": "#CFDAE5",
        "glass": "#FFFFFFC4",
        "heroSurface": "#FFFFFFCC",
        "heroLine": "#B9C8D73D",
    },
}


ATOM_THEMES: dict[str, dict[str, str]] = {
    "nuclear_waste": {
        "name": "nuclear_waste",
        "displayName": "Nuclear Waste",
        "accent": "#A8FF4D",
        "accentStrong": "#67F83A",
        "accentSoftDark": "#244E1D",
        "accentSoftLight": "#DDF6C5",
        "accentSecondary": "#D8FF7A",
        "accentSecondarySoftDark": "#3D5723",
        "accentSecondarySoftLight": "#EEF8D7",
        "atomOrbit": "#88FF44",
        "atomGlow": "#B4FF72",
        "atomGlowStrong": "#53FF2E",
        "electron": "#EDFFC6",
        "electronAlt": "#BFFF6E",
        "proton": "#82FF34",
        "neutron": "#D8FF93",
        "listeningGlow": "#C6FF67",
        "thinkingGlow": "#92FF35",
        "speakingGlow": "#E7FF9C",
        "executingGlow": "#7DFF43",
        "idleGlow": "#345C2B",
    },
    "blood_red": {
        "name": "blood_red",
        "displayName": "Blood Red",
        "accent": "#E24A5D",
        "accentStrong": "#B61D36",
        "accentSoftDark": "#3D1520",
        "accentSoftLight": "#F2D6DB",
        "accentSecondary": "#8A1734",
        "accentSecondarySoftDark": "#471321",
        "accentSecondarySoftLight": "#E8CAD2",
        "atomOrbit": "#A92B40",
        "atomGlow": "#F06A75",
        "atomGlowStrong": "#B91733",
        "electron": "#FFD7DB",
        "electronAlt": "#FF8998",
        "proton": "#D91D38",
        "neutron": "#F7A2AE",
        "listeningGlow": "#F26B74",
        "thinkingGlow": "#E02A42",
        "speakingGlow": "#FFA2AF",
        "executingGlow": "#C51B35",
        "idleGlow": "#5A2631",
    },
    "cold_blue": {
        "name": "cold_blue",
        "displayName": "Cold Blue",
        "accent": "#72DFFF",
        "accentStrong": "#2DB4FF",
        "accentSoftDark": "#163B58",
        "accentSoftLight": "#D8ECFB",
        "accentSecondary": "#7768FF",
        "accentSecondarySoftDark": "#2D2F67",
        "accentSecondarySoftLight": "#E0E1FB",
        "atomOrbit": "#5FD4FF",
        "atomGlow": "#96E8FF",
        "atomGlowStrong": "#58BBFF",
        "electron": "#F3FBFF",
        "electronAlt": "#B98CFF",
        "proton": "#53D4FF",
        "neutron": "#9FBCFF",
        "listeningGlow": "#61E6FF",
        "thinkingGlow": "#7392FF",
        "speakingGlow": "#B49CFF",
        "executingGlow": "#7D8EFF",
        "idleGlow": "#32516E",
    },
}


def normalize_surface_theme(theme_name: str) -> str:
    name = (theme_name or "dark").strip().lower()
    return name if name in SURFACE_THEMES else "dark"


def normalize_theme(theme_name: str) -> str:
    return normalize_surface_theme(theme_name)


def normalize_atom_theme(theme_name: str) -> str:
    name = (theme_name or "cold_blue").strip().lower()
    return name if name in ATOM_THEMES else "cold_blue"


def get_theme_palette(surface_theme: str, atom_theme: str | None = None) -> dict[str, str]:
    surface_name = normalize_surface_theme(surface_theme)
    atom_name = normalize_atom_theme(atom_theme or "cold_blue")

    surface = SURFACE_THEMES[surface_name].copy()
    atom = ATOM_THEMES[atom_name]
    is_dark = surface_name == "dark"

    surface.update(
        {
            "surfaceTheme": surface_name,
            "atomTheme": atom_name,
            "accent": atom["accent"],
            "accentStrong": atom["accentStrong"],
            "accentSoft": atom["accentSoftDark"] if is_dark else atom["accentSoftLight"],
            "accentSecondary": atom["accentSecondary"],
            "accentSecondarySoft": (
                atom["accentSecondarySoftDark"]
                if is_dark
                else atom["accentSecondarySoftLight"]
            ),
            "orbCore": atom["atomGlow"],
            "orbOuter": surface["cardBackgroundStrong"],
            "listeningGlow": atom["listeningGlow"],
            "thinkingGlow": atom["thinkingGlow"],
            "speakingGlow": atom["speakingGlow"],
            "executingGlow": atom["executingGlow"],
            "idleGlow": atom["idleGlow"],
            "atomOrbit": atom["atomOrbit"],
            "atomGlow": atom["atomGlow"],
            "atomGlowStrong": atom["atomGlowStrong"],
            "atomElectron": atom["electron"],
            "atomElectronAlt": atom["electronAlt"],
            "atomProton": atom["proton"],
            "atomNeutron": atom["neutron"],
            "atomCoreGlass": "#FFFFFF16" if is_dark else "#F7FBFFCC",
            "atomBackdrop": "#8FE9FF10" if atom_name == "cold_blue" else (
                "#A2FF4D12" if atom_name == "nuclear_waste" else "#F06A7512"
            ),
        }
    )
    return surface


def available_themes() -> list[str]:
    return list(SURFACE_THEMES.keys())


def available_atom_themes() -> list[str]:
    return list(ATOM_THEMES.keys())


def atom_theme_display_name(theme_name: str) -> str:
    return ATOM_THEMES[normalize_atom_theme(theme_name)]["displayName"]


def choose_font_family(preferred_families: list[str], fallback: str) -> str:
    families = {name.casefold(): name for name in QFontDatabase.families()}
    for preferred in preferred_families:
        if preferred.casefold() in families:
            return families[preferred.casefold()]
    return fallback
