"""kit.parts.template_name: NX's own blank template, or a site's model template."""

from __future__ import annotations

from types import SimpleNamespace as NS

import pytest

from nx_mcp.core.errors import NXError
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


def test_no_site_template_in_these_units_is_refused_before_nx():
    """Live BFH NX 2512: no inch template; NX's commit failed as NX_SAVE_FAILED."""
    builder = Builder(Template("template_mod_bfh.prt", units=1))
    with pytest.raises(NXError) as error:
        parts.template_name(TX, builder, "in")
    assert error.value.code == "NX_UNSUPPORTED_OPTION" and error.value.field == "/units"


def test_a_builder_without_template_list_keeps_nx_own_name():
    assert parts.template_name(TX, NS(), "mm") == parts.SCRATCH_TEMPLATE
