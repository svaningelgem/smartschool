from smartschool import Results


def test_results_normal_flow(mocker):
    mocker.patch("smartschool.results.RESULTS_PER_PAGE", new=1)

    sut = list(Results())

    assert len(sut) == 1
    assert sut[0].name == "Repetitie hoofdstuk 1"
    assert sut[0].graphic.total_points == 18
    assert sut[0].graphic.achieved_points == 13.5
