import pytest

from smartschool.agenda import AgendaMomentInfos


def test_agenda_moment_info_normal_flow():
    sut = list(AgendaMomentInfos("3732340"))

    assert len(sut) == 1
    assert sut[0].className == "AAR1 - Lotte Peeters - 223"
    assert len(sut[0].assignments) == 1
    assert sut[0].assignments[0].atdescription == "Toets"


def test_moment_info_fails_with_empty_moment():
    with pytest.raises(ValueError, match="Please provide a valid MomentID"):
        AgendaMomentInfos("        ")


def test_agenda_moment_info_no_assignments():
    sut = list(AgendaMomentInfos("3732340"))

    assert len(sut) == 1
    assert sut[0].className == "AAR1 - Lotte Peeters - 223"
    assert len(sut[0].assignments) == 0


def test_agenda_moment_info_multiple_assignments():
    sut = list(AgendaMomentInfos("3732340"))

    assert len(sut) == 1
    assert sut[0].className == "AAR1 - Lotte Peeters - 223"

    assert len(sut[0].assignments) == 2
    assert sut[0].assignments[0].description == "Toets 3. De koolstofcyclus in het systeem aarde pagina 42 - 47"
    assert sut[0].assignments[1].description == "123"
