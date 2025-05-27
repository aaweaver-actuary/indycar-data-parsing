import pdfplumber
import re
import pandas as pd


class SectionTimesParser:
    """Parser for extracting section times from IndyCar section results PDFs."""

    def __init__(self, pdf_path: str, car_number: int):
        self._pdf_path = pdf_path
        self._car_number = car_number
        self._laps = []
        self._header = None
        self.is_in_car_section = False

    @property
    def pdf_path(self) -> str:
        """Returns the path to the PDF file."""
        return self._pdf_path

    @property
    def car_number(self) -> int:
        """Returns the car number for which section times are being parsed."""
        return self._car_number

    @property
    def laps(self) -> list[dict[str, str]]:
        """Returns the parsed lap and section times."""
        return self._laps

    @laps.setter
    def laps(self, value: list[dict[str, str]]) -> None:
        """Sets the parsed lap and section times."""
        self._laps = value

    @property
    def header(self) -> str:
        """Returns the header line of the section times."""
        return self._header

    @header.setter
    def header(self, value: str) -> None:
        """Sets the header line of the section times."""
        self._header = value

    @staticmethod
    def _is_header_line(line: str) -> bool:
        """Checks if a line is a header line based on its content."""
        return bool(re.match(r"Lap\s+T/S", line.strip()))

    @staticmethod
    def parse_column_names_from_header(header: str) -> list[str]:
        """Extracts column names from a header line."""
        return re.split(r"\s{1,}", header.strip())

    def get_car_section_header(self) -> str:
        """Generates the section header for the specified car number."""
        return f"Section Data for Car {self.car_number}"

    def is_end_of_current_car_section(self, text: str) -> bool:
        """Checks if the end of the current car section is reached."""
        return "Section Data for Car" in text and not self.is_in_car_section

    def create_lap_dict(
        self, col_names: list[str], lap_data: list[str]
    ) -> dict[str, str]:
        """Creates a dictionary for a lap entry with the specified column and value.

        Args:
            col_names (list[str]): The list of column names for the lap entry.
            lap_data (list[str]): The list of values for the lap entry.

        Returns:
            dict: A dictionary representing the lap entry.
        """
        return {f"{col}_time": val for col, val in zip(col_names, lap_data)}

    def update_lap_dict_with_speed_data(
        self, lap_dict: dict[str, str], speed_data: list[str]
    ) -> dict[str, str]:
        """Updates the lap dictionary with speed data.

        Args:
            lap_dict (dict[str, str]): The lap dictionary to update.
            speed_data (list[str]): The list of speed values to add to the lap dictionary.

        Returns:
            dict[str, str]: The updated lap dictionary with speed data.
        """
        for col, val in zip(list(lap_dict.keys()), speed_data):
            if col == "Lap":
                lap_dict[f"{col}_speed"] = None
            else:
                lap_dict[f"{col}_speed"] = val if val != "" else None
        return lap_dict

    def parse_section_times(self) -> pd.DataFrame:
        """Extracts lap and section times for a given car number from an IndyCar section results PDF.

        Returns:
            pd.DataFrame: A DataFrame containing the lap and section times for the specified car number.
        """
        laps = []

        with pdfplumber.open(self.pdf_path) as pdf:
            car_section_header = self.get_car_section_header()
            col_names = []
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue

                if car_section_header in text:
                    self.is_in_car_section = True
                elif self.is_end_of_current_car_section(text):
                    self.is_in_car_section = False
                    break

                if self.is_in_car_section:
                    lines = text.split("\n")
                    for i, line in enumerate(lines):
                        # Stop if a new car section header is found in the middle of the page
                        if (
                            "Section Data for Car" in line
                            and line.strip() != self.get_car_section_header()
                        ):
                            self.is_in_car_section = False
                            break

                        if self._is_header_line(line):
                            col_names = self.parse_column_names_from_header(line)
                            continue

                        elif re.match(r"^\d+\s+T\s", line):
                            lap_data = re.split(r"\s{1,}", line.strip())
                            if i + 1 < len(lines) and lines[i + 1].strip().startswith(
                                "S "
                            ):
                                speed_data = re.split(r"\s{1,}", lines[i + 1].strip())
                            else:
                                speed_data = []

                            lap_dict = self.create_lap_dict(col_names, lap_data)
                            lap_dict = self.update_lap_dict_with_speed_data(
                                lap_dict, speed_data
                            )

                            laps.append(lap_dict)

        df = pd.DataFrame(laps)
        if "Lap_time" in df.columns:
            df["Lap"] = df["Lap_time"]
            df = df.drop(columns=["Lap_time"], errors="ignore")
        return df
