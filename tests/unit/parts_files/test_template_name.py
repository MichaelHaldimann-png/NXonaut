"""kit.parts.template_name: NX's own blank template, or a site's model template."""

from __future__ import annotations

from types import SimpleNamespace as NS

from nx_mcp.kit import parts

UNITS = NS(Millimeters=1, Inches=0)
TX = NS(nx=NS(PartUnits=UNITS))


class Template:
    def __init__(self, name, units=1, blank=False):
        self.name, self.units, self.blank, self.disposed = name, units, blank, False

    def GetName(self):
        return self.name

    def GetUnits(self):
        return self.units

    def IsBlank(self):
        return self.blank

    def Dispose(self):
        self.disposed = True


class Builder:
    def __init__(self, *templates):
        self.templates = list(templates)

    def GetTemplates(self):
        return self.templates


def test_nx_own_template_when_offered():
    builder = Builder(Template("template_mod_bfh.prt"), Template(parts.SCRATCH_TEMPLATE))
    assert parts.template_name(TX, builder) == parts.SCRATCH_TEMPLATE
    assert all(t.disposed for t in builder.templates)


def test_a_site_template_set_gives_its_model_template():
    builder = Builder(
        Template("template_dwg_bfh_DE.prt"),
        Template("template_ass_bfh.prt"),
        Template("Leer/ohne Vorlage", blank=True),
        Template("company_part.prt"),
        Template("template_mod_bfh.prt"),
    )
    assert parts.template_name(TX, builder) == "template_mod_bfh.prt"  # "mod" first


def test_units_must_match_else_nx_own_name():
    builder = Builder(Template("template_mod_bfh.prt", units=1))
    assert parts.template_name(TX, builder, "in") == parts.TEMPLATES["in"]


def test_a_builder_without_template_list_keeps_nx_own_name():
    assert parts.template_name(TX, NS(), "mm") == parts.SCRATCH_TEMPLATE
