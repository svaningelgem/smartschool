import pytest

from smartschool import Results


@pytest.fixture()
def _setup_pages(requests_mock, mocker) -> None:
    mocker.patch("smartschool.results.RESULTS_PER_PAGE", new=1)

    requests_mock.get(
        "/results/api/v1/evaluations/?pageNumber=1&itemsOnPage=1",
        text="""[{
        "identifier": "49_10880_0_normal_769824",
        "type": "normal",
        "name": "Repetitie hoofdstuk 1",
        "graphic": {
            "type": "percentage",
            "color": "green",
            "value": 75,
            "description": "13,5/18"
        },
        "date": "2023-11-10T00:00:00+01:00",
        "gradebookOwner": {
            "id": "49_10844_0",
            "pictureHash": "initials_GS",
            "pictureUrl": "https://userpicture20.smartschool.be/User/Userimage/hashimage/hash/initials_GS/plain/1/res/128",
            "description": {
                "startingWithFirstName": "",
                "startingWithLastName": ""
            },
            "name": {
                "startingWithFirstName": "Gert Segers",
                "startingWithLastName": "Segers Gert"
            },
            "sort": "segers-gert"
        },
        "component": {
            "id": 7,
            "name": "dagelijks werk",
            "abbreviation": "DW"
        },
        "courses": [{
                "id": 1227,
                "name": "Geschiedenis",
                "graphic": {
                    "type": "icon",
                    "value": "knight2"
                },
                "teachers": [{
                        "id": "49_10844_0",
                        "pictureHash": "initials_GS",
                        "pictureUrl": "https://userpicture20.smartschool.be/User/Userimage/hashimage/hash/initials_GS/plain/1/res/128",
                        "description": {
                            "startingWithFirstName": "",
                            "startingWithLastName": ""
                        },
                        "name": {
                            "startingWithFirstName": "Gert Segers",
                            "startingWithLastName": "Segers Gert"
                        },
                        "sort": "segers-gert"
                    }
                ],
                "class": {
                    "identifier": "49_3467",
                    "id": 3467,
                    "platformId": 49,
                    "name": "3ENW",
                    "type": "K",
                    "icon": "briefcase"
                },
                "skoreClassId": 6104,
                "parentCourseId": null,
                "skoreWorkYear": {
                    "id": 32,
                    "dateRange": {
                        "start": "2023-09-01T00:00:00+02:00",
                        "end": "2024-08-31T00:00:00+02:00"
                    }
                }
            }
        ],
        "period": {
            "id": 4056,
            "name": "25 oktober - 19 december",
            "icon": "cal_purple_generic_week",
            "class": {
                "identifier": "49_3467",
                "id": 3467,
                "platformId": 49,
                "name": "3ENW",
                "type": "K",
                "icon": "briefcase"
            },
            "skoreWorkYear": {
                "id": 32,
                "dateRange": {
                    "start": "2023-09-01T00:00:00+02:00",
                    "end": "2024-08-31T00:00:00+02:00"
                }
            },
            "isActive": true
        },
        "feedback": [],
        "feedbacks": [],
        "availabilityDate": "2023-11-14T18:00:00+01:00",
        "isPublished": true,
        "doesCount": true
    }
]""",
    )
    requests_mock.get("/results/api/v1/evaluations/?pageNumber=2&itemsOnPage=1", text="[]")


@pytest.mark.usefixtures("_setup_pages")
def test_results_normal_flow():
    sut = list(Results())

    assert len(sut) == 1
    assert sut[0].name == "Repetitie hoofdstuk 1"
    assert sut[0].graphic.total_points == 18
    assert sut[0].graphic.achieved_points == 13.5
