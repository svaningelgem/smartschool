

from smartschool import Smartschool
from smartschool.reports import Reports


def test_reports_normal_flow(session: Smartschool):
    sut = list(Reports(session))

    assert len(sut) == 5

    result = sut[0]
    assert result.name == "Rapport 1"
    assert result.class_.name == "4CNW"
    assert result.download().startswith(b"%PDF-")
