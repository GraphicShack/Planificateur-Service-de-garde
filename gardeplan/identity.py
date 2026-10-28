"""Local educator colours, independent of group colours and seniority ranks."""
import colorsys

EDUCATOR_COLORS = (
    "#548B76", "#8C76AD", "#B98358", "#5C88B0", "#AD718D", "#889C52",
    "#4E929D", "#AF6964", "#6D7BAC", "#9B8B53", "#779487",
)


def next_educator_color(educators) -> str:
    used = {person.color.casefold() for person in educators}
    for color in EDUCATOR_COLORS:
        if color.casefold() not in used:
            return color
    # Extend the palette for larger teams rather than reusing the first colour.
    for index in range(4096):
        rgb = colorsys.hsv_to_rgb((index * .61803398875) % 1, .40 + (index % 3) * .07, .66 + (index % 4) * .04)
        color = "#" + "".join(f"{round(component * 255):02X}" for component in rgb)
        if color.casefold() not in used:
            return color
    raise ValueError("Choisissez une couleur pour cette éducatrice.")
