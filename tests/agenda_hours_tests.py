import pytest

from smartschool.agenda import AgendaHours
from smartschool.objects import AgendaHour


def test_agenda_hours_normal_flow(requests_mock):
    requests_mock.post(
        "https://site/?module=Agenda&file=dispatcher",
        text="""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<server>
  <response>
    <status>ok</status>
    <actions>
      <action>
        <subsystem>grid</subsystem>
        <command>handle hours</command>
        <data>
          <content>
            <hours>
              <hour>
                <hourID>318</hourID>
                <start>08:25</start>
                <end>09:15</end>
                <title>1</title>
              </hour>
              <hour>
                <hourID>320</hourID>
                <start>09:15</start>
                <end>10:05</end>
                <title>2</title>
              </hour>
            </hours>
            <status>1</status>
          </content>
        </data>
      </action>
    </actions>
  </response>
</server>
""",
    )

    sut = AgendaHours()

    assert sut.search_by_hourId("318") == AgendaHour(hourID="318", start="08:25", end="09:15", title="1")
    assert sut.search_by_hourId("320") == AgendaHour(hourID="320", start="09:15", end="10:05", title="2")

    with pytest.raises(ValueError, match="Couldn't find 123456789"):
        sut.search_by_hourId("123456789")
