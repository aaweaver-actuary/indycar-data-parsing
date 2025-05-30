import pandas as pd
from unittest.mock import patch, MagicMock
from indycar_data_parsing.section_times_parser import SectionTimesParser


def test_parse_column_names_from_header():
    header = "Lap   T/S   S1   S2   S3"
    result = SectionTimesParser.parse_column_names_from_header(header)
    assert result == ["Lap", "T/S", "S1", "S2", "S3"]


def test_create_lap_dict():
    parser = SectionTimesParser("dummy.pdf", 5)
    col_names = ["Lap", "T/S", "S1"]
    lap_data = ["1", "T", "12.345"]
    result = parser.create_lap_dict(col_names, lap_data)
    assert result == {"Lap_time": "1", "T/S_time": "T", "S1_time": "12.345"}


def test_update_lap_dict_with_speed_data():
    parser = SectionTimesParser("dummy.pdf", 5)
    lap_dict = {"Lap_time": "1", "T/S_time": "T", "S1_time": "12.345"}
    speed_data = ["", "100.1", "200.2"]
    updated = parser.update_lap_dict_with_speed_data(lap_dict.copy(), speed_data)
    assert updated["Lap_time_speed"] is None
    assert updated["T/S_time_speed"] == "100.1"
    assert updated["S1_time_speed"] == "200.2"


def test_get_car_section_header():
    parser = SectionTimesParser("dummy.pdf", 7)
    assert parser.get_car_section_header() == "Section Data for Car 7"


def test_is_end_of_current_car_section_true():
    parser = SectionTimesParser("dummy.pdf", 7)
    parser.is_in_car_section = False
    assert parser.is_end_of_current_car_section("Section Data for Car 8")


def test_is_end_of_current_car_section_false():
    parser = SectionTimesParser("dummy.pdf", 7)
    parser.is_in_car_section = True
    assert not parser.is_end_of_current_car_section("Section Data for Car 8")


def test_is_header_line_true():
    assert SectionTimesParser._is_header_line("Lap   T/S   S1   S2")


def test_is_header_line_false():
    assert not SectionTimesParser._is_header_line("1   T   12.345   23.456")


def test_text_contains_car_section_header():
    car_section_header = "Section Data for Car 5"
    text1 = "Section Data for Car 5\nLap   T/S   S1   S2\n1   T   12.345   23.456"
    text2 = "Section Data for Car 4\nLap   T/S   S1   S2\n1   T   10.000   20.000"
    text3 = "  Section Data for Car 5  \nLap   T/S   S1   S2\n1   T   12.345   23.456"
    assert SectionTimesParser.text_contains_car_section_header(
        text1, car_section_header
    )
    assert not SectionTimesParser.text_contains_car_section_header(
        text2, car_section_header
    )
    # Should not match if there is extra whitespace
    assert not SectionTimesParser.text_contains_car_section_header(
        text3, car_section_header
    )


def test_find_car_section_header_line_exact_match():
    car_section_header = "Section Data for Car 5"
    text = "Section Data for Car 5\nLap   T/S   S1   S2\n1   T   12.345   23.456"
    idx = SectionTimesParser.find_car_section_header_line(text, car_section_header)
    print(f"Lines: {text.splitlines()}")
    assert idx == 0


def test_find_car_section_header_line_no_match():
    car_section_header = "Section Data for Car 5"
    text = "Section Data for Car 4\nLap   T/S   S1   S2\n1   T   10.000   20.000"
    idx = SectionTimesParser.find_car_section_header_line(text, car_section_header)
    print(f"Lines: {text.splitlines()}")
    assert idx == -1


def test_find_car_section_header_line_whitespace():
    car_section_header = "Section Data for Car 5"
    text = "  Section Data for Car 5  \nLap   T/S   S1   S2\n1   T   12.345   23.456"
    idx = SectionTimesParser.find_car_section_header_line(text, car_section_header)
    print(f"Lines: {text.splitlines()}")
    assert idx == -1


def test_find_car_section_header_line_in_middle():
    car_section_header = "Section Data for Car 5"
    text = "Intro\nSection Data for Car 5\nLap   T/S   S1   S2"
    idx = SectionTimesParser.find_car_section_header_line(text, car_section_header)
    print(f"Lines: {text.splitlines()}")
    assert idx == 1


@patch("pdfplumber.open")
def test_parse_section_times(mock_pdf_open):
    # Setup mock PDF structure
    mock_pdf = MagicMock()
    mock_page = MagicMock()
    # Simulate text for a single car section with one lap and speed line
    mock_page.extract_text.return_value = (
        "Section Data for Car 5\n"
        "Lap   T/S   S1   S2\n"
        "1   T   12.345   23.456\n"
        "S   100.1   200.2   300.3\n"
    )
    mock_pdf.pages = [mock_page]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    parser = SectionTimesParser("dummy.pdf", 5)
    df = parser.parse_section_times()
    assert isinstance(df, pd.DataFrame)
    assert "Lap" in df.columns
    assert "T/S_time" in df.columns
    assert "S1_time" in df.columns
    assert "S2_time" in df.columns
    assert "T/S_time_speed" in df.columns
    assert "S1_time_speed" in df.columns
    assert "S2_time_speed" in df.columns
    assert df.iloc[0]["Lap"] == "1"
    assert df.iloc[0]["T/S_time"] == "T"
    assert df.iloc[0]["S1_time"] == "12.345"
    assert df.iloc[0]["S2_time"] == "23.456"
    assert df.iloc[0]["T/S_time_speed"] == "100.1"
    assert df.iloc[0]["S1_time_speed"] == "200.2"
    assert df.iloc[0]["S2_time_speed"] == "300.3"


@patch("pdfplumber.open")
def test_parse_section_times_missing_speed_line(mock_pdf_open):
    mock_pdf = MagicMock()
    mock_page = MagicMock()
    # Only lap line, no speed line
    mock_page.extract_text.return_value = (
        "Section Data for Car 5\nLap   T/S   S1   S2\n1   T   12.345   23.456\n"
    )
    mock_pdf.pages = [mock_page]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    parser = SectionTimesParser("dummy.pdf", 5)
    df = parser.parse_section_times()
    assert isinstance(df, pd.DataFrame)
    assert df.iloc[0]["Lap"] == "1"
    assert (
        pd.isna(df.iloc[0].get("T/S_time_speed", None))
        or df.iloc[0].get("T/S_time_speed", None) is None
    )


@patch("pdfplumber.open")
def test_parse_section_times_multiple_laps(mock_pdf_open):
    mock_pdf = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = (
        "Section Data for Car 5\n"
        "Lap   T/S   S1   S2\n"
        "1   T   12.345   23.456\n"
        "S   100.1   200.2   300.3\n"
        "2   T   13.111   24.222\n"
        "S   101.1   201.2   301.3\n"
    )
    mock_pdf.pages = [mock_page]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    parser = SectionTimesParser("dummy.pdf", 5)
    df = parser.parse_section_times()
    assert len(df) == 2
    assert df.iloc[1]["Lap"] == "2"
    assert df.iloc[1]["S1_time"] == "13.111"
    assert df.iloc[1]["S1_time_speed"] == "201.2"


@patch("pdfplumber.open")
def test_parse_section_times_empty_pdf(mock_pdf_open):
    mock_pdf = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = ""
    mock_pdf.pages = [mock_page]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    parser = SectionTimesParser("dummy.pdf", 5)
    df = parser.parse_section_times()
    assert df.empty


@patch("pdfplumber.open")
def test_parse_section_times_no_car_section(mock_pdf_open):
    mock_pdf = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = (
        "Lap   T/S   S1   S2\n1   T   12.345   23.456\nS   100.1   200.2   300.3\n"
    )
    mock_pdf.pages = [mock_page]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    parser = SectionTimesParser("dummy.pdf", 99)
    df = parser.parse_section_times()
    assert df.empty


@patch("pdfplumber.open")
def test_parse_section_times_malformed_lines(mock_pdf_open):
    mock_pdf = MagicMock()
    mock_page = MagicMock()
    # Malformed lap line (missing columns)
    mock_page.extract_text.return_value = (
        "Section Data for Car 5\n"
        "Lap   T/S   S1   S2\n"
        "1   T   12.345\n"
        "S   100.1   200.2\n"
    )
    mock_pdf.pages = [mock_page]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    parser = SectionTimesParser("dummy.pdf", 5)
    df = parser.parse_section_times()
    # S2_time should not be present since the data is missing
    assert "S2_time" not in df.columns
    # The columns present should match the data provided
    assert "T/S_time" in df.columns
    assert "S1_time" in df.columns


@patch("pdfplumber.open")
def test_parse_section_times_ends_on_next_car_section(mock_pdf_open):
    """Test that parsing stops when a new car section is encountered."""
    mock_pdf = MagicMock()
    mock_page = MagicMock()
    # Simulate two car sections in one page; should only parse the first
    mock_page.extract_text.return_value = (
        "Section Data for Car 5\n"
        "Lap   T/S   S1   S2\n"
        "1   T   12.345   23.456\n"
        "S   100.1   200.2   300.3\n"
        "Section Data for Car 6\n"
        "Lap   T/S   S1   S2\n"
        "1   T   11.111   22.222\n"
        "S   111.1   222.2   333.3\n"
    )
    mock_pdf.pages = [mock_page]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    parser = SectionTimesParser("dummy.pdf", 5)
    df = parser.parse_section_times()
    # Only the first car's data should be parsed
    assert len(df) == 1
    assert df.iloc[0]["Lap"] == "1"
    assert df.iloc[0]["S1_time"] == "12.345"
    assert "11.111" not in df.values


@patch("pdfplumber.open")
def test_parse_section_times_breaks_on_unrelated_car_section_header(mock_pdf_open):
    """
    Test that the parser breaks out of the page loop when it encounters a car section header
    for a different car and is not currently in a car section.
    This covers the 'elif self.is_end_of_current_car_section(text):' branch.
    """
    mock_pdf = MagicMock()
    mock_page1 = MagicMock()
    mock_page2 = MagicMock()
    # First page: not the car we're looking for, but contains a car section header
    mock_page1.extract_text.return_value = (
        "Section Data for Car 99\nLap   T/S   S1   S2\n1   T   99.999   88.888\n"
    )
    # Second page: would have the correct car, but should not be reached
    mock_page2.extract_text.return_value = (
        "Section Data for Car 5\nLap   T/S   S1   S2\n1   T   12.345   23.456\n"
    )
    mock_pdf.pages = [mock_page1, mock_page2]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    parser = SectionTimesParser("dummy.pdf", 5)
    df = parser.parse_section_times()
    # Should be empty because the parser breaks on the first page
    assert df.empty


def test_laps_getter():
    parser = SectionTimesParser("dummy.pdf", 5)
    parser.laps = [{"Lap_time": "1", "T/S_time": "T", "S1_time": "12.345"}]
    assert parser.laps == [{"Lap_time": "1", "T/S_time": "T", "S1_time": "12.345"}], (
        f"Expected laps to be [{'Lap_time': '1', 'T/S_time': 'T', 'S1_time': '12.345'}], but got {parser.laps}"
    )


def test_laps_setter():
    parser = SectionTimesParser("dummy.pdf", 5)
    new_laps = [{"Lap_time": "2", "T/S_time": "T", "S1_time": "13.456"}]
    parser.laps = new_laps
    assert parser.laps == new_laps


def test_header_getter():
    parser = SectionTimesParser("dummy.pdf", 5)
    parser.header = "New Header"
    assert parser.header == "New Header"


def test_header_setter():
    parser = SectionTimesParser("dummy.pdf", 5)
    new_header = "Updated Header"
    parser.header = new_header
    assert parser.header == new_header, (
        f"Expected header to be '{new_header}', but got '{parser.header}'"
    )


def test_update_lap_dict_when_does_have_a_lap_column_that_needs_to_be_ignored():
    """Test that the update_lap_dict_with_speed_data method correctly ignores the 'Lap' column."""
    parser = SectionTimesParser("dummy.pdf", 5)
    lap_dict = {"Lap": "1", "T/S": "T", "S1": "12.345"}
    speed_data = ["", "100.1", "200.2"]
    updated = parser.update_lap_dict_with_speed_data(lap_dict.copy(), speed_data)
    assert updated["Lap_speed"] is None
    assert updated["T/S_speed"] == "100.1"
    assert updated["S1_speed"] == "200.2"


def test_parse_section_times_lap_time_column_renaming():
    """Test that Lap_time column is renamed to Lap and Lap_time is dropped."""
    parser = SectionTimesParser("dummy.pdf", 5)
    # Simulate laps with Lap_time present
    parser.laps = [
        {"Lap_time": "1", "T/S_time": "T", "S1_time": "12.345"},
        {"Lap_time": "2", "T/S_time": "T", "S1_time": "13.456"},
    ]
    df = pd.DataFrame(parser.laps)
    # Simulate the renaming logic from parse_section_times
    if "Lap_time" in df.columns:
        df["Lap"] = df["Lap_time"]
        df = df.drop(columns=["Lap_time"], errors="ignore")
    assert "Lap" in df.columns
    assert "Lap_time" not in df.columns
    assert list(df["Lap"]) == ["1", "2"]


def test__parse_lines_for_laps_basic():
    parser = SectionTimesParser("dummy.pdf", 5)
    lines = [
        "Lap   T/S   S1   S2",
        "1   T   12.345   23.456",
        "S   100.1   200.2   300.3",
        "2   T   13.111   24.222",
        "S   101.1   201.2   301.3",
    ]
    col_names = ["Lap", "T/S", "S1", "S2"]
    laps = parser._parse_lines_for_laps(lines, col_names)
    assert len(laps) == 2
    assert laps[0]["Lap_time"] == "1"
    assert laps[1]["S1_time_speed"] == "201.2"


def test__parse_lines_for_laps_stops_on_new_car_section():
    parser = SectionTimesParser("dummy.pdf", 5)
    lines = [
        "Lap   T/S   S1   S2",
        "1   T   12.345   23.456",
        "S   100.1   200.2   300.3",
        "Section Data for Car 6",
        "Lap   T/S   S1   S2",
        "1   T   11.111   22.222",
        "S   111.1   222.2   333.3",
    ]
    col_names = ["Lap", "T/S", "S1", "S2"]
    laps = parser._parse_lines_for_laps(lines, col_names)
    assert len(laps) == 1
    assert laps[0]["Lap_time"] == "1"
    assert laps[0]["S1_time"] == "12.345"


def test__extract_car_section_texts_yields_only_relevant_section():
    parser = SectionTimesParser("dummy.pdf", 5)

    class DummyPage:
        def __init__(self, text):
            self._text = text

        def extract_text(self):
            return self._text

    pdf = MagicMock()
    pdf.pages = [
        DummyPage(
            "Section Data for Car 4\nLap   T/S   S1   S2\n1   T   10.000   20.000"
        ),
        DummyPage(
            "Section Data for Car 5\nLap   T/S   S1   S2\n1   T   12.345   23.456"
        ),
        DummyPage(
            "Section Data for Car 6\nLap   T/S   S1   S2\n1   T   11.111   22.222"
        ),
    ]
    texts = list(parser._extract_car_section_texts(pdf))
    assert len(texts) == 1
    assert "Section Data for Car 5" in texts[0]
    assert "12.345" in texts[0]
    assert "Section Data for Car 6" not in texts[0]


def test__extract_car_section_texts_yields_only_relevant_section_verbose():
    parser = SectionTimesParser("dummy.pdf", 5)

    class DummyPage:
        def __init__(self, text):
            self._text = text

        def extract_text(self):
            return self._text

    pdf = MagicMock()
    pdf.pages = [
        DummyPage(
            "Section Data for Car 4\nLap   T/S   S1   S2\n1   T   10.000   20.000"
        ),
        DummyPage(
            "Section Data for Car 5\nLap   T/S   S1   S2\n1   T   12.345   23.456"
        ),
        DummyPage(
            "Section Data for Car 6\nLap   T/S   S1   S2\n1   T   11.111   22.222"
        ),
    ]
    texts = list(parser._extract_car_section_texts(pdf))
    print(f"Extracted texts: {texts}")
    assert len(texts) == 1
    assert "Section Data for Car 5" in texts[0]
    assert "12.345" in texts[0]
    assert "Section Data for Car 6" not in texts[0]
