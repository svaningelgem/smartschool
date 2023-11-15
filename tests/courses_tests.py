from smartschool import Courses, TopNavCourses


def test_topnav_courses_normal_flow(requests_mock):
    requests_mock.post(
        "https://site/Topnav/getCourseConfig",
        text=r"""{
    "courseFilters": [{
        "title": "Vakken",
        "type": "own"
    }
    ],
    "own": [{
        "name": "Aardrijkskunde_3_LOP_2023-2024",
        "descr": "",
        "icon": "earth",
        "url": "/?module=News\u0026file=coursenews\u0026courseID=3885\u0026ssID=49",
        "teacher": "Peeters Lotte"
    }, {
        "name": "bibliotheek",
        "descr": "Schoolbibliotheek_23-24",
        "icon": "books",
        "url": "/?module=News\u0026file=coursenews\u0026courseID=845\u0026ssID=49",
        "teacher": "Verbanck Annelies"
    }
    ],
    "courseManagementLink": null
}""",
    )

    x = list(TopNavCourses())

    assert x[0].name == "Aardrijkskunde_3_LOP_2023-2024"
    assert x[1].name == "bibliotheek"


def test_courses_normal_flow(requests_mock):
    requests_mock.get(
        "https://site/results/api/v1/courses/",
        text="""[{
        "id": 1173,
        "name": "Aardrijkskunde",
        "graphic": {
            "type": "icon",
            "value": "earth"
        },
        "teachers": [{
            "id": "49_9423_0",
            "pictureHash": "initials_LP",
            "pictureUrl": "https://userpicture20.smartschool.be/User/Userimage/hashimage/hash/initials_LP/plain/1/res/128",
            "description": {
                "startingWithFirstName": "",
                "startingWithLastName": ""
            },
            "name": {
                "startingWithFirstName": "Lotte Peeters",
                "startingWithLastName": "Peeters Lotte"
            },
            "sort": "peeters-lotte"
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
    }, {
        "id": 1179,
        "name": "Biologie",
        "graphic": {
            "type": "icon",
            "value": "tree"
        },
        "teachers": [{
            "id": "49_2825_0",
            "pictureHash": "initials_CV",
            "pictureUrl": "https://userpicture20.smartschool.be/User/Userimage/hashimage/hash/initials_CV/plain/1/res/128",
            "description": {
                "startingWithFirstName": "",
                "startingWithLastName": ""
            },
            "name": {
                "startingWithFirstName": "Carla Verhoelst",
                "startingWithLastName": "Verhoelst Carla"
            },
            "sort": "verhoelst-carla"
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
    ]""",
    )

    x = list(Courses())

    assert x[0].name == "Aardrijkskunde"
    assert x[1].name == "Biologie"
