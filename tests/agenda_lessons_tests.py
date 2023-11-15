from smartschool.agenda import AgendaLessons


def test_agenda_lessons_normal_flow(requests_mock):
    requests_mock.post(
        "https://site/?module=Agenda&file=dispatcher",
        text="""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<server>
  <response>
    <status>ok</status>
    <actions>
      <action>
        <subsystem>agenda</subsystem>
        <command>handle lessons</command>
        <data>
          <content>
            <lessons>
              <lesson>
                <momentID>3728444</momentID>
                <lessonID>259</lessonID>
                <hourID>318</hourID>
                <date>2023-11-15</date>
                <subject>Verbuga: explication//Les prépositions devant un nom géographique: ex p104-107 (+canva)// Présenter un pays: explication</subject>
                <course>FR4</course>
                <courseTitle>FR4</courseTitle>
                <classroom>E.3.12</classroom>
                <classroomTitle>E.3.12</classroomTitle>
                <teacher>Ghysen H.</teacher>
                <teacherTitle>HG (Ghysen H.)</teacherTitle>
                <klassen>3ENW</klassen>
                <klassenTitle>3ENW</klassenTitle>
                <classIDs>3467</classIDs>
                <bothStartStatus>0</bothStartStatus>
                <assignmentEndStatus>0</assignmentEndStatus>
                <testDeadlineStatus>0</testDeadlineStatus>
                <noteStatus>-1</noteStatus>
                <note/>
                <date_listview>woensdag 15 november 2023</date_listview>
                <hour>1</hour>
                <activity>0</activity>
                <activityID/>
                <color>zilver</color>
                <hourValue>08:25 - 09:15</hourValue>
                <components_hidden>
                  <hiddencomponent/>
                </components_hidden>
                <freedayIcon>0</freedayIcon>
                <someSubjectsEmpty/>
              </lesson>
              <lesson>
                <momentID>3728468</momentID>
                <lessonID>265</lessonID>
                <hourID>320</hourID>
                <date>2023-11-15</date>
                <subject/>
                <course>WIS5</course>
                <courseTitle>WIS5</courseTitle>
                <classroom>E.3.12</classroom>
                <classroomTitle>E.3.12</classroomTitle>
                <teacher>Binnemans J.</teacher>
                <teacherTitle>JBI (Binnemans J.)</teacherTitle>
                <klassen>3ENW</klassen>
                <klassenTitle>3ENW</klassenTitle>
                <classIDs>3467</classIDs>
                <bothStartStatus>0</bothStartStatus>
                <assignmentEndStatus>0</assignmentEndStatus>
                <testDeadlineStatus>0</testDeadlineStatus>
                <noteStatus>-1</noteStatus>
                <note/>
                <date_listview>woensdag 15 november 2023</date_listview>
                <hour>2</hour>
                <activity>0</activity>
                <activityID/>
                <color>zilver</color>
                <hourValue>09:15 - 10:05</hourValue>
                <components_hidden>
                  <hiddencomponent/>
                </components_hidden>
                <freedayIcon>0</freedayIcon>
                <someSubjectsEmpty/>
              </lesson>
            </lessons>
            <title>
              <teacher>3ENW</teacher>
              <class/>
              <classroom/>
            </title>
            <freedays hideLessonInfo="0"/>
            <freedeadlines/>
            <freeNotes/>
            <deadlineRestrictions/>
          </content>
        </data>
      </action>
    </actions>
  </response>
</server>
""",
    )

    sut = AgendaLessons()

    x = list(sut)

    assert x[0].momentID == "3728444"
    assert x[1].momentID == "3728468"
