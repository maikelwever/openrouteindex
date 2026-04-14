from jinja2 import Environment, PackageLoader, select_autoescape

templates = Environment(
    loader=PackageLoader("openrouteindex"),
    autoescape=select_autoescape(),
    trim_blocks=True,
    lstrip_blocks=True,
)
